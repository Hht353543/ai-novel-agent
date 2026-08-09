"""文档切片模块。

使用 LangChain RecursiveCharacterTextSplitter 对长文档按中文语义边界
（句号/分号/换行等）进行重叠切片，保证检索单元的完整性。

针对新版知识库做了适配：
- novel_info / rag_chunks 下的 Markdown 文件本身就是按主题组织的内容
  （如「主角总览」「金手指与力量体系」「爽点模板」），使用更大的切片，
  避免把一个完整主题切得太碎；
- 普通 .txt 板块仍使用配置中的常规 chunk_size。
"""

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings
from app.rag.loader import Document


def split_documents(documents: list[Document]) -> list[Document]:
    """将加载的文档切片为适合向量化的文本块。

    Args:
        documents: loader 返回的原始文档列表。

    Returns:
        切片后的 Document 列表；metadata 中保留 parent_source 用于溯源。
    """
    chunks: list[Document] = []
    for doc in documents:
        # Markdown 结构化知识使用大块切片，保留主题完整性
        use_large_chunk = any(
            part in doc.source
            for part in ("novel_info/", "rag_chunks/")
        )
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=(
                settings.markdown_chunk_size if use_large_chunk else settings.chunk_size
            ),
            chunk_overlap=(
                settings.markdown_chunk_overlap
                if use_large_chunk
                else settings.chunk_overlap
            ),
            separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""],
        )
        texts = splitter.split_text(doc.content)
        for idx, text in enumerate(texts):
            text = text.strip()
            if not text:
                continue
            chunks.append(
                Document(
                    content=text,
                    source=doc.source,
                    category=doc.category,
                    metadata={
                        "category": doc.category,
                        "parent_source": doc.source,
                        "chunk_index": idx,
                    },
                )
            )
    return chunks


if __name__ == "__main__":  # 便于单独调试
    from app.rag.loader import load_knowledge_files

    chunks = split_documents(load_knowledge_files())
    print(f"共生成 {len(chunks)} 个文本块")
