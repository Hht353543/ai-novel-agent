"""Token 预算估算与上下文裁剪工具。"""

from app.config import settings

# 除知识库外其它输入的保守预留（附件上限 15000 + 大纲/上文/系统提示余量）
KNOWLEDGE_RESERVE_CHARS = 16000


def estimate_tokens(text: str) -> int:
    """保守估算文本 token 数。

    中日韩字符按 1 字符 ≈ 1 token（略高于实际，留安全余量）；
    其它字符按 4 字符 ≈ 1 token。
    """
    cjk = 0
    for ch in text:
        if "\u4e00" <= ch <= "\u9fff" or "\u3400" <= ch <= "\u4dbf":
            cjk += 1
    other = len(text) - cjk
    return cjk + (other + 3) // 4


def available_input_tokens() -> int:
    """当前模型可用的输入 token 预算（上下文 - 输出上限 - 安全余量）。"""
    return max(
        1,
        settings.llm_context_tokens
        - settings.deepseek_max_tokens
        - settings.llm_budget_safety_margin,
    )


def knowledge_char_budget() -> int:
    """知识库总注入字符预算。

    取「配置上限」与「按上下文动态计算的上限」的较小值；
    预留 KNOWLEDGE_RESERVE_CHARS 给附件、大纲、上文与系统提示。
    """
    dynamic = available_input_tokens() - KNOWLEDGE_RESERVE_CHARS
    return max(0, min(settings.knowledge_max_total_chars, dynamic))


def truncate_with_note(text: str, limit: int, reason: str) -> str:
    """按字符上限截断，并在末尾附加说明；未超限时原样返回。"""
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n……（{reason}）"
