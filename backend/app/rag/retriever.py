"""RAG 检索实现。

- BudgetRetriever：默认实现，保持「按板块全量注入到预算」的既有行为；
- KeywordRetriever：轻量关键词检索（文件名/正文命中打分 + Top-K），
  不引入向量库；命中为空时回退为按文件顺序取前 K 个。
"""

import re
from functools import lru_cache

from app.config import settings
from app.llm.budget import knowledge_char_budget, truncate_with_note
from app.services.knowledge_compress import load_compressed_category_context
from app.rag.cache import directory_fingerprint
from app.rag.loader import load_category_files_cached
from app.rag.base import RetrievalProvider


def _query_terms(query: str) -> list[str]:
    """把查询文本拆成检索词：ASCII 词 + 中日韩二元组。"""
    text = (query or "").lower()
    terms: list[str] = re.findall(r"[a-z0-9_]{2,}", text)
    chars = re.findall(r"[\u4e00-\u9fff]", text)
    terms.extend("".join(chars[i : i + 2]) for i in range(len(chars) - 1))
    return [t for t in terms if t]


class BudgetRetriever:
    """默认检索器：保持现有全量注入行为。"""

    def retrieve(
        self,
        query: str,
        categories: list[str],
        per_category_chars: int | None = None,
        per_file_chars: int | None = None,
    ) -> list[dict]:
        del query  # 预算模式不依赖查询文本
        return load_compressed_category_context(
            categories,
            per_category_chars,
            per_file_chars,
        )


class KeywordRetriever:
    """轻量关键词检索：文件名/正文命中打分 + Top-K。"""

    def __init__(self, top_k: int | None = None):
        self.top_k = max(1, top_k or settings.rag_keyword_top_k)

    def retrieve(
        self,
        query: str,
        categories: list[str],
        per_category_chars: int | None = None,
        per_file_chars: int | None = None,
    ) -> list[dict]:
        per_cat = per_category_chars or (
            settings.knowledge_category_max_chars_compressed
            if settings.knowledge_compress
            else settings.knowledge_category_max_chars
        )
        per_file = per_file_chars or settings.knowledge_file_max_chars
        terms = _query_terms(query)
        total_budget = knowledge_char_budget()
        total_injected = 0
        result: list[dict] = []
        # 目录指纹只计算一次：文档缓存按指纹失效，避免每个板块重复扫描文件
        fingerprint = (
            directory_fingerprint(settings.knowledge_dir)
            if settings.knowledge_cache_enabled
            else None
        )

        for category in categories:
            docs = load_category_files_cached(category, fingerprint=fingerprint)
            if not docs:
                continue

            scored: list[tuple[int, str, str]] = []
            for doc in docs:
                content = doc.content[:per_file] if len(doc.content) > per_file else doc.content
                score = 0
                lower = content.lower()
                source_lower = doc.source.lower()
                for term in terms:
                    score += lower.count(term)
                    if term in source_lower:
                        score += 5
                scored.append((score, doc.source, content))

            # 按分数降序；同分保持文件顺序（稳定排序）
            scored.sort(key=lambda item: -item[0])
            for _score, source, content in scored[: self.top_k]:
                if not content.strip():
                    continue
                if len(content) > per_cat:
                    content = truncate_with_note(content, per_cat, "超出板块长度限制，已截断")
                remaining_total = total_budget - total_injected
                if remaining_total <= 0:
                    return result
                if len(content) > remaining_total:
                    content = truncate_with_note(
                        content, remaining_total, "知识库总注入超限，已截断"
                    )
                result.append(
                    {"source": source, "content": content, "category": category}
                )
                total_injected += len(content)
                per_cat -= len(content)
                if per_cat <= 0 or total_injected >= total_budget:
                    break
        return result


def create_retriever() -> RetrievalProvider:
    """按配置创建检索器：budget（默认）或 keyword。"""
    if settings.rag_retriever == "keyword":
        return KeywordRetriever()
    return BudgetRetriever()


@lru_cache(maxsize=1)
def get_retriever() -> RetrievalProvider:
    """进程级检索器单例：所有生成服务与 API 共用同一实例。"""
    return create_retriever()
