"""Embedding 向量生成模块。

基于 SentenceTransformers 提供本地中文向量化能力，
同时实现 LangChain Embeddings 接口，保留 LangChain 生态扩展点。
"""

import logging
import os
from functools import lru_cache

# 必须在导入 huggingface_hub / sentence_transformers 之前设置：
# 离线开关在包导入时即被缓存，迟设不会生效。
if os.getenv("EMBEDDING_OFFLINE", "true").lower() in ("1", "true", "yes"):
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"

from langchain_core.embeddings import Embeddings
from sentence_transformers import SentenceTransformer

from app.config import settings

logger = logging.getLogger(__name__)


class LocalEmbeddings(Embeddings):
    """SentenceTransformers 的 LangChain 兼容封装。"""

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or settings.embedding_model
        self._model = None  # 延迟加载，避免启动时下载模型

    def _get_model(self) -> SentenceTransformer:
        """延迟初始化模型。

        默认离线加载（模型已由 build_index 下载缓存）；
        若离线加载失败（首次使用且尚未下载），自动回退为联网下载。
        """
        if self._model is None:
            try:
                self._model = self._load(offline=settings.embedding_offline)
            except Exception as exc:  # noqa: BLE001 - 离线失败时回退在线下载
                if settings.embedding_offline:
                    logger.warning("离线加载模型失败（%s），尝试联网下载...", exc)
                    self._model = self._load(offline=False)
                else:
                    raise
        return self._model

    @staticmethod
    def _load(offline: bool) -> SentenceTransformer:
        """按模式加载 SentenceTransformer 模型。"""
        if offline:
            os.environ["TRANSFORMERS_OFFLINE"] = "1"
            os.environ["HF_HUB_OFFLINE"] = "1"
        else:
            os.environ.pop("TRANSFORMERS_OFFLINE", None)
            os.environ.pop("HF_HUB_OFFLINE", None)
        return SentenceTransformer(settings.embedding_model)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """批量生成文档向量。"""
        vectors = self._get_model().encode(texts, normalize_embeddings=True)
        return [vec.tolist() for vec in vectors]

    def embed_query(self, text: str) -> list[float]:
        """生成单个查询向量。"""
        return self.embed_documents([text])[0]


@lru_cache(maxsize=1)
def get_embeddings() -> LocalEmbeddings:
    """返回全局共享的 Embedding 实例（缓存单例）。"""
    return LocalEmbeddings()
