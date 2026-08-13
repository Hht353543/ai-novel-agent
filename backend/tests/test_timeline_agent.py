"""Timeline Agent 测试。"""

import pytest

from app.agents.base import AgentError
from app.agents.context import AgentContext
from app.agents.protocol import (
    NovelPlan,
    PlannerRequest,
    TimelineEntry,
    TimelineUpdate,
)
from app.agents.timeline_agent import TimelineAgent, parse_timeline_update
from app.llm.mock_provider import MockProvider
from agents_test_utils import (
    FakeRetriever,
    PLAN,
    ScriptedLLM,
    TIMELINE_UPDATE,
    sync_test,
)


def _ctx(llm, existing=None, events=None):
    return AgentContext(
        run_id="run-t",
        llm=llm,
        retriever=FakeRetriever(),
        planner_request=PlannerRequest(),
        plan=NovelPlan(**PLAN),
        current_chapter=0,
        chapter_title="第一章 觉醒",
        chapter_text="正文内容",
        memory_events=events or ["觉醒武学熔炉"],
        timeline=existing or [],
    )


@sync_test
async def test_timeline_success():
    llm = ScriptedLLM(json_results=[TIMELINE_UPDATE])
    agent = TimelineAgent(llm=llm, retriever=FakeRetriever())
    update = await agent.execute(_ctx(llm))
    assert update.entries[0].event == "觉醒武学熔炉"
    assert update.entries[0].location == "县城"
    assert update.warnings == []


@sync_test
async def test_timeline_parse_sorts_and_filters_empty():
    data = {
        "entries": [
            {"sequence": 2, "event": "B", "chapter_index": 1},
            {"sequence": 1, "event": "A", "chapter_index": 0},
            {"sequence": 3, "event": "  ", "chapter_index": 1},
        ],
        "warnings": ["时间矛盾"],
    }
    update = parse_timeline_update(data, 1, "第二章")
    update.entries = sorted(
        [e for e in update.entries if e.event.strip()],
        key=lambda e: e.sequence,
    )
    assert [e.event for e in update.entries] == ["A", "B"]
    assert update.warnings == ["时间矛盾"]


@sync_test
async def test_timeline_demo_appends_entry():
    agent = TimelineAgent(llm=MockProvider(), retriever=FakeRetriever())
    update = await agent.execute(_ctx(MockProvider()))
    assert len(update.entries) == 1
    assert update.entries[0].chapter_index == 0


def test_timeline_validate_output_rejects_unsorted():
    agent = TimelineAgent(llm=MockProvider(), retriever=FakeRetriever())
    ctx = _ctx(MockProvider())
    update = TimelineUpdate(
        entries=[
            TimelineEntry(sequence=2, event="B"),
            TimelineEntry(sequence=1, event="A"),
        ]
    )
    with pytest.raises(AgentError) as exc_info:
        agent.validate_output(ctx, update)
    assert exc_info.value.error_type == "validation"
