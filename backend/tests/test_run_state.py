"""Pipeline 运行状态与进度追踪测试。"""

from app.agents.orchestrator import NovelOrchestrator
from app.agents.protocol import PipelineRequest
from app.agents.run_state import RunStore, RunTracker
from agents_test_utils import (
    CHARACTER_SYSTEM,
    FakeRetriever,
    MEMORY_UPDATE,
    PLAN,
    REVIEW_PASS,
    ScriptedLLM,
    TIMELINE_UPDATE,
    sync_test,
)


def test_run_store_create_get_update():
    store = RunStore()
    state = store.create("r1")
    assert state.status == "CREATED"
    assert store.get("r1").run_id == "r1"
    store.update("r1", status="WRITING", current_agent="writer")
    assert store.get("r1").status == "WRITING"
    assert store.get("missing") is None


def test_run_store_caps_entries():
    store = RunStore(max_entries=10)
    for i in range(15):
        store.create(f"r{i}")
    assert len(store.list_recent(limit=100)) <= 10


def test_run_tracker_records_progress_and_finish():
    store = RunStore()
    store.create("r1")
    tracker = RunTracker(store, "r1")
    tracker.set("WRITING", agent="writer", message="写作中", step="WRITING")
    tracker.mark_step_done("WRITING")
    tracker.set("REVIEWING", agent="reviewer", message="审校中", step="REVIEWING")
    tracker.finish(result={"ok": True})
    state = store.get("r1")
    assert state.status == "COMPLETED"
    assert state.current_agent == "reviewer"
    assert state.result == {"ok": True}
    assert [p.step for p in state.progress] == ["WRITING", "REVIEWING"]
    assert state.progress[0].status == "done"
    assert state.end_time


@sync_test
async def test_orchestrator_updates_tracker_through_pipeline():
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
    store = RunStore()
    run_id = "run-tracked"
    store.create(run_id)
    tracker = RunTracker(store, run_id)
    orchestrator = NovelOrchestrator(llm=llm, retriever=FakeRetriever())
    result = await orchestrator.run_pipeline(
        PipelineRequest(genre="武侠", requirement="10万字"),
        tracker=tracker,
        run_id=run_id,
    )
    assert result.status == "success"
    state = store.get(run_id)
    assert state.status == "COMPLETED"
    steps = [p.step for p in state.progress]
    assert "PLANNING" in steps
    assert "CHARACTER_DESIGN" in steps
    assert "WRITING" in steps
    assert "REVIEWING" in steps
    assert state.result["chapter"]["content"] == "正文v1"


@sync_test
async def test_orchestrator_tracker_marks_failure():
    llm = ScriptedLLM(json_results=[{}])  # planner 输出为空 → 校验失败
    store = RunStore()
    run_id = "run-fail"
    store.create(run_id)
    tracker = RunTracker(store, run_id)
    orchestrator = NovelOrchestrator(llm=llm, retriever=FakeRetriever())
    result = await orchestrator.run_pipeline(
        PipelineRequest(genre="武侠", requirement="10万字"),
        tracker=tracker,
        run_id=run_id,
    )
    assert result.status == "error"
    state = store.get(run_id)
    assert state.status == "FAILED"
    assert state.error is not None
    assert state.error.error_type == "validation"
