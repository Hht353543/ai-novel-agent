"""Reviewer Agent 测试。"""

import pytest

from app.agents.base import AgentError
from app.agents.context import AgentContext
from app.agents.protocol import NovelPlan, PlannerRequest
from app.agents.reviewer_agent import ReviewerAgent, parse_review_result
from app.llm.mock_provider import MockProvider
from agents_test_utils import (
    FakeRetriever,
    PLAN,
    REVIEW_PASS,
    ScriptedLLM,
    review_fail,
    sync_test,
)


def _ctx(llm, chapter_text="章节正文内容"):
    return AgentContext(
        run_id="run-r",
        llm=llm,
        retriever=FakeRetriever(),
        planner_request=PlannerRequest(),
        plan=NovelPlan(**PLAN),
        chapter_title="第一章 觉醒",
        chapter_text=chapter_text,
    )


@sync_test
async def test_reviewer_pass():
    llm = ScriptedLLM(json_results=[REVIEW_PASS])
    review = await ReviewerAgent(llm=llm, retriever=FakeRetriever()).execute(_ctx(llm))
    assert review.passed is True
    assert review.score == 90
    assert review.revision_required is False


@sync_test
async def test_reviewer_reject_with_issues():
    llm = ScriptedLLM(json_results=[review_fail(score=40)])
    review = await ReviewerAgent(llm=llm, retriever=FakeRetriever()).execute(_ctx(llm))
    assert review.passed is False
    assert review.score == 40
    assert len(review.issues) == 1
    assert review.issues[0].severity == "high"


def test_parse_review_result_clamps_score():
    result = parse_review_result({"score": 150, "passed": True})
    assert result.score == 100
    result = parse_review_result({"score": -5, "passed": False})
    assert result.score == 0


@sync_test
async def test_reviewer_demo_without_api_key():
    agent = ReviewerAgent(llm=MockProvider(), retriever=FakeRetriever())
    review = await agent.execute(_ctx(MockProvider()))
    assert review.passed is True
    assert review.score == 85


@sync_test
async def test_reviewer_empty_text_is_validation_error():
    llm = ScriptedLLM()
    with pytest.raises(AgentError) as exc_info:
        await ReviewerAgent(llm=llm, retriever=FakeRetriever()).execute(
            _ctx(llm, chapter_text="  ")
        )
    assert exc_info.value.error_type == "validation"
