"""多 Agent API 路由（新增入口，不影响现有接口）。"""

import asyncio
import logging
import time
import uuid
from typing import TypeVar

from fastapi import APIRouter

from app.agents.base import AgentError
from app.agents.context import AgentContext
from app.agents.orchestrator import NovelOrchestrator
from app.agents.protocol import (
    AgentResponse,
    CharacterRequest,
    CharacterResponse,
    PipelineAsyncResponse,
    PipelineRequest,
    PipelineResponse,
    PlannerRequest,
    PlannerResponse,
    ReviewRequest,
    ReviewerResponse,
    SequenceRequest,
    SequenceResponse,
    WriterRequest,
    WriterResponse,
)
from app.agents.run_state import PipelineRunState, RunTracker, run_store
from app.traces.store import trace_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agents", tags=["agents"])

# 编排器（进程级单例；测试通过替换该实例注入 Mock）
orchestrator = NovelOrchestrator()

T = TypeVar("T", bound=AgentResponse)


def _finish(ctx: AgentContext, start: float) -> None:
    ctx.telemetry.duration_ms = (time.perf_counter() - start) * 1000


def _error_response(
    response_cls: type[T],
    agent: str,
    ctx: AgentContext,
    exc: AgentError,
) -> T:
    return response_cls(
        success=False,
        status="error",
        agent=agent,
        run_id=ctx.run_id,
        message=str(exc),
        error=exc.info,
        telemetry=ctx.telemetry.dict(),
    )


@router.post("/plan", response_model=PlannerResponse)
async def plan_agent(request: PlannerRequest) -> PlannerResponse:
    """运行 PlannerAgent：根据用户需求生成结构化小说规划。"""
    start = time.perf_counter()
    ctx = orchestrator.new_context(
        project_id=request.project_id,
        planner_request=request,
    )
    try:
        plan = await orchestrator.plan(ctx)
        _finish(ctx, start)
        status = "demo" if not orchestrator.llm.available else "success"
        return PlannerResponse(
            success=True,
            status=status,
            agent="planner",
            run_id=ctx.run_id,
            plan=plan,
            telemetry=ctx.telemetry.dict(),
        )
    except AgentError as exc:
        _finish(ctx, start)
        return _error_response(PlannerResponse, "planner", ctx, exc)


@router.post("/characters", response_model=CharacterResponse)
async def character_agent(request: CharacterRequest) -> CharacterResponse:
    """运行 CharacterAgent：根据规划建立人物系统。"""
    start = time.perf_counter()
    ctx = orchestrator.new_context(
        project_id=request.project_id,
        plan=request.plan,
    )
    try:
        system = await orchestrator.characters(ctx)
        _finish(ctx, start)
        status = "demo" if not orchestrator.llm.available else "success"
        return CharacterResponse(
            success=True,
            status=status,
            agent="character",
            run_id=ctx.run_id,
            characters=system,
            telemetry=ctx.telemetry.dict(),
        )
    except AgentError as exc:
        _finish(ctx, start)
        return _error_response(CharacterResponse, "character", ctx, exc)


@router.post("/write", response_model=WriterResponse)
async def writer_agent(request: WriterRequest) -> WriterResponse:
    """运行 WriterAgent：根据上下文生成章节正文（不含审校循环）。"""
    start = time.perf_counter()
    ctx = orchestrator.new_context(
        project_id=request.project_id,
        plan=request.plan,
        current_arc=request.volume_index,
        current_chapter=request.chapter_index,
        context_text=request.context_text,
        previous_chapter_text=request.previous_chapter_text,
        target_length=request.target_length,
        extra_requirements=request.extra_requirements,
        attachment_name=request.attachment_name,
        attachment_text=request.attachment_text,
        memory=request.memory,
        revision_instructions=request.revision_instructions,
    )
    ctx.chapter_outline = orchestrator.resolve_chapter_outline(
        request.plan, request.volume_index, request.chapter_index
    )
    ctx.chapter_title = ctx.chapter_outline.title or f"第{request.chapter_index + 1}章"
    try:
        chapter = await orchestrator.write_chapter(ctx)
        _finish(ctx, start)
        status = "demo" if not orchestrator.llm.available else "success"
        return WriterResponse(
            success=True,
            status=status,
            agent="writer",
            run_id=ctx.run_id,
            chapter=chapter,
            telemetry=ctx.telemetry.dict(),
        )
    except AgentError as exc:
        _finish(ctx, start)
        return _error_response(WriterResponse, "writer", ctx, exc)


@router.post("/review", response_model=ReviewerResponse)
async def reviewer_agent(request: ReviewRequest) -> ReviewerResponse:
    """运行 ReviewerAgent：对章节做质量审校并返回结构化结果。"""
    start = time.perf_counter()
    ctx = orchestrator.new_context(
        project_id=request.project_id,
        plan=request.plan,
        chapter_title=request.chapter_title,
        chapter_text=request.chapter_text,
        memory=request.memory,
    )
    try:
        review = await orchestrator.review_chapter(ctx)
        _finish(ctx, start)
        status = "demo" if not orchestrator.llm.available else "success"
        return ReviewerResponse(
            success=True,
            status=status,
            agent="reviewer",
            run_id=ctx.run_id,
            review=review,
            telemetry=ctx.telemetry.dict(),
        )
    except AgentError as exc:
        _finish(ctx, start)
        return _error_response(ReviewerResponse, "reviewer", ctx, exc)


@router.post("/pipeline", response_model=PipelineResponse)
async def pipeline_agent(request: PipelineRequest) -> PipelineResponse:
    """运行完整多 Agent Pipeline（含 Writer ↔ Reviewer 修订循环）。"""
    run_id = uuid.uuid4().hex
    run_store.create(run_id)
    tracker = RunTracker(run_store, run_id)
    result = await orchestrator.run_pipeline(
        request,
        tracker=tracker,
        run_id=run_id,
    )
    return PipelineResponse(
        success=result.status != "error",
        status=result.status,
        agent="pipeline",
        run_id=result.run_id,
        message=result.message,
        result=result,
        telemetry=result.telemetry,
    )


@router.post("/pipeline/async", response_model=PipelineAsyncResponse)
async def pipeline_agent_async(request: PipelineRequest) -> PipelineAsyncResponse:
    """异步启动 Pipeline：立即返回 run_id，进度通过 GET /runs/{run_id} 获取。"""
    run_id = uuid.uuid4().hex
    run_store.create(run_id)
    tracker = RunTracker(run_store, run_id)

    async def _run() -> None:
        try:
            await orchestrator.run_pipeline(
                request,
                tracker=tracker,
                run_id=run_id,
            )
        except Exception as exc:  # noqa: BLE001 - 兜底标记失败
            from app.agents.protocol import AgentErrorInfo

            tracker.finish(
                error=AgentErrorInfo(
                    agent="pipeline",
                    operation="run_pipeline",
                    error_type="unknown",
                    message=str(exc),
                    run_id=run_id,
                )
            )

    asyncio.create_task(_run())
    return PipelineAsyncResponse(run_id=run_id, status="CREATED")


@router.post("/sequence", response_model=SequenceResponse)
async def sequence_agent(request: SequenceRequest) -> SequenceResponse:
    """连续章节创作（同步）：规划/人物一次，逐章写作与状态更新。"""
    run_id = uuid.uuid4().hex
    run_store.create(run_id, kind="sequence")
    tracker = RunTracker(run_store, run_id)
    result = await orchestrator.run_sequence(
        request,
        tracker=tracker,
        run_id=run_id,
    )
    return SequenceResponse(
        success=result.status != "error",
        status=result.status,
        agent="pipeline",
        run_id=result.run_id,
        message=result.message,
        result=result,
        telemetry=result.telemetry,
    )


@router.post("/sequence/async", response_model=PipelineAsyncResponse)
async def sequence_agent_async(request: SequenceRequest) -> PipelineAsyncResponse:
    """异步启动连续章节创作，进度通过 GET /runs/{run_id} 获取。"""
    run_id = uuid.uuid4().hex
    run_store.create(run_id, kind="sequence")
    tracker = RunTracker(run_store, run_id)

    async def _run() -> None:
        try:
            await orchestrator.run_sequence(
                request,
                tracker=tracker,
                run_id=run_id,
            )
        except Exception as exc:  # noqa: BLE001 - 兜底标记失败
            from app.agents.protocol import AgentErrorInfo

            tracker.finish(
                error=AgentErrorInfo(
                    agent="pipeline",
                    operation="run_sequence",
                    error_type="unknown",
                    message=str(exc),
                    run_id=run_id,
                )
            )

    asyncio.create_task(_run())
    return PipelineAsyncResponse(run_id=run_id, status="CREATED")


@router.get("/runs/{run_id}", response_model=PipelineRunState)
async def get_pipeline_run(run_id: str) -> PipelineRunState:
    """获取一次 Pipeline 运行的状态与进度。"""
    state = run_store.get(run_id)
    if state is None:
        saved = trace_store.load(run_id)
        if saved is not None:
            return PipelineRunState(
                run_id=run_id,
                kind=str(saved.get("kind", "pipeline")),
                status=str(saved.get("status", "COMPLETED")),
                message=str(saved.get("message", "")),
                start_time=str(saved.get("start_time", "")),
                end_time=str(saved.get("end_time", "")),
                error=saved.get("error"),
            )
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail=f"运行不存在或已过期: {run_id}")
    return state


@router.get("/runs", response_model=list[PipelineRunState])
async def list_pipeline_runs(limit: int = 20) -> list[PipelineRunState]:
    """列出最近的 Pipeline 运行（调试用）。"""
    recent = run_store.list_recent(limit=min(limit, 100))
    ids = {r.run_id for r in recent}
    for saved in trace_store.list_recent(limit=min(limit, 100)):
        if saved["run_id"] not in ids:
            recent.append(
                PipelineRunState(
                    run_id=saved["run_id"],
                    kind=str(saved.get("kind", "pipeline")),
                    status=str(saved.get("status", "COMPLETED")),
                    message=str(saved.get("message", "")),
                    start_time=str(saved.get("start_time", "")),
                    end_time=str(saved.get("end_time", "")),
                    error=saved.get("error"),
                )
            )
    recent.sort(key=lambda s: s.start_time, reverse=True)
    return recent[:limit]
