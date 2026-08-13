"""Agent Tool 层：资源访问统一走工具，按权限矩阵校验。"""

from app.tools.base import (
    AgentTool,
    Permission,
    ToolError,
    ToolRegistry,
    ToolResult,
)
from app.tools.registry import (
    DEFAULT_AGENT_PERMISSIONS,
    create_default_tool_registry,
)

__all__ = [
    "AgentTool",
    "Permission",
    "ToolError",
    "ToolRegistry",
    "ToolResult",
    "DEFAULT_AGENT_PERMISSIONS",
    "create_default_tool_registry",
]
