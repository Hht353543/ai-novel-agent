"""Planner Agent：根据用户需求生成结构化小说规划。"""

import logging
from typing import Any

from app.agents.base import AgentError, BaseAgent
from app.agents.context import AgentContext
from app.agents.protocol import (
    ChapterOutline,
    MainPlot,
    NovelPlan,
    PlannerRequest,
    StoryArc,
    WorldSetting,
)
from app.agents.prompts import build_planner_prompt
from app.schemas.novel import Character, NovelGenerateRequest
from app.services.novel_service import demo_outline, novel_retrieval_query

logger = logging.getLogger(__name__)

SYSTEM_ROLE = (
    "你是一名拥有20年经验的网络小说白金作者与首席策划，"
    "擅长输出结构化、可执行的小说规划。"
)


def _to_novel_request(request: PlannerRequest) -> NovelGenerateRequest:
    """把 PlannerRequest 转换为现有 NovelGenerateRequest（复用检索查询）。"""
    return NovelGenerateRequest(
        title=request.title,
        genre=request.genre,
        theme=request.theme,
        keywords=request.keywords,
        requirement=request.requirement,
        extra_requirements=request.extra_requirements,
        attachment_name=request.attachment_name,
        attachment_text=request.attachment_text,
    )


def parse_plan(data: dict[str, Any]) -> NovelPlan:
    """把模型返回的 dict 容错解析为 NovelPlan。"""
    world = data.get("world_setting") or {}
    main = data.get("main_plot") or {}
    arcs: list[StoryArc] = []
    for item in data.get("arcs") or []:
        if not isinstance(item, dict):
            continue
        chapters: list[ChapterOutline] = []
        for c in item.get("chapters") or []:
            if not isinstance(c, dict):
                continue
            chapters.append(
                ChapterOutline(
                    chapter_index=int(c.get("chapter_index", 0)),
                    title=str(c.get("title", "")),
                    goal=str(c.get("goal", "")),
                    beats=[str(b) for b in (c.get("beats") or []) if str(b).strip()],
                    key_characters=[
                        str(k) for k in (c.get("key_characters") or []) if str(k).strip()
                    ],
                    location=str(c.get("location", "")),
                )
            )
        arcs.append(
            StoryArc(
                arc_index=int(item.get("arc_index", len(arcs))),
                name=str(item.get("name", "")),
                goal=str(item.get("goal", "")),
                chapters=chapters,
            )
        )
    characters = []
    for item in data.get("characters") or []:
        if isinstance(item, dict):
            characters.append(
                Character(
                    name=str(item.get("name", "")),
                    role=str(item.get("role", "")),
                    description=str(item.get("description", "")),
                )
            )
    return NovelPlan(
        title=str(data.get("title", "")),
        genre=str(data.get("genre", "")),
        premise=str(data.get("premise", "")),
        summary=str(data.get("summary", "")),
        world_setting=WorldSetting(
            overview=str(world.get("overview", "")),
            power_system=str(world.get("power_system", "")),
            factions=[str(x) for x in (world.get("factions") or []) if str(x).strip()],
            locations=[str(x) for x in (world.get("locations") or []) if str(x).strip()],
        ),
        main_plot=MainPlot(
            premise=str(main.get("premise", "")),
            main_goal=str(main.get("main_goal", "")),
            core_conflict=str(main.get("core_conflict", "")),
            theme=str(main.get("theme", "")),
        ),
        characters=characters,
        arcs=arcs,
    )


def demo_plan(request: PlannerRequest) -> NovelPlan:
    """无 API Key 时的演示规划（基于现有 demo_outline）。"""
    demo = demo_outline()
    arcs: list[StoryArc] = []
    for vi, vol in enumerate(demo.get("volume_plan") or []):
        chapters = [
            ChapterOutline(chapter_index=ci, title=str(title))
            for ci, title in enumerate(vol.get("chapters") or [])
        ]
        arcs.append(
            StoryArc(
                arc_index=vi,
                name=str(vol.get("volume", "")),
                goal="",
                chapters=chapters,
            )
        )
    return NovelPlan(
        title=str(demo.get("title", "")),
        genre=request.genre,
        premise=str(demo.get("summary", "")),
        summary=str(demo.get("summary", "")),
        world_setting=WorldSetting(overview=str(demo.get("world", ""))),
        main_plot=MainPlot(
            premise=str(demo.get("summary", "")),
            theme=request.theme,
        ),
        characters=[Character(**c) for c in demo.get("characters") or []],
        arcs=arcs,
        requirement=request.requirement,
        extra_requirements=request.extra_requirements,
    )


class PlannerAgent(BaseAgent[NovelPlan]):
    """大纲规划 Agent：输出结构化 NovelPlan。"""

    name = "planner"
    role = "大纲规划 Agent"

    def validate_input(self, ctx: AgentContext) -> None:
        if ctx.planner_request is None:
            raise AgentError(
                self.name,
                "validate_input",
                "validation",
                "缺少用户创作需求",
                run_id=ctx.run_id,
            )

    def validate_output(self, ctx: AgentContext, plan: NovelPlan) -> None:
        if not plan.title and not plan.arcs:
            raise AgentError(
                self.name,
                "validate_output",
                "validation",
                "规划结果为空",
                run_id=ctx.run_id,
            )

    async def _run(self, ctx: AgentContext) -> NovelPlan:
        if ctx.planner_request is None:
            raise AgentError(
                self.name,
                "_run",
                "validation",
                "缺少用户创作需求",
                run_id=ctx.run_id,
            )
        request = ctx.planner_request
        if not self.llm.available:
            logger.warning("未配置 DEEPSEEK_API_KEY，Planner 返回演示规划")
            return demo_plan(request)
        context = await self._retrieve(ctx, novel_retrieval_query(_to_novel_request(request)))
        ctx.retrieved_context = context
        prompt = build_planner_prompt(request, context)
        data = await self._llm_json(ctx, prompt, SYSTEM_ROLE)
        plan = parse_plan(data)
        plan.requirement = request.requirement
        plan.extra_requirements = request.extra_requirements
        return plan
