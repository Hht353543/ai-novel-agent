"""全局配置管理模块。

所有可调参数统一从环境变量 / .env 文件读取。
使用 python-dotenv 加载，保持依赖组合简单可靠。
"""

import os
from pathlib import Path

from dotenv import load_dotenv


# 项目根目录：backend/
BASE_DIR = Path(__file__).resolve().parent.parent

# 加载 backend/.env（若存在）
load_dotenv(BASE_DIR / ".env", override=False)


class Settings:
    """应用配置项。

    优先级：环境变量 > .env 文件 > 默认值。
    """

    # ---------- DeepSeek API ----------
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_base_url: str = os.getenv(
        "DEEPSEEK_BASE_URL", "https://api.deepseek.com/"
    )
    deepseek_model: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    deepseek_temperature: float = float(os.getenv("DEEPSEEK_TEMPERATURE", "0.7"))
    deepseek_max_tokens: int = int(os.getenv("DEEPSEEK_MAX_TOKENS", "8192"))
    # API 请求超时（秒）：避免网络异常时请求长时间挂起
    deepseek_timeout: int = int(os.getenv("DEEPSEEK_TIMEOUT", "120"))
    # 模型返回非法 JSON 时，是否自动让模型修复一次（会多消耗一次 API 调用）
    deepseek_auto_repair_json: bool = os.getenv(
        "DEEPSEEK_AUTO_REPAIR_JSON", "true"
    ).lower() in ("1", "true", "yes")

    # ---------- Embedding / 向量库 ----------
    embedding_model: str = os.getenv(
        "EMBEDDING_MODEL", "shibing624/text2vec-base-chinese"
    )
    # 模型加载策略：offline 时不再联网检查更新（首次构建需先下载模型）
    embedding_offline: bool = os.getenv("EMBEDDING_OFFLINE", "true").lower() in (
        "1",
        "true",
        "yes",
    )
    chroma_persist_dir: Path = Path(
        os.getenv("CHROMA_PERSIST_DIR", str(BASE_DIR / "vector_db"))
    )
    chroma_collection: str = os.getenv("CHROMA_COLLECTION", "novel_knowledge")

    # ---------- 知识库 ----------
    knowledge_dir: Path = Path(os.getenv("KNOWLEDGE_DIR", str(BASE_DIR / "knowledge")))
    # 灵感剧情板块默认不启用（构建索引时可通过 --with-inspiration 打开）
    inspiration_enabled: bool = os.getenv("INSPIRATION_ENABLED", "false").lower() in (
        "1",
        "true",
        "yes",
    )
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "500"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "80"))
    # Markdown 结构化知识（novel_info / rag_chunks）使用更大的切片
    markdown_chunk_size: int = int(os.getenv("MARKDOWN_CHUNK_SIZE", "1500"))
    markdown_chunk_overlap: int = int(os.getenv("MARKDOWN_CHUNK_OVERLAP", "200"))

    # ---------- 知识库原文读取（按板块直接注入） ----------
    # 每个板块最多注入的字符数（防止整本小说原文撑爆上下文）
    knowledge_category_max_chars: int = int(
        os.getenv("KNOWLEDGE_CATEGORY_MAX_CHARS", "8000")
    )
    # 单个 txt 文件最多注入的字符数
    knowledge_file_max_chars: int = int(
        os.getenv("KNOWLEDGE_FILE_MAX_CHARS", "2000")
    )
    # 是否用 DeepSeek 对长原文做摘要压缩（默认 false=直接截断，实测大文件压缩太慢）
    knowledge_compress: bool = os.getenv("KNOWLEDGE_COMPRESS", "false").lower() in (
        "1",
        "true",
        "yes",
    )
    # 每个板块最多参与压缩的原文长度（超出部分不处理）
    knowledge_compress_source_max: int = int(
        os.getenv("KNOWLEDGE_COMPRESS_SOURCE_MAX", "30000")
    )
    # 压缩时原文分块大小（字符）
    knowledge_compress_chunk_size: int = int(
        os.getenv("KNOWLEDGE_COMPRESS_CHUNK_SIZE", "2500")
    )
    # 每块摘要目标字数
    knowledge_compress_summary_max: int = int(
        os.getenv("KNOWLEDGE_COMPRESS_SUMMARY_MAX", "700")
    )
    # 压缩并发线程数
    knowledge_compress_workers: int = int(
        os.getenv("KNOWLEDGE_COMPRESS_WORKERS", "4")
    )
    # 压缩后每个板块最多注入的字符数
    knowledge_category_max_chars_compressed: int = int(
        os.getenv("KNOWLEDGE_CATEGORY_MAX_CHARS_COMPRESSED", "16000")
    )

    # ---------- 大纲卷章规划 ----------
    # 每章标准字数：总章数 = ceil(总字数 / 每章字数)
    outline_chapter_words: int = int(os.getenv("OUTLINE_CHAPTER_WORDS", "4000"))
    # 卷数随总章数增长：约每多少章分一卷
    outline_chapters_per_volume: int = int(os.getenv("OUTLINE_CHAPTERS_PER_VOLUME", "30"))
    # 卷数上下限
    outline_volume_min: int = int(os.getenv("OUTLINE_VOLUME_MIN", "3"))
    outline_volume_max: int = int(os.getenv("OUTLINE_VOLUME_MAX", "8"))
    # 解析不出字数规模时的默认总字数
    outline_default_total_words: int = int(os.getenv("OUTLINE_DEFAULT_TOTAL_WORDS", "1000000"))

    # ---------- RAG 检索 ----------
    retriever_top_k: int = int(os.getenv("RETRIEVER_TOP_K", "4"))
    # 分组检索时每个板块取几条（保证人物/世界观/剧情/技巧都有覆盖）
    retriever_per_category: int = int(os.getenv("RETRIEVER_PER_CATEGORY", "2"))

    # ---------- 服务 ----------
    app_name: str = os.getenv("APP_NAME", "AI 网文作者 Agent")
    cors_origins: list[str] = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        ).split(",")
        if origin.strip()
    ]


# 全局单例，避免每个模块重复加载配置
settings = Settings()
