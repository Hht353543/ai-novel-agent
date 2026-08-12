"""DeepSeek LLM Provider：封装 DeepSeekClient，作为 service 的默认注入实现。"""

import logging
import time
from typing import Any, Iterator

from openai import APIConnectionError, APIError, APITimeoutError

from app.config import settings
from app.llm.deepseek import DeepSeekClient

logger = logging.getLogger(__name__)


def _is_retryable(exc: Exception) -> bool:
    """判断异常是否值得重试/降级：连接/超时与 429、5xx。"""
    if isinstance(exc, (APIConnectionError, APITimeoutError)):
        return True
    if isinstance(exc, APIError):
        return getattr(exc, "status_code", None) in (429, 500, 502, 503, 504)
    return False


class DeepSeekProvider:
    """DeepSeek 实现：指数退避重试 + 模型列表降级。"""

    def __init__(self, client: DeepSeekClient | None = None):
        self._client = client or DeepSeekClient()

    @property
    def available(self) -> bool:
        return self._client.available

    def _invoke(self, call, *args: Any, **kwargs: Any) -> Any:
        """带重试与模型降级地调用客户端方法。

        对 429/5xx/连接/超时：同模型指数退避重试，耗尽后切换下一个模型；
        其它异常直接抛出（不重试、不降级，避免掩盖参数错误）。
        """
        models = settings.deepseek_models or [settings.deepseek_model]
        last_error: Exception | None = None
        for model in models:
            for attempt in range(settings.llm_max_retries + 1):
                try:
                    return call(*args, **kwargs, model=model)
                except Exception as exc:  # noqa: BLE001 - 统一重试判定
                    last_error = exc
                    if not _is_retryable(exc):
                        raise
                    if attempt < settings.llm_max_retries:
                        delay = min(
                            settings.llm_retry_base_delay * (2**attempt),
                            settings.llm_retry_max_delay,
                        )
                        logger.warning(
                            "DeepSeek 调用失败（%s，模型 %s），%.1fs 后重试 %d/%d",
                            exc,
                            model,
                            delay,
                            attempt + 1,
                            settings.llm_max_retries,
                        )
                        time.sleep(delay)
            logger.warning("模型 %s 重试耗尽，尝试降级", model)
        raise last_error  # type: ignore[misc]

    def generate(
        self,
        prompt: str,
        json_mode: bool = True,
        system_prompt: str | None = None,
    ) -> str:
        return self._invoke(
            self._client.generate,
            prompt,
            json_mode=json_mode,
            system_prompt=system_prompt,
        )

    def generate_json(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        return self._invoke(
            self._client.generate_json,
            prompt,
            system_prompt=system_prompt,
        )

    def generate_json_array(
        self,
        prompt: str,
        json_mode: bool = False,
        system_prompt: str | None = None,
    ) -> list[Any]:
        return self._invoke(
            self._client.generate_json_array,
            prompt,
            json_mode=json_mode,
            system_prompt=system_prompt,
        )

    def generate_stream(
        self,
        prompt: str,
        json_mode: bool = True,
        system_prompt: str | None = None,
    ) -> Iterator[str]:
        # 流式调用暂不做重试/降级（中途重试会重复输出）；单次直连
        return self._client.generate_stream(
            prompt,
            json_mode=json_mode,
            system_prompt=system_prompt,
        )
