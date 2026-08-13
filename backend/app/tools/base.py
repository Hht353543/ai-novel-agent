"""工具抽象与权限模型。"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Callable

from pydantic import BaseModel, Field


class ToolError(Exception):
    """工具执行错误（含类型与工具名）。"""

    def __init__(self, tool: str, error_type: str, message: str) -> None:
        super().__init__(message)
        self.tool = tool
        self.error_type = error_type
        self.message = message


class ToolResult(BaseModel):
    """工具调用统一结果。"""

    success: bool = True
    tool: str = ""
    action: str = ""
    data: dict[str, Any] = Field(default_factory=dict)
    message: str = ""
    error_type: str = ""


@dataclass(frozen=True)
class Permission:
    """权限声明：如 Permission("memory:read") / Permission("character:write")。"""

    scope: str

    def allows(self, scope: str) -> bool:
        return self.scope == "*" or self.scope == scope


class AgentTool:
    """工具基类：name / description / required_scope + execute。"""

    name: str = ""
    description: str = ""
    required_scope: str = "*"

    async def execute(self, ctx: Any, **kwargs: Any) -> ToolResult:
        raise NotImplementedError


class ToolRegistry:
    """工具注册表：按 Agent 权限校验调用。"""

    def __init__(
        self,
        tools: dict[str, AgentTool] | None = None,
        permissions: dict[str, list[Permission]] | None = None,
    ) -> None:
        self._tools: dict[str, AgentTool] = tools or {}
        self._permissions: dict[str, list[Permission]] = permissions or {}
        self.calls: list[dict[str, Any]] = []

    def register(self, tool: AgentTool) -> None:
        self._tools[tool.name] = tool

    async def call(
        self,
        agent: str,
        tool_name: str,
        ctx: Any,
        **kwargs: Any,
    ) -> ToolResult:
        tool = self._tools.get(tool_name)
        if tool is None:
            return ToolResult(
                success=False,
                tool=tool_name,
                error_type="unknown_tool",
                message=f"未知工具: {tool_name}",
            )
        allowed = any(
            perm.allows(tool.required_scope)
            for perm in self._permissions.get(agent, [])
        )
        self.calls.append(
            {
                "agent": agent,
                "tool": tool_name,
                "scope": tool.required_scope,
                "allowed": allowed,
            }
        )
        if not allowed:
            return ToolResult(
                success=False,
                tool=tool_name,
                action=kwargs.get("action", ""),
                error_type="permission_denied",
                message=(
                    f"Agent {agent} 无权限调用工具 {tool_name} "
                    f"（需要 {tool.required_scope}）"
                ),
            )
        try:
            return await tool.execute(ctx, **kwargs)
        except ToolError as exc:
            return ToolResult(
                success=False,
                tool=tool_name,
                action=kwargs.get("action", ""),
                error_type=exc.error_type,
                message=exc.message,
            )
        except Exception as exc:  # noqa: BLE001 - 工具兜底，避免 Agent 崩溃
            return ToolResult(
                success=False,
                tool=tool_name,
                action=kwargs.get("action", ""),
                error_type="unknown",
                message=str(exc),
            )

    def reset_calls(self) -> None:
        self.calls.clear()


__all__ = [
    "AgentTool",
    "Permission",
    "ToolError",
    "ToolRegistry",
    "ToolResult",
]
