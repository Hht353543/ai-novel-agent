"""多 Agent 协议序列化与转换测试。"""

from app.agents.protocol import (
    ChapterOutline,
    CharacterSystem,
    NovelPlan,
    ReviewResult,
    StoryArc,
)
from agents_test_utils import CHARACTER_SYSTEM, PLAN


def test_novel_plan_roundtrip():
    plan = NovelPlan(**PLAN)
    restored = NovelPlan(**plan.dict())
    assert restored.title == "测试书"
    assert restored.arcs[0].chapters[0].beats == ["遭袭", "觉醒", "反击"]
    assert restored.world_setting.factions == ["朝廷", "江湖"]


def test_novel_plan_to_outline():
    plan = NovelPlan(**PLAN)
    outline = plan.to_outline()
    assert outline.title == "测试书"
    assert outline.world == "大乾王朝，武学昌盛\n力量体系：内力九境"
    assert len(outline.volume_plan) == 1
    assert outline.volume_plan[0].volume == "第一卷 初出茅庐"
    assert outline.volume_plan[0].chapters == ["第一章 觉醒"]


def test_novel_plan_empty_to_outline_fallback():
    outline = NovelPlan().to_outline()
    assert outline.volume_plan[0].volume == "第一卷"
    assert outline.volume_plan[0].chapters == ["第一章"]


def test_character_system_roundtrip():
    system = CharacterSystem(**CHARACTER_SYSTEM)
    restored = CharacterSystem(**system.dict())
    assert restored.profiles[0].name == "沈惊堂"
    assert restored.states[0].cultivation == "锻体"
    assert restored.relationships[0].relation == "搭档"


def test_review_result_defaults_and_serialization():
    review = ReviewResult(passed=True, score=88)
    data = review.dict()
    assert data["passed"] is True
    assert data["score"] == 88
    assert data["issues"] == []
    assert data["revision_required"] is False


def test_story_arc_defaults():
    arc = StoryArc(arc_index=0, name="第一卷")
    assert arc.chapters == []
    assert arc.goal == ""


def test_chapter_outline_defaults():
    c = ChapterOutline(chapter_index=2)
    assert c.title == ""
    assert c.beats == []
