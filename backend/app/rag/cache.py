"""知识库注入结果的内存缓存。

键 = (板块列表, 注入预算, 目录指纹, 配置版本)。
目录指纹覆盖全部 txt 文件的路径 + mtime + size；配置版本覆盖知识库相关设置。
文件或配置变更后指纹变化，自动重新计算；同一键并发时只计算一次。
"""

import hashlib
import threading
from pathlib import Path
from typing import Callable

from app.config import settings

# 缓存条目上限：超过后整体清空（知识库文件变更频率很低，简单策略足够）
MAX_CACHE_ENTRIES = 16


def directory_fingerprint(knowledge_dir: Path) -> str:
    """计算知识库目录指纹：全部 .txt 文件的路径 + mtime + size。"""
    hasher = hashlib.sha256()
    if not knowledge_dir.exists():
        hasher.update(b"<missing>")
        return hasher.hexdigest()
    for file_path in sorted(knowledge_dir.rglob("*.txt")):
        try:
            stat = file_path.stat()
        except OSError:
            continue
        hasher.update(file_path.relative_to(knowledge_dir).as_posix().encode("utf-8"))
        hasher.update(str(stat.st_mtime_ns).encode("utf-8"))
        hasher.update(str(stat.st_size).encode("utf-8"))
    return hasher.hexdigest()


def config_version() -> str:
    """知识库相关配置版本：配置变更后缓存自动失效。"""
    parts = [
        str(settings.knowledge_dir),
        settings.inspiration_enabled,
        settings.knowledge_category_max_chars,
        settings.knowledge_file_max_chars,
        settings.knowledge_compress,
        settings.knowledge_compress_source_max,
        settings.knowledge_compress_chunk_size,
        settings.knowledge_compress_summary_max,
        settings.knowledge_compress_workers,
        settings.knowledge_category_max_chars_compressed,
        settings.knowledge_max_total_chars,
        settings.llm_context_tokens,
        settings.llm_budget_safety_margin,
    ]
    return "|".join(str(p) for p in parts)


class KnowledgeCache:
    """进程内缓存：同一键只计算一次，文件/配置变更自动失效。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._entries: dict[tuple, list[dict]] = {}
        self._inflight: dict[tuple, threading.Lock] = {}

    def get_or_compute(
        self,
        key: tuple,
        compute: Callable[[], list[dict]],
    ) -> list[dict]:
        with self._lock:
            cached = self._entries.get(key)
            if cached is not None:
                return cached
            lock = self._inflight.setdefault(key, threading.Lock())

        with lock:
            # 等待期间可能已被其它线程计算完成
            with self._lock:
                cached = self._entries.get(key)
                if cached is not None:
                    return cached
            result = compute()
            with self._lock:
                self._entries[key] = result
                self._inflight.pop(key, None)
                if len(self._entries) > MAX_CACHE_ENTRIES:
                    self._entries.clear()
        return result
