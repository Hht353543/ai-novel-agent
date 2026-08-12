"""Mock LLM Provider：测试注入用；available=False 时业务层走演示模式。"""

from typing import Any, Iterator


class MockProvider:
    """可配置的测试替身：默认不可用（触发演示模式），可注入返回值。"""

    def __init__(
        self,
        available: bool = False,
        generate_result: str = "",
        generate_json_result: dict[str, Any] | None = None,
        generate_json_array_result: list[Any] | None = None,
    ):
        self._available = available
        self._generate_result = generate_result
        self._generate_json_result = generate_json_result
        self._generate_json_array_result = generate_json_array_result

    @property
    def available(self) -> bool:
        return self._available

    def generate(
        self,
        prompt: str,
        json_mode: bool = True,
        system_prompt: str | None = None,
    ) -> str:
        return self._generate_result

    def generate_json(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        if self._generate_json_result is None:
            raise ValueError("MockProvider 未配置 generate_json 返回值")
        return self._generate_json_result

    def generate_json_array(
        self,
        prompt: str,
        json_mode: bool = False,
        system_prompt: str | None = None,
    ) -> list[Any]:
        if self._generate_json_array_result is None:
            raise ValueError("MockProvider 未配置 generate_json_array 返回值")
        return self._generate_json_array_result

    def generate_stream(
        self,
        prompt: str,
        json_mode: bool = True,
        system_prompt: str | None = None,
    ) -> Iterator[str]:
        yield ""
