"""LLM 调用统一封装。

把同步 LLM 调用放到线程池执行，并把常见异常归一为 LLMError，
供各业务 service 统一处理错误语义（connection / api / parse / unknown）。
"""

import asyncio
from typing import Any, Callable

from openai import APIConnectionError, APIError, APITimeoutError


class LLMError(Exception):
    """归一化的 LLM 调用错误。"""

    def __init__(self, kind: str, message: str):
        super().__init__(message)
        self.kind = kind
        self.message = message


async def run_llm(func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """在线程池中执行同步 LLM 调用，并把常见异常归一为 LLMError。

    Args:
        func: 同步 LLM 方法（如 DeepSeekClient.generate_json）。
        *args / **kwargs: 透传给 func 的参数。

    Returns:
        模型返回的原始结果（类型取决于 func）。

    Raises:
        LLMError: kind 为 connection / api / parse / unknown。
    """
    try:
        return await asyncio.to_thread(func, *args, **kwargs)
    except (APIConnectionError, APITimeoutError) as exc:
        raise LLMError("connection", f"无法连接到 DeepSeek API：{exc}") from exc
    except APIError as exc:
        raise LLMError("api", f"DeepSeek API 返回错误：{exc}") from exc
    except ValueError as exc:
        raise LLMError("parse", str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - 统一为 unknown
        raise LLMError("unknown", str(exc)) from exc


def llm_error_message(exc: LLMError, subject: str) -> str:
    """生成通用的用户可见错误文案。

    连接/API 错误直接使用归一化说明；其余类型按业务前缀包装。
    """
    if exc.kind in ("connection", "api"):
        return exc.message
    return f"{subject}失败：{exc.message}"
