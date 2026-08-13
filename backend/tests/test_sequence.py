"""连续章节创作（Sequence）测试：状态继承、前文传递、持久化与错误恢复。"""

from app.agents.orchestrator import NovelOrchestrator
from app.agents.protocol import SequenceRequest
from app.llm.mock_provider import MockProvider
from agents_test_utils import (
    CHARACTER_SYSTEM,
    FakePersister,
    FakeRetriever,
    MEMORY_UPDATE,
    PLAN,
    REVIEW_PASS,
    ScriptedLLM,
    sync_test,
)


def _timeline(seq, ci, title, event):
    return {
        "entries": [
            {
                "sequence": seq,
                "chapter_index": ci,
                "chapter_title": title,
                "time_label": f"第{ci + 1}天",
                "event": event,
                "location": "县城",
                "characters": ["沈惊堂"],
            }
        ],
        "warnings": [],
    }


def _per_chapter_json(ci, title):
    return [
        REVIEW_PASS,
        MEMORY_UPDATE,
        _timeline(ci + 1, ci, title, f"事件{ci + 1}"),
    ]


def _request(**kwargs):
    defaults = dict(
        genre="武侠",
        theme="无敌流",
        requirement="10万字",
        start_chapter=0,
        end_chapter=2,
        with_review=True,
    )
    defaults.update(kwargs)
    return SequenceRequest(**defaults)


@sync_test
async def test_sequence_three_chapters_continuous_state_flow():
    json_results = [
        PLAN,
        CHARACTER_SYSTEM,
        *_per_chapter_json(0, "第一章 觉醒"),
        *_per_chapter_json(1, "第二章 冲突"),
        *_per_chapter_json(2, "第三章 突破"),
    ]
    llm = ScriptedLLM(
        json_results=json_results,
        text_results=["第一章正文", "第二章正文", "第三章正文"],
    )
    orchestrator = NovelOrchestrator(llm=llm, retriever=FakeRetriever())
    result = await orchestrator.run_sequence(_request())

    assert result.status == "success"
    assert [c.chapter.content for c in result.chapters] == [
        "第一章正文",
        "第二章正文",
        "第三章正文",
    ]
    # 前文传递：第二章 Prompt 携带第一章正文结尾
    assert "第一章正文" in llm.text_prompts[1]
    assert "第三章正文" not in llm.text_prompts[1]
    # 状态继承：每章应用同一增量，最终状态一致且更新记录累积
    assert result.character_states[0].cultivation == "先天"
    assert "玉佩" in result.character_states[0].possessions
    assert len(result.chapters[-1].character_state_updates) == 3
    # 时间线按章累积（每章不同事件），记忆事实去重
    assert [e.event for e in result.timeline] == ["事件1", "事件2", "事件3"]
    assert len(result.memory_facts) == 2


@sync_test
async def test_sequence_without_review_and_save():
    json_results = [
        PLAN,
        CHARACTER_SYSTEM,
        MEMORY_UPDATE,
        _timeline(1, 0, "第一章 觉醒", "事件1"),
    ]
    llm = ScriptedLLM(
        json_results=json_results,
        text_results=["第一章正文"],
    )
    persister = FakePersister()
    orchestrator = NovelOrchestrator(
        llm=llm,
        retriever=FakeRetriever(),
        persister=persister,
    )
    result = await orchestrator.run_sequence(
        _request(end_chapter=0, with_review=False, save=True)
    )
    assert result.status == "success"
    assert len(result.chapters) == 1
    assert len(persister.calls) == 1
    saved = persister.calls[0]
    assert saved.chapters[0].content == "第一章正文"
    assert saved.chapters[0].version == 1
    assert saved.timeline[0].event == "事件1"


@sync_test
async def test_sequence_error_midway_keeps_partial_results():
    # 第三章 writer 无预设 → 抛错，Sequence 返回 error 但保留前两章结果
    llm = ScriptedLLM(
        json_results=[
            PLAN,
            CHARACTER_SYSTEM,
            *_per_chapter_json(0, "第一章 觉醒"),
            *_per_chapter_json(1, "第二章 冲突"),
        ],
        text_results=["第一章正文", "第二章正文"],
    )
    orchestrator = NovelOrchestrator(llm=llm, retriever=FakeRetriever())
    result = await orchestrator.run_sequence(_request())
    assert result.status == "error"
    assert len(result.chapters) == 2
    assert result.chapters[0].chapter.content == "第一章正文"
    assert result.chapters[1].chapter.content == "第二章正文"
    assert result.message


@sync_test
async def test_sequence_demo_without_api_key():
    orchestrator = NovelOrchestrator(llm=MockProvider(), retriever=FakeRetriever())
    result = await orchestrator.run_sequence(_request())
    assert result.status == "demo"
    assert len(result.chapters) == 3
    assert result.chapters[0].chapter.content.startswith("（演示正文）")


def test_sequence_rejects_invalid_range():
    request = SequenceRequest(genre="武侠", start_chapter=2, end_chapter=1)
    assert request.start_chapter > request.end_chapter
