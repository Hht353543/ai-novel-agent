"""多 Agent API 路由（新增入口，不影响现有接口）。"""

import logging
import time
from typing import TypeVar

from fastapi import APIRouter

from app.agents.base import AgentError
from app.agents.context import AgentContext
from app.agents.orchestrator import NovelOrchestrator
from app.agents.protocol import (
    AgentResponse,
    CharacterRequest,
    CharacterResponse,
    PipelineRequest,
    PipelineResponse,
    PlannerRequest,
    PlannerResponse,
    ReviewRequest,
    ReviewerResponse,
    WriterRequest,
    WriterResponse,
)

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
    result = await orchestrator.run_pipeline(request)
    return PipelineResponse(
        success=result.status != "error",
        status=result.status,
        agent="pipeline",
        run_id=result.run_id,
        message=result.message,
        result=result,
        telemetry=result.telemetry,
    )
