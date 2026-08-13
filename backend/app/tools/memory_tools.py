"""记忆相关工具：检索/保存记忆与角色状态。"""

from __future__ import annotations

from typing import Any

from app.agents.context import AgentContext
from app.agents.protocol import (
    CharacterState,
    CharacterStateDelta,
    MemoryFact,
)
from app.agents.state_engine import apply_character_state_deltas
from app.tools.base import AgentTool, ToolResult


class RetrieveMemoryTool(AgentTool):
    """检索当前工作记忆与长期事实（只读）。"""

    name = "retrieve_memory"
    description = "读取章节滚动记忆、长期事实与关键事件。"
    required_scope = "memory:read"

    async def execute(self, ctx: AgentContext, **kwargs: Any) -> ToolResult:
        return ToolResult(
            success=True,
            tool=self.name,
            action="retrieve",
            data={
                "memory": ctx.memory,
                "facts": [f.dict() for f in ctx.memory_facts],
                "events": list(ctx.memory_events),
            },
        )


class SaveMemoryTool(AgentTool):
    """保存长期事实（去重 + 重要性排序，写权限）。"""

    name = "save_memory"
    description = "把新事实合并进长期记忆，按 dedup_key 去重。"
    required_scope = "memory:write"

    async def execute(self, ctx: AgentContext, **kwargs: Any) -> ToolResult:
        facts = kwargs.get("facts") or []
        existing_keys = {f.dedup_key for f in ctx.memory_facts if f.dedup_key}
        added = 0
        for item in facts:
            fact = item if isinstance(item, MemoryFact) else MemoryFact(**item)
            if fact.dedup_key and fact.dedup_key in existing_keys:
                continue
            ctx.memory_facts.append(fact)
            existing_keys.add(fact.dedup_key)
            added += 1
        importance = {"high": 0, "medium": 1, "low": 2}
        ctx.memory_facts = sorted(
            ctx.memory_facts,
            key=lambda f: importance.get(f.importance, 1),
        )
        return ToolResult(
            success=True,
            tool=self.name,
            action="save",
            data={"added": added, "total": len(ctx.memory_facts)},
        )


class GetCharacterTool(AgentTool):
    """读取角色档案与当前状态（只读）。"""

    name = "get_character"
    description = "读取角色档案、当前状态与关系网。"
    required_scope = "character:read"

    async def execute(self, ctx: AgentContext, **kwargs: Any) -> ToolResult:
        return ToolResult(
            success=True,
            tool=self.name,
            action="get",
            data={
                "profiles": [p.dict() for p in ctx.characters],
                "states": [s.dict() for s in ctx.character_states],
                "relationships": [r.dict() for r in ctx.relationships],
            },
        )


class UpdateCharacterTool(AgentTool):
    """按状态增量更新角色（写权限，规则由 state_engine 保证）。"""

    name = "update_character"
    description = "应用 CharacterStateDelta 更新角色当前状态。"
    required_scope = "character:write"

    async def execute(self, ctx: AgentContext, **kwargs: Any) -> ToolResult:
        deltas = kwargs.get("deltas") or []
        parsed: list[CharacterStateDelta] = []
        for item in deltas:
            if isinstance(item, CharacterStateDelta):
                parsed.append(item)
            elif isinstance(item, dict):
                parsed.append(CharacterStateDelta(**item))
        ctx.character_states = apply_character_state_deltas(
            ctx.character_states, parsed
        )
        return ToolResult(
            success=True,
            tool=self.name,
            action="update",
            data={
                "applied": len(parsed),
                "states": [s.dict() for s in ctx.character_states],
            },
        )


__all__ = [
    "RetrieveMemoryTool",
    "SaveMemoryTool",
    "GetCharacterTool",
    "UpdateCharacterTool",
]
