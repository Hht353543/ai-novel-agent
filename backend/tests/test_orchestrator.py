"""NovelOrchestrator：完整流程、审校循环与持久化测试。"""

from app.agents.orchestrator import NovelOrchestrator
from app.agents.protocol import PipelineRequest
from app.llm.mock_provider import MockProvider
from agents_test_utils import (
    CHARACTER_SYSTEM,
    FakePersister,
    FakeRetriever,
    MEMORY_UPDATE,
    PLAN,
    REVIEW_PASS,
    ScriptedLLM,
    TIMELINE_UPDATE,
    review_fail,
    sync_test,
)


def _request(**kwargs):
    defaults = dict(
        title="测试书",
        genre="武侠",
        theme="无敌流",
        keywords="系统流",
        requirement="10万字",
        extra_requirements="",
        volume_index=0,
        chapter_index=0,
        target_length=800,
        with_review=True,
    )
    defaults.update(kwargs)
    return PipelineRequest(**defaults)


@sync_test
async def test_pipeline_success_first_review_passes():
    llm = ScriptedLLM(
        json_results=[
            PLAN,
            CHARACTER_SYSTEM,
            REVIEW_PASS,
            MEMORY_UPDATE,
            TIMELINE_UPDATE,
        ],
        text_results=["正文v1"],
    )
    orchestrator = NovelOrchestrator(llm=llm, retriever=FakeRetriever())
    result = await orchestrator.run_pipeline(_request())
    assert result.status == "success"
    assert result.plan.title == "测试书"
    assert result.characters.profiles[0].name == "沈惊堂"
    assert result.chapter.content == "正文v1"
    assert result.latest_review.passed is True
    assert len(result.revision_history) == 1
    assert result.telemetry["llm_calls"] == 6
    assert result.telemetry["rag_calls"] == 6
    assert result.revision_history[0].instructions == ""
    assert result.character_state_updates[0].deltas[0].changes[0].new == "先天"
    assert result.timeline[0].event == "觉醒武学熔炉"
    assert result.memory_facts[0].content == "主角在县城觉醒武学熔炉"


@sync_test
async def test_pipeline_revision_loop_passes_on_second():
    llm = ScriptedLLM(
        json_results=[
            PLAN,
            CHARACTER_SYSTEM,
            review_fail(score=50),
            REVIEW_PASS,
            MEMORY_UPDATE,
            TIMELINE_UPDATE,
        ],
        text_results=["正文v1", "正文v2"],
    )
    orchestrator = NovelOrchestrator(llm=llm, retriever=FakeRetriever())
    result = await orchestrator.run_pipeline(_request())
    assert result.status == "success"
    assert result.chapter.content == "正文v2"
    assert result.telemetry["revision_attempts"] == 1
    assert len(result.revision_history) == 2
    assert "审校未通过" in llm.text_prompts[1]
    assert "人设冲突" in llm.text_prompts[1]
    assert result.revision_history[1].instructions.startswith("审校未通过")


@sync_test
async def test_pipeline_max_revisions_returns_best_version():
    llm = ScriptedLLM(
        json_results=[
            PLAN,
            CHARACTER_SYSTEM,
            review_fail(score=50),
            review_fail(score=70),
            review_fail(score=60),
            MEMORY_UPDATE,
            TIMELINE_UPDATE,
        ],
        text_results=["v1", "v2", "v3"],
    )
    orchestrator = NovelOrchestrator(llm=llm, retriever=FakeRetriever())
    result = await orchestrator.run_pipeline(
        _request(max_revisions=2)
    )
    assert result.status == "revision_exhausted"
    assert "最高分版本" in result.message
    assert len(result.revision_history) == 3
    assert result.telemetry["revision_attempts"] == 2
    # 最高分是第 2 版（70 分），返回该版本
    assert result.chapter.attempt == 2
    assert result.chapter.content == "v2"
    assert result.latest_review.score == 70


@sync_test
async def test_pipeline_without_review_skips_reviewer():
    llm = ScriptedLLM(
        json_results=[PLAN, CHARACTER_SYSTEM, MEMORY_UPDATE, TIMELINE_UPDATE],
        text_results=["正文v1"],
    )
    orchestrator = NovelOrchestrator(llm=llm, retriever=FakeRetriever())
    result = await orchestrator.run_pipeline(_request(with_review=False))
    assert result.status == "success"
    assert result.latest_review is None
    assert result.revision_history == []
    assert result.telemetry["llm_calls"] == 5  # plan+char+writer+memory+timeline
    assert result.telemetry["rag_calls"] == 5


@sync_test
async def test_pipeline_demo_without_api_key():
    orchestrator = NovelOrchestrator(llm=MockProvider(), retriever=FakeRetriever())
    result = await orchestrator.run_pipeline(_request())
    assert result.status == "demo"
    assert result.plan.title
    assert result.chapter.content.startswith("（演示正文）")
    assert result.latest_review.passed is True


@sync_test
async def test_pipeline_agent_error_is_explicit():
    # Planner 返回空 dict → validate_output 抛 AgentError → PipelineResult(status=error)
    llm = ScriptedLLM(json_results=[{}])
    orchestrator = NovelOrchestrator(llm=llm, retriever=FakeRetriever())
    result = await orchestrator.run_pipeline(_request())
    assert result.status == "error"
    assert "规划结果为空" in result.message
    assert result.telemetry["llm_calls"] == 1


@sync_test
async def test_pipeline_persists_when_save_enabled():
    llm = ScriptedLLM(
        json_results=[
            PLAN,
            CHARACTER_SYSTEM,
            REVIEW_PASS,
            MEMORY_UPDATE,
            TIMELINE_UPDATE,
        ],
        text_results=["正文v1"],
    )
    persister = FakePersister()
    orchestrator = NovelOrchestrator(
        llm=llm,
        retriever=FakeRetriever(),
        persister=persister,
    )
    result = await orchestrator.run_pipeline(_request(save=True))
    assert result.status == "success"
    assert result.project_id == "p_new"
    assert len(persister.calls) == 1
    saved = persister.calls[0]
    assert saved.plan.title == "测试书"
    assert saved.character_profiles[0].name == "沈惊堂"
    assert saved.latest_review.passed is True
    assert saved.timeline[0].event == "觉醒武学熔炉"
    assert saved.memory_facts[0].importance == "high"


@sync_test
async def test_pipeline_does_not_persist_without_save():
    llm = ScriptedLLM(
        json_results=[
            PLAN,
            CHARACTER_SYSTEM,
            REVIEW_PASS,
            MEMORY_UPDATE,
            TIMELINE_UPDATE,
        ],
        text_results=["正文v1"],
    )
    persister = FakePersister()
    orchestrator = NovelOrchestrator(
        llm=llm,
        retriever=FakeRetriever(),
        persister=persister,
    )
    await orchestrator.run_pipeline(_request(save=False))
    assert persister.calls == []
