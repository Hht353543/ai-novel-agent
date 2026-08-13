"""Writer Agent 测试。"""

import pytest

from app.agents.base import AgentError
from app.agents.context import AgentContext
from app.agents.protocol import NovelPlan, PlannerRequest
from app.agents.writer_agent import WriterAgent
from app.llm.mock_provider import MockProvider
from agents_test_utils import FakeRetriever, PLAN, ScriptedLLM, sync_test


def _ctx(llm, revision_instructions="", previous_draft="", base_version=0):
    return AgentContext(
        run_id="run-w",
        llm=llm,
        retriever=FakeRetriever(),
        planner_request=PlannerRequest(),
        plan=NovelPlan(**PLAN),
        current_arc=0,
        current_chapter=0,
        context_text="上文内容",
        target_length=800,
        revision_instructions=revision_instructions,
        previous_draft=previous_draft,
        base_version=base_version,
    )


@sync_test
async def test_writer_success():
    llm = ScriptedLLM(text_results=["正文内容"])
    agent = WriterAgent(llm=llm, retriever=FakeRetriever())
    result = await agent.execute(_ctx(llm))
    assert result.content == "正文内容"
    assert result.full_text == "上文内容\n\n正文内容"
    assert result.attempt == 1
    assert llm.text_prompts[0].startswith("请为一部网络小说创作章节正文")


@sync_test
async def test_writer_revision_instructions_in_prompt():
    llm = ScriptedLLM(text_results=["修订后正文"])
    agent = WriterAgent(llm=llm, retriever=FakeRetriever())
    await agent.execute(_ctx(llm, revision_instructions="人设冲突，请修正"))
    assert "修订意见" in llm.text_prompts[0]
    assert "人设冲突" in llm.text_prompts[0]


@sync_test
async def test_writer_receives_previous_draft_for_incremental_revision():
    llm = ScriptedLLM(text_results=["修订后正文"])
    agent = WriterAgent(llm=llm, retriever=FakeRetriever())
    await agent.execute(
        _ctx(
            llm,
            revision_instructions="修正对话",
            previous_draft="上一稿完整正文",
            base_version=1,
        )
    )
    prompt = llm.text_prompts[0]
    assert "上一稿全文" in prompt
    assert "上一稿完整正文" in prompt
    assert "第 1 版" in prompt
    assert "修订意见" in prompt


@sync_test
async def test_writer_demo_without_api_key():
    agent = WriterAgent(llm=MockProvider(), retriever=FakeRetriever())
    result = await agent.execute(_ctx(MockProvider()))
    assert result.content.startswith("（演示正文）")


@sync_test
async def test_writer_empty_output_is_validation_error():
    llm = ScriptedLLM(text_results=["   "])
    with pytest.raises(AgentError) as exc_info:
        await WriterAgent(llm=llm, retriever=FakeRetriever()).execute(_ctx(llm))
    assert exc_info.value.error_type == "validation"
    assert "章节正文为空" in exc_info.value.message


@sync_test
async def test_writer_missing_plan_is_validation_error():
    llm = ScriptedLLM(text_results=["x"])
    ctx = AgentContext(
        run_id="run-w",
        llm=llm,
        retriever=FakeRetriever(),
        planner_request=PlannerRequest(),
    )
    with pytest.raises(AgentError) as exc_info:
        await WriterAgent(llm=llm, retriever=FakeRetriever()).execute(ctx)
    assert exc_info.value.error_type == "validation"
