"""知识库索引构建命令模块。

用法（在 backend 目录下执行）：
    python -m app.rag.build_index                        # 常规构建（灵感板块不启用）
    python -m app.rag.build_index --with-inspiration     # 启用「灵感剧情添加」板块
    python -m app.rag.build_index --online               # 首次使用：联网下载模型

流程：txt/md 文件 -> 文本切片 -> Embedding -> 存入 ChromaDB。
"""

import argparse
import logging
import os

from app.config import settings
from app.rag.loader import load_knowledge_files
from app.rag.splitter import split_documents
from app.rag.vector_store import VectorStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def run(online: bool = False, with_inspiration: bool = False) -> None:
    """执行完整索引构建流程。"""
    if online:
        # 联网模式：确保模型可下载（离线开关需在导入 sentence_transformers 前关闭）
        os.environ["HF_HUB_OFFLINE"] = "0"
        os.environ["TRANSFORMERS_OFFLINE"] = "0"

    # 灵感剧情板块：默认关闭，--with-inspiration 或环境变量可打开
    settings.inspiration_enabled = settings.inspiration_enabled or with_inspiration
    if settings.inspiration_enabled:
        logger.info("灵感剧情板块已启用，将包含「灵感剧情添加」目录")
    else:
        logger.info("灵感剧情板块未启用（需要时加 --with-inspiration）")

    logger.info("第一步：加载知识库 txt/md 文件...")
    documents = load_knowledge_files()

    logger.info("第二步：文本切片...")
    chunks = split_documents(documents)

    logger.info("第三步：Embedding 并写入 ChromaDB...")
    store = VectorStore()
    store.clear()  # 重建索引前清空旧数据，避免脏数据累积
    count = store.add_documents(chunks)

    logger.info("完成：共入库 %d 个文本块（来自 %d 个文档）", count, len(documents))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="构建小说知识库向量索引")
    parser.add_argument(
        "--with-inspiration",
        action="store_true",
        help="启用「灵感剧情添加」板块（默认不启用）",
    )
    parser.add_argument(
        "--online",
        action="store_true",
        help="首次使用时联网下载 Embedding 模型（默认离线加载）",
    )
    args = parser.parse_args()
    run(online=args.online, with_inspiration=args.with_inspiration)
