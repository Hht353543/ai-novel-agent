"""DeepSeek 调用封装模块。

使用 OpenAI SDK 兼容模式访问 DeepSeek API；JSON 容错解析由 json_parser 承担。
"""

import logging
import time
from typing import Any, Iterator

from openai import OpenAI

from app.config import settings
from app.llm.json_parser import parse_json_array_response, parse_json_response

logger = logging.getLogger(__name__)

# 修复 Prompt 最多携带的原始输出字符数（过长内容修复时截断，避免撑爆上下文）
REPAIR_JSON_MAX_CHARS = 6000


def _build_request_kwargs(
    prompt: str,
    json_mode: bool,
    system_prompt: str | None,
    model: str | None,
    *,
    stream: bool = False,
) -> dict[str, Any]:
    """构造 DeepSeek Chat 请求参数（generate / generate_stream 共用）。"""
    kwargs: dict[str, Any] = {
        "model": model or settings.deepseek_model,
        "messages": [
            {
                "role": "system",
                "content": system_prompt
                or "你是一位专业的网络小说大纲策划助手，严格遵循用户给出的输出格式。",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": settings.deepseek_temperature,
        "max_tokens": settings.deepseek_max_tokens,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    if stream:
        kwargs["stream"] = True
    return kwargs


class DeepSeekClient:
    """DeepSeek Chat 客户端封装。"""

    def __init__(self):
        self.api_key = settings.deepseek_api_key
        self.client = (
            OpenAI(
                api_key=self.api_key,
                base_url=settings.deepseek_base_url,
                timeout=(
                    settings.deepseek_connect_timeout,
                    settings.deepseek_timeout,
                ),
            )
            if self.api_key
            else None
        )

    @property
    def available(self) -> bool:
        """是否已配置 API Key。"""
        return self.client is not None

    def generate(
        self,
        prompt: str,
        json_mode: bool = True,
        system_prompt: str | None = None,
        model: str | None = None,
    ) -> str:
        """调用 DeepSeek 生成文本。

        Args:
            prompt: 完整的提示词。
            json_mode: 是否使用 JSON 输出模式。正文生成等纯文本场景应传 False，
               否则 DeepSeek 会要求 Prompt 中出现 "json" 字样并可能报 400。
            system_prompt: 自定义 system 角色；为 None 时使用默认大纲助手角色。

        Returns:
            模型返回的原始文本。
        """
        if not self.available:
            raise RuntimeError("未配置 DEEPSEEK_API_KEY，无法调用 DeepSeek API")

        request_kwargs = _build_request_kwargs(
            prompt, json_mode, system_prompt, model
        )

        start = time.perf_counter()
        response = self.client.chat.completions.create(
            **request_kwargs,
        )
        duration_ms = (time.perf_counter() - start) * 1000
        content = response.choices[0].message.content or ""
        usage = response.usage
        if usage:
            cost = (
                usage.prompt_tokens / 1000 * settings.llm_cost_per_1k_input
                + usage.completion_tokens / 1000 * settings.llm_cost_per_1k_output
            )
            logger.info(
                "DeepSeek 调用完成 model=%s output_chars=%d "
                "tokens_in=%s tokens_out=%s total=%s duration_ms=%.0f cost_cny=%.4f",
                request_kwargs["model"],
                len(content),
                usage.prompt_tokens,
                usage.completion_tokens,
                usage.total_tokens,
                duration_ms,
                cost,
            )
        else:
            logger.info(
                "DeepSeek 调用完成 model=%s output_chars=%d duration_ms=%.0f",
                request_kwargs["model"],
                len(content),
                duration_ms,
            )
        return content

    def generate_stream(
        self,
        prompt: str,
        json_mode: bool = True,
        system_prompt: str | None = None,
        model: str | None = None,
    ) -> Iterator[str]:
        """流式调用 DeepSeek，逐段产出文本增量。"""
        if not self.available:
            raise RuntimeError("未配置 DEEPSEEK_API_KEY，无法调用 DeepSeek API")

        request_kwargs = _build_request_kwargs(
            prompt, json_mode, system_prompt, model, stream=True
        )

        stream = self.client.chat.completions.create(**request_kwargs)
        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    def generate_json(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        """调用 DeepSeek 并解析为 JSON 对象（带容错与自动修复）。

        首次解析失败时，若配置开启自动修复（默认开启），会额外调用一次
        DeepSeek 让模型修复 JSON；修复仍失败则抛出原始解析异常。
        """
        raw = self.generate(prompt, system_prompt=system_prompt, model=model)
        try:
            return parse_json_response(raw)
        except ValueError:
            if not settings.deepseek_auto_repair_json:
                raise
            logger.warning("首次 JSON 解析失败，尝试让模型修复一次...")
            repaired = self._repair_json(raw, model=model)
            return parse_json_response(repaired)

    def _repair_json(self, raw: str, model: str | None = None) -> str:
        """让模型把残缺/带噪声的输出修复为纯 JSON（消耗一次额外调用）。"""
        repair_prompt = (
            "你是一个严格的 JSON 修复助手。下面是另一次大模型生成的内容，"
            "它本应是一个合法的 JSON 对象，但解析失败（可能被截断或混入了解释文字）。\n"
            "请只输出修复后的完整合法 JSON 对象，不要输出任何解释、代码块标记或多余文字。\n\n"
            f"需要修复的内容：\n{raw[:REPAIR_JSON_MAX_CHARS]}"
        )
        repaired = self.generate(repair_prompt, model=model)
        logger.info("JSON 修复调用完成，输出 %d 字符", len(repaired))
        return repaired

    def generate_json_array(
        self,
        prompt: str,
        json_mode: bool = False,
        system_prompt: str | None = None,
        model: str | None = None,
    ) -> list[Any]:
        """调用 DeepSeek 并解析为「标题数组」。

        兼容模型输出两种形态：
        - 顶层数组：["标题1", "标题2", ...]
        - 对象：{"titles": ["标题1", ...]} 或 {"title": "标题"}

        默认使用纯文本模式（json_mode=False）：部分模型在强制
        json_object 模式下可能返回空对象，纯文本模式更稳定。

        解析失败时同样走自动修复（与 generate_json 一致）。
        """
        raw = self.generate(
            prompt,
            json_mode=json_mode,
            system_prompt=system_prompt,
            model=model,
        )
        try:
            return parse_json_array_response(raw)
        except ValueError:
            if not settings.deepseek_auto_repair_json:
                raise
            logger.warning("标题数组解析失败，尝试让模型修复一次...")
            repaired = self._repair_json(raw, model=model)
            return parse_json_array_response(repaired)
