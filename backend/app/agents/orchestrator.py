"""多 Agent 编排器：Planner → Character → Writer → Reviewer（含修订循环）。"""

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

from app.agents.base import AgentError, BaseAgent
from app.agents.context import AgentContext
from app.agents.protocol import (
    ChapterOutline,
    ChapterResult,
    CharacterSystem,
    CharacterStateUpdateRecord,
    NovelPlan,
    ChapterRunResult,
    PipelineRequest,
    PipelineResult,
    PlannerRequest,
    ReviewResult,
    RevisionAttempt,
    SequenceRequest,
    SequenceResult,
)
from app.agents.registry import AgentRegistry, default_registry
from app.agents.run_state import RunTracker
from app.agents.state_engine import apply_character_state_deltas
from app.llm.deepseek_provider import DeepSeekProvider
from app.llm.provider import BaseLLM
from app.rag.base import RetrievalProvider
from app.rag.retriever import get_retriever
from app.services.chapter_service import join_text
from app.tools.registry import create_default_tool_registry

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


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
        self.tools = create_default_tool_registry()
        # 持久化回调：默认接线到 project_service.save_project；测试可注入替身
        self.persister = persister

    def new_context(self, **kwargs: Any) -> AgentContext:
        """创建带新 run_id 的 AgentContext。"""
        run_id = kwargs.pop("run_id", None) or uuid.uuid4().hex
        return AgentContext(
            run_id=run_id,
            llm=self.llm,
            retriever=self.retriever,
            tools=self.tools,
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

    async def run_pipeline(
        self,
        request: PipelineRequest,
        tracker: RunTracker | None = None,
        run_id: str | None = None,
    ) -> PipelineResult:
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
            run_id=run_id,
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
            if tracker:
                tracker.set(
                    "PLANNING",
                    agent="planner",
                    message="正在生成小说规划",
                    step="PLANNING",
                )
            plan = await self.plan(ctx)
            if tracker:
                tracker.mark_step_done("PLANNING")
            ctx.plan = plan
            if tracker:
                tracker.set(
                    "CHARACTER_DESIGN",
                    agent="character",
                    message="正在设计人物系统",
                    step="CHARACTER_DESIGN",
                )
            characters = await self.characters(ctx)
            if tracker:
                tracker.mark_step_done("CHARACTER_DESIGN")
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

            status, message, chapter, history, latest_review = (
                await self._write_with_review(
                    ctx,
                    with_review=request.with_review,
                    max_revisions=request.max_revisions,
                    tracker=tracker,
                    chapter_label=f"第 {request.chapter_index + 1} 章",
                    default_status="demo" if not self.llm.available else "success",
                )
            )
            await self._update_memory_and_timeline(
                ctx,
                chapter_index=request.chapter_index,
                tracker=tracker,
                plan=plan,
                chapter=chapter,
            )

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
            result = PipelineResult(
                run_id=ctx.run_id,
                project_id=project_id,
                status=status,
                message=message,
                plan=plan,
                outline=plan.to_outline(),
                characters=characters,
                character_states=ctx.character_states,
                chapter=chapter,
                latest_review=latest_review,
                revision_history=history,
                character_state_updates=ctx.character_state_updates,
                timeline=ctx.timeline,
                memory_facts=ctx.memory_facts,
                telemetry=ctx.telemetry.dict(),
            )
            if tracker:
                tracker.finish(result=result.dict())
            return result

        except AgentError as exc:
            ctx.telemetry.duration_ms = (time.perf_counter() - start) * 1000
            logger.error("Pipeline 失败 run_id=%s: %s", ctx.run_id, exc)
            result = PipelineResult(
                run_id=ctx.run_id,
                project_id=request.project_id,
                status="error",
                message=str(exc),
                telemetry=ctx.telemetry.dict(),
            )
            if tracker:
                tracker.finish(error=exc.info, result=result.dict())
            return result
        except Exception as exc:  # noqa: BLE001 - 显式返回错误，禁止静默
            ctx.telemetry.duration_ms = (time.perf_counter() - start) * 1000
            logger.exception("Pipeline 未预期异常 run_id=%s", ctx.run_id)
            result = PipelineResult(
                run_id=ctx.run_id,
                project_id=request.project_id,
                status="error",
                message=f"Pipeline 内部错误：{exc}",
                telemetry=ctx.telemetry.dict(),
            )
            if tracker:
                from app.agents.protocol import AgentErrorInfo

                tracker.finish(
                    error=AgentErrorInfo(
                        agent="pipeline",
                        operation="run_pipeline",
                        error_type="unknown",
                        message=str(exc),
                        run_id=ctx.run_id,
                    ),
                    result=result.dict(),
                )
            return result

    async def run_sequence(
        self,
        request: SequenceRequest,
        tracker: RunTracker | None = None,
        run_id: str | None = None,
    ) -> SequenceResult:
        """连续章节创作：规划/人物只做一次，逐章写作→审校→状态/记忆/时间线更新。"""
        if request.start_chapter > request.end_chapter:
            return SequenceResult(
                run_id=run_id or "",
                status="error",
                message="start_chapter 不能大于 end_chapter",
            )
        planner_kwargs = request.dict(
            exclude={
                "project_id",
                "save",
                "start_chapter",
                "end_chapter",
                "target_length",
                "with_review",
                "max_revisions",
            }
        )
        ctx = self.new_context(
            run_id=run_id,
            project_id=request.project_id,
            planner_request=PlannerRequest(**planner_kwargs),
            current_arc=0,
            current_chapter=request.start_chapter,
            target_length=request.target_length,
            extra_requirements=request.extra_requirements,
            attachment_name=request.attachment_name,
            attachment_text=request.attachment_text,
        )
        start = time.perf_counter()
        chapter_runs: list[ChapterRunResult] = []
        try:
            if tracker:
                tracker.set(
                    "PLANNING",
                    agent="planner",
                    message="正在生成小说规划",
                    step="PLANNING",
                )
            plan = await self.plan(ctx)
            if tracker:
                tracker.mark_step_done("PLANNING")
            ctx.plan = plan
            if tracker:
                tracker.set(
                    "CHARACTER_DESIGN",
                    agent="character",
                    message="正在设计人物系统",
                    step="CHARACTER_DESIGN",
                )
            characters = await self.characters(ctx)
            if tracker:
                tracker.mark_step_done("CHARACTER_DESIGN")
            ctx.characters = characters.profiles
            ctx.character_states = characters.states
            ctx.relationships = characters.relationships

            last_content = ""
            for ci in range(request.start_chapter, request.end_chapter + 1):
                ctx.current_chapter = ci
                ctx.chapter_outline = self.resolve_chapter_outline(plan, 0, ci)
                ctx.chapter_title = (
                    ctx.chapter_outline.title or f"第{ci + 1}章"
                )
                ctx.context_text = ""
                ctx.previous_chapter_text = (
                    last_content[-2500:] if last_content else ""
                )
                ctx.previous_draft = ""
                ctx.base_version = 0
                ctx.revision_instructions = ""
                ctx.metadata.pop("attempt", None)
                status, message, chapter, history, latest_review = (
                    await self._write_with_review(
                        ctx,
                        with_review=request.with_review,
                        max_revisions=request.max_revisions,
                        tracker=tracker,
                        chapter_label=f"第 {ci + 1} 章",
                        default_status=(
                            "demo" if not self.llm.available else "success"
                        ),
                    )
                )
                last_content = chapter.content
                await self._update_memory_and_timeline(
                    ctx,
                    chapter_index=ci,
                    tracker=tracker,
                    plan=plan,
                    chapter=chapter,
                )
                chapter_runs.append(
                    ChapterRunResult(
                        chapter_index=ci,
                        chapter_title=ctx.chapter_title,
                        status=status,
                        message=message,
                        chapter=chapter,
                        latest_review=latest_review,
                        revision_history=history,
                        character_state_updates=list(ctx.character_state_updates),
                    )
                )

            project_id = request.project_id
            if request.save or bool(request.project_id):
                project = self._persist_sequence(
                    ctx,
                    request,
                    plan,
                    characters,
                    chapter_runs,
                )
                project_id = project.id

            all_ok = all(r.status != "error" for r in chapter_runs)
            ctx.telemetry.duration_ms = (time.perf_counter() - start) * 1000
            final_status = (
                "demo"
                if not self.llm.available
                else ("success" if all_ok else "error")
            )
            result = SequenceResult(
                run_id=ctx.run_id,
                project_id=project_id,
                status=final_status,
                message=(
                    "连续章节创作完成"
                    if all_ok
                    else "部分章节失败，请查看各章状态"
                ),
                plan=plan,
                outline=plan.to_outline(),
                characters=characters,
                character_states=ctx.character_states,
                chapters=chapter_runs,
                timeline=ctx.timeline,
                memory_facts=ctx.memory_facts,
                telemetry=ctx.telemetry.dict(),
            )
            if tracker:
                tracker.finish(result=result.dict())
            return result
        except AgentError as exc:
            ctx.telemetry.duration_ms = (time.perf_counter() - start) * 1000
            logger.error("Sequence 失败 run_id=%s: %s", ctx.run_id, exc)
            result = SequenceResult(
                run_id=ctx.run_id,
                project_id=request.project_id,
                status="error",
                message=str(exc),
                chapters=chapter_runs,
                telemetry=ctx.telemetry.dict(),
            )
            if tracker:
                tracker.finish(error=exc.info, result=result.dict())
            return result
        except Exception as exc:  # noqa: BLE001 - 显式返回错误，禁止静默
            ctx.telemetry.duration_ms = (time.perf_counter() - start) * 1000
            logger.exception("Sequence 未预期异常 run_id=%s", ctx.run_id)
            result = SequenceResult(
                run_id=ctx.run_id,
                project_id=request.project_id,
                status="error",
                message=f"Sequence 内部错误：{exc}",
                chapters=chapter_runs,
                telemetry=ctx.telemetry.dict(),
            )
            if tracker:
                from app.agents.protocol import AgentErrorInfo

                tracker.finish(
                    error=AgentErrorInfo(
                        agent="pipeline",
                        operation="run_sequence",
                        error_type="unknown",
                        message=str(exc),
                        run_id=ctx.run_id,
                    ),
                    result=result.dict(),
                )
            return result

    async def _write_with_review(
        self,
        ctx: AgentContext,
        *,
        with_review: bool,
        max_revisions: int | None,
        tracker: RunTracker | None,
        chapter_label: str,
        default_status: str,
    ) -> tuple[str, str, ChapterResult, list[RevisionAttempt], ReviewResult | None]:
        """写一章并根据需要执行审校-修订循环。"""
        if tracker:
            tracker.set(
                "WRITING",
                agent="writer",
                message=f"正在生成{chapter_label}",
                step="WRITING",
            )
        chapter = await self.write_chapter(ctx)
        if tracker:
            tracker.mark_step_done("WRITING")
        ctx.chapter_text = chapter.content
        history: list[RevisionAttempt] = []
        latest_review: ReviewResult | None = None
        status = default_status
        message = ""
        limit = (
            max_revisions
            if max_revisions is not None
            else ctx.config.agent_max_revisions
        )
        if not with_review:
            return status, message, chapter, history, latest_review

        if tracker:
            tracker.set(
                "REVIEWING",
                agent="reviewer",
                message="正在审校章节",
                step="REVIEWING",
            )
        review = await self.review_chapter(ctx)
        if tracker:
            tracker.mark_step_done("REVIEWING")
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
            and attempts <= limit
        ):
            if tracker:
                tracker.set(
                    "REVISING",
                    agent="writer",
                    message=f"根据审校意见修订（第 {attempts + 1} 版）",
                    step="REVISING",
                )
            ctx.telemetry.revision_attempts += 1
            instructions = self._revision_instructions(review)
            ctx.revision_instructions = instructions
            ctx.previous_draft = chapter.content[
                : ctx.config.agent_revision_draft_max_chars
            ]
            ctx.base_version = chapter.attempt
            ctx.metadata["attempt"] = attempts + 1
            chapter = await self.write_chapter(ctx)
            ctx.chapter_text = chapter.content
            if tracker:
                tracker.set(
                    "REVIEWING",
                    agent="reviewer",
                    message="正在复审修订稿",
                    step="REVIEWING",
                )
            review = await self.review_chapter(ctx)
            if tracker:
                tracker.mark_step_done("REVIEWING")
            chapter.review = review
            history.append(
                RevisionAttempt(
                    attempt=chapter.attempt,
                    base_version=chapter.base_version,
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
                base_version=best.base_version,
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
        return status, message, chapter, history, latest_review

    async def _update_memory_and_timeline(
        self,
        ctx: AgentContext,
        *,
        chapter_index: int,
        tracker: RunTracker | None,
        plan: NovelPlan,
        chapter: ChapterResult,
    ) -> None:
        """Memory/Timeline 更新：人物状态增量、长期事实、时间线。"""
        if not ctx.config.agent_memory_enabled:
            if ctx.config.memory_enabled:
                from app.services.memory_service import update_memory

                if tracker:
                    tracker.set(
                        "UPDATING_MEMORY",
                        agent="memory",
                        message="正在更新章节记忆",
                        step="UPDATING_MEMORY",
                    )
                memory = await update_memory(
                    self.llm,
                    chapter.memory,
                    plan.to_outline(),
                    ctx.chapter_title,
                    chapter.content,
                )
                chapter.memory = memory
                ctx.memory = memory
                if tracker:
                    tracker.mark_step_done("UPDATING_MEMORY")
            return

        if tracker:
            tracker.set(
                "UPDATING_MEMORY",
                agent="memory",
                message="正在提取人物状态与长期记忆",
                step="UPDATING_MEMORY",
            )
        memory_update = await self._agent("memory").execute(ctx)
        ctx.memory_events = memory_update.events
        ctx.character_states = apply_character_state_deltas(
            ctx.character_states,
            memory_update.state_deltas,
        )
        existing_keys = {f.dedup_key for f in ctx.memory_facts if f.dedup_key}
        for fact in memory_update.facts:
            if fact.dedup_key and fact.dedup_key not in existing_keys:
                ctx.memory_facts.append(fact)
                existing_keys.add(fact.dedup_key)
        importance = {"high": 0, "medium": 1, "low": 2}
        ctx.memory_facts = sorted(
            ctx.memory_facts,
            key=lambda f: importance.get(f.importance, 1),
        )[: ctx.config.agent_memory_max_facts]
        ctx.character_state_updates.append(
            CharacterStateUpdateRecord(
                chapter_index=chapter_index,
                chapter_title=ctx.chapter_title,
                deltas=memory_update.state_deltas,
                created_at=_now(),
            )
        )
        if ctx.config.agent_timeline_enabled:
            timeline_update = await self._agent("timeline").execute(ctx)
            ctx.timeline = timeline_update.entries[
                -ctx.config.agent_timeline_max_entries :
            ]
            if timeline_update.warnings:
                logger.warning(
                    "Timeline 一致性警告 run_id=%s: %s",
                    ctx.run_id,
                    "; ".join(timeline_update.warnings),
                )
        if tracker:
            tracker.mark_step_done("UPDATING_MEMORY")

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
            character_state_updates=ctx.character_state_updates,
            timeline=ctx.timeline,
            memory_facts=ctx.memory_facts,
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

    def _persist_sequence(
        self,
        ctx: AgentContext,
        request: SequenceRequest,
        plan: NovelPlan,
        characters: CharacterSystem,
        chapter_runs: list[ChapterRunResult],
    ):
        """把连续章节结果合并进项目（按卷/章索引合并，保留已有数据）。"""
        from app.schemas.project import ChapterDraft, ProjectSaveRequest
        from app.services.project_service import get_project, save_project

        existing = get_project(request.project_id) if request.project_id else None
        by_key = {
            (c.volume_index, c.chapter_index): c
            for c in (list(existing.chapters) if existing else [])
        }
        for run in chapter_runs:
            if run.chapter is None:
                continue
            by_key[(0, run.chapter_index)] = ChapterDraft(
                volume_index=0,
                chapter_index=run.chapter_index,
                chapter_title=run.chapter_title,
                content=run.chapter.content,
                version=run.chapter.attempt,
            )
        merged_chapters = [by_key[k] for k in sorted(by_key)]
        latest_review = (
            chapter_runs[-1].latest_review if chapter_runs else None
        )
        save_req = ProjectSaveRequest(
            id=request.project_id or "",
            title=plan.title or (existing.title if existing else "未命名小说"),
            outline=plan.to_outline(),
            chapters=merged_chapters,
            character_cards=list(existing.character_cards) if existing else [],
            memory=ctx.memory or (existing.memory if existing else ""),
            plan=plan,
            character_profiles=characters.profiles,
            character_states=ctx.character_states,
            character_relations=characters.relationships,
            latest_review=latest_review,
            character_state_updates=ctx.character_state_updates,
            timeline=ctx.timeline,
            memory_facts=ctx.memory_facts,
        )
        persister = self.persister or save_project
        saved = persister(save_req)
        if saved is None:
            raise AgentError(
                "pipeline",
                "persist_sequence",
                "storage",
                "项目保存回调未返回结果",
                run_id=ctx.run_id,
            )
        return saved
