"""Timeline Agent：维护小说时间线并发现时间矛盾。"""

import logging
from typing import Any

from app.agents.base import AgentError, BaseAgent
from app.agents.context import AgentContext
from app.agents.protocol import NovelPlan, TimelineEntry, TimelineUpdate
from app.agents.prompts import build_timeline_prompt

logger = logging.getLogger(__name__)

SYSTEM_ROLE = "你是一名小说时间线管理员，负责维护事件顺序并发现时间矛盾。"


def parse_timeline_update(
    data: dict[str, Any],
    chapter_index: int,
    chapter_title: str,
) -> TimelineUpdate:
    """把模型返回的 dict 容错解析为 TimelineUpdate。"""
    entries = []
    for i, item in enumerate(data.get("entries") or []):
        if not isinstance(item, dict):
            continue
        entries.append(
            TimelineEntry(
                sequence=int(item.get("sequence", i)),
                chapter_index=int(item.get("chapter_index", chapter_index)),
                chapter_title=str(item.get("chapter_title", chapter_title)),
                time_label=str(item.get("time_label", "")),
                event=str(item.get("event", "")),
                location=str(item.get("location", "")),
                characters=[
                    str(c) for c in (item.get("characters") or []) if str(c).strip()
                ],
            )
        )
    warnings = [str(w) for w in (data.get("warnings") or []) if str(w).strip()]
    return TimelineUpdate(entries=entries, warnings=warnings)


class TimelineAgent(BaseAgent[TimelineUpdate]):
    """时间线 Agent：输出完整时间线与一致性警告。"""

    name = "timeline"
    role = "时间线 Agent"

    def validate_input(self, ctx: AgentContext) -> None:
        if not ctx.chapter_title and not ctx.chapter_text.strip():
            raise AgentError(
                self.name,
                "validate_input",
                "validation",
                "缺少章节信息，无法维护时间线",
                run_id=ctx.run_id,
            )

    def validate_output(self, ctx: AgentContext, update: TimelineUpdate) -> None:
        entries = [e for e in update.entries if e.event.strip()]
        if entries and entries != sorted(entries, key=lambda e: e.sequence):
            raise AgentError(
                self.name,
                "validate_output",
                "validation",
                "时间线条目未按 sequence 排序",
                run_id=ctx.run_id,
            )

    async def _run(self, ctx: AgentContext) -> TimelineUpdate:
        if not self.llm.available:
            logger.warning("未配置 DEEPSEEK_API_KEY，Timeline 追加演示条目")
            entries = list(ctx.timeline)
            entries.append(
                TimelineEntry(
                    sequence=len(entries) + 1,
                    chapter_index=ctx.current_chapter,
                    chapter_title=ctx.chapter_title,
                    time_label=f"第{ctx.current_chapter + 1}章",
                    event="（演示事件）",
                )
            )
            return TimelineUpdate(entries=entries, warnings=[])
        context = await self._retrieve(ctx, _timeline_query(ctx))
        ctx.retrieved_context = context
        prompt = build_timeline_prompt(
            plan=ctx.plan or NovelPlan(),
            chapter_title=ctx.chapter_title,
            chapter_index=ctx.current_chapter,
            events=ctx.memory_events,
            existing_entries=ctx.timeline,
            chapter_text=ctx.chapter_text,
        )
        data = await self._llm_json(ctx, prompt, SYSTEM_ROLE)
        update = parse_timeline_update(
            data,
            ctx.current_chapter,
            ctx.chapter_title,
        )
        update.entries = sorted(
            [e for e in update.entries if e.event.strip()],
            key=lambda e: e.sequence,
        )
        return update


def _timeline_query(ctx: AgentContext) -> str:
    return " ".join(
        part
        for part in [
            ctx.plan.title if ctx.plan else "",
            ctx.chapter_title,
            " ".join(ctx.memory_events),
        ]
        if part
    )
