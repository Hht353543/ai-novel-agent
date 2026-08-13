"""Reviewer Agent：质量审校，输出结构化 ReviewResult。"""

import logging
from typing import Any

from app.agents.base import AgentError, BaseAgent
from app.agents.context import AgentContext
from app.agents.protocol import CharacterSystem, NovelPlan, ReviewResult
from app.agents.prompts import build_reviewer_prompt
from app.schemas.novel import ReviewIssue

logger = logging.getLogger(__name__)

SYSTEM_ROLE = (
    "你是一名资深网文主编，负责审校章节的一致性、爽点节奏、错字与设定冲突，"
    "只报告真实问题并给出可操作的修改建议。"
)


def _reviewer_query(ctx: AgentContext) -> str:
    return " ".join(
        part
        for part in [
            ctx.plan.title if ctx.plan else "",
            ctx.plan.main_plot.premise if ctx.plan else "",
            ctx.chapter_title,
            ctx.memory,
        ]
        if part
    )


def parse_review_result(data: dict[str, Any]) -> ReviewResult:
    """把模型返回的 dict 容错解析为 ReviewResult。"""
    score = int(data.get("score", 0) or 0)
    score = max(0, min(100, score))
    issues = []
    for item in data.get("issues") or []:
        if isinstance(item, dict):
            issues.append(
                ReviewIssue(
                    type=str(item.get("type", "")),
                    severity=str(item.get("severity", "")),
                    description=str(item.get("description", "")),
                    suggestion=str(item.get("suggestion", "")),
                )
            )
    return ReviewResult(
        passed=bool(data.get("passed", False)),
        score=score,
        issues=issues,
        summary=str(data.get("summary", "")),
        revision_required=bool(data.get("revision_required", False)),
    )


class ReviewerAgent(BaseAgent[ReviewResult]):
    """质量审校 Agent：输出结构化 ReviewResult。"""

    name = "reviewer"
    role = "质量审校 Agent"

    def validate_input(self, ctx: AgentContext) -> None:
        if not ctx.chapter_text.strip():
            raise AgentError(
                self.name,
                "validate_input",
                "validation",
                "正文为空，无法审校",
                run_id=ctx.run_id,
            )

    def validate_output(self, ctx: AgentContext, result: ReviewResult) -> None:
        if not (0 <= result.score <= 100):
            raise AgentError(
                self.name,
                "validate_output",
                "validation",
                "审校分数超出 0-100",
                run_id=ctx.run_id,
            )

    async def _run(self, ctx: AgentContext) -> ReviewResult:
        if not self.llm.available:
            logger.warning("未配置 DEEPSEEK_API_KEY，Reviewer 返回演示通过")
            return ReviewResult(
                passed=True,
                score=85,
                revision_required=False,
                summary="演示模式：未发现问题",
            )
        context = await self._retrieve(ctx, _reviewer_query(ctx))
        ctx.retrieved_context = context
        plan = ctx.plan or NovelPlan()
        prompt = build_reviewer_prompt(
            plan=plan,
            chapter_title=ctx.chapter_title,
            chapter_text=ctx.chapter_text,
            characters=CharacterSystem(
                profiles=ctx.characters,
                states=ctx.character_states,
                relationships=ctx.relationships,
            ),
            memory=ctx.memory,
            rag_context=context,
        )
        data = await self._llm_json(ctx, prompt, SYSTEM_ROLE)
        return parse_review_result(data)
