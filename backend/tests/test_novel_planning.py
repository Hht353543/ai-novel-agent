"""大纲卷章规划与字数解析的纯函数测试。"""

from app.config import settings
from app.prompts.novel_prompt import (
    MAX_EXTRA_REQUIREMENTS_CHARS,
    format_extra_requirements,
    group_context,
    parse_total_words,
    plan_volumes,
)
from app.services.novel_service import ensure_volume_plan


def test_parse_total_words():
    assert parse_total_words("100万字") == 1_000_000
    assert parse_total_words("100万") == 1_000_000
    assert parse_total_words("1,000,000字") == 1_000_000
    assert parse_total_words("5000字") == 5000
    assert parse_total_words("约30万字") == 300_000
    assert parse_total_words("随便") == settings.outline_default_total_words
    assert parse_total_words("") == settings.outline_default_total_words


def test_plan_volumes_single_chapter():
    total, per = plan_volumes(settings.outline_chapter_words)
    assert total == 1
    assert per == [1]


def test_plan_volumes_short_book():
    total, per = plan_volumes(settings.outline_chapter_words * 10)
    assert total == 10
    assert len(per) == settings.outline_volume_min
    assert sum(per) == total


def test_plan_volumes_long_book_caps_volumes():
    total, per = plan_volumes(settings.outline_chapter_words * 250)
    assert total == 250
    assert len(per) == settings.outline_volume_max
    assert sum(per) == total


def test_ensure_volume_plan_generates_full_toc():
    outline = {"volume_plan": [{"volume": "第一卷"}, {"volume": "第二卷"}]}
    out = ensure_volume_plan(outline, "100000字")
    total_chapters = parse_total_words("100000字") // settings.outline_chapter_words
    assert sum(len(v["chapters"]) for v in out["volume_plan"]) == total_chapters
    assert out["volume_plan"][0]["chapters"][0] == "第1章"
    assert out["volume_plan"][-1]["chapters"][-1] == f"第{total_chapters}章"


def test_ensure_volume_plan_fills_missing_names():
    out = ensure_volume_plan({"volume_plan": []}, "100000字")
    assert out["volume_plan"][0]["volume"] == "第1卷"


def test_group_context_groups_by_category():
    context = [
        {"source": "a.txt", "content": "A", "category": "世界观"},
        {"source": "b.txt", "content": "B", "category": "other"},
        {"source": "c.txt", "content": "C", "category": "世界观"},
    ]
    grouped = group_context(context)
    assert grouped == {
        "世界观": ["【来源：a.txt】\nA", "【来源：c.txt】\nC"],
        "other": ["【来源：b.txt】\nB"],
    }


def test_group_context_defaults_missing_category_to_other():
    assert group_context([{"source": "x", "content": "X"}]) == {
        "other": ["【来源：x】\nX"]
    }


def test_format_extra_requirements_empty_and_short():
    assert format_extra_requirements("") == "（无，由你自行把握）"
    assert format_extra_requirements("  风格明快  ") == "风格明快"


def test_format_extra_requirements_truncates_overlong():
    long_text = "a" * (MAX_EXTRA_REQUIREMENTS_CHARS + 100)
    out = format_extra_requirements(long_text)
    assert len(out) == MAX_EXTRA_REQUIREMENTS_CHARS + len("\n……（其他要求过长，已截断）")
    assert out.startswith("a" * MAX_EXTRA_REQUIREMENTS_CHARS)
    assert out.endswith("（其他要求过长，已截断）")
