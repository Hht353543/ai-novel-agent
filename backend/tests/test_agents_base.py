"""Agent 基类：校验、错误包装与遥测测试。"""

import httpx
import pytest
from openai import APIConnectionError

from app.agents.base import AgentError, BaseAgent
from app.agents.context import AgentContext
from app.agents.protocol import PlannerRequest
from agents_test_utils import FakeRetriever, ScriptedLLM, sync_test


def _ctx(llm, retriever=None):
    return AgentContext(
        run_id="run-1",
        llm=llm,
        retriever=retriever or FakeRetriever(),
        planner_request=PlannerRequest(),
    )


class EchoAgent(BaseAgent[int]):
    name = "echo"
    role = "test"

    async def _run(self, ctx):
        return 42


class BadOutputAgent(BaseAgent[int]):
    name = "bad_output"
    role = "test"

    async def _run(self, ctx):
        return 0

    def validate_output(self, ctx, result):
        raise AgentError(self.name, "validate_output", "validation", "输出无效", run_id=ctx.run_id)


class LlmAgent(BaseAgent[str]):
    name = "llm"
    role = "test"

    async def _run(self, ctx):
        await self._llm_json(ctx, "p", "s")
        return await self._llm_text(ctx, "p", "s")


class RagAgent(BaseAgent[list]):
    name = "rag"
    role = "test"

    async def _run(self, ctx):
        return await self._retrieve(ctx, "q")


@sync_test
async def test_execute_records_telemetry_step():
    ctx = _ctx(ScriptedLLM())
    result = await EchoAgent().execute(ctx)
    assert result == 42
    assert len(ctx.telemetry.steps) == 1
    step = ctx.telemetry.steps[0]
    assert step.agent == "echo"
    assert step.status == "ok"
    assert step.output_type == "int"
    assert step.duration_ms >= 0


@sync_test
async def test_validate_output_error_is_wrapped():
    ctx = _ctx(ScriptedLLM())
    with pytest.raises(AgentError) as exc_info:
        await BadOutputAgent().execute(ctx)
    assert exc_info.value.error_type == "validation"
    assert exc_info.value.info.run_id == "run-1"
    assert ctx.telemetry.steps[0].status == "error"


@sync_test
async def test_llm_calls_counted_and_connection_error_wrapped():
    class ConnErrorLLM:
        available = True

        def generate_json(self, prompt, system_prompt=None):
            raise APIConnectionError(
                request=httpx.Request("POST", "https://api.deepseek.com/")
            )

    ctx = _ctx(ConnErrorLLM())
    with pytest.raises(AgentError) as exc_info:
        await LlmAgent(llm=ConnErrorLLM(), retriever=FakeRetriever()).execute(ctx)
    assert exc_info.value.error_type == "connection"

    llm = ScriptedLLM(json_results=[{"a": 1}], text_results=["ok"])
    ctx2 = _ctx(llm)
    assert (
        await LlmAgent(llm=llm, retriever=FakeRetriever()).execute(ctx2)
        == "ok"
    )
    assert ctx2.telemetry.llm_calls == 2


@sync_test
async def test_rag_failure_is_wrapped_and_counted():
    ctx = _ctx(ScriptedLLM(), retriever=FakeRetriever(error=RuntimeError("disk")))
    with pytest.raises(AgentError) as exc_info:
        await RagAgent(
            llm=ScriptedLLM(),
            retriever=FakeRetriever(error=RuntimeError("disk")),
        ).execute(ctx)
    assert exc_info.value.error_type == "rag"
    assert ctx.telemetry.rag_calls == 1


@sync_test
async def test_rag_success_returns_context():
    retriever = FakeRetriever(context=[{"source": "a", "content": "x", "category": "c"}])
    ctx = _ctx(ScriptedLLM(), retriever=retriever)
    result = await RagAgent(llm=ScriptedLLM(), retriever=retriever).execute(ctx)
    assert result[0]["source"] == "a"
    assert ctx.telemetry.rag_calls == 1
