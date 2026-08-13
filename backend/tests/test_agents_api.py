"""多 Agent API 集成测试（不触网）。"""

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.agents.orchestrator import NovelOrchestrator
from app.agents.protocol import PipelineRequest
from app.agents.run_state import RunTracker, run_store
from app.llm.deepseek_provider import DeepSeekProvider
from app.llm.mock_provider import MockProvider
from app.main import app
import app.api.agents as api_agents
from agents_test_utils import (
    CHARACTER_SYSTEM,
    FakeRetriever,
    PLAN,
    REVIEW_PASS,
    ScriptedLLM,
)


def _client():
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def client():
    return _client()


def _patch_orchestrator(monkeypatch, llm):
    monkeypatch.setattr(
        api_agents,
        "orchestrator",
        NovelOrchestrator(llm=llm, retriever=FakeRetriever()),
    )


def test_plan_endpoint_success(client, monkeypatch):
    _patch_orchestrator(monkeypatch, ScriptedLLM(json_results=[PLAN]))
    r = client.post("/api/agents/plan", json={})
    d = r.json()
    assert r.status_code == 200
    assert d["success"] is True and d["status"] == "success"
    assert d["agent"] == "planner"
    assert d["plan"]["title"] == "测试书"
    assert d["run_id"]
    assert d["telemetry"]["llm_calls"] == 1


def test_plan_endpoint_demo(client, monkeypatch):
    _patch_orchestrator(monkeypatch, DeepSeekProvider())
    r = client.post("/api/agents/plan", json={})
    d = r.json()
    assert d["success"] is True and d["status"] == "demo"
    assert d["plan"]["title"]


def test_plan_endpoint_error_is_structured(client, monkeypatch):
    _patch_orchestrator(monkeypatch, ScriptedLLM(json_results=[{}]))
    r = client.post("/api/agents/plan", json={})
    d = r.json()
    assert r.status_code == 200
    assert d["success"] is False and d["status"] == "error"
    assert d["error"]["error_type"] == "validation"
    assert d["run_id"]


def test_characters_endpoint_success(client, monkeypatch):
    _patch_orchestrator(monkeypatch, ScriptedLLM(json_results=[CHARACTER_SYSTEM]))
    r = client.post("/api/agents/characters", json={"plan": PLAN})
    d = r.json()
    assert d["success"] is True
    assert d["characters"]["profiles"][0]["name"] == "沈惊堂"


def test_write_endpoint_success(client, monkeypatch):
    _patch_orchestrator(monkeypatch, ScriptedLLM(text_results=["正文"]))
    r = client.post(
        "/api/agents/write",
        json={"plan": PLAN, "volume_index": 0, "chapter_index": 0},
    )
    d = r.json()
    assert d["success"] is True
    assert d["chapter"]["content"] == "正文"


def test_review_endpoint_success(client, monkeypatch):
    _patch_orchestrator(monkeypatch, ScriptedLLM(json_results=[REVIEW_PASS]))
    r = client.post(
        "/api/agents/review",
        json={"plan": PLAN, "chapter_title": "第一章", "chapter_text": "正文"},
    )
    d = r.json()
    assert d["success"] is True
    assert d["review"]["passed"] is True


def test_review_endpoint_empty_text_is_error(client, monkeypatch):
    _patch_orchestrator(monkeypatch, ScriptedLLM())
    r = client.post(
        "/api/agents/review",
        json={"plan": PLAN, "chapter_text": "  "},
    )
    d = r.json()
    assert d["success"] is False and d["status"] == "error"
    assert d["error"]["error_type"] == "validation"


def test_pipeline_endpoint_success(client, monkeypatch):
    llm = ScriptedLLM(
        json_results=[PLAN, CHARACTER_SYSTEM, REVIEW_PASS],
        text_results=["正文v1"],
    )
    _patch_orchestrator(monkeypatch, llm)
    r = client.post(
        "/api/agents/pipeline",
        json={
            "title": "测试书",
            "genre": "武侠",
            "requirement": "10万字",
            "volume_index": 0,
            "chapter_index": 0,
        },
    )
    d = r.json()
    assert r.status_code == 200
    assert d["success"] is True
    assert d["result"]["status"] == "success"
    assert d["result"]["chapter"]["content"] == "正文v1"
    assert d["result"]["latest_review"]["passed"] is True


def test_pipeline_endpoint_demo(client, monkeypatch):
    _patch_orchestrator(monkeypatch, MockProvider())
    r = client.post(
        "/api/agents/pipeline",
        json={"genre": "武侠", "requirement": "10万字"},
    )
    d = r.json()
    assert d["success"] is True
    assert d["result"]["status"] == "demo"


def test_project_roundtrip_with_agent_fields(client, tmp_path, monkeypatch):
    """多 Agent 产物经真实项目存储保存/读取（含新可选字段）。"""
    import app.services.project_service as ps
    from app.services.project_repository import JsonProjectRepository

    monkeypatch.setattr(
        ps,
        "_repository",
        JsonProjectRepository(tmp_path / "projects.json"),
    )
    r = client.post(
        "/api/projects",
        json={
            "title": "测试书",
            "outline": {},
            "chapters": [],
            "character_cards": [],
            "memory": "",
            "plan": PLAN,
            "character_profiles": CHARACTER_SYSTEM["profiles"],
            "character_states": CHARACTER_SYSTEM["states"],
            "character_relations": CHARACTER_SYSTEM["relationships"],
            "latest_review": REVIEW_PASS,
        },
    )
    assert r.status_code == 200
    project = r.json()["project"]
    assert project["plan"]["title"] == "测试书"
    assert project["latest_review"]["passed"] is True
    assert project["character_states"][0]["name"] == "沈惊堂"

    pid = project["id"]
    loaded = client.get(f"/api/projects/{pid}").json()
    assert loaded["plan"]["title"] == "测试书"
    assert loaded["character_relations"][0]["relation"] == "搭档"
    assert loaded["latest_review"]["score"] == 90


def test_pipeline_async_returns_run_id(client, monkeypatch):
    _patch_orchestrator(monkeypatch, MockProvider())
    run_store._runs.clear()
    r = client.post(
        "/api/agents/pipeline/async",
        json={"genre": "武侠", "requirement": "10万字"},
    )
    assert r.status_code == 200
    run_id = r.json()["run_id"]
    assert r.json()["status"] == "CREATED"
    assert run_store.get(run_id) is not None


def test_pipeline_run_polling_contract(client, monkeypatch):
    llm = ScriptedLLM(
        json_results=[PLAN, CHARACTER_SYSTEM, REVIEW_PASS],
        text_results=["正文v1"],
    )
    _patch_orchestrator(monkeypatch, llm)
    run_store._runs.clear()
    run_id = "poll-run"
    run_store.create(run_id)
    tracker = RunTracker(run_store, run_id)
    asyncio.run(
        api_agents.orchestrator.run_pipeline(
            PipelineRequest(genre="武侠", requirement="10万字"),
            tracker=tracker,
            run_id=run_id,
        )
    )

    state = client.get(f"/api/agents/runs/{run_id}").json()
    assert state["status"] == "COMPLETED"
    steps = [p["step"] for p in state["progress"]]
    assert "PLANNING" in steps and "WRITING" in steps and "REVIEWING" in steps
    assert state["result"]["chapter"]["content"] == "正文v1"


def test_pipeline_run_404(client, monkeypatch):
    _patch_orchestrator(monkeypatch, ScriptedLLM())
    assert client.get("/api/agents/runs/missing").status_code == 404


def test_pipeline_runs_list(client, monkeypatch):
    _patch_orchestrator(monkeypatch, ScriptedLLM())
    r = client.get("/api/agents/runs")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
