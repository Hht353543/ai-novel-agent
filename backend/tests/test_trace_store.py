"""Trace 持久化测试。"""

from app.traces.store import TraceStore


def test_trace_save_load_list(tmp_path):
    store = TraceStore(tmp_path)
    store.save(
        "run-1",
        {
            "kind": "pipeline",
            "status": "COMPLETED",
            "message": "ok",
            "start_time": "2026-01-01T00:00:00+08:00",
            "end_time": "2026-01-01T00:01:00+08:00",
        },
    )
    loaded = store.load("run-1")
    assert loaded is not None
    assert loaded["status"] == "COMPLETED"
    assert loaded["saved_at"]
    recent = store.list_recent(limit=10)
    assert len(recent) == 1
    assert recent[0]["run_id"] == "run-1"


def test_trace_missing_returns_none(tmp_path):
    store = TraceStore(tmp_path)
    assert store.load("missing") is None


def test_trace_survives_new_store_instance(tmp_path):
    store = TraceStore(tmp_path)
    store.save("run-2", {"kind": "sequence", "status": "FAILED"})
    reopened = TraceStore(tmp_path)
    loaded = reopened.load("run-2")
    assert loaded is not None
    assert loaded["kind"] == "sequence"
