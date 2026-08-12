"""章节正文生成业务编排服务。

流程：接收章节请求 -> RAG 检索（人物/世界观/文风） -> 拼接正文 Prompt
      -> 调用 DeepSeek -> 返回新生成文本（含拼接后的完整文本）。

支持三种模式：
- generate：首次生成；
- continue：以编辑后全文为上文，从末尾续写；
- rewrite：以修改处之前的内容为上文，重新生成其后内容。
"""

import logging
import re
import asyncio
from typing import AsyncIterator

from app.config import settings
from app.llm.call import LLMError, run_llm
from app.llm.deepseek_provider import DeepSeekProvider
from app.llm.provider import BaseLLM
from app.rag.retriever import get_retriever
from app.prompts.chapter_prompt import SYSTEM_ROLE, build_chapter_prompt
from app.services.errors import (
    llm_error_response,
    unexpected_error_response,
)
from app.services.memory_service import update_memory
from app.services.knowledge_compress import (
    default_categories,
)
from app.schemas.novel import ChapterGenerateRequest, ChapterGenerateResponse

logger = logging.getLogger(__name__)

# RAG 检索器（进程级单例；默认 budget，可用 RAG_RETRIEVER=keyword 切换）
_retriever = get_retriever()


def _chapter_retrieval_query(request: ChapterGenerateRequest) -> str:
    """把章节生成请求转换为知识库检索查询文本。"""
    return " ".join(
        part
        for part in [
            request.outline.title,
            request.outline.summary,
            request.chapter_title,
            request.extra_requirements,
        ]
        if part
    )


class ChapterService:
    """章节正文生成编排服务。"""

    def __init__(self, llm: BaseLLM | None = None):
        self.llm = llm or DeepSeekProvider()

    async def generate(self, request: ChapterGenerateRequest) -> ChapterGenerateResponse:
        """生成 / 续写 / 重写章节正文。"""
        try:
            # 1. 按板块读取知识库参考小说原文（txt），长文自动摘要压缩
            context = await asyncio.to_thread(
                _retriever.retrieve,
                _chapter_retrieval_query(request),
                default_categories(),
            )
            prompt = build_chapter_prompt(request, context)

            if not self.llm.available:
                logger.warning("未配置 DEEPSEEK_API_KEY，返回演示正文")
                content = demo_chapter(request)
                return ChapterGenerateResponse(
                    success=True,
                    status="demo",
                    message="未配置 DEEPSEEK_API_KEY，当前返回演示正文。",
                    content=content,
                    full_text=request.context_text.rstrip() + "\n\n" + content,
                    memory=request.memory,
                )

            # 正文生成是纯文本：不使用 JSON 输出模式，并使用正文作者角色
            raw = await run_llm(
                self.llm.generate,
                prompt,
                json_mode=False,
                system_prompt=SYSTEM_ROLE,
            )
            content = clean_chapter_output(raw)
            if not content:
                raise ValueError("DeepSeek 返回内容为空")
            memory = request.memory
            if settings.memory_enabled:
                memory = await update_memory(
                    self.llm,
                    request.memory,
                    request.outline,
                    request.chapter_title or f"第{request.chapter_index + 1}章",
                    content,
                )
            return ChapterGenerateResponse(
                success=True,
                status="success",
                content=content,
                full_text=join_text(request.context_text, content),
                memory=memory,
            )
        except LLMError as exc:
            return llm_error_response(
                ChapterGenerateResponse,
                logger,
                exc,
                "章节生成",
            )
        except Exception as exc:  # noqa: BLE001 - 全部转为结构化响应
            return unexpected_error_response(
                ChapterGenerateResponse,
                logger,
                exc,
                "章节生成",
            )

    async def generate_stream(
        self,
        request: ChapterGenerateRequest,
    ) -> AsyncIterator[dict]:
        """流式生成章节正文：产出 SSE 事件 dict。

        事件类型：
        - {"type": "meta", "status": "demo" | "error", "message": ...}
        - {"type": "delta", "text": ...}
        - {"type": "meta", "status": "success", "content_len": N}
        """
        try:
            context = await asyncio.to_thread(
                _retriever.retrieve,
                _chapter_retrieval_query(request),
                default_categories(),
            )
            prompt = build_chapter_prompt(request, context)
        except Exception as exc:  # noqa: BLE001 - 流式错误也结构化返回
            yield {
                "type": "meta",
                "status": "error",
                "message": f"知识库加载失败：{exc}",
            }
            return

        if not self.llm.available:
            content = demo_chapter(request)
            yield {
                "type": "meta",
                "status": "demo",
                "message": "未配置 DEEPSEEK_API_KEY，当前返回演示正文。",
                "memory": request.memory,
            }
            yield {"type": "delta", "text": content}
            return

        queue: asyncio.Queue = asyncio.Queue()

        def producer() -> None:
            try:
                for piece in self.llm.generate_stream(
                    prompt,
                    json_mode=False,
                    system_prompt=SYSTEM_ROLE,
                ):
                    queue.put_nowait(("delta", piece))
            except Exception as exc:  # noqa: BLE001 - 统一转为流式错误事件
                queue.put_nowait(("error", str(exc)))
            finally:
                queue.put_nowait(("done", None))

        task = asyncio.create_task(asyncio.to_thread(producer))
        parts: list[str] = []
        try:
            while True:
                kind, value = await queue.get()
                if kind == "done":
                    break
                if kind == "error":
                    yield {
                        "type": "meta",
                        "status": "error",
                        "message": f"流式生成失败：{value}",
                    }
                    return
                parts.append(value)
                yield {"type": "delta", "text": value}

            content = clean_chapter_output("".join(parts))
            if not content:
                yield {
                    "type": "meta",
                    "status": "error",
                    "message": "DeepSeek 返回内容为空",
                }
                return
            memory = request.memory
            if settings.memory_enabled:
                memory = await update_memory(
                    self.llm,
                    request.memory,
                    request.outline,
                    request.chapter_title or f"第{request.chapter_index + 1}章",
                    content,
                )
            yield {
                "type": "meta",
                "status": "success",
                "content_len": len(content),
                "memory": memory,
            }
        finally:
            if not task.done():
                task.cancel()


def clean_chapter_output(raw: str) -> str:
    """清理模型输出：剥离代码围栏与多余的 Markdown 标题。"""
    text = raw.strip()
    # 去掉 ```markdown / ``` 围栏
    text = re.sub(r"^```(?:markdown|text|plain)?\s*", "", text, flags=re.I)
    text = re.sub(r"\s*```$", "", text)
    # 去掉开头孤立的 Markdown 标题行（如 # 第一章 xxx）
    lines = text.split("\n")
    while lines and re.match(r"^#{1,6}\s+\S", lines[0].strip()):
        lines.pop(0)
    return "\n".join(lines).strip()


def join_text(context_text: str, content: str) -> str:
    """把上文与新生成文本拼接成完整文本。"""
    base = context_text.rstrip()
    if not base:
        return content
    return base + "\n\n" + content


def demo_chapter(request: ChapterGenerateRequest) -> str:
    """无 API Key 时的演示正文。"""
    title = request.chapter_title or f"第{request.chapter_index + 1}章"
    return (
        f"（演示正文）{title}。\n\n"
        "夜色如墨，檐角风灯忽明忽暗。主角立在长街尽头，握紧手中的刀，"
        "他知道，这一夜过后，江湖上再没有人敢小看他。\n\n"
        "远处传来更鼓声，他缓缓迈出第一步——故事，才刚刚开始。"
    )
