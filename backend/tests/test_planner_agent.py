"""Planner Agent 测试。"""

import httpx
import pytest
from openai import APIConnectionError

from app.agents.base import AgentError
from app.agents.context import AgentContext
from app.agents.planner_agent import PlannerAgent, parse_plan
from app.agents.protocol import PlannerRequest
from app.llm.mock_provider import MockProvider
from agents_test_utils import FakeRetriever, PLAN, ScriptedLLM, sync_test


def _ctx(llm, request=None):
    return AgentContext(
        run_id="run-p",
        llm=llm,
        retriever=FakeRetriever(),
        planner_request=request or PlannerRequest(),
    )


@sync_test
async def test_planner_success():
    llm = ScriptedLLM(json_results=[PLAN])
    ctx = _ctx(llm)
    plan = await PlannerAgent(llm=llm, retriever=FakeRetriever()).execute(ctx)
    assert plan.title == "测试书"
    assert len(plan.arcs) == 1
    assert plan.arcs[0].chapters[0].title == "第一章 觉醒"
    assert plan.requirement == "100万字"
    assert ctx.telemetry.llm_calls == 1
    assert ctx.telemetry.rag_calls == 1


@sync_test
async def test_planner_demo_without_api_key():
    agent = PlannerAgent(llm=MockProvider(), retriever=FakeRetriever())
    plan = await agent.execute(_ctx(MockProvider()))
    assert plan.title  # 演示规划非空
    assert len(plan.arcs) >= 1


@sync_test
async def test_planner_missing_request_is_validation_error():
    ctx = AgentContext(run_id="run-p", llm=MockProvider(), retriever=FakeRetriever())
    with pytest.raises(AgentError) as exc_info:
        await PlannerAgent(llm=MockProvider(), retriever=FakeRetriever()).execute(ctx)
    assert exc_info.value.error_type == "validation"


@sync_test
async def test_planner_empty_output_is_validation_error():
    llm = ScriptedLLM(json_results=[{}])
    with pytest.raises(AgentError) as exc_info:
        await PlannerAgent(llm=llm, retriever=FakeRetriever()).execute(_ctx(llm))
    assert exc_info.value.error_type == "validation"
    assert "规划结果为空" in exc_info.value.message


@sync_test
async def test_planner_llm_error_is_wrapped():
    class ConnErrorLLM:
        available = True

        def generate_json(self, prompt, system_prompt=None):
            raise APIConnectionError(
                request=httpx.Request("POST", "https://api.deepseek.com/")
            )

    with pytest.raises(AgentError) as exc_info:
        await PlannerAgent(llm=ConnErrorLLM(), retriever=FakeRetriever()).execute(
            _ctx(ConnErrorLLM())
        )
    assert exc_info.value.error_type == "connection"


def test_parse_plan_tolerates_missing_sections():
    plan = parse_plan({"title": "T"})
    assert plan.title == "T"
    assert plan.arcs == []
    assert plan.world_setting.overview == ""
