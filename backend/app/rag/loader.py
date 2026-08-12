"""本地知识库文档加载模块。

按板块读取 txt 原文并注入生成 Prompt（当前生成流程使用的方式）。
板块约定（用户提供参考小说原文 txt）：
- 世界观/   ：小说原文，作为新作世界观参考；
- 剧情大纲/ ：小说原文，作为剧情结构与节奏参考；
- 人物角色卡/：小说原文，作为人物塑造参考；
- other/    ：其它参考资料。
"""

from dataclasses import dataclass, field
from pathlib import Path

from app.config import settings
from app.rag.cache import KnowledgeCache, directory_fingerprint

# 文档级内存缓存（进程级）：键 = (板块, 目录指纹)。
# 与知识库注入结果缓存共用同一开关（knowledge_cache_enabled）；
# 知识库文件路径/mtime/size 变化后指纹变化，自动重新读取。
_doc_cache = KnowledgeCache()


@dataclass
class Document:
    """知识库文档的轻量结构。"""

    content: str
    source: str = ""          # 相对 knowledge_dir 的路径，如 world/example.txt
    category: str = ""        # 板块目录名，如 世界观 / 剧情大纲 / 人物角色卡 / other
    metadata: dict = field(default_factory=dict)


def _read_text(file_path: Path) -> str:
    """读取文本文件，优先 UTF-8，失败时回退 GBK。"""
    for encoding in ("utf-8", "gbk", "utf-8-sig"):
        try:
            return file_path.read_text(encoding=encoding)
        except (UnicodeDecodeError, UnicodeError):
            continue
    return file_path.read_text(encoding="utf-8", errors="ignore")


def load_category_files(
    category: str,
    knowledge_dir: Path | None = None,
) -> list[Document]:
    """读取指定板块目录下的全部 txt 文件（当前知识库约定为小说原文 txt）。

    Args:
        category: 板块目录名，如「世界观」「剧情大纲」「人物角色卡」「other」。
        knowledge_dir: 知识库根目录，默认取配置。

    Returns:
        Document 列表；板块不存在或为空时返回空列表。
    """
    root = knowledge_dir or settings.knowledge_dir
    category_dir = root / category
    if not category_dir.exists():
        return []

    documents: list[Document] = []
    for file_path in sorted(category_dir.rglob("*.txt")):
        content = _read_text(file_path).strip()
        if not content:
            continue
        rel_path = file_path.relative_to(root).as_posix()
        documents.append(
            Document(
                content=content,
                source=rel_path,
                category=category,
                metadata={"category": category, "format": file_path.suffix.lower()},
            )
        )
    return documents


def load_category_files_cached(
    category: str,
    knowledge_dir: Path | None = None,
    fingerprint: str | None = None,
) -> list[Document]:
    """读取板块文档并做进程内缓存（按目录指纹失效）。

    Args:
        category: 板块目录名。
        knowledge_dir: 知识库根目录，默认取配置。
        fingerprint: 目录指纹；由调用方一次性计算并传入，可避免
            每次读取重复扫描全部文件（关键字检索逐板块调用时尤其重要）。

    缓存关闭（knowledge_cache_enabled=false）时退化为直接读取，行为不变。
    """
    root = knowledge_dir or settings.knowledge_dir
    if not settings.knowledge_cache_enabled:
        return load_category_files(category, root)
    if fingerprint is None:
        fingerprint = directory_fingerprint(root)
    return _doc_cache.get_or_compute(
        (category, fingerprint),
        lambda: load_category_files(category, root),
    )
