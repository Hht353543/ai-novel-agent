"""默认工具注册表与 Agent 权限矩阵。"""

from __future__ import annotations

from app.tools.base import Permission, ToolRegistry
from app.tools.knowledge_tool import SearchKnowledgeTool
from app.tools.memory_tools import (
    GetCharacterTool,
    RetrieveMemoryTool,
    SaveMemoryTool,
    UpdateCharacterTool,
)


DEFAULT_AGENT_PERMISSIONS: dict[str, list[Permission]] = {
    "planner": [Permission("knowledge:read")],
    "character": [
        Permission("knowledge:read"),
        Permission("character:read"),
        Permission("character:write"),
    ],
    "writer": [
        Permission("knowledge:read"),
        Permission("character:read"),
        Permission("memory:read"),
    ],
    "reviewer": [
        Permission("knowledge:read"),
        Permission("character:read"),
        Permission("memory:read"),
    ],
    "memory": [
        Permission("knowledge:read"),
        Permission("character:read"),
        Permission("character:write"),
        Permission("memory:read"),
        Permission("memory:write"),
    ],
    "timeline": [
        Permission("knowledge:read"),
        Permission("character:read"),
        Permission("memory:read"),
    ],
}


def create_default_tool_registry() -> ToolRegistry:
    """创建默认工具集（进程级实例由 orchestrator 持有）。"""

    registry = ToolRegistry(permissions=DEFAULT_AGENT_PERMISSIONS)
    registry.register(SearchKnowledgeTool())
    registry.register(RetrieveMemoryTool())
    registry.register(SaveMemoryTool())
    registry.register(GetCharacterTool())
    registry.register(UpdateCharacterTool())
    return registry


__all__ = ["DEFAULT_AGENT_PERMISSIONS", "create_default_tool_registry"]
