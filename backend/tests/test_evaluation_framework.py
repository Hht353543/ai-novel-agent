"""Evaluation 框架测试：指标、数据集、Mock Provider。"""

import json
import os
import tempfile
from pathlib import Path

from evaluation.metrics import (
    context_relevance,
    hit_rate,
    precision_at_k,
    quality_score,
    reviewer_detection_rate,
    task_success,
)
from evaluation.mock_provider import (
    MockLLM,
    MockRetriever,
    TrackingLLM,
    estimate_tokens,
)


def _rows():
    return [
        {"hit": True, "precision@3": 0.67, "relevance": 0.5},
        {"hit": False, "precision@3": 0.0, "relevance": 0.2},
        {"hit": True, "precision@3": 1.0, "relevance": 0.8},
    ]


def test_hit_rate():
    assert hit_rate(_rows()) == 2 / 3


def test_precision_at_k():
    assert precision_at_k(_rows(), 3) == (0.67 + 0.0 + 1.0) / 3


def test_context_relevance():
    assert context_relevance(_rows()) == (0.5 + 0.2 + 0.8) / 3


def test_task_success_and_reviewer_detection():
    results = [
        {"status": "success", "injection": True, "review": True,
         "reviewer_detected": True},
        {"status": "success", "injection": True, "review": True,
         "reviewer_detected": False},
        {"status": "error", "injection": True, "review": False,
         "reviewer_detected": False},
        {"status": "success", "injection": False, "review": True,
         "reviewer_detected": False},
    ]
    assert task_success(results) == 0.75
    assert reviewer_detection_rate(results) == 0.5


def test_quality_score():
    text = (
        "沈惊澜在县城觉醒武道熔炉，刀光剑影中破开旧案迷局。"
        "楚云岚负剑而立，血煞宗弟子步步逼近。"
    ) * 8
    assert quality_score(text, ["沈惊澜"]) == 100
    assert quality_score("", ["沈惊澜"]) < 100


def test_estimate_tokens():
    assert estimate_tokens("中" * 10) == 10
    assert estimate_tokens("abcd") == 1


def test_tracking_llm_counts_tokens():
    llm = TrackingLLM(MockLLM())
    llm.generate("写一段话", json_mode=False)
    llm.generate_json("规划小说", system_prompt="planner")
    assert llm.calls == 2
    assert llm.input_tokens > 0
    assert llm.output_tokens > 0
    assert llm.total_cost == 0.0


def test_mock_retriever_scores_and_filters():
    documents = [
        {"source": "世界观/a.txt", "category": "世界观",
         "content": "修炼境界分为九重"},
        {"source": "世界观/b.txt", "category": "世界观",
         "content": "夜市小吃闻名"},
    ]
    retriever = MockRetriever(documents, top_k=1)
    results = retriever.retrieve("修炼境界突破", ["世界观"])
    assert len(results) == 1
    assert results[0]["source"] == "世界观/a.txt"


def test_datasets_have_required_shape():
    base = Path(__file__).resolve().parents[1] / "evaluation" / "datasets"
    retrieval = json.loads(
        (base / "retrieval.json").read_text(encoding="utf-8")
    )
    agent = json.loads((base / "agent.json").read_text(encoding="utf-8"))
    knowledge = json.loads(
        (base / "knowledge.json").read_text(encoding="utf-8")
    )
    assert len(retrieval["scenarios"]) >= 4
    assert len(agent["scenarios"]) >= 2
    assert len(knowledge["documents"]) >= 8


def test_real_retrievers_agree_on_dataset(tmp_path):
    """真实 Budget/Keyword 检索器在评测知识库上均可运行且能命中。"""

    from app.config import settings
    from app.rag.retriever import BudgetRetriever, KeywordRetriever

    base = Path(__file__).resolve().parents[1] / "evaluation" / "datasets"
    knowledge = json.loads(
        (base / "knowledge.json").read_text(encoding="utf-8")
    )["documents"]
    for doc in knowledge:
        path = tmp_path / doc["source"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(doc["content"], encoding="utf-8")

    saved = settings.knowledge_dir
    settings.knowledge_dir = tmp_path
    try:
        for retriever in (BudgetRetriever(), KeywordRetriever(top_k=3)):
            results = retriever.retrieve(
                "修炼境界突破", ["世界观", "other"]
            )
            assert isinstance(results, list)
            assert len(results) > 0
    finally:
        settings.knowledge_dir = saved
