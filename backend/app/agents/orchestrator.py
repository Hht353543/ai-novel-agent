"""多 Agent 编排器：Planner → Character → Writer → Reviewer（含修订循环）。"""

import logging
import time
import uuid
from typing import Any, Callable

from app.agents.base import AgentError, BaseAgent
from app.agents.context import AgentContext
from app.agents.protocol import (
    ChapterOutline,
    ChapterResult,
    CharacterSystem,
    NovelPlan,
    PipelineRequest,
    PipelineResult,
    PlannerRequest,
    ReviewResult,
    RevisionAttempt,
)
from app.agents.registry import AgentRegistry, default_registry
from app.llm.deepseek_provider import DeepSeekProvider
from app.llm.provider import BaseLLM
from app.rag.base import RetrievalProvider
from app.rag.retriever import get_retriever
from app.services.chapter_service import join_text

logger = logging.getLogger(__name__)


class NovelOrchestrator:
    """Agent 编排入口：负责创建 Context、按序调用 Agent、驱动审校循环。"""

    def __init__(
        self,
        llm: BaseLLM | None = None,
        retriever: RetrievalProvider | None = None,
        registry: AgentRegistry | None = None,
        persister: Callable[..., Any] | None = None,
    ) -> None:
        self.llm = llm or DeepSeekProvider()
        self.retriever = retriever or get_retriever()
        self.registry = registry or default_registry
        # 持久化回调：默认接线到 project_service.save_project；测试可注入替身
        self.persister = persister

    def new_context(self, **kwargs: Any) -> AgentContext:
        """创建带新 run_id 的 AgentContext。"""
        run_id = kwargs.pop("run_id", None) or uuid.uuid4().hex
        return AgentContext(
            run_id=run_id,
            llm=self.llm,
            retriever=self.retriever,
            **kwargs,
        )

    def _agent(self, name: str) -> BaseAgent:
        return self.registry.create(name, llm=self.llm, retriever=self.retriever)

    async def plan(self, ctx: AgentContext) -> NovelPlan:
        """运行 PlannerAgent。"""
        return await self._agent("planner").execute(ctx)

    async def characters(self, ctx: AgentContext) -> CharacterSystem:
        """运行 CharacterAgent。"""
        return await self._agent("character").execute(ctx)

    async def write_chapter(self, ctx: AgentContext) -> ChapterResult:
        """运行 WriterAgent。"""
        return await self._agent("writer").execute(ctx)

    async def review_chapter(self, ctx: AgentContext) -> ReviewResult:
        """运行 ReviewerAgent。"""
        return await self._agent("reviewer").execute(ctx)

    @staticmethod
    def resolve_chapter_outline(
        plan: NovelPlan,
        volume_index: int,
        chapter_index: int,
    ) -> ChapterOutline:
        """从规划中解析章节大纲；缺失时生成占位标题。"""
        if 0 <= volume_index < len(plan.arcs):
            arc = plan.arcs[volume_index]
            if 0 <= chapter_index < len(arc.chapters):
                return arc.chapters[chapter_index]
        return ChapterOutline(
            chapter_index=chapter_index,
            title=f"第{chapter_index + 1}章",
        )

    @staticmethod
    def _passed(review: ReviewResult, threshold: int) -> bool:
        return (
            review.passed
            and review.score >= threshold
            and not review.revision_required
        )

    @staticmethod
    def _revision_instructions(review: ReviewResult) -> str:
        lines = [f"审校未通过（评分 {review.score}）。"]
        if review.summary:
            lines.append(review.summary)
        for issue in review.issues:
            lines.append(
                f"- [{issue.severity}] {issue.type}：{issue.description}"
                f"；建议：{issue.suggestion or '（无）'}"
            )
        return "\n".join(lines)

    async def run_pipeline(self, request: PipelineRequest) -> PipelineResult:
        """完整流程：规划 → 人物 → 写作 → 审校 → （必要时）修订循环。"""
        planner_kwargs = request.dict(
            exclude={
                "project_id",
                "save",
                "volume_index",
                "chapter_index",
                "target_length",
                "with_review",
                "max_revisions",
            }
        )
        ctx = self.new_context(
            project_id=request.project_id,
            planner_request=PlannerRequest(**planner_kwargs),
            current_arc=request.volume_index,
            current_chapter=request.chapter_index,
            target_length=request.target_length,
            extra_requirements=request.extra_requirements,
            attachment_name=request.attachment_name,
            attachment_text=request.attachment_text,
        )
        start = time.perf_counter()
        try:
            plan = await self.plan(ctx)
            ctx.plan = plan
            characters = await self.characters(ctx)
            ctx.characters = characters.profiles
            ctx.character_states = characters.states
            ctx.relationships = characters.relationships
            ctx.chapter_outline = self.resolve_chapter_outline(
                plan, request.volume_index, request.chapter_index
            )
            ctx.chapter_title = (
                ctx.chapter_outline.title
                or f"第{request.chapter_index + 1}章"
            )

            chapter = await self.write_chapter(ctx)
            history: list[RevisionAttempt] = []
            latest_review: ReviewResult | None = None
            status = "demo" if not self.llm.available else "success"
            message = ""
            max_revisions = (
                request.max_revisions
                if request.max_revisions is not None
                else ctx.config.agent_max_revisions
            )

            if request.with_review:
                ctx.chapter_text = chapter.content
                review = await self.review_chapter(ctx)
                chapter.review = review
                history.append(
                    RevisionAttempt(
                        attempt=chapter.attempt,
                        content=chapter.content,
                        review=review,
                    )
                )
                attempts = 1
                while (
                    not self._passed(review, ctx.config.review_pass_score)
                    and attempts <= max_revisions
                ):
                    ctx.telemetry.revision_attempts += 1
                    instructions = self._revision_instructions(review)
                    ctx.revision_instructions = instructions
                    ctx.metadata["attempt"] = attempts + 1
                    chapter = await self.write_chapter(ctx)
                    ctx.chapter_text = chapter.content
                    review = await self.review_chapter(ctx)
                    chapter.review = review
                    history.append(
                        RevisionAttempt(
                            attempt=chapter.attempt,
                            instructions=instructions,
                            content=chapter.content,
                            review=review,
                        )
                    )
                    attempts += 1
                latest_review = review
                if not self._passed(review, ctx.config.review_pass_score):
                    # 达到上限：返回最高分版本，显式告知，不静默失败
                    best = max(
                        history,
                        key=lambda h: (h.review.score if h.review else 0, h.attempt),
                    )
                    chapter = ChapterResult(
                        attempt=best.attempt,
                        content=best.content,
                        full_text=join_text(ctx.context_text, best.content),
                        memory=chapter.memory,
                        review=best.review,
                    )
                    latest_review = best.review
                    status = "revision_exhausted"
                    message = (
                        f"审校未通过，已返回最高分版本"
                        f"（第 {best.attempt} 版，评分 "
                        f"{best.review.score if best.review else 0}）。"
                    )

            if ctx.config.memory_enabled:
                from app.services.memory_service import update_memory

                memory = await update_memory(
                    self.llm,
                    chapter.memory,
                    plan.to_outline(),
                    ctx.chapter_title,
                    chapter.content,
                )
                chapter.memory = memory
                ctx.memory = memory

            project_id = request.project_id
            if request.save or bool(request.project_id):
                project = self._persist(
                    ctx,
                    request,
                    plan,
                    characters,
                    chapter,
                    latest_review,
                    project_id,
                )
                project_id = project.id

            ctx.telemetry.duration_ms = (time.perf_counter() - start) * 1000
            return PipelineResult(
                run_id=ctx.run_id,
                project_id=project_id,
                status=status,
                message=message,
                plan=plan,
                characters=characters,
                chapter=chapter,
                latest_review=latest_review,
                revision_history=history,
                telemetry=ctx.telemetry.dict(),
            )
        except AgentError as exc:
            ctx.telemetry.duration_ms = (time.perf_counter() - start) * 1000
            logger.error("Pipeline 失败 run_id=%s: %s", ctx.run_id, exc)
            return PipelineResult(
                run_id=ctx.run_id,
                project_id=request.project_id,
                status="error",
                message=str(exc),
                telemetry=ctx.telemetry.dict(),
            )
        except Exception as exc:  # noqa: BLE001 - 显式返回错误，禁止静默
            ctx.telemetry.duration_ms = (time.perf_counter() - start) * 1000
            logger.exception("Pipeline 未预期异常 run_id=%s", ctx.run_id)
            return PipelineResult(
                run_id=ctx.run_id,
                project_id=request.project_id,
                status="error",
                message=f"Pipeline 内部错误：{exc}",
                telemetry=ctx.telemetry.dict(),
            )

    def _persist(
        self,
        ctx: AgentContext,
        request: PipelineRequest,
        plan: NovelPlan,
        characters: CharacterSystem,
        chapter: ChapterResult,
        latest_review: ReviewResult | None,
        project_id: str,
    ):
        """把 Agent 产物合并进项目（保留已有章节与角色卡，不覆盖）。"""
        from app.schemas.project import ProjectSaveRequest
        from app.services.project_service import get_project, save_project

        existing = get_project(project_id) if project_id else None
        save_req = ProjectSaveRequest(
            id=project_id or "",
            title=plan.title or (existing.title if existing else "未命名小说"),
            outline=plan.to_outline(),
            chapters=list(existing.chapters) if existing else [],
            character_cards=list(existing.character_cards) if existing else [],
            memory=chapter.memory or (existing.memory if existing else ""),
            plan=plan,
            character_profiles=characters.profiles,
            character_states=characters.states,
            character_relations=characters.relationships,
            latest_review=latest_review,
        )
        persister = self.persister or save_project
        saved = persister(save_req)
        if saved is None:
            raise AgentError(
                "pipeline",
                "persist",
                "storage",
                "项目保存回调未返回结果",
                run_id=ctx.run_id,
            )
        return saved
