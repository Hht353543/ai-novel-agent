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
    # 模型降级列表（逗号分隔）：主模型重试失败后按顺序切换
    deepseek_models: list[str] = [
        model.strip()
        for model in os.getenv("DEEPSEEK_MODELS", "").split(",")
        if model.strip()
    ]
    deepseek_temperature: float = float(os.getenv("DEEPSEEK_TEMPERATURE", "0.7"))
    deepseek_max_tokens: int = int(os.getenv("DEEPSEEK_MAX_TOKENS", "8192"))
    # API 请求超时（秒）：避免网络异常时请求长时间挂起
    deepseek_timeout: int = int(os.getenv("DEEPSEEK_TIMEOUT", "120"))
    # 连接阶段超时（秒）：与读取超时分离，快速失败
    deepseek_connect_timeout: int = int(
        os.getenv("DEEPSEEK_CONNECT_TIMEOUT", "10")
    )
    # 429/5xx 可重试次数（每次重试指数退避）
    llm_max_retries: int = int(os.getenv("LLM_MAX_RETRIES", "2"))
    llm_retry_base_delay: float = float(os.getenv("LLM_RETRY_BASE_DELAY", "1.0"))
    llm_retry_max_delay: float = float(os.getenv("LLM_RETRY_MAX_DELAY", "8.0"))
    # LLM 成本估算单价（元/1k tokens；0 表示不估算，仅记录用量）
    llm_cost_per_1k_input: float = float(os.getenv("LLM_COST_PER_1K_INPUT", "0"))
    llm_cost_per_1k_output: float = float(os.getenv("LLM_COST_PER_1K_OUTPUT", "0"))
    # 模型上下文窗口（token）：用于计算输入预算，防止超限
    llm_context_tokens: int = int(os.getenv("LLM_CONTEXT_TOKENS", "65536"))
    # 输入预算安全余量（token）：留给输出波动与解析开销
    llm_budget_safety_margin: int = int(os.getenv("LLM_BUDGET_SAFETY_MARGIN", "1024"))
    # 模型返回非法 JSON 时，是否自动让模型修复一次（会多消耗一次 API 调用）
    deepseek_auto_repair_json: bool = os.getenv(
        "DEEPSEEK_AUTO_REPAIR_JSON", "true"
    ).lower() in ("1", "true", "yes")

    # ---------- 知识库 ----------
    knowledge_dir: Path = Path(os.getenv("KNOWLEDGE_DIR", str(BASE_DIR / "knowledge")))
    # 灵感剧情板块默认不参与生成，开启后随其它板块一起注入
    inspiration_enabled: bool = os.getenv("INSPIRATION_ENABLED", "false").lower() in (
        "1",
        "true",
        "yes",
    )

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
    # 知识库注入结果的内存缓存开关（默认开启；知识库文件或配置变更后自动失效）
    knowledge_cache_enabled: bool = os.getenv("KNOWLEDGE_CACHE_ENABLED", "true").lower() in (
        "1",
        "true",
        "yes",
    )
    # 知识库所有板块合计最多注入的字符数（防止压缩模式撑爆上下文）
    knowledge_max_total_chars: int = int(
        os.getenv("KNOWLEDGE_MAX_TOTAL_CHARS", "40000")
    )
    # RAG 检索器：budget（默认，全量注入）或 keyword（轻量关键词检索）
    rag_retriever: str = os.getenv("RAG_RETRIEVER", "budget").strip().lower()
    # 关键词检索每板块最多选中的文件数
    rag_keyword_top_k: int = int(os.getenv("RAG_KEYWORD_TOP_K", "3"))
    # 章节跨章记忆（滚动摘要）：默认关闭（每次生成会增加一次轻量 LLM 调用）
    memory_enabled: bool = os.getenv("MEMORY_ENABLED", "false").lower() in (
        "1",
        "true",
        "yes",
    )
    # 记忆摘要目标字数
    memory_summary_max_chars: int = int(
        os.getenv("MEMORY_SUMMARY_MAX_CHARS", "800")
    )
    # 章节审校（Reviewer）开关：默认关闭（每次审校会增加一次 LLM 调用）
    review_enabled: bool = os.getenv("REVIEW_ENABLED", "false").lower() in (
        "1",
        "true",
        "yes",
    )

    # ---------- 多 Agent ----------
    # Pipeline 中审校失败后的最大修订次数（禁止无限循环）
    agent_max_revisions: int = int(os.getenv("AGENT_MAX_REVISIONS", "2"))
    # Reviewer 通过分数阈值（0-100）
    review_pass_score: int = int(os.getenv("REVIEW_PASS_SCORE", "80"))
    # Pipeline 是否执行 MemoryAgent（章节事实提取 + 人物状态更新）
    agent_memory_enabled: bool = os.getenv("AGENT_MEMORY_ENABLED", "true").lower() in (
        "1",
        "true",
        "yes",
    )
    # Pipeline 是否执行 TimelineAgent（时间线维护与一致性检查）
    agent_timeline_enabled: bool = os.getenv("AGENT_TIMELINE_ENABLED", "true").lower() in (
        "1",
        "true",
        "yes",
    )
    # 长期记忆保留的事实数量上限（超出按 importance 排序截断）
    agent_memory_max_facts: int = int(os.getenv("AGENT_MEMORY_MAX_FACTS", "30"))
    # 时间线保留的条目数量上限
    agent_timeline_max_entries: int = int(
        os.getenv("AGENT_TIMELINE_MAX_ENTRIES", "50")
    )
    # 修订时携带的上一稿最大字符数（控制 token 成本）
    agent_revision_draft_max_chars: int = int(
        os.getenv("AGENT_REVISION_DRAFT_MAX_CHARS", "4000")
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

    # ---------- 服务 ----------
    # 请求体大小上限（字节）：防止超大附件/正文打满内存与磁盘，0 表示不限制
    max_request_body_size: int = int(
        os.getenv("MAX_REQUEST_BODY_SIZE", str(10 * 1024 * 1024))
    )
    # 项目存储：json（默认，向后兼容）或 sqlite（需先运行迁移脚本）
    project_storage: str = os.getenv("PROJECT_STORAGE", "json").strip().lower()
    # 项目 JSON 存储文件
    projects_file: Path = Path(
        os.getenv("PROJECTS_FILE", str(BASE_DIR / "data" / "projects.json"))
    )
    # 项目 SQLite 存储文件
    project_db: Path = Path(
        os.getenv("PROJECT_DB", str(BASE_DIR / "data" / "projects.db"))
    )
    # Agent 运行 Trace 持久化目录（进程重启后可查询）
    traces_dir: Path = Path(
        os.getenv("TRACES_DIR", str(BASE_DIR / "data" / "traces"))
    )
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
