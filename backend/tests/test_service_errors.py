"""service 统一错误响应助手测试。"""

import logging

from pydantic import BaseModel

from app.llm.call import LLMError
from app.services.errors import llm_error_response, unexpected_error_response


class DummyResponse(BaseModel):
    success: bool = True
    status: str = "success"
    message: str = ""


def _logger():
    return logging.getLogger("test_service_errors")


def test_llm_error_response_uses_default_message():
    resp = llm_error_response(
        DummyResponse, _logger(), LLMError("unknown", "boom"), "章节生成"
    )
    assert resp.success is False
    assert resp.status == "error"
    assert resp.message == "章节生成失败：boom"


def test_llm_error_response_accepts_custom_message_and_extra():
    resp = llm_error_response(
        DummyResponse,
        _logger(),
        LLMError("connection", "无法连接"),
        "大纲生成",
        message="自定义提示",
    )
    assert resp.message == "自定义提示"


def test_unexpected_error_response_keeps_subject_prefix():
    resp = unexpected_error_response(
        DummyResponse, _logger(), RuntimeError("x"), "标题生成"
    )
    assert resp.success is False
    assert resp.status == "error"
    assert resp.message == "标题生成失败：x"
