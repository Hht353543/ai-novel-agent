"""知识库原文压缩服务。

把长篇小说原文分块，用 DeepSeek 逐块压缩成高密度摘要，
再把摘要注入生成 Prompt，让有限的预算承载更多小说信息。

特性：
- 并发压缩（默认 4 线程）；
- 按文件内容哈希缓存（backend/data/knowledge_cache），首次慢、之后秒开；
- 压缩失败 / 未配置 API Key 时自动回退为直接截断；
- 每个板块有源文处理上限，避免首次调用过多。
"""

import hashlib
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from app.config import BASE_DIR, settings
from app.llm.deepseek import DeepSeekClient
from app.prompts.knowledge_compress_prompt import build_compress_prompt
from app.rag.loader import load_category_files

logger = logging.getLogger(__name__)

# 压缩结果缓存目录
CACHE_DIR = BASE_DIR / "data" / "knowledge_cache"


def default_categories() -> list[str]:
    """生成流程默认读取的知识库板块。

    「灵感剧情添加」板块平时不参与，仅当 INSPIRATION_ENABLED=true 时加入。
    """
    categories = ["世界观", "剧情大纲", "人物角色卡", "other"]
    if settings.inspiration_enabled:
        categories.append("灵感剧情添加")
    return categories


def _preprocess(text: str) -> str:
    """规则预处理：去行首尾空白、合并连续空行、去掉头尾空行。"""
    lines = [line.strip() for line in text.splitlines()]
    out: list[str] = []
    blank = False
    for line in lines:
        if not line:
            if not blank:
                out.append("")
            blank = True
        else:
            out.append(line)
            blank = False
    return "\n".join(out).strip()


def _file_hash(content: str) -> str:
    """文件内容哈希（缓存键的一部分）。"""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def _cache_path(category: str, source: str, digest: str) -> Path:
    """计算缓存文件路径。"""
    safe_source = source.replace("/", "__").replace("\\", "__")
    return CACHE_DIR / category / f"{safe_source}.{digest}.json"


def _read_cache(path: Path) -> str | None:
    """读取缓存摘要，失败返回 None。"""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        summary = str(data.get("summary", "")).strip()
        return summary or None
    except (OSError, ValueError, json.JSONDecodeError):
        return None


def _write_cache(path: Path, summary: str) -> None:
    """写入缓存摘要（失败静默）。"""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"summary": summary}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        logger.warning("写入知识库压缩缓存失败: %s", exc)


def _compress_chunk(
    llm: DeepSeekClient,
    category: str,
    chunk_index: int,
    chunk_total: int,
    chunk: str,
) -> str:
    """压缩单个分块，失败返回空串。"""
    try:
        prompt = build_compress_prompt(category, chunk_index, chunk_total, chunk)
        data = llm.generate_json(prompt)
        return str(data.get("summary", "")).strip()
    except Exception as exc:  # noqa: BLE001 - 单块失败不影响整体
        logger.warning("知识库压缩分块 %d/%d 失败: %s", chunk_index + 1, chunk_total, exc)
        return ""


def _compress_file(
    llm: DeepSeekClient,
    category: str,
    source: str,
    content: str,
) -> str:
    """压缩单个文件：命中缓存直接返回，否则并发分块压缩。"""
    digest = _file_hash(content)
    cache = _cache_path(category, source, digest)
    cached = _read_cache(cache)
    if cached:
        return cached

    text = _preprocess(content)
    chunk_size = settings.knowledge_compress_chunk_size
    chunks = [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]
    if not chunks:
        return ""

    summaries: list[str] = [""] * len(chunks)
    workers = max(1, settings.knowledge_compress_workers)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(
                _compress_chunk, llm, category, i, len(chunks), chunk
            ): i
            for i, chunk in enumerate(chunks)
        }
        for future in as_completed(futures):
            idx = futures[future]
            try:
                summaries[idx] = future.result()
            except Exception:  # noqa: BLE001 - 单块异常不影响整体
                summaries[idx] = ""

    result = "\n\n".join(s for s in summaries if s).strip()
    if result:
        _write_cache(cache, result)
    return result


def load_compressed_category_context(
    categories: list[str],
    per_category_chars: int | None = None,
    per_file_chars: int | None = None,
) -> list[dict]:
    """按板块读取原文并压缩后返回，供生成 Prompt 使用。

    - 开启压缩且有 API Key 时：长文件先分块摘要（有缓存），注入压缩版；
    - 未开启 / 压缩失败 / 无 API Key：回退为直接截断。

    Returns:
        [{"source": "...", "content": "...", "category": "..."}, ...]
    """
    llm = DeepSeekClient()
    per_cat = per_category_chars or (
        settings.knowledge_category_max_chars_compressed
        if settings.knowledge_compress
        else settings.knowledge_category_max_chars
    )
    per_file = per_file_chars or settings.knowledge_file_max_chars
    result: list[dict] = []

    for category in categories:
        docs = load_category_files(category)
        if not docs:
            continue
        budget = per_cat
        source_budget = settings.knowledge_compress_source_max
        for doc in docs:
            content = doc.content.strip()
            if not content:
                continue

            compressable = (
                settings.knowledge_compress
                and llm.available
                and len(content) > per_file
            )
            if compressable:
                # 只压缩源文预算内的部分（防止首次调用过多）
                source_piece = content[:source_budget]
                summary = _compress_file(llm, category, doc.source, source_piece)
                piece = summary if summary else (
                    content[:per_file] + "\n……（压缩失败，已截断）"
                )
            else:
                piece = (
                    content
                    if len(content) <= per_file
                    else content[:per_file] + "\n……（原文过长，已截断）"
                )

            if len(piece) > budget:
                piece = piece[:budget] + "\n……（超出板块长度限制，已截断）"
            if not piece.strip():
                continue
            result.append(
                {
                    "source": doc.source,
                    "content": piece,
                    "category": category,
                }
            )
            budget -= len(piece)
            source_budget -= len(content)
            if budget <= 0 or source_budget <= 0:
                break
    return result
