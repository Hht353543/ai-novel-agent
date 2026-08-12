"""LLM Provider 接口。"""

from typing import Any, Iterator, Protocol


class BaseLLM(Protocol):
    """模型提供者统一接口。

    available=False 时由业务层走演示模式；
    generate_stream 为流式输出预留（TASK-028 实现）。
    """

    @property
    def available(self) -> bool:
        ...

    def generate(
        self,
        prompt: str,
        json_mode: bool = True,
        system_prompt: str | None = None,
    ) -> str:
        ...

    def generate_json(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        ...

    def generate_json_array(
        self,
        prompt: str,
        json_mode: bool = False,
        system_prompt: str | None = None,
    ) -> list[Any]:
        ...

    def generate_stream(
        self,
        prompt: str,
        json_mode: bool = True,
        system_prompt: str | None = None,
    ) -> Iterator[str]:
        ...
