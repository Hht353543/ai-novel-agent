"""DeepSeek 调用封装模块。

使用 OpenAI SDK 兼容模式访问 DeepSeek API。
"""

import json
import logging
import re
from typing import Any

from openai import OpenAI

from app.config import settings

logger = logging.getLogger(__name__)


class DeepSeekClient:
    """DeepSeek Chat 客户端封装。"""

    def __init__(self):
        self.api_key = settings.deepseek_api_key
        self.client = (
            OpenAI(
                api_key=self.api_key,
                base_url=settings.deepseek_base_url,
                timeout=settings.deepseek_timeout,
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

        request_kwargs: dict[str, Any] = {
            "model": settings.deepseek_model,
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
            request_kwargs["response_format"] = {"type": "json_object"}

        response = self.client.chat.completions.create(
            **request_kwargs,
        )
        content = response.choices[0].message.content or ""
        logger.info("DeepSeek 调用完成，输出 %d 字符", len(content))
        return content

    def generate_json(self, prompt: str) -> dict[str, Any]:
        """调用 DeepSeek 并解析为 JSON 对象（带容错与自动修复）。

        首次解析失败时，若配置开启自动修复（默认开启），会额外调用一次
        DeepSeek 让模型修复 JSON；修复仍失败则抛出原始解析异常。
        """
        raw = self.generate(prompt)
        try:
            return parse_json_response(raw)
        except ValueError:
            if not settings.deepseek_auto_repair_json:
                raise
            logger.warning("首次 JSON 解析失败，尝试让模型修复一次...")
            repaired = self._repair_json(raw)
            return parse_json_response(repaired)

    def _repair_json(self, raw: str) -> str:
        """让模型把残缺/带噪声的输出修复为纯 JSON（消耗一次额外调用）。"""
        repair_prompt = (
            "你是一个严格的 JSON 修复助手。下面是另一次大模型生成的内容，"
            "它本应是一个合法的 JSON 对象，但解析失败（可能被截断或混入了解释文字）。\n"
            "请只输出修复后的完整合法 JSON 对象，不要输出任何解释、代码块标记或多余文字。\n\n"
            f"需要修复的内容：\n{raw[:6000]}"
        )
        repaired = self.generate(repair_prompt)
        logger.info("JSON 修复调用完成，输出 %d 字符", len(repaired))
        return repaired

    def generate_json_array(
        self,
        prompt: str,
        json_mode: bool = False,
    ) -> list[Any]:
        """调用 DeepSeek 并解析为「标题数组」。

        兼容模型输出两种形态：
        - 顶层数组：["标题1", "标题2", ...]
        - 对象：{"titles": ["标题1", ...]} 或 {"title": "标题"}

        默认使用纯文本模式（json_mode=False）：部分模型在强制
        json_object 模式下可能返回空对象，纯文本模式更稳定。

        解析失败时同样走自动修复（与 generate_json 一致）。
        """
        raw = self.generate(prompt, json_mode=json_mode)
        try:
            return parse_json_array_response(raw)
        except ValueError:
            if not settings.deepseek_auto_repair_json:
                raise
            logger.warning("标题数组解析失败，尝试让模型修复一次...")
            repaired = self._repair_json(raw)
            return parse_json_array_response(repaired)


def parse_json_response(raw: str) -> dict[str, Any]:
    """解析模型输出为 JSON，兼容代码块、前后缀文字、宽松引号等常见噪声。

    依次尝试：
    1. 直接解析；
    2. 去掉 ```json ... ``` 代码块后解析；
    3. 截取第一个 { 到最后一个 } 后解析；
    4. 对候选文本依次做：单引号宽松、去尾逗号、清控制字符、截断补全；
    5. raw_decode 从头扫描，解析第一个完整 JSON 对象。

    全部失败时记录原始内容（便于排查），并抛出带样本的异常。
    """
    text = raw.strip()

    candidates: list[str] = [text]

    # 代码块包裹：```json ... ``` / ```JSON ... ``` / ``` ... ```
    fence = re.search(r"```(?:json|JSON)?\s*(.*?)\s*```", text, re.S)
    if fence:
        candidates.append(fence.group(1).strip())

    # 截取首个 { 到末个 }
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        candidates.append(text[start : end + 1].strip())

    for candidate in candidates:
        if not candidate:
            continue
        # 1) 直接解析
        parsed = _try_load(candidate)
        if parsed is not None:
            return parsed
        # 2) 单引号宽松修复（把 ' 替换为 "，保留已转义引号）
        parsed = _try_load(_loose_quotes(candidate))
        if parsed is not None:
            return parsed
        # 3) 常见尾部逗号修复
        parsed = _try_load(_fix_trailing_commas(candidate))
        if parsed is not None:
            return parsed
        # 4) 清理非法控制字符
        parsed = _try_load(_strip_control_chars(candidate))
        if parsed is not None:
            return parsed
        # 5) 截断补全（补引号 / ] / }）
        parsed = _try_load(_repair_truncated_json(candidate))
        if parsed is not None:
            return parsed
        # 6) 组合修复：宽松引号 + 尾逗号 + 控制字符 + 截断补全
        combined = _repair_truncated_json(
            _strip_control_chars(_fix_trailing_commas(_loose_quotes(candidate)))
        )
        parsed = _try_load(combined)
        if parsed is not None:
            return parsed

    # 兜底：raw_decode 从头扫描，尝试解析第一个完整 JSON
    parsed = _try_raw_decode(text)
    if parsed is not None:
        return parsed

    # 记录原始内容便于诊断（日志 + 异常信息）
    logger.error("JSON 解析失败，原始输出前 1000 字符: %s", raw[:1000])
    raise ValueError(
        "DeepSeek 返回内容不是合法 JSON（可能因 max_tokens 截断或混入解释文字）。"
        f"已尝试多种修复均失败。原始输出前 500 字符：{raw[:500]}"
    )


def _try_load(text: str) -> dict[str, Any] | None:
    """尝试 json.loads，成功且结果为 dict 时返回，否则返回 None。"""
    try:
        obj = json.loads(text)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
    return obj if isinstance(obj, dict) else None


def _try_raw_decode(text: str) -> dict[str, Any] | None:
    """用 raw_decode 从头扫描，返回第一个能完整解码的 JSON 对象。"""
    decoder = json.JSONDecoder()
    idx = 0
    while True:
        idx = text.find("{", idx)
        if idx == -1:
            return None
        try:
            obj, end = decoder.raw_decode(text[idx:])
        except json.JSONDecodeError:
            idx += 1
            continue
        if isinstance(obj, dict):
            return obj
        idx += end


def parse_json_array_response(raw: str) -> list[Any]:
    """解析模型输出为标题数组（兼容对象包装与顶层数组）。

    依次尝试：
    1. 顶层 JSON 数组；
    2. 对象中的 titles / title / chapters 字段；
    3. 代码块、前后缀剥离后重复上述尝试。
    """
    text = raw.strip()
    candidates: list[str] = [text]
    fence = re.search(r"```(?:json|JSON)?\s*(.*?)\s*```", text, re.S)
    if fence:
        candidates.append(fence.group(1).strip())

    # 1) 顶层数组
    for candidate in candidates:
        try:
            obj = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, list):
            return [str(item).strip() for item in obj if str(item).strip()]

    # 2) 对象中的标题字段
    for candidate in candidates:
        try:
            obj = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            for key in ("titles", "title", "chapters"):
                val = obj.get(key)
                if isinstance(val, list):
                    items = [str(item).strip() for item in val if str(item).strip()]
                    if items:
                        return items
                elif isinstance(val, str) and val.strip():
                    return [val.strip()]

    # 3) 宽松修复后重试
    for candidate in candidates:
        for cleaned in (
            _loose_quotes(candidate),
            _fix_trailing_commas(candidate),
            _strip_control_chars(candidate),
            _repair_truncated_json(candidate),
        ):
            try:
                obj = json.loads(cleaned)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, list):
                return [str(item).strip() for item in obj if str(item).strip()]
            if isinstance(obj, dict):
                for key in ("titles", "title", "chapters"):
                    val = obj.get(key)
                    if isinstance(val, list) and val:
                        return [str(item).strip() for item in val if str(item).strip()]
                    if isinstance(val, str) and val.strip():
                        return [val.strip()]

    logger.error("标题数组解析失败，原始输出前 1000 字符: %s", raw[:1000])
    raise ValueError(
        "DeepSeek 返回内容无法解析为标题数组（可能被截断或格式不符）。"
        f"原始输出前 300 字符：{raw[:300]}"
    )


def _loose_quotes(text: str) -> str:
    """将未转义的单引号替换为双引号（简单启发式，仅作兜底）。"""
    out: list[str] = []
    in_string = False
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == "\\" and i + 1 < len(text):
            out.extend([ch, text[i + 1]])
            i += 2
            continue
        if ch == '"':
            in_string = not in_string
            out.append(ch)
        elif ch == "'" and not in_string:
            out.append('"')
        else:
            out.append(ch)
        i += 1
    return "".join(out)


def _fix_trailing_commas(text: str) -> str:
    """去除对象/数组中的尾部逗号（如 {"a":1,} -> {"a":1}）。"""
    return re.sub(r",(\s*[}\]])", r"\1", text)


def _strip_control_chars(text: str) -> str:
    """删除 JSON 字符串值中常见的非法控制字符（兜底清洗）。"""
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)


def _repair_truncated_json(text: str) -> str:
    """对截断的 JSON 做启发式补全。

    适用场景：模型输出被 max_tokens 截断，例如
    {"title":"...","chapters":["第一章 废柴"  —— 缺少闭合引号/中括号/大括号。

    策略：找到第一个 {，扫描引号与括号配对，若字符串未闭合则补引号，
    再按括号栈反向补全 ] / }。
    """
    start = text.find("{")
    if start == -1:
        return text
    body = text[start:]

    stack: list[str] = []
    in_string = False
    escaped = False
    i = 0
    while i < len(body):
        ch = body[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            i += 1
            continue
        if ch == '"':
            in_string = True
        elif ch in "{[":
            stack.append(ch)
        elif ch in "}]":
            if stack:
                stack.pop()
        i += 1

    repaired = body
    if in_string:
        repaired += '"'
    closing = "".join("]" if ch == "[" else "}" for ch in reversed(stack))
    return repaired + closing
