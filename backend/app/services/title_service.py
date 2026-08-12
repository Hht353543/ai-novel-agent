"""章节标题生成业务服务。

两种模式：
- volume：按卷生成该卷前 10 章的具体标题（分批生成，避免一次输出过长）；
- chapter：根据已写正文重新生成当前章节标题。
"""

import logging

from app.llm.call import LLMError, run_llm
from app.llm.deepseek_provider import DeepSeekProvider
from app.llm.provider import BaseLLM
from app.prompts.title_prompt import (
    SYSTEM_ROLE,
    build_chapter_title_prompt,
    build_volume_titles_prompt,
)
from app.services.errors import (
    llm_error_response,
    unexpected_error_response,
)
from app.schemas.novel import TitlesGenerateRequest, TitlesGenerateResponse

logger = logging.getLogger(__name__)


class TitleService:
    """章节标题生成编排服务。"""

    def __init__(self, llm: BaseLLM | None = None):
        self.llm = llm or DeepSeekProvider()

    async def generate(self, request: TitlesGenerateRequest) -> TitlesGenerateResponse:
        """生成章节标题（volume=按卷前10章 / chapter=根据正文单章）。"""
        try:
            if request.mode == "chapter":
                prompt = build_chapter_title_prompt(request)
            else:
                prompt = build_volume_titles_prompt(request)

            if not self.llm.available:
                logger.warning("未配置 DEEPSEEK_API_KEY，返回演示标题")
                titles = demo_titles(request)
                return TitlesGenerateResponse(
                    success=True,
                    status="demo",
                    message="未配置 DEEPSEEK_API_KEY，当前返回演示标题。",
                    titles=titles,
                )

            # 兼容顶层数组 / {"titles": [...]} / {"title": "..."} 三种输出
            titles = await run_llm(
                self.llm.generate_json_array,
                prompt,
                system_prompt=SYSTEM_ROLE,
            )
            if not titles:
                raise ValueError("DeepSeek 返回的标题为空")
            return TitlesGenerateResponse(
                success=True,
                status="success",
                titles=titles,
            )
        except LLMError as exc:
            return llm_error_response(
                TitlesGenerateResponse,
                logger,
                exc,
                "标题生成",
            )
        except Exception as exc:  # noqa: BLE001 - 全部转为结构化响应
            return unexpected_error_response(
                TitlesGenerateResponse,
                logger,
                exc,
                "标题生成",
            )


def demo_titles(request: TitlesGenerateRequest) -> list[str]:
    """无 API Key 时的演示标题。"""
    if request.mode == "chapter":
        return ["风雨夜，刀出鞘"]
    return [
        "开局满级，龙象镇山河",
        "第一案：当街杀人者",
        "验尸房里的破绽",
        "恶霸背后还有人",
        "夜探福寿坊",
        "金丝绕指，杀机暗藏",
        "公堂之上，无人敢认",
        "以命搏命，破限一拳",
        "惊龙会浮出水面",
        "第一卷末：刀指绣衣",
    ]
