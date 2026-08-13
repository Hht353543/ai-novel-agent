"""Prompt 版本管理与注册表校验。"""

from pathlib import Path


PROMPTS_DIR = Path(__file__).resolve().parent

# 每个 Prompt 构建器对应的版本登记（单一事实源：registry.md 与之保持一致）
PROMPT_VERSIONS: dict[str, str] = {
    "planner": "v1",
    "character": "v1",
    "writer": "v1",
    "reviewer": "v1",
    "memory": "v1",
    "timeline": "v1",
    "knowledge_compress": "v1",
}


def load_registry() -> str:
    """读取 Prompt Registry 文档。"""

    return (PROMPTS_DIR / "registry.md").read_text(encoding="utf-8")


def validate_registry() -> list[str]:
    """校验 registry.md 覆盖全部已登记 Prompt。"""

    text = load_registry()
    errors = []
    for name, version in PROMPT_VERSIONS.items():
        row = f"| {name} | {version} |"
        if row not in text:
            errors.append(f"registry.md 缺少登记: {name} {version}")
    return errors


__all__ = ["PROMPTS_DIR", "PROMPT_VERSIONS", "load_registry", "validate_registry"]
