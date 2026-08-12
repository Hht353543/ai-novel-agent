"""RAG 检索接口。"""

from typing import Protocol


class RetrievalProvider(Protocol):
    """知识库检索提供者。

    retrieve 返回可直接注入 Prompt 的上下文列表，每项含
    source / content / category 三个字段。
    """

    def retrieve(
        self,
        query: str,
        categories: list[str],
        per_category_chars: int | None = None,
        per_file_chars: int | None = None,
    ) -> list[dict]:
        ...
