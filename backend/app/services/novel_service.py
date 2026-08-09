"""小说生成业务编排服务。

流程：接收需求 -> RAG 检索 -> 拼接 Prompt -> 调用 DeepSeek -> 返回结构化大纲。
"""

import logging
import traceback
import asyncio
from typing import Any

from openai import APIConnectionError, APIError, APITimeoutError

from app.llm.deepseek import DeepSeekClient
from app.prompts.novel_prompt import (
    build_novel_prompt,
    parse_total_words,
    plan_volumes,
)
from app.services.knowledge_compress import (
    default_categories,
    load_compressed_category_context,
)
from app.schemas.novel import (
    Character,
    NovelGenerateRequest,
    NovelGenerateResponse,
    NovelOutline,
    VolumePlan,
)

logger = logging.getLogger(__name__)


class NovelService:
    """业务编排层：串联 RAG、Prompt 与 DeepSeek。"""

    def __init__(self):
        self.llm = DeepSeekClient()

    async def generate(self, request: NovelGenerateRequest) -> NovelGenerateResponse:
        """生成小说大纲（异步接口，内部调用为同步实现）。"""
        try:
            # 1. 按板块读取知识库参考小说原文（txt），长文自动摘要压缩
            context = await asyncio.to_thread(
                load_compressed_category_context,
                default_categories(),
            )

            # 2. 拼接 Prompt
            prompt = build_novel_prompt(request, context)

            # 3. 调用 DeepSeek（失败时降级为演示大纲并给出明确提示）
            try:
                if not self.llm.available:
                    logger.warning("未配置 DEEPSEEK_API_KEY，返回本地示例大纲（演示模式）")
                    demo = ensure_volume_plan(demo_outline(), request.requirement)
                    return NovelGenerateResponse(
                        success=True,
                        status="demo",
                        message="未配置 DEEPSEEK_API_KEY，当前返回演示大纲。请在 backend/.env 中配置后重启后端。",
                        context=context,
                        outline=parse_outline(demo),
                        raw=demo,
                    )
                raw = self.llm.generate_json(prompt)
            except (APIConnectionError, APITimeoutError) as exc:
                logger.error("DeepSeek 连接失败: %s", exc)
                return NovelGenerateResponse(
                    success=True,
                    status="error",
                    message="无法连接到 DeepSeek API（网络不通或代理未配置）。请检查网络/代理后重试；当前已返回演示大纲。",
                    context=context,
                    outline=parse_outline(ensure_volume_plan(demo_outline(), request.requirement)),
                    raw=None,
                )
            except APIError as exc:
                logger.error("DeepSeek API 错误: %s", exc)
                return NovelGenerateResponse(
                    success=True,
                    status="error",
                    message=f"DeepSeek API 返回错误：{exc}",
                    context=context,
                    outline=parse_outline(ensure_volume_plan(demo_outline(), request.requirement)),
                    raw=None,
                )
            except ValueError as exc:
                # JSON 解析失败（含自动修复失败）：给用户可操作的提示
                logger.error("DeepSeek 输出解析失败: %s", exc)
                return NovelGenerateResponse(
                    success=True,
                    status="error",
                    message=(
                        "DeepSeek 返回内容无法解析为 JSON（可能因输出过长被截断）。"
                        "已尝试自动修复仍未成功；请重试，或在 backend/.env 中调大 "
                        "DEEPSEEK_MAX_TOKENS 后重启后端。当前已返回演示大纲。"
                    ),
                    context=context,
                    outline=parse_outline(ensure_volume_plan(demo_outline(), request.requirement)),
                    raw=None,
                )
            except Exception as exc:  # noqa: BLE001 - 模型层其它异常
                logger.error("调用 DeepSeek 时异常: %s", exc)
                return NovelGenerateResponse(
                    success=False,
                    status="error",
                    message=f"调用 DeepSeek 时发生错误：{exc}",
                    context=context,
                    outline=parse_outline(ensure_volume_plan(demo_outline(), request.requirement)),
                    raw=None,
                )
        except Exception as exc:
            # 任何其它异常（如模型加载失败）也返回结构化错误而不是 500
            logger.error("生成流程异常: %s\n%s", exc, traceback.format_exc())
            return NovelGenerateResponse(
                success=False,
                status="error",
                message=f"生成流程内部错误：{exc}",
                context=[],
                outline=parse_outline(ensure_volume_plan(demo_outline(), request.requirement)),
                raw=None,
            )

        # 4. 强制按字数规划生成完整章节目录（数量绝对正确）
        raw = ensure_volume_plan(raw, request.requirement)

        # 5. 解析为结构化大纲
        try:
            outline = parse_outline(raw)
        except Exception as exc:  # noqa: BLE001 - 结构转换失败不崩溃
            logger.error("大纲结构转换异常: %s", exc)
            return NovelGenerateResponse(
                success=False,
                status="error",
                message=f"大纲结构转换失败：{exc}",
                context=context,
                outline=parse_outline(ensure_volume_plan(demo_outline(), request.requirement)),
                raw=raw,
            )
        return NovelGenerateResponse(
            success=True,
            context=context,
            outline=outline,
            raw=raw,
        )


def parse_outline(raw: dict[str, Any]) -> NovelOutline:
    """将模型返回的 dict 转为 NovelOutline（容错处理）。"""
    characters = []
    for item in raw.get("characters") or []:
        if isinstance(item, dict):
            characters.append(
                Character(
                    name=str(item.get("name", "")),
                    role=str(item.get("role", "")),
                    description=str(item.get("description", "")),
                )
            )

    volumes = []
    for item in raw.get("volume_plan") or []:
        if isinstance(item, dict):
            volumes.append(
                VolumePlan(
                    volume=str(item.get("volume", "")),
                    chapters=[str(c) for c in (item.get("chapters") or [])],
                )
            )

    return NovelOutline(
        title=str(raw.get("title", "")),
        summary=str(raw.get("summary", "")),
        world=str(raw.get("world", "")),
        characters=characters,
        volume_plan=volumes,
    )


def demo_outline() -> dict[str, Any]:
    """无 API Key 时的演示大纲。

    以知识库样本《错练邪功，法天象地》（邪功反转、设定即笑点、无敌流）
    与《武侠：开局满级九阳神功》（满级开局、任务系统、捕快破案、江湖朝堂）
    为蓝本设计的「武侠 + 无敌流 + 系统流 + 极道流」预设大纲。
    """
    return {
        "title": "武侠：满级邪功，开局无敌",
        "summary": (
            "捕快沈惊堂穿越到邪功横行的大乾王朝，觉醒【武学熔炉】系统："
            "任何秘籍投入熔炉都能练成满级神功，别人照练则入魔。"
            "他以最底层的皂衣捕快身份，靠以命搏命的极道修炼与系统奖励，"
            "从县城小吏一路横推江湖与朝堂。"
        ),
        "world": (
            "大乾王朝，江湖与朝堂并存。天下邪功横行、正派功法式微，"
            "修炼邪功者轻则性情大变，重则沦为‘大药’被幕后种药人收割；"
            "官府捕快体系昌盛（皂衣→青衫→绣衣），门派、镖行、杀手组织林立。"
            "主角的武学熔炉可以‘邪功正练’，成为打破这套生态的唯一变数。"
        ),
        "characters": [
            {"name": "沈惊堂", "role": "主角", "description": "穿越者皂衣捕快，冷静缜密、杀伐果断；武学熔炉在手，邪功正练、开局满级"},
            {"name": "楚云萝", "role": "搭档", "description": "青衫女捕头，正直爽利，负责牵出大案主线"},
            {"name": "玄阴老祖", "role": "反派", "description": "幕后种药人，散播邪功收割江湖，与朝堂权贵勾结"},
            {"name": "老捕头", "role": "前辈", "description": "教主角江湖规矩与查案心法，后卷入惊龙会阴谋"},
        ],
        "volume_plan": [
            {"volume": "第一卷 邪功初成", "chapters": [
                "第一章 皂衣捕快", "第二章 武学熔炉", "第三章 邪功正练",
                "第四章 当街验功", "第五章 恶霸伏诛", "第六章 种药人现踪",
                "第七章 大案初起", "第八章 以命搏命",
            ]},
            {"volume": "第二卷 捕快扬名", "chapters": [
                "第九章 青衫之职", "第十章 邪功疑云", "第十一章 门派黑幕",
                "第十二章 熔炉升级", "第十三章 绣衣密令", "第十四章 惊龙会",
                "第十五章 朝堂暗线", "第十六章 双面神捕",
            ]},
            {"volume": "第三卷 横推江湖", "chapters": [
                "第十七章 传武天下", "第十八章 大药反噬", "第十九章 老祖出关",
                "第二十章 正邪之辩", "第二十一章 皇城博弈", "第二十二章 万侠法身",
                "第二十三章 剑指玄阴", "第二十四章 侠气永存",
            ]},
        ],
    }


def ensure_volume_plan(outline: dict[str, Any], requirement: str) -> dict[str, Any]:
    """按字数规划强制生成完整章节目录。

    模型只需要给出卷名（chapters 可为示例），这里会把每卷 chapters
    替换为「第一章～第N章」的编号目录，保证总章数与卷数严格符合规划。

    Args:
        outline: 模型返回的大纲 dict（或演示大纲）。
        requirement: 用户填写的字数规模。

    Returns:
        处理后的 outline dict（volume_plan 已重建）。
    """
    total_words = parse_total_words(requirement)
    total_chapters, per_volume = plan_volumes(total_words)
    model_volumes = outline.get("volume_plan") or []

    volumes = []
    start = 0
    for vi, count in enumerate(per_volume):
        vol_name = ""
        if vi < len(model_volumes) and isinstance(model_volumes[vi], dict):
            vol_name = str(model_volumes[vi].get("volume", "")).strip()
        if not vol_name:
            vol_name = f"第{vi + 1}卷"
        chapters = [f"第{n}章" for n in range(start + 1, start + count + 1)]
        start += count
        volumes.append({"volume": vol_name, "chapters": chapters})

    outline["volume_plan"] = volumes
    logger.info(
        "已按规划生成目录：%d 卷 / %d 章（总字数 %d）",
        len(volumes),
        total_chapters,
        total_words,
    )
    return outline
