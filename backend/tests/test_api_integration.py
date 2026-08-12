"""后端 API 集成测试（Mock LLM，不触网）。"""

import os
import tempfile
import threading
import time

import httpx
import pytest
from openai import APIConnectionError

os.environ.setdefault("DEEPSEEK_API_KEY", "")
os.environ.setdefault(
    "PROJECTS_FILE",
    os.path.join(tempfile.gettempdir(), "pytest_projects.json"),
)

from fastapi import FastAPI  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.llm.deepseek_provider import DeepSeekProvider  # noqa: E402
from app.llm.mock_provider import MockProvider  # noqa: E402
from app.main import RequestSizeLimitMiddleware, app  # noqa: E402
from app.services.project_repository import JsonProjectRepository  # noqa: E402
import app.api.novel as api  # noqa: E402
import app.services.project_service as ps  # noqa: E402

OUTLINE = {
    "title": "T",
    "summary": "S",
    "world": "W",
    "characters": [],
    "volume_plan": [],
}
CARD = {
    "character_cards": [
        {
            "volume_index": 0,
            "name": "a",
            "role": "r",
            "age": "",
            "appearance": "",
            "personality": "",
            "background": "",
            "goals": "",
            "speech_style": "",
            "notes": "",
        }
    ]
}


class ConnErrProvider:
    available = True

    def generate_json(self, prompt, system_prompt=None):
        raise APIConnectionError(
            request=httpx.Request("POST", "https://api.deepseek.com/")
        )


class SlowProvider:
    available = True

    def generate(self, prompt, json_mode=True, system_prompt=None, model=None):
        time.sleep(0.3)
        return "body"


class StreamProvider:
    available = True

    def generate_stream(self, prompt, json_mode=True, system_prompt=None, model=None):
        yield "a"
        yield "b"


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


def _mock_success(monkeypatch):
    monkeypatch.setattr(
        api.novel_service, "llm",
        MockProvider(available=True, generate_json_result=OUTLINE),
    )
    monkeypatch.setattr(
        api.chapter_service, "llm",
        MockProvider(available=True, generate_result="正文"),
    )
    monkeypatch.setattr(
        api.title_service, "llm",
        MockProvider(available=True, generate_json_array_result=["标题1"]),
    )
    monkeypatch.setattr(
        api.character_card_service, "llm",
        MockProvider(available=True, generate_json_result=CARD),
    )


def _mock_demo(monkeypatch):
    monkeypatch.setattr(api.novel_service, "llm", DeepSeekProvider())
    monkeypatch.setattr(api.chapter_service, "llm", DeepSeekProvider())
    monkeypatch.setattr(api.title_service, "llm", DeepSeekProvider())
    monkeypatch.setattr(api.character_card_service, "llm", DeepSeekProvider())


def test_novel_generate_success(client, monkeypatch):
    _mock_success(monkeypatch)
    r = client.post("/api/novel/generate", json={})
    d = r.json()
    assert r.status_code == 200
    assert d["success"] is True and d["status"] == "success"
    assert d["outline"]["title"] == "T"


def test_novel_generate_demo(client, monkeypatch):
    _mock_demo(monkeypatch)
    r = client.post("/api/novel/generate", json={})
    d = r.json()
    assert d["status"] == "demo" and d["demo"] is True


def test_novel_generate_connection_error(client, monkeypatch):
    monkeypatch.setattr(api.novel_service, "llm", ConnErrProvider())
    r = client.post("/api/novel/generate", json={})
    d = r.json()
    assert d["success"] is False and d["status"] == "error"
    assert "DeepSeek API" in d["message"]
    assert d["outline"]["title"] == ""


def test_chapter_titles_cards_success(client, monkeypatch):
    _mock_success(monkeypatch)
    r = client.post("/api/novel/chapter/generate", json={"mode": "generate"})
    d = r.json()
    assert d["status"] == "success" and d["content"] == "正文"
    r = client.post("/api/novel/titles/generate", json={"mode": "volume"})
    d = r.json()
    assert d["status"] == "success" and d["titles"] == ["标题1"]
    r = client.post("/api/novel/character-cards/generate", json={})
    d = r.json()
    assert d["status"] == "success" and len(d["character_cards"]) == 1


def test_chapter_titles_cards_demo(client, monkeypatch):
    _mock_demo(monkeypatch)
    for path, body in (
        ("/api/novel/chapter/generate", {"mode": "generate"}),
        ("/api/novel/titles/generate", {"mode": "volume"}),
        ("/api/novel/character-cards/generate", {}),
    ):
        assert client.post(path, json=body).json()["status"] == "demo"


def test_project_crud(client, tmp_path, monkeypatch):
    monkeypatch.setattr(
        ps, "_repository", JsonProjectRepository(tmp_path / "projects.json")
    )
    r = client.post(
        "/api/projects",
        json={"title": "B", "outline": {}, "chapters": [], "character_cards": [], "memory": "M"},
    )
    assert r.status_code == 200 and r.json()["project"]["memory"] == "M"
    pid = r.json()["project"]["id"]
    r = client.get("/api/projects")
    assert len(r.json()["projects"]) == 1
    r = client.get(f"/api/projects/{pid}")
    assert r.json()["title"] == "B"
    assert client.get("/api/projects/missing").status_code == 404
    assert client.delete(f"/api/projects/{pid}").json()["success"] is True
    assert client.get("/api/projects").json()["projects"] == []


def test_stream_chapter_success_and_demo(client, monkeypatch):
    monkeypatch.setattr(api.chapter_service, "llm", StreamProvider())
    with client.stream("POST", "/api/novel/chapter/stream", json={"mode": "generate"}) as resp:
        body = "".join(resp.iter_text())
    assert '"type": "delta"' in body and '"status": "success"' in body

    monkeypatch.setattr(api.chapter_service, "llm", DeepSeekProvider())
    with client.stream("POST", "/api/novel/chapter/stream", json={"mode": "generate"}) as resp:
        body = "".join(resp.iter_text())
    assert '"type": "delta"' in body and '"status": "demo"' in body


def test_review_disabled_and_enabled(client, monkeypatch):
    monkeypatch.setattr(settings, "review_enabled", False)
    r = client.post("/api/novel/chapter/review", json={"chapter_text": "x"})
    assert r.json()["status"] == "disabled"
    monkeypatch.setattr(settings, "review_enabled", True)
    monkeypatch.setattr(
        api.chapter_service, "llm",
        MockProvider(
            available=True,
            generate_json_result={
                "issues": [{"type": "错字", "severity": "low", "description": "d", "suggestion": "s"}]
            },
        ),
    )
    r = client.post("/api/novel/chapter/review", json={"chapter_text": "正文"})
    d = r.json()
    assert d["status"] == "success" and len(d["issues"]) == 1


def test_health_during_slow_generation(client, monkeypatch):
    monkeypatch.setattr(api.chapter_service, "llm", SlowProvider())
    results = {}

    def run_generate():
        results["gen"] = client.post("/api/novel/chapter/generate", json={"mode": "generate"})

    t = threading.Thread(target=run_generate)
    t.start()
    time.sleep(0.05)
    h = client.get("/api/health")
    assert h.status_code == 200 and h.json()["status"] == "ok"
    t.join(timeout=5)
    assert results["gen"].status_code == 200


def test_request_size_limit_413():
    mini = FastAPI()
    mini.add_middleware(RequestSizeLimitMiddleware, max_bytes=100)

    @mini.post("/x")
    async def x():
        return JSONResponse({"ok": True})

    c = TestClient(mini, raise_server_exceptions=False)
    r = c.post("/x", content=b"y" * 200, headers={"Content-Type": "application/json"})
    assert r.status_code == 413
    r2 = c.post("/x", content=b"{}", headers={"Content-Type": "application/json"})
    assert r2.status_code == 200


def test_novel_generate_unexpected_error_is_structured(client, monkeypatch):
    import app.services.novel_service as ns

    def boom(request, context):
        raise RuntimeError("boom")

    monkeypatch.setattr(ns, "build_novel_prompt", boom)
    r = client.post("/api/novel/generate", json={})
    d = r.json()
    assert r.status_code == 200
    assert d["success"] is False
    assert d["status"] == "error"
    assert "生成流程内部错误" in d["message"]
    assert d["outline"]["title"] == ""


def test_chapter_generate_unexpected_error_is_structured(client, monkeypatch):
    import app.services.chapter_service as cs

    def boom(request, rag_context):
        raise RuntimeError("boom")

    monkeypatch.setattr(cs, "build_chapter_prompt", boom)
    r = client.post("/api/novel/chapter/generate", json={"mode": "generate"})
    d = r.json()
    assert r.status_code == 200
    assert d["success"] is False
    assert d["status"] == "error"
    assert "章节生成失败" in d["message"]
