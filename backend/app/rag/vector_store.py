"""ChromaDB 向量库管理模块。

负责创建持久化客户端、写入文本块向量、以及按 ID 清理旧数据。
使用本地持久化目录（默认 backend/vector_db）。
"""

import logging

import chromadb

from app.config import settings
from app.rag.embedding import get_embeddings
from app.rag.loader import Document

logger = logging.getLogger(__name__)


class VectorStore:
    """ChromaDB 持久化向量库封装。"""

    def __init__(self):
        # 确保持久化目录存在
        settings.chroma_persist_dir.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(settings.chroma_persist_dir))
        self.collection = self.client.get_or_create_collection(
            name=settings.chroma_collection,
            metadata={"hnsw:space": "cosine"},  # 余弦相似度
        )

    def add_documents(self, documents: list[Document]) -> int:
        """将切片后的文档写入向量库。

        Args:
            documents: 待入库的文本块列表。

        Returns:
            成功写入的文本块数量。
        """
        if not documents:
            return 0

        embeddings = get_embeddings().embed_documents([doc.content for doc in documents])
        ids = [f"{doc.source}#{doc.metadata.get('chunk_index', i)}" for i, doc in enumerate(documents)]
        metadatas = [
            {
                "source": doc.source,
                "category": doc.category,
                **doc.metadata,
            }
            for doc in documents
        ]

        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=[doc.content for doc in documents],
            metadatas=metadatas,
        )
        logger.info("已写入 %d 个文本块到 ChromaDB", len(documents))
        return len(documents)

    def count(self) -> int:
        """返回当前向量库中的文本块数量。"""
        return self.collection.count()

    def list_categories(self) -> list[str]:
        """返回向量库中实际存在的板块分类（category）列表。

        用于分组检索：先枚举板块，再按板块分别做相似度查询，
        避免 Top K 结果全部来自同一本书/同一个板块。
        """
        metas = self.collection.get(include=["metadatas"])["metadatas"] or []
        categories = {
            str(meta.get("category", "other"))
            for meta in metas
            if isinstance(meta, dict) and meta.get("category")
        }
        return sorted(categories)

    def clear(self) -> None:
        """清空当前 collection 的全部数据（重建索引前使用）。"""
        ids = self.collection.get()["ids"]
        if ids:  # ChromaDB 不允许对空列表执行 delete
            self.collection.delete(ids=ids)
        logger.info("已清空向量库 collection: %s", settings.chroma_collection)

    def query(
        self,
        query_embedding: list[float],
        top_k: int,
        where: dict | None = None,
    ) -> list[tuple[str, str, dict, float]]:
        """按向量相似度查询。

        Returns:
            [(content, source, metadata, distance), ...]
        """
        result = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        items: list[tuple[str, str, dict, float]] = []
        docs = (result.get("documents") or [[]])[0]
        metas = (result.get("metadatas") or [[]])[0]
        dists = (result.get("distances") or [[]])[0]
        for content, meta, distance in zip(docs, metas, dists):
            items.append((content, meta.get("source", ""), meta, float(distance)))
        return items
