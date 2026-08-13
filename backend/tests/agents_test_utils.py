"""多 Agent 测试公共替身。"""

import asyncio
import functools

from app.schemas.project import NovelProject


def sync_test(async_fn):
    """把 async 测试函数包装为同步 pytest 测试（避免引入 pytest-asyncio 依赖）。"""

    @functools.wraps(async_fn)
    def wrapper(*args, **kwargs):
        return asyncio.run(async_fn(*args, **kwargs))

    return wrapper


class ScriptedLLM:
    """按调用顺序返回预设结果的 LLM 替身（不触网）。"""

    available = True

    def __init__(self, json_results=None, text_results=None):
        self.json_results = list(json_results or [])
        self.text_results = list(text_results or [])
        self.json_prompts = []
        self.text_prompts = []

    def generate_json(self, prompt, system_prompt=None):
        self.json_prompts.append(prompt)
        if not self.json_results:
            raise AssertionError("意外调用 generate_json（预设已耗尽）")
        return self.json_results.pop(0)

    def generate(self, prompt, json_mode=True, system_prompt=None):
        self.text_prompts.append(prompt)
        if not self.text_results:
            raise AssertionError("意外调用 generate（预设已耗尽）")
        return self.text_results.pop(0)

    def generate_json_array(self, prompt, json_mode=False, system_prompt=None):
        raise NotImplementedError("测试替身不支持标题数组")

    def generate_stream(self, prompt, json_mode=True, system_prompt=None):
        yield ""


class FakeRetriever:
    """返回固定上下文的检索替身，可注入异常。"""

    def __init__(self, context=None, error=None):
        self.context = list(context or [])
        self.error = error
        self.calls = 0

    def retrieve(
        self,
        query,
        categories,
        per_category_chars=None,
        per_file_chars=None,
    ):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return list(self.context)


class FakePersister:
    """记录保存请求并返回项目的持久化替身。"""

    def __init__(self):
        self.calls = []

    def __call__(self, save_request):
        self.calls.append(save_request)
        return NovelProject(
            id=save_request.id or "p_new",
            title=save_request.title,
            outline=save_request.outline,
            chapters=save_request.chapters,
            character_cards=save_request.character_cards,
            memory=save_request.memory,
            plan=save_request.plan,
            character_profiles=save_request.character_profiles,
            character_states=save_request.character_states,
            character_relations=save_request.character_relations,
            latest_review=save_request.latest_review,
            character_state_updates=save_request.character_state_updates,
            timeline=save_request.timeline,
            memory_facts=save_request.memory_facts,
        )


# ---------- 常用数据 ----------

PLAN = {
    "title": "测试书",
    "genre": "武侠",
    "premise": "少年觉醒武学熔炉",
    "summary": "主角一路横推，最终名震天下",
    "world_setting": {
        "overview": "大乾王朝，武学昌盛",
        "power_system": "内力九境",
        "factions": ["朝廷", "江湖"],
        "locations": ["京城", "县城"],
    },
    "main_plot": {
        "premise": "少年觉醒武学熔炉",
        "main_goal": "查明家族旧案",
        "core_conflict": "邪功与正法的对立",
        "theme": "无敌流",
    },
    "characters": [
        {"name": "沈惊堂", "role": "主角", "description": "冷静缜密"}
    ],
    "arcs": [
        {
            "arc_index": 0,
            "name": "第一卷 初出茅庐",
            "goal": "在县城立足",
            "chapters": [
                {
                    "chapter_index": 0,
                    "title": "第一章 觉醒",
                    "goal": "主角觉醒熔炉",
                    "beats": ["遭袭", "觉醒", "反击"],
                    "key_characters": ["沈惊堂"],
                    "location": "县城",
                }
            ],
        }
    ],
}

CHARACTER_SYSTEM = {
    "profiles": [
        {
            "name": "沈惊堂",
            "role": "主角",
            "age": "18",
            "appearance": "清瘦",
            "personality": "冷静",
            "background": "捕快世家",
            "goals": "查案",
            "motivation": "复仇",
            "speech_style": "短句",
            "growth_arc": "从皂衣到青衫",
            "faction": "捕快",
        }
    ],
    "states": [
        {
            "name": "沈惊堂",
            "current_location": "县城",
            "current_faction": "捕快",
            "current_identity": "皂衣捕快",
            "cultivation": "锻体",
            "possessions": ["朴刀"],
            "known_info": ["武学熔炉"],
            "relationships": [],
            "plot_status": "刚觉醒",
        }
    ],
    "relationships": [
        {
            "from_name": "沈惊堂",
            "to_name": "楚云萝",
            "relation": "搭档",
            "notes": "本卷结为搭档",
        }
    ],
}

REVIEW_PASS = {
    "passed": True,
    "score": 90,
    "revision_required": False,
    "summary": "整体合格",
    "issues": [],
}

MEMORY_UPDATE = {
    "state_deltas": [
        {
            "character": "沈惊堂",
            "changes": [
                {
                    "field": "cultivation",
                    "action": "set",
                    "old": "锻体",
                    "new": "先天",
                    "reason": "章节突破",
                },
                {
                    "field": "possessions",
                    "action": "add",
                    "new": "玉佩",
                    "reason": "获得信物",
                },
            ],
        }
    ],
    "facts": [
        {
            "category": "event",
            "content": "主角在县城觉醒武学熔炉",
            "importance": "high",
        },
        {
            "category": "item",
            "content": "获得神秘玉佩",
            "importance": "medium",
        },
    ],
    "events": ["觉醒武学熔炉", "获得玉佩"],
}

TIMELINE_UPDATE = {
    "entries": [
        {
            "sequence": 1,
            "chapter_index": 0,
            "chapter_title": "第一章 觉醒",
            "time_label": "当天",
            "event": "觉醒武学熔炉",
            "location": "县城",
            "characters": ["沈惊堂"],
        }
    ],
    "warnings": [],
}


def review_fail(score=50, issue=True):
    return {
        "passed": False,
        "score": score,
        "revision_required": True,
        "summary": "需要修订",
        "issues": (
            [
                {
                    "type": "character_consistency",
                    "severity": "high",
                    "description": "人设冲突",
                    "suggestion": "修正对话",
                }
            ]
            if issue
            else []
        ),
    }
