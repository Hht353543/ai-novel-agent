"""知识检索工具：统一 RAG 访问边界。"""

from __future__ import annotations

from typing import Any

from app.agents.context import AgentContext
from app.tools.base import AgentTool, ToolResult


class SearchKnowledgeTool(AgentTool):
    """知识库检索（只读，走 RetrievalProvider）。"""

    name = "search_knowledge"
    description = "按查询检索本地知识库并返回上下文。"
    required_scope = "knowledge:read"

    async def execute(self, ctx: AgentContext, **kwargs: Any) -> ToolResult:
        query = str(kwargs.get("query", ""))
        categories = kwargs.get("categories")
        from app.services.knowledge_compress import default_categories

        cats = categories if categories is not None else default_categories()
        try:
            import asyncio

            results = await asyncio.to_thread(
                ctx.retriever.retrieve, query, cats
            )
        except Exception as exc:  # noqa: BLE001 - 检索失败返回结构化错误
            return ToolResult(
                success=False,
                tool=self.name,
                action="search",
                error_type="rag",
                message=str(exc),
            )
        ctx.retrieved_context = list(results)
        return ToolResult(
            success=True,
            tool=self.name,
            action="search",
            data={"hits": results, "total": len(results)},
        )


__all__ = ["SearchKnowledgeTool"]
