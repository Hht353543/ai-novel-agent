"""Tool 层与权限矩阵测试。"""

import asyncio

import pytest

from app.agents.context import AgentContext
from app.agents.protocol import (
    CharacterState,
    CharacterStateDelta,
    MemoryFact,
    StateChange,
)
from app.llm.mock_provider import MockProvider
from app.tools.base import Permission, ToolRegistry
from app.tools.knowledge_tool import SearchKnowledgeTool
from app.tools.memory_tools import (
    GetCharacterTool,
    RetrieveMemoryTool,
    SaveMemoryTool,
    UpdateCharacterTool,
)
from app.tools.registry import (
    DEFAULT_AGENT_PERMISSIONS,
    create_default_tool_registry,
)
from agents_test_utils import FakeRetriever, sync_test


def _ctx():
    return AgentContext(
        run_id="run-tools",
        llm=MockProvider(),
        retriever=FakeRetriever(),
        memory="旧记忆",
        memory_facts=[
            MemoryFact(
                category="event",
                content="已有事实",
                importance="high",
                dedup_key="event:已有事实",
            )
        ],
        character_states=[CharacterState(name="沈惊澜", cultivation="炼体")],
    )


@sync_test
async def test_retrieve_memory_tool_reads_context():
    registry = create_default_tool_registry()
    ctx = _ctx()
    result = await registry.call("memory", "retrieve_memory", ctx)
    assert result.success is True
    assert result.data["memory"] == "旧记忆"
    assert len(result.data["facts"]) == 1


@sync_test
async def test_save_memory_tool_dedup():
    registry = create_default_tool_registry()
    ctx = _ctx()
    result = await registry.call(
        "memory",
        "save_memory",
        ctx,
        facts=[
            {
                "category": "event",
                "content": "已有事实",
                "importance": "high",
                "dedup_key": "event:已有事实",
            },
            {
                "category": "item",
                "content": "新玉佩",
                "importance": "medium",
                "dedup_key": "item:新玉佩",
            },
        ],
    )
    assert result.success is True
    assert result.data["added"] == 1
    assert len(ctx.memory_facts) == 2


@sync_test
async def test_update_character_tool_applies_delta():
    registry = create_default_tool_registry()
    ctx = _ctx()
    result = await registry.call(
        "memory",
        "update_character",
        ctx,
        deltas=[
            CharacterStateDelta(
                character="沈惊澜",
                changes=[
                    StateChange(
                        field="cultivation",
                        action="set",
                        old="炼体",
                        new="筑基",
                        reason="突破",
                    )
                ],
            )
        ],
    )
    assert result.success is True
    assert ctx.character_states[0].cultivation == "筑基"


@sync_test
async def test_permission_matrix_denies_writer_write():
    registry = create_default_tool_registry()
    ctx = _ctx()
    result = await registry.call(
        "writer", "save_memory", ctx, facts=[]
    )
    assert result.success is False
    assert result.error_type == "permission_denied"


@sync_test
async def test_unknown_tool_and_unknown_agent():
    registry = create_default_tool_registry()
    ctx = _ctx()
    unknown = await registry.call("memory", "no_such_tool", ctx)
    assert unknown.error_type == "unknown_tool"
    denied = await registry.call("ghost", "retrieve_memory", ctx)
    assert denied.error_type == "permission_denied"


def test_permission_scopes():
    assert Permission("memory:read").allows("memory:read")
    assert Permission("*").allows("anything")
    assert not Permission("memory:read").allows("memory:write")


def test_default_permissions_cover_all_agents():
    for agent in ("planner", "character", "writer", "reviewer", "memory", "timeline"):
        assert agent in DEFAULT_AGENT_PERMISSIONS
        assert DEFAULT_AGENT_PERMISSIONS[agent]
