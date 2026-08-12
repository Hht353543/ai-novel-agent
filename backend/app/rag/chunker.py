"""知识分块：按段落/空行边界切块，并保留少量重叠。"""

import re

# 分块器版本：修改切块策略后必须递增，压缩磁盘缓存会自动失效
CHUNKER_VERSION = "v1"
# 相邻分块的重叠字符数（防止边界切断关键设定）
CHUNK_OVERLAP_CHARS = 200


def _split_paragraphs(text: str) -> list[str]:
    """按空行切分为段落（Markdown 标题行也作为独立段落）。"""
    parts = re.split(r"\n\s*\n", text)
    result: list[str] = []
    for part in parts:
        for line in part.splitlines():
            if line.strip().startswith("#"):
                result.append(line.strip())
                rest = part.split(line, 1)[1]
                if rest.strip():
                    result.append(rest.strip())
                break
        else:
            result.append(part.strip())
    return [p for p in result if p]


def _tail(text: str, length: int) -> str:
    """取文本尾部作为重叠上下文。"""
    return text[-length:] if len(text) > length else text


def chunk_text(
    text: str,
    chunk_size: int,
    overlap: int = CHUNK_OVERLAP_CHARS,
) -> list[str]:
    """把文本切分为不超过 chunk_size 的分块。

    优先按段落边界打包，避免在段落中间硬切；
    单个段落超过 chunk_size 时退化为带重叠的字符切块。
    """
    if not text.strip():
        return []
    if chunk_size <= 0:
        return [text]
    if len(text) <= chunk_size:
        return [text]

    paragraphs = _split_paragraphs(text)
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        if current:
            candidate = current + "\n\n" + para
            if len(candidate) <= chunk_size:
                current = candidate
                continue
            chunks.append(current)
            current = _tail(current, overlap)

        if current and len(current) + 2 + len(para) <= chunk_size:
            current = current + "\n\n" + para
        elif len(para) <= chunk_size:
            current = para
        else:
            if current:
                chunks.append(current)
                current = ""
            start = 0
            while start < len(para):
                end = min(len(para), start + chunk_size)
                chunks.append(para[start:end])
                if end == len(para):
                    break
                start = max(start + chunk_size - overlap, start + 1)

    if current:
        chunks.append(current)
    return chunks
