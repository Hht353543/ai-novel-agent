"""模型 JSON 输出容错解析模块。

从 deepseek.py 中拆出，独立承担「解析 + 修复」职责：
- parse_json_response：解析 JSON 对象；
- parse_json_array_response：解析标题数组（兼容对象包装）；
- 其余 _ 开头函数为内部修复工具。
"""

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


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
