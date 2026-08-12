"""角色卡生成业务服务。

输入：大纲 + 卷索引；输出：该卷主要人物的角色卡列表。
角色卡可由用户继续编辑，并随项目保存。
"""

import logging

from app.llm.call import LLMError, run_llm
from app.llm.deepseek_provider import DeepSeekProvider
from app.llm.provider import BaseLLM
from app.prompts.character_card_prompt import (
    SYSTEM_ROLE,
    build_character_card_prompt,
)
from app.services.errors import (
    llm_error_response,
    unexpected_error_response,
)
from app.schemas.character import CharacterCard
from app.schemas.novel import (
    CharacterCardsGenerateRequest,
    CharacterCardsGenerateResponse,
)

logger = logging.getLogger(__name__)


class CharacterCardService:
    """角色卡生成编排服务。"""

    def __init__(self, llm: BaseLLM | None = None):
        self.llm = llm or DeepSeekProvider()

    async def generate(
        self, request: CharacterCardsGenerateRequest
    ) -> CharacterCardsGenerateResponse:
        """生成指定卷的角色卡。"""
        prompt = build_character_card_prompt(request)
        try:
            if not self.llm.available:
                logger.warning("未配置 DEEPSEEK_API_KEY，返回演示角色卡")
                return CharacterCardsGenerateResponse(
                    success=True,
                    status="demo",
                    message="未配置 DEEPSEEK_API_KEY，当前返回演示角色卡。",
                    character_cards=demo_cards(request.volume_index),
                )
            data = await run_llm(
                self.llm.generate_json,
                prompt,
                system_prompt=SYSTEM_ROLE,
            )
            cards = [
                CharacterCard(**item)
                for item in (data.get("character_cards") or [])
                if isinstance(item, dict)
            ]
            if not cards:
                raise ValueError("DeepSeek 返回的角色卡为空")
            return CharacterCardsGenerateResponse(
                success=True,
                status="success",
                character_cards=cards,
            )
        except LLMError as exc:
            return llm_error_response(
                CharacterCardsGenerateResponse,
                logger,
                exc,
                "角色卡生成",
            )
        except Exception as exc:  # noqa: BLE001 - 全部转为结构化响应
            return unexpected_error_response(
                CharacterCardsGenerateResponse,
                logger,
                exc,
                "角色卡生成",
            )


def demo_cards(volume_index: int) -> list[CharacterCard]:
    """无 API Key 时的演示角色卡。"""
    return [
        CharacterCard(
            volume_index=volume_index,
            name="沈惊堂",
            role="主角",
            age="十八岁",
            appearance="身形清瘦，眉眼锐利，常年皂衣，腰间挂一柄朴刀",
            personality="冷静缜密、杀伐果断，话少但每句都切中要害",
            background="穿越者，前世从事追索真相的职业，今生为县城最底层捕快",
            goals="查清惊龙会阴谋，让江湖与朝堂都按规矩运转",
            speech_style="短句，常用反问，'你的事，发了'",
            notes="本卷从皂衣捕快成长为青衫捕头",
        ),
        CharacterCard(
            volume_index=volume_index,
            name="楚云萝",
            role="搭档",
            age="二十岁",
            appearance="高挑女捕头，束发佩剑，左眉一道细疤",
            personality="正直爽利，嫉恶如仇，嘴硬心软",
            background="青衫捕头，父亲是上一代名捕，旧案未雪",
            goals="查清父亲旧案，与主角并肩办案",
            speech_style="语速快，爱用'姑奶奶'自称",
            notes="本卷与主角从互不信任到默契搭档",
        ),
        CharacterCard(
            volume_index=volume_index,
            name="玄阴老祖",
            role="反派",
            age="面相五十，实际百岁开外",
            appearance="鹤发童颜，常披黑氅，指尖缠一根乌金丝",
            personality="笑里藏刀，视江湖人为可收割的大药",
            background="种药人组织幕后首脑，与朝堂权贵勾结",
            goals="以邪功收割天下高手，完成血祭突破",
            speech_style="慢条斯理，爱称人为'好材料'",
            notes="本卷末现真身，留下惊龙会线索",
        ),
        CharacterCard(
            volume_index=volume_index,
            name="老捕头",
            role="前辈",
            age="六十余岁",
            appearance="头发花白，背微驼，烟杆不离手",
            personality="圆滑世故，但骨子里守着捕快的底线",
            background="干了一辈子公差，见过太多官匪勾结",
            goals="把主角带成能独当一面的捕头",
            speech_style="慢悠悠，爱说'规矩是死的，人是活的'",
            notes="知道惊龙会的一些旧事，本卷中段遭暗算",
        ),
    ]
