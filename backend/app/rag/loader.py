"""本地知识库文档加载模块。

两种用途：
1. load_knowledge_files：扫描全部板块（构建向量索引用）；
2. load_category_files / load_category_context：按板块直接读取
   txt/md 原文并注入生成 Prompt（当前生成流程使用的方式）。

知识库板块约定（用户提供参考小说原文 txt）：
- 世界观/   ：小说原文，作为新作世界观参考；
- 剧情大纲/ ：小说原文，作为剧情结构与节奏参考；
- 人物角色卡/：小说原文，作为人物塑造参考；
- other/    ：其它参考资料。

「灵感剧情添加」板块默认跳过，仅当灵感开关开启时加载。
"""

from dataclasses import dataclass, field
from pathlib import Path

from app.config import settings

# 灵感板块目录名：平时不启用，构建索引时通过 --with-inspiration 打开
INSPIRATION_DIRNAME = "灵感剧情添加"


@dataclass
class Document:
    """知识库文档的轻量结构。"""

    content: str
    source: str = ""          # 相对 knowledge_dir 的路径，如 world/example.txt
    category: str = ""        # 一级分类：world / characters / plots / other
    metadata: dict = field(default_factory=dict)


def _read_text(file_path: Path) -> str:
    """读取文本文件，优先 UTF-8，失败时回退 GBK。"""
    for encoding in ("utf-8", "gbk", "utf-8-sig"):
        try:
            return file_path.read_text(encoding=encoding)
        except (UnicodeDecodeError, UnicodeError):
            continue
    return file_path.read_text(encoding="utf-8", errors="ignore")


def load_knowledge_files(knowledge_dir: Path | None = None) -> list[Document]:
    """递归加载知识库目录下所有 .txt / .md 文件。

    Args:
        knowledge_dir: 知识库根目录，默认取配置中的 knowledge_dir。

    Returns:
        Document 列表，每个元素代表一个文本文件。
    """
    root = knowledge_dir or settings.knowledge_dir
    if not root.exists():
        raise FileNotFoundError(f"知识库目录不存在: {root}")

    documents: list[Document] = []
    # 同时支持 txt 与 md（新版知识库为 Markdown 结构）
    for file_path in sorted(list(root.rglob("*.txt")) + list(root.rglob("*.md"))):
        rel_path = file_path.relative_to(root)
        # 灵感板块默认不启用：平时不参与构建与检索
        if (
            not settings.inspiration_enabled
            and INSPIRATION_DIRNAME in rel_path.parts
        ):
            continue
        content = _read_text(file_path).strip()
        if not content:
            continue
        # 相对路径的第一段作为分类（world / characters / plots ...）
        category = rel_path.parts[0] if len(rel_path.parts) > 1 else "other"
        documents.append(
            Document(
                content=content,
                source=rel_path.as_posix(),
                category=category,
                metadata={"category": category, "format": file_path.suffix.lower()},
            )
        )
    return documents


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


def load_category_context(
    categories: list[str],
    per_category_chars: int | None = None,
    per_file_chars: int | None = None,
) -> list[dict]:
    """按板块读取知识库原文，供生成 Prompt 直接使用。

    规则：
    - 按传入的板块顺序读取；
    - 每个板块累计最多注入 per_category_chars 字符；
    - 单个文件最多注入 per_file_chars 字符（超出截断并标注）；
    - 超长原文只取开头部分（小说开头通常包含核心设定）。

    Returns:
        [{"source": "...", "content": "...", "category": "..."}, ...]
    """
    per_cat = per_category_chars or settings.knowledge_category_max_chars
    per_file = per_file_chars or settings.knowledge_file_max_chars
    result: list[dict] = []

    for category in categories:
        docs = load_category_files(category)
        if not docs:
            continue
        budget = per_cat
        for doc in docs:
            content = doc.content
            if len(content) > per_file:
                content = content[:per_file] + "\n……（原文过长，已截断）"
            if len(content) > budget:
                content = content[:budget] + "\n……（超出板块长度限制，已截断）"
            if not content.strip():
                continue
            result.append(
                {
                    "source": doc.source,
                    "content": content,
                    "category": category,
                }
            )
            budget -= len(content)
            if budget <= 0:
                break
    return result


if __name__ == "__main__":  # 便于单独调试
    docs = load_knowledge_files()
    print(f"加载到 {len(docs)} 个文档:")
    for doc in docs:
        print(f"  - {doc.source} ({len(doc.content)} 字符)")
