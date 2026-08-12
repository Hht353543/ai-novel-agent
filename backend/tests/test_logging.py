"""请求日志与 LLM 计量测试。"""

import logging
import os

os.environ.setdefault("DEEPSEEK_API_KEY", "")

from fastapi import FastAPI  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.llm.deepseek import DeepSeekClient  # noqa: E402
from app.main import RequestLogMiddleware, app  # noqa: E402


class Capture(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record.getMessage())


def _capture():
    handler = Capture()
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    return handler


def test_request_log_middleware():
    mini = FastAPI()
    mini.add_middleware(RequestLogMiddleware)

    @mini.get("/ping")
    async def ping():
        return JSONResponse({"ok": True})

    handler = _capture()
    try:
        r = TestClient(mini).get("/ping")
        rid = r.headers.get("x-request-id")
        assert r.status_code == 200 and rid
        assert any(
            f"request_id={rid}" in rec
            and "method=GET" in rec
            and "path=/ping" in rec
            and "status=200" in rec
            and "duration_ms=" in rec
            for rec in handler.records
        ), handler.records
    finally:
        logging.getLogger().removeHandler(handler)


def test_health_reports_llm_available():
    d = TestClient(app).get("/api/health").json()
    assert d["status"] == "ok"
    assert d["llm_available"] is False


class _FakeUsage:
    prompt_tokens = 10
    completion_tokens = 5
    total_tokens = 15


class _FakeChoice:
    class Msg:
        content = "hello"

    message = Msg()


class _FakeResp:
    choices = [_FakeChoice()]
    usage = _FakeUsage()


class _FakeCompletions:
    def create(self, **kwargs):
        self.kwargs = kwargs
        return _FakeResp()


class _FakeChat:
    completions = _FakeCompletions()


class _FakeOpenAI:
    chat = _FakeChat()


def test_deepseek_usage_log_has_model_and_duration():
    client = DeepSeekClient()
    client.client = _FakeOpenAI()
    handler = _capture()
    try:
        out = client.generate("p")
        assert out == "hello"
        assert any(
            "model=deepseek-chat" in rec
            and "tokens_in=10" in rec
            and "tokens_out=5" in rec
            and "duration_ms=" in rec
            for rec in handler.records
        ), handler.records
    finally:
        logging.getLogger().removeHandler(handler)


def test_deepseek_cost_estimate(monkeypatch):
    monkeypatch.setattr(settings, "llm_cost_per_1k_input", 1.0)
    monkeypatch.setattr(settings, "llm_cost_per_1k_output", 2.0)
    client = DeepSeekClient()
    client.client = _FakeOpenAI()
    handler = _capture()
    try:
        client.generate("p")
        assert any(
            "cost_cny=0.0200" in rec for rec in handler.records
        ), handler.records
    finally:
        logging.getLogger().removeHandler(handler)
