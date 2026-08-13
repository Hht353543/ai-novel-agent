"""Character Agent 测试。"""

import pytest

from app.agents.base import AgentError
from app.agents.context import AgentContext
from app.agents.character_agent import CharacterAgent, parse_character_system
from app.agents.protocol import NovelPlan, PlannerRequest
from app.llm.mock_provider import MockProvider
from agents_test_utils import (
    CHARACTER_SYSTEM,
    FakeRetriever,
    PLAN,
    ScriptedLLM,
    sync_test,
)


def _ctx(llm, plan=None):
    return AgentContext(
        run_id="run-c",
        llm=llm,
        retriever=FakeRetriever(),
        planner_request=PlannerRequest(),
        plan=plan or NovelPlan(**PLAN),
    )


@sync_test
async def test_character_success():
    llm = ScriptedLLM(json_results=[CHARACTER_SYSTEM])
    ctx = _ctx(llm)
    system = await CharacterAgent(llm=llm, retriever=FakeRetriever()).execute(ctx)
    assert system.profiles[0].name == "沈惊堂"
    assert system.states[0].cultivation == "锻体"
    assert system.relationships[0].relation == "搭档"


def test_character_states_auto_completed():
    data = {"profiles": CHARACTER_SYSTEM["profiles"]}
    system = parse_character_system(data)
    assert len(system.states) == 1
    assert system.states[0].name == "沈惊堂"
    assert system.states[0].plot_status == "初始状态"


@sync_test
async def test_character_demo_without_api_key():
    agent = CharacterAgent(llm=MockProvider(), retriever=FakeRetriever())
    system = await agent.execute(_ctx(MockProvider()))
    assert len(system.profiles) >= 1
    assert len(system.states) == len(system.profiles)


@sync_test
async def test_character_missing_plan_is_validation_error():
    ctx = AgentContext(
        run_id="run-c",
        llm=MockProvider(),
        retriever=FakeRetriever(),
        planner_request=PlannerRequest(),
    )
    with pytest.raises(AgentError) as exc_info:
        await CharacterAgent(llm=MockProvider(), retriever=FakeRetriever()).execute(ctx)
    assert exc_info.value.error_type == "validation"


@sync_test
async def test_character_empty_profiles_is_validation_error():
    llm = ScriptedLLM(json_results=[{}])
    with pytest.raises(AgentError) as exc_info:
        await CharacterAgent(llm=llm, retriever=FakeRetriever()).execute(_ctx(llm))
    assert exc_info.value.error_type == "validation"
