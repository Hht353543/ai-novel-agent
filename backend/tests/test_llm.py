"""LLM 调用归一化、预算与 Provider 重试测试。"""

import time

import httpx
import pytest
from openai import APIConnectionError, APIError

from app.config import settings
from app.llm.budget import estimate_tokens, truncate_with_note
from app.llm.call import LLMError, llm_error_message, run_llm
from app.llm.deepseek_provider import DeepSeekProvider
from app.llm.mock_provider import MockProvider


class RetryableError(Exception):
    def __init__(self, retryable=True):
        super().__init__("x")
        self.retryable = retryable


def test_run_llm_normalizes_errors():
    async def check(fn, expected_kind):
        with pytest.raises(LLMError) as exc_info:
            await run_llm(fn)
        assert exc_info.value.kind == expected_kind

    async def main():
        def conn():
            raise APIConnectionError(request=httpx.Request("POST", "https://x"))

        def api():
            exc = APIError.__new__(APIError)
            exc.status_code = 429
            raise exc

        def parse():
            raise ValueError("bad json")

        def unknown():
            raise RuntimeError("boom")

        await check(conn, "connection")
        await check(api, "api")
        await check(parse, "parse")
        await check(unknown, "unknown")

    import asyncio

    asyncio.run(main())


def test_llm_error_message():
    assert llm_error_message(LLMError("connection", "无法连接"), "章节生成") == "无法连接"
    assert llm_error_message(LLMError("unknown", "x"), "章节生成") == "章节生成失败：x"


def test_estimate_tokens():
    assert estimate_tokens("你好世界") == 4
    assert estimate_tokens("abcd") == 1
    assert estimate_tokens("你好abc") == 3


def test_truncate_with_note():
    assert truncate_with_note("abc", 10, "太长") == "abc"
    assert truncate_with_note("abcdef", 3, "太长") == "abc\n……（太长）"


def test_mock_provider_demo_and_success():
    assert MockProvider().available is False
    assert MockProvider(available=True, generate_result="x").generate("p") == "x"
    assert MockProvider(available=True, generate_json_result={"a": 1}).generate_json("p") == {"a": 1}
    with pytest.raises(ValueError):
        MockProvider(available=True).generate_json("p")


def test_provider_retry_fallback(monkeypatch):
    import app.llm.deepseek_provider as dp

    monkeypatch.setattr(settings, "deepseek_models", ["m1", "m2"])
    monkeypatch.setattr(settings, "llm_max_retries", 2)
    monkeypatch.setattr(settings, "llm_retry_base_delay", 0.01)
    monkeypatch.setattr(settings, "llm_retry_max_delay", 0.05)
    monkeypatch.setattr(dp, "_is_retryable", lambda exc: exc.retryable)
    monkeypatch.setattr(time, "sleep", lambda s: None)

    provider = DeepSeekProvider()
    calls = []

    def stub(prompt, model=None):
        calls.append(model)
        if len(calls) < 3:
            raise RetryableError()
        return f"ok-{model}"

    assert provider._invoke(stub, "p") == "ok-m1"
    assert calls == ["m1", "m1", "m1"]

    calls.clear()

    def stub_fallback(prompt, model=None):
        calls.append(model)
        if model == "m1":
            raise RetryableError()
        return "ok-m2"

    assert provider._invoke(stub_fallback, "p") == "ok-m2"
    assert calls == ["m1", "m1", "m1", "m2"]
