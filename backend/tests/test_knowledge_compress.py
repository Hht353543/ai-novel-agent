"""知识压缩与缓存测试。"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor

from app.config import settings
from app.rag.cache import KnowledgeCache
from app.rag.chunker import chunk_text
from app.services import knowledge_compress as kc


class FakeLLM:
    available = True

    def __init__(self):
        self.calls = 0

    def generate_json(self, prompt, system_prompt=None):
        self.calls += 1
        return {"summary": "S"}


def test_compression_fingerprint_stable_and_changes(monkeypatch):
    monkeypatch.setattr(settings, "knowledge_compress_chunk_size", 100)
    monkeypatch.setattr(settings, "knowledge_compress_summary_max", 50)
    fp1 = kc._compression_config_fingerprint()
    assert fp1 == kc._compression_config_fingerprint()
    monkeypatch.setattr(settings, "knowledge_compress_chunk_size", 200)
    assert kc._compression_config_fingerprint() != fp1


def test_compress_file_disk_cache_hit_and_miss(tmp_path, monkeypatch):
    monkeypatch.setattr(kc, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(settings, "knowledge_compress_chunk_size", 100)
    monkeypatch.setattr(settings, "knowledge_compress_summary_max", 50)
    llm = FakeLLM()
    content = "x" * 300
    chunk_count = len(chunk_text(content, 100))
    expected = "\n\n".join(["S"] * chunk_count)
    assert kc._compress_file(llm, "world", "a.txt", content) == expected
    assert llm.calls == chunk_count
    assert kc._compress_file(llm, "world", "a.txt", content) == expected
    assert llm.calls == chunk_count
    monkeypatch.setattr(settings, "knowledge_compress_chunk_size", 150)
    chunk_count2 = len(chunk_text(content, 150))
    assert kc._compress_file(llm, "world", "a.txt", content) == "\n\n".join(["S"] * chunk_count2)
    assert llm.calls == chunk_count + chunk_count2


def test_knowledge_cache_single_compute():
    cache = KnowledgeCache()
    counter = {"n": 0}

    def slow_compute():
        counter["n"] += 1
        time.sleep(0.05)
        return [{"source": "x", "content": "y", "category": "c"}]

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(cache.get_or_compute, ("k",), slow_compute) for _ in range(8)]
        results = [f.result() for f in futures]
    assert counter["n"] == 1
    assert all(r == results[0] for r in results)


def test_knowledge_budget_defaults():
    from app.llm.budget import available_input_tokens, estimate_tokens, knowledge_char_budget

    assert estimate_tokens("你好世界") == 4
    assert estimate_tokens("abcd") == 1
    assert available_input_tokens() == (
        settings.llm_context_tokens
        - settings.deepseek_max_tokens
        - settings.llm_budget_safety_margin
    )
    assert knowledge_char_budget() <= settings.knowledge_max_total_chars
