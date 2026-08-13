"""Memory Agent 测试。"""

import pytest

from app.agents.base import AgentError
from app.agents.context import AgentContext
from app.agents.memory_agent import (
    MemoryAgent,
    dedup_facts,
    parse_memory_update,
)
from app.agents.protocol import (
    CharacterState,
    MemoryFact,
    MemoryUpdate,
    NovelPlan,
    PlannerRequest,
)
from app.llm.mock_provider import MockProvider
from agents_test_utils import (
    FakeRetriever,
    MEMORY_UPDATE,
    PLAN,
    ScriptedLLM,
    sync_test,
)


def _ctx(llm, chapter_text="正文内容", existing_facts=None):
    return AgentContext(
        run_id="run-m",
        llm=llm,
        retriever=FakeRetriever(),
        planner_request=PlannerRequest(),
        plan=NovelPlan(**PLAN),
        current_chapter=0,
        chapter_title="第一章 觉醒",
        chapter_text=chapter_text,
        character_states=[CharacterState(name="沈惊堂", cultivation="锻体")],
        memory_facts=existing_facts or [],
    )


@sync_test
async def test_memory_success_parse_and_dedup():
    llm = ScriptedLLM(json_results=[MEMORY_UPDATE])
    agent = MemoryAgent(llm=llm, retriever=FakeRetriever())
    update = await agent.execute(_ctx(llm))
    assert update.state_deltas[0].character == "沈惊堂"
    assert update.state_deltas[0].changes[0].new == "先天"
    assert len(update.facts) == 2
    assert update.events == ["觉醒武学熔炉", "获得玉佩"]


@sync_test
async def test_memory_dedup_against_existing():
    existing = [
        MemoryFact(
            category="event",
            content="主角在县城觉醒武学熔炉",
            importance="high",
            dedup_key="event:主角在县城觉醒武学熔炉",
        )
    ]
    update = parse_memory_update(MEMORY_UPDATE, 0)
    update = dedup_facts(update, existing)
    assert len(update.facts) == 1
    assert update.facts[0].content == "获得神秘玉佩"


@sync_test
async def test_memory_demo_without_api_key():
    agent = MemoryAgent(llm=MockProvider(), retriever=FakeRetriever())
    update = await agent.execute(_ctx(MockProvider()))
    assert update.facts == []
    assert update.state_deltas == []


@sync_test
async def test_memory_empty_text_is_validation_error():
    with pytest.raises(AgentError) as exc_info:
        await MemoryAgent(
            llm=MockProvider(), retriever=FakeRetriever()
        ).execute(_ctx(MockProvider(), chapter_text="  "))
    assert exc_info.value.error_type == "validation"


@sync_test
async def test_memory_unknown_state_field_is_validation_error():
    data = {
        "state_deltas": [
            {
                "character": "沈惊堂",
                "changes": [
                    {"field": "not_a_field", "action": "set", "new": "x"}
                ],
            }
        ],
        "facts": [],
        "events": [],
    }
    llm = ScriptedLLM(json_results=[data])
    with pytest.raises(AgentError) as exc_info:
        await MemoryAgent(llm=llm, retriever=FakeRetriever()).execute(_ctx(llm))
    assert exc_info.value.error_type == "validation"
    assert "未知人物状态字段" in exc_info.value.message
