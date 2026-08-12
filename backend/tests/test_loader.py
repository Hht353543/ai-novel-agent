"""知识库加载器测试。"""

from app.config import settings
from app.rag import loader as loader_module
from app.rag.loader import load_category_files, load_category_files_cached


def test_load_category_files_utf8_and_gbk(tmp_path):
    category = "world"
    (tmp_path / category).mkdir()
    (tmp_path / category / "a.txt").write_text("utf8 content", encoding="utf-8")
    (tmp_path / category / "b.txt").write_text("gbk content", encoding="gbk")
    docs = load_category_files(category, knowledge_dir=tmp_path)
    contents = {d.source for d in docs}
    assert contents == {"world/a.txt", "world/b.txt"}
    by_source = {d.source: d.content for d in docs}
    assert by_source["world/a.txt"] == "utf8 content"
    assert by_source["world/b.txt"] == "gbk content"


def test_load_category_files_missing_dir(tmp_path):
    assert load_category_files("missing", knowledge_dir=tmp_path) == []


def test_load_category_files_skips_empty(tmp_path):
    category = "empty"
    (tmp_path / category).mkdir()
    (tmp_path / category / "a.txt").write_text("   \n  ", encoding="utf-8")
    assert load_category_files(category, knowledge_dir=tmp_path) == []


def test_cached_loader_reuses_documents_until_fingerprint_changes(tmp_path):
    loader_module._doc_cache._entries.clear()
    category = "world"
    (tmp_path / category).mkdir()
    file_path = tmp_path / category / "a.txt"
    file_path.write_text("one", encoding="utf-8")

    docs1 = load_category_files_cached(category, knowledge_dir=tmp_path)
    docs2 = load_category_files_cached(category, knowledge_dir=tmp_path)
    assert docs1 is docs2  # 同一指纹命中同一缓存对象，不再读盘

    # 内容变化（长度不同，指纹必然变化）后自动重新读取
    file_path.write_text("much longer content", encoding="utf-8")
    docs3 = load_category_files_cached(category, knowledge_dir=tmp_path)
    assert docs3 is not docs1
    assert docs3[0].content == "much longer content"


def test_cached_loader_disabled_falls_through(tmp_path, monkeypatch):
    loader_module._doc_cache._entries.clear()
    monkeypatch.setattr(settings, "knowledge_cache_enabled", False)
    category = "world"
    (tmp_path / category).mkdir()
    (tmp_path / category / "a.txt").write_text("one", encoding="utf-8")

    docs1 = load_category_files_cached(category, knowledge_dir=tmp_path)
    docs2 = load_category_files_cached(category, knowledge_dir=tmp_path)
    assert docs1 is not docs2  # 关闭缓存时每次都重新读取
    assert docs1[0].content == docs2[0].content == "one"
