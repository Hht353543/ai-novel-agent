"""service 层统一错误响应构造。

各生成服务此前重复书写同一套「记录日志 + 返回结构化错误响应」的脚手架，
本模块集中该语义，避免 success=False / status="error" / 日志格式四处漂移。
"""

import logging
import traceback
from typing import Type, TypeVar

from app.llm.call import LLMError, llm_error_message

T = TypeVar("T")


def llm_error_response(
    response_cls: Type[T],
    logger: logging.Logger,
    exc: LLMError,
    subject: str,
    message: str | None = None,
    **extra,
) -> T:
    """LLM 调用失败：记录归一化错误并返回结构化错误响应。

    message 缺省时使用 llm_error_message 的统一文案；
    需要特化文案（如大纲生成对 connection/parse 的专属提示）时显式传入。
    extra 透传给响应构造函数（如大纲响应携带 context/outline/raw）。
    """
    logger.error("DeepSeek 调用失败(%s): %s", exc.kind, exc.message)
    return response_cls(
        success=False,
        status="error",
        message=message if message is not None else llm_error_message(exc, subject),
        **extra,
    )


def unexpected_error_response(
    response_cls: Type[T],
    logger: logging.Logger,
    exc: Exception,
    subject: str,
    message: str | None = None,
    log_traceback: bool = False,
    **extra,
) -> T:
    """未预期异常：记录堆栈并返回结构化错误响应（不向客户端泄漏堆栈）。"""
    if log_traceback:
        logger.error("%s异常: %s\n%s", subject, exc, traceback.format_exc())
    else:
        logger.exception("%s异常", subject)
    return response_cls(
        success=False,
        status="error",
        message=message if message is not None else f"{subject}失败：{exc}",
        **extra,
    )
