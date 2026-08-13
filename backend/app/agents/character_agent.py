"""Character Agent：根据小说规划建立人物系统（档案 + 状态 + 关系）。"""

import logging
from typing import Any

from app.agents.base import AgentError, BaseAgent
from app.agents.context import AgentContext
from app.agents.protocol import (
    CharacterProfile,
    CharacterRelation,
    CharacterState,
    CharacterSystem,
    NovelPlan,
)
from app.agents.prompts import build_character_prompt
from app.services.character_card_service import demo_cards

logger = logging.getLogger(__name__)

SYSTEM_ROLE = (
    "你是一名资深小说人物设计师，擅长建立人物系统、关系网与可推进的人物状态。"
)


def _character_query(plan: NovelPlan) -> str:
    return " ".join(
        part
        for part in [
            plan.title,
            plan.genre,
            plan.main_plot.premise,
            plan.main_plot.main_goal,
        ]
        if part
    )


def parse_character_system(data: dict[str, Any]) -> CharacterSystem:
    """把模型返回的 dict 容错解析为 CharacterSystem。"""
    profiles = [
        CharacterProfile(**item)
        for item in (data.get("profiles") or data.get("characters") or [])
        if isinstance(item, dict)
    ]
    states = [
        CharacterState(**item)
        for item in (data.get("states") or [])
        if isinstance(item, dict)
    ]
    relationships = [
        CharacterRelation(**item)
        for item in (data.get("relationships") or [])
        if isinstance(item, dict)
    ]
    # 补全：每个档案至少对应一个初始状态
    existing = {s.name for s in states}
    for profile in profiles:
        if profile.name and profile.name not in existing:
            states.append(CharacterState(name=profile.name, plot_status="初始状态"))
    return CharacterSystem(
        profiles=profiles,
        states=states,
        relationships=relationships,
    )


def demo_system(plan: NovelPlan | None) -> CharacterSystem:
    """无 API Key 时的演示人物系统（基于现有 demo_cards）。"""
    profiles = []
    states = []
    relationships = []
    for card in demo_cards(0):
        profiles.append(
            CharacterProfile(
                name=card.name,
                role=card.role,
                age=card.age,
                appearance=card.appearance,
                personality=card.personality,
                background=card.background,
                goals=card.goals,
                motivation=card.goals,
                speech_style=card.speech_style,
                growth_arc=card.notes,
            )
        )
        states.append(CharacterState(name=card.name, plot_status="登场，剧情初始状态"))
    del plan  # 演示数据与规划无关
    return CharacterSystem(
        profiles=profiles,
        states=states,
        relationships=relationships,
    )


class CharacterAgent(BaseAgent[CharacterSystem]):
    """人物设计 Agent：输出结构化人物系统。"""

    name = "character"
    role = "人物设计 Agent"

    def validate_input(self, ctx: AgentContext) -> None:
        if ctx.plan is None:
            raise AgentError(
                self.name,
                "validate_input",
                "validation",
                "缺少小说规划",
                run_id=ctx.run_id,
            )

    def validate_output(self, ctx: AgentContext, system: CharacterSystem) -> None:
        if not system.profiles:
            raise AgentError(
                self.name,
                "validate_output",
                "validation",
                "人物系统为空",
                run_id=ctx.run_id,
            )

    async def _run(self, ctx: AgentContext) -> CharacterSystem:
        if ctx.plan is None:
            raise AgentError(
                self.name,
                "_run",
                "validation",
                "缺少小说规划",
                run_id=ctx.run_id,
            )
        plan = ctx.plan
        if not self.llm.available:
            logger.warning("未配置 DEEPSEEK_API_KEY，Character 返回演示人物系统")
            return demo_system(plan)
        context = await self._retrieve(ctx, _character_query(plan))
        ctx.retrieved_context = context
        prompt = build_character_prompt(plan, context)
        data = await self._llm_json(ctx, prompt, SYSTEM_ROLE)
        return parse_character_system(data)
