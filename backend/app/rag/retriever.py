"""RAG 检索模块。

流程：用户需求文本 -> Embedding -> ChromaDB 相似度搜索 -> Top K 上下文。

提供两种检索方式：
- retrieve: 单次全局 Top K（兼容旧调用）；
- retrieve_grouped: 按知识库板块（人物/世界观/剧情/技巧等）分组各取若干条，
  确保注入 Prompt 的资料覆盖多个维度，而不是全来自同一本书。
"""

import logging

from app.config import settings
from app.rag.embedding import get_embeddings
from app.rag.vector_store import VectorStore

logger = logging.getLogger(__name__)


class Retriever:
    """向量检索器。"""

    def __init__(self, vector_store: VectorStore | None = None, top_k: int | None = None):
        self.vector_store = vector_store or VectorStore()
        self.top_k = top_k or settings.retriever_top_k

    def retrieve(self, query: str, top_k: int | None = None) -> list[dict]:
        """检索与 query 最相关的 Top K 资料。

        Returns:
            [{"source": "...", "content": "...", "category": "..."}, ...]
        """
        k = top_k or self.top_k
        if self.vector_store.count() == 0:
            logger.warning("向量库为空，请先运行: python -m app.rag.build_index")
            return []

        query_embedding = get_embeddings().embed_query(query)
        results = self.vector_store.query(query_embedding, top_k=k)
        return [
            {"source": source, "content": content, "category": meta.get("category", "other")}
            for content, source, _meta, _distance in results
        ]

    def retrieve_grouped(
        self,
        query: str,
        per_category: int | None = None,
    ) -> list[dict]:
        """按知识库板块分组检索，每个板块取 top N，再按板块顺序返回。

        Args:
            query: 用户需求文本。
            per_category: 每个板块取几条，默认取配置 retriever_per_category。

        Returns:
            [{"source": "...", "content": "...", "category": "..."}, ...]
        """
        per = per_category or settings.retriever_per_category
        if self.vector_store.count() == 0:
            logger.warning("向量库为空，请先运行: python -m app.rag.build_index")
            return []

        query_embedding = get_embeddings().embed_query(query)
        results: list[dict] = []
        seen: set[str] = set()
        # 固定板块展示顺序，保证 Prompt 里资料分类稳定
        category_order = [
            "novel_info",
            "rag_chunks",
            "主要人物侧写",
            "世界观",
            "剧情大纲",
            "优秀情节",
            "作品借鉴",
            "灵感剧情添加",
            "other",
        ]
        categories = self.vector_store.list_categories()
        ordered = [c for c in category_order if c in categories] + [
            c for c in categories if c not in category_order
        ]

        for category in ordered:
            hits = self.vector_store.query(
                query_embedding,
                top_k=per,
                where={"category": category},
            )
            for content, source, meta, _distance in hits:
                # 同一来源文件只保留最相关的一条，避免重复灌入
                if source in seen:
                    continue
                seen.add(source)
                results.append(
                    {
                        "source": source,
                        "content": content,
                        "category": meta.get("category", "other"),
                    }
                )
        return results

    def retrieve_as_text(self, query: str, top_k: int | None = None) -> str:
        """检索并将结果拼接为可直接注入 Prompt 的文本。"""
        context = self.retrieve_grouped(query)
        if not context:
            return "（知识库中未检索到相关资料）"
        return "\n\n".join(
            f"【板块：{item['category']}｜来源：{item['source']}】\n{item['content']}"
            for item in context
        )
