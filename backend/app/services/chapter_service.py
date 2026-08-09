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

from openai import APIConnectionError, APIError, APITimeoutError

from app.llm.deepseek import DeepSeekClient
from app.prompts.chapter_prompt import SYSTEM_ROLE, build_chapter_prompt
from app.services.knowledge_compress import (
    default_categories,
    load_compressed_category_context,
)
from app.schemas.novel import ChapterGenerateRequest, ChapterGenerateResponse

logger = logging.getLogger(__name__)


class ChapterService:
    """章节正文生成编排服务。"""

    def __init__(self):
        self.llm = DeepSeekClient()

    async def generate(self, request: ChapterGenerateRequest) -> ChapterGenerateResponse:
        """生成 / 续写 / 重写章节正文。"""
        try:
            # 1. 按板块读取知识库参考小说原文（txt），长文自动摘要压缩
            context = await asyncio.to_thread(
                load_compressed_category_context,
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
                )

            # 正文生成是纯文本：不使用 JSON 输出模式，并使用正文作者角色
            raw = self.llm.generate(
                prompt,
                json_mode=False,
                system_prompt=SYSTEM_ROLE,
            )
            content = clean_chapter_output(raw)
            if not content:
                raise ValueError("DeepSeek 返回内容为空")
            return ChapterGenerateResponse(
                success=True,
                status="success",
                content=content,
                full_text=join_text(request.context_text, content),
            )
        except (APIConnectionError, APITimeoutError) as exc:
            logger.error("DeepSeek 连接失败: %s", exc)
            return ChapterGenerateResponse(
                success=False,
                status="error",
                message=f"无法连接到 DeepSeek API：{exc}",
            )
        except APIError as exc:
            logger.error("DeepSeek API 错误: %s", exc)
            return ChapterGenerateResponse(
                success=False,
                status="error",
                message=f"DeepSeek API 返回错误：{exc}",
            )
        except Exception as exc:  # noqa: BLE001 - 全部转为结构化响应
            logger.exception("章节生成异常")
            return ChapterGenerateResponse(
                success=False,
                status="error",
                message=f"章节生成失败：{exc}",
            )


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
