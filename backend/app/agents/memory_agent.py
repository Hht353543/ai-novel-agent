"""Memory Agent：从章节提取人物状态增量、长期事实与关键事件。"""

import logging
from typing import Any

from app.agents.base import AgentError, BaseAgent
from app.agents.context import AgentContext
from app.agents.protocol import (
    CharacterStateDelta,
    CharacterSystem,
    MemoryFact,
    MemoryUpdate,
    NovelPlan,
    StateChange,
)
from app.agents.prompts import build_memory_prompt

logger = logging.getLogger(__name__)

SYSTEM_ROLE = (
    "你是一名小说设定管理员，负责从章节中提取人物状态变化、长期事实与关键事件。"
)

KNOWN_STATE_FIELDS = {
    "current_location",
    "current_faction",
    "current_identity",
    "cultivation",
    "plot_status",
    "possessions",
    "known_info",
    "relationships",
}


def _memory_query(ctx: AgentContext) -> str:
    return " ".join(
        part
        for part in [
            ctx.plan.title if ctx.plan else "",
            ctx.chapter_title,
            ctx.memory,
        ]
        if part
    )


def parse_memory_update(
    data: dict[str, Any],
    chapter_index: int,
) -> MemoryUpdate:
    """把模型返回的 dict 容错解析为 MemoryUpdate。"""
    deltas = []
    for item in data.get("state_deltas") or []:
        if not isinstance(item, dict):
            continue
        changes = [
            StateChange(**c)
            for c in (item.get("changes") or [])
            if isinstance(c, dict)
        ]
        deltas.append(
            CharacterStateDelta(
                character=str(item.get("character", "")),
                changes=changes,
            )
        )
    facts = []
    for item in data.get("facts") or []:
        if not isinstance(item, dict):
            continue
        content = str(item.get("content", "")).strip()
        if not content:
            continue
        fact = MemoryFact(
            category=str(item.get("category", "other")),
            content=content,
            importance=str(item.get("importance", "medium")),
            source_chapter=chapter_index,
        )
        fact.dedup_key = f"{fact.category}:{content}"
        facts.append(fact)
    events = [str(e) for e in (data.get("events") or []) if str(e).strip()]
    return MemoryUpdate(state_deltas=deltas, facts=facts, events=events)


def dedup_facts(update: MemoryUpdate, existing: list[MemoryFact]) -> MemoryUpdate:
    """按 dedup_key 去掉与已有记忆重复的事实。"""
    existing_keys = {f.dedup_key for f in existing if f.dedup_key}
    seen: set[str] = set()
    unique: list[MemoryFact] = []
    for fact in update.facts:
        if fact.dedup_key in existing_keys or fact.dedup_key in seen:
            continue
        seen.add(fact.dedup_key)
        unique.append(fact)
    update.facts = unique
    return update


class MemoryAgent(BaseAgent[MemoryUpdate]):
    """长期记忆 Agent：输出状态增量 + 事实 + 事件。"""

    name = "memory"
    role = "长期记忆 Agent"

    def validate_input(self, ctx: AgentContext) -> None:
        if not ctx.chapter_text.strip():
            raise AgentError(
                self.name,
                "validate_input",
                "validation",
                "章节正文为空，无法提取记忆",
                run_id=ctx.run_id,
            )

    def validate_output(self, ctx: AgentContext, update: MemoryUpdate) -> None:
        for delta in update.state_deltas:
            for change in delta.changes:
                if change.field not in KNOWN_STATE_FIELDS:
                    raise AgentError(
                        self.name,
                        "validate_output",
                        "validation",
                        f"未知人物状态字段: {change.field}",
                        run_id=ctx.run_id,
                    )

    async def _run(self, ctx: AgentContext) -> MemoryUpdate:
        if not self.llm.available:
            logger.warning("未配置 DEEPSEEK_API_KEY，Memory 返回空更新")
            return MemoryUpdate(events=["（演示事件）"])
        search = await self.call_tool(
            ctx, "search_knowledge", query=_memory_query(ctx)
        )
        if not search.success:
            raise AgentError(
                self.name, "_run", "rag", search.message, run_id=ctx.run_id
            )
        context = list(search.data.get("hits") or [])
        ctx.retrieved_context = context
        plan = ctx.plan or NovelPlan()
        prompt = build_memory_prompt(
            plan=plan,
            chapter_title=ctx.chapter_title,
            chapter_index=ctx.current_chapter,
            chapter_text=ctx.chapter_text,
            characters=CharacterSystem(
                profiles=ctx.characters,
                states=ctx.character_states,
                relationships=ctx.relationships,
            ),
            existing_facts=ctx.memory_facts,
        )
        data = await self._llm_json(ctx, prompt, SYSTEM_ROLE)
        update = parse_memory_update(data, ctx.current_chapter)
        update = dedup_facts(update, ctx.memory_facts)
        # 状态增量与长期事实通过工具落库，Agent 不直接改状态
        await self.call_tool(
            ctx,
            "update_character",
            deltas=[d.dict() for d in update.state_deltas],
        )
        await self.call_tool(
            ctx,
            "save_memory",
            facts=[f.dict() for f in update.facts],
        )
        return update
