"""Prompt Registry 校验测试。"""

from app.prompts import PROMPT_VERSIONS, load_registry, validate_registry
from app.agents import prompts as agent_prompts


def test_registry_covers_all_builders():
    builders = {
        "planner",
        "character",
        "writer",
        "reviewer",
        "memory",
        "timeline",
    }
    assert builders <= set(PROMPT_VERSIONS)
    assert validate_registry() == []


def test_registry_document_lists_versions():
    text = load_registry()
    assert "| planner | v1 |" in text
    assert "| writer | v1 |" in text
    assert "## 变更记录" in text


def test_prompt_builders_are_callable():
    for name in ("build_planner_prompt", "build_character_prompt", "build_writer_prompt"):
        assert callable(getattr(agent_prompts, name))
