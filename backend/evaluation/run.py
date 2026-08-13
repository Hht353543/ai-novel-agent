"""Evaluation Runner：检索质量 + Agent Benchmark（mock 默认，real 可选）。

用法（backend 目录下）：
    python -m evaluation.run
    EVAL_MODE=real DEEPSEEK_API_KEY=... python -m evaluation.run
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import tempfile
import time
from pathlib import Path
from typing import Any

from app.agents.orchestrator import NovelOrchestrator
from app.agents.protocol import PipelineRequest, PipelineResult
from app.agents.run_state import RunTracker, run_store
from app.config import settings
from app.rag.retriever import BudgetRetriever, KeywordRetriever
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
)


DATASETS = Path(__file__).resolve().parent / "datasets"
REPORTS = Path(__file__).resolve().parent / "reports"


def _load(name: str) -> dict[str, Any]:
    return json.loads((DATASETS / name).read_text(encoding="utf-8"))


def _overlap(query: str, content: str) -> float:
    q = set(query)
    c = set(content[:200])
    common = len(q & c)
    return common / max(1, len(q))


def _build_temp_knowledge() -> Path:
    """把评测知识库写入临时目录（类别目录结构），供真实检索器使用。"""

    knowledge = _load("knowledge.json")["documents"]
    tmp = Path(tempfile.mkdtemp(prefix="novel-eval-kb-"))
    for doc in knowledge:
        path = tmp / doc["source"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(doc["content"], encoding="utf-8")
    return tmp


def _retrieval_metrics(variant: str, top_k: int) -> dict[str, Any]:
    """对每个查询分别用真实 BudgetRetriever / KeywordRetriever 检索。"""

    data = _load("retrieval.json")
    knowledge_dir = _build_temp_knowledge()
    saved_dir = settings.knowledge_dir
    settings.knowledge_dir = knowledge_dir
    rows = []
    try:
        if variant == "budget":
            retriever = BudgetRetriever()
        else:
            retriever = KeywordRetriever(top_k=top_k)
        for sc in data["scenarios"]:
            query = sc["query"]
            relevant = set(sc["relevant"])
            results = retriever.retrieve(query, sc["categories"])
            sources = [r["source"] for r in results[:top_k]]
            hits = [s in relevant for s in sources]
            rows.append(
                {
                    "query": query,
                    "retrieved": sources,
                    "hit": any(hits),
                    f"precision@{top_k}": sum(hits) / max(1, top_k),
                    "relevance": (
                        sum(
                            _overlap(query, r["content"])
                            for r in results[:top_k]
                        )
                        / max(1, top_k)
                    ),
                }
            )
    finally:
        settings.knowledge_dir = saved_dir
    return {
        "variant": variant,
        "hit_rate": hit_rate(rows),
        f"precision@{top_k}": precision_at_k(rows, top_k),
        "context_relevance": context_relevance(rows),
        "rows": rows,
    }


def _agent_scenario(
    llm: Any,
    retriever: Any,
    scenario: dict[str, Any],
    *,
    memory: bool,
    review: bool,
) -> dict[str, Any]:
    """运行一次 Pipeline，返回结构化指标。"""

    req = scenario["request"]
    request = PipelineRequest(
        title=req.get("title", ""),
        genre=req.get("genre", "武侠"),
        theme=req.get("theme", ""),
        keywords=req.get("keywords", ""),
        requirement=req.get("requirement", ""),
        extra_requirements=req.get("extra_requirements", ""),
        volume_index=0,
        chapter_index=0,
        target_length=req.get("target_length", 800),
        with_review=review,
        max_revisions=1,
    )
    orch = NovelOrchestrator(llm=llm, retriever=retriever)
    run_id = f"eval-{scenario['id']}-{int(time.time() * 1000)}"
    run_store.create(run_id)
    tracker = RunTracker(run_store, run_id)

    saved_memory = settings.agent_memory_enabled
    saved_timeline = settings.agent_timeline_enabled
    settings.agent_memory_enabled = memory
    settings.agent_timeline_enabled = memory
    try:
        result: PipelineResult = asyncio.run(
            orch.run_pipeline(
                request,
                tracker=tracker,
                run_id=run_id,
            )
        )
    finally:
        settings.agent_memory_enabled = saved_memory
        settings.agent_timeline_enabled = saved_timeline

    chapter_text = result.chapter.content if result.chapter else ""
    expected = scenario.get("expected_characters", [])
    injection = bool(scenario.get("injection"))
    return {
        "id": scenario["id"],
        "name": scenario.get("name", ""),
        "memory": memory,
        "review": review,
        "injection": injection,
        "status": result.status,
        "success": result.status == "success",
        "reviewer_detected": any(
            h.review is not None and not h.review.passed
            for h in result.revision_history
        ),
        "quality": quality_score(chapter_text, expected),
        "latency_ms": float(result.telemetry.get("duration_ms", 0.0)),
        "llm_calls": int(result.telemetry.get("llm_calls", 0)),
        "rag_calls": int(result.telemetry.get("rag_calls", 0)),
        "revisions": int(result.telemetry.get("revision_attempts", 0)),
        "tokens": (
            getattr(llm, "input_tokens", 0) + getattr(llm, "output_tokens", 0)
        ),
        "cost": float(getattr(llm, "total_cost", 0.0)),
    }


def _run_agent_benchmarks() -> dict[str, Any]:
    data = _load("agent.json")
    knowledge = _load("knowledge.json")["documents"]
    results: list[dict[str, Any]] = []
    top_k = 3

    retriever = MockRetriever(knowledge, top_k=top_k)
    for scenario in data["scenarios"]:
        for memory in (True, False):
            for review in (True, False):
                llm = TrackingLLM(MockLLM())
                row = _agent_scenario(
                    llm,
                    retriever,
                    scenario,
                    memory=memory,
                    review=review,
                )
                row["retriever"] = "keyword"
                results.append(row)
    return {
        "results": results,
        "summary": {
            "task_success": task_success(results),
            "reviewer_detection": reviewer_detection_rate(results),
            "avg_quality": statistics.mean([r["quality"] for r in results]),
            "avg_latency_ms": statistics.mean(
                [r["latency_ms"] for r in results]
            ),
            "avg_tokens": statistics.mean([r["tokens"] for r in results]),
            "total_cost": sum(r["cost"] for r in results),
        },
    }


def _make_llm(mode: str) -> Any:
    if mode == "real":
        from app.llm.deepseek_provider import DeepSeekProvider

        if not settings.deepseek_api_key:
            raise SystemExit("real 模式需要 DEEPSEEK_API_KEY")
        return TrackingLLM(
            DeepSeekProvider(),
            cost_per_1k_input=settings.llm_cost_per_1k_input,
            cost_per_1k_output=settings.llm_cost_per_1k_output,
        )
    return TrackingLLM(MockLLM())


def write_report(
    retrieval: list[dict[str, Any]],
    agent: dict[str, Any],
    mode: str,
) -> Path:
    REPORTS.mkdir(parents=True, exist_ok=True)
    path = REPORTS / "report.md"
    lines = [
        "# AI Novel Agent Evaluation Report",
        "",
        f"- Mode: `{mode}`",
        f"- Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Retrieval",
        "",
        "| variant | hit_rate | precision@3 | context_relevance |",
        "| --- | --- | --- | --- |",
    ]
    for r in retrieval:
        lines.append(
            f"| {r['variant']} | {r['hit_rate']:.2%} | "
            f"{r['precision@3']:.2%} | {r['context_relevance']:.2%} |"
        )
    s = agent["summary"]
    lines += [
        "",
        "## Agent Pipeline",
        "",
        f"- Task Success: {s['task_success']:.2%}",
        f"- Reviewer Detection: {s['reviewer_detection']:.2%}",
        f"- Average Quality: {s['avg_quality']:.1f}",
        f"- Average Latency: {s['avg_latency_ms']:.1f} ms",
        f"- Average Tokens: {s['avg_tokens']:.0f}",
        f"- Total Estimated Cost: {s['total_cost']:.6f}",
        "",
        "| id | retriever | memory | review | status | quality | "
        "latency_ms | llm_calls | tokens | cost |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in agent["results"]:
        lines.append(
            f"| {r['id']} | {r['retriever']} | {r['memory']} | "
            f"{r['review']} | {r['status']} | {r['quality']} | "
            f"{r['latency_ms']:.1f} | {r['llm_calls']} | "
            f"{r['tokens']} | {r['cost']:.6f} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="AI Novel Agent Evaluation")
    parser.add_argument(
        "--mode",
        choices=("mock", "real"),
        default=os.getenv("EVAL_MODE", "mock"),
    )
    parser.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args()

    retrieval = [
        _retrieval_metrics("budget", args.top_k),
        _retrieval_metrics("keyword", args.top_k),
    ]
    agent = _run_agent_benchmarks()
    path = write_report(retrieval, agent, args.mode)

    print(
        "Retrieval Hit Rate: "
        f"budget={retrieval[0]['hit_rate']:.0%} "
        f"keyword={retrieval[1]['hit_rate']:.0%}"
    )
    print(f"Task Success: {agent['summary']['task_success']:.0%}")
    print(
        "Reviewer Detection: "
        f"{agent['summary']['reviewer_detection']:.0%}"
    )
    print(f"Average Quality: {agent['summary']['avg_quality']:.1f}")
    print(f"Average Latency: {agent['summary']['avg_latency_ms']:.1f} ms")
    print(f"Average Tokens: {agent['summary']['avg_tokens']:.0f}")
    print(f"Total Estimated Cost: {agent['summary']['total_cost']:.6f}")
    print(f"Report: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
