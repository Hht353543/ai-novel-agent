"""评测指标：检索质量与 Agent 质量。"""

from __future__ import annotations

from typing import Any


def hit_rate(results: list[dict[str, Any]]) -> float:
    """命中率：每个查询是否检索到至少一个相关文档。"""

    hits = [r["hit"] for r in results]
    return sum(hits) / max(1, len(hits))


def precision_at_k(results: list[dict[str, Any]], k: int = 3) -> float:
    """Precision@K：Top-K 中相关文档占比的平均值。"""

    values = [r.get(f"precision@{k}", 0.0) for r in results]
    return sum(values) / max(1, len(values))


def context_relevance(results: list[dict[str, Any]]) -> float:
    """上下文相关性：检索结果与查询的文本重合度（0-1）。"""

    scores = [r.get("relevance", 0.0) for r in results]
    return sum(scores) / max(1, len(scores))


def task_success(results: list[dict[str, Any]]) -> float:
    """任务成功率：status == success 的占比。"""

    ok = [r for r in results if r.get("status") == "success"]
    return len(ok) / max(1, len(results))


def reviewer_detection_rate(results: list[dict[str, Any]]) -> float:
    """审校检出率：注入场景中被 Reviewer 标记 needs_fix 的占比。"""

    injection = [r for r in results if r.get("injection") and r.get("review")]
    if not injection:
        return 0.0
    detected = [r for r in injection if r.get("reviewer_detected")]
    return len(detected) / len(injection)


def quality_score(chapter_text: str, expected_chars: list[str]) -> int:
    """轻量质量分（mock/规则）：长度、角色一致性、文本多样性。"""

    score = 0
    text = chapter_text or ""
    if len(text) >= 200:
        score += 40
    elif len(text) >= 100:
        score += 25
    else:
        score += 10

    missing = [c for c in expected_chars if c and c not in text]
    score += max(0, 40 - 20 * len(missing))

    bigrams = {
        text[i : i + 2] for i in range(max(0, len(text) - 1))
    }
    if len(bigrams) > 40:
        score += 20
    else:
        score += 10
    return min(100, score)


__all__ = [
    "hit_rate",
    "precision_at_k",
    "context_relevance",
    "task_success",
    "reviewer_detection_rate",
    "quality_score",
]
