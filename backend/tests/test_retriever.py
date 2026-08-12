"""KeywordRetriever 检索行为与文档缓存测试。"""

from app.config import settings
from app.rag import loader as loader_module
from app.rag.retriever import KeywordRetriever, _query_terms


def _make_kb(tmp_path):
    """构造一个小知识库：world 板块含匹配/不匹配两个文件。"""
    root = tmp_path / "kb"
    cat_dir = root / "world"
    cat_dir.mkdir(parents=True)
    (cat_dir / "match.txt").write_text(
        "lingli gongfa jingjie " * 300, encoding="utf-8"
    )
    (cat_dir / "other.txt").write_text(
        "completely unrelated content " * 300, encoding="utf-8"
    )
    return root


def test_query_terms_mixes_ascii_words_and_cjk_bigrams():
    terms = _query_terms("lingli gongfa 功法")
    assert "lingli" in terms
    assert "gongfa" in terms
    assert "功法" in terms
    assert "法" not in terms  # 单字不构成二元组


def test_keyword_retriever_ranks_matches_and_truncates(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "knowledge_dir", _make_kb(tmp_path))
    monkeypatch.setattr(settings, "knowledge_file_max_chars", 5000)
    monkeypatch.setattr(settings, "knowledge_category_max_chars", 800)
    monkeypatch.setattr(settings, "knowledge_category_max_chars_compressed", 800)
    monkeypatch.setattr(settings, "knowledge_max_total_chars", 2000)
    monkeypatch.setattr(settings, "knowledge_cache_enabled", True)
    loader_module._doc_cache._entries.clear()

    result = KeywordRetriever(top_k=1).retrieve("lingli gongfa", ["world"])
    assert len(result) == 1
    assert result[0]["source"] == "world/match.txt"
    # 单文件注入受板块预算限制并附截断说明
    note = "\n……（超出板块长度限制，已截断）"
    assert len(result[0]["content"]) == 800 + len(note)
    assert result[0]["content"].endswith(note)


def test_keyword_retriever_reuses_document_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "knowledge_dir", _make_kb(tmp_path))
    monkeypatch.setattr(settings, "knowledge_cache_enabled", True)
    loader_module._doc_cache._entries.clear()

    real_load = loader_module.load_category_files
    calls = {"n": 0}

    def counting_load(category, knowledge_dir=None):
        calls["n"] += 1
        return real_load(category, knowledge_dir)

    monkeypatch.setattr(loader_module, "load_category_files", counting_load)
    retriever = KeywordRetriever(top_k=5)
    retriever.retrieve("lingli", ["world"])
    first = calls["n"]
    retriever.retrieve("lingli", ["world"])
    assert calls["n"] == first  # 第二次调用命中缓存，不再读盘

    # 知识库内容变化后指纹变化，重新读取
    (tmp_path / "kb" / "world" / "match.txt").write_text(
        "changed content " * 10, encoding="utf-8"
    )
    retriever.retrieve("lingli", ["world"])
    assert calls["n"] == first + 1


def test_keyword_retriever_cache_disabled_reads_every_time(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "knowledge_dir", _make_kb(tmp_path))
    monkeypatch.setattr(settings, "knowledge_cache_enabled", False)
    loader_module._doc_cache._entries.clear()

    real_load = loader_module.load_category_files
    calls = {"n": 0}

    def counting_load(category, knowledge_dir=None):
        calls["n"] += 1
        return real_load(category, knowledge_dir)

    monkeypatch.setattr(loader_module, "load_category_files", counting_load)
    retriever = KeywordRetriever(top_k=5)
    retriever.retrieve("lingli", ["world"])
    retriever.retrieve("lingli", ["world"])
    assert calls["n"] == 2
