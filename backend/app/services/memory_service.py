"""章节跨章记忆：维护「事件线 + 角色状态」的滚动摘要。"""

from app.config import settings
from app.llm.call import run_llm
from app.schemas.novel import NovelOutline

MEMORY_SYSTEM_ROLE = (
    "你是一名小说设定管理员，负责维护全书事件线与角色状态的紧凑摘要。"
)


def build_memory_update_prompt(
    old_memory: str,
    outline: NovelOutline,
    chapter_label: str,
    content: str,
) -> str:
    """构建记忆增量更新 Prompt。"""
    target = settings.memory_summary_max_chars
    excerpt = content[:3000]
    old = old_memory.strip() or "（暂无）"
    return f"""请把已有的小说记忆与新章节内容合并，输出更新后的记忆摘要。

## 已有记忆
{old}

## 新章节
章节：{chapter_label}
书名：{outline.title or "（未命名）"}
全书梗概：{outline.summary or "（无）"}
新章节内容节选：
{excerpt}

## 输出要求
只输出一个合法的 JSON 对象：{{"memory": "更新后的记忆"}}
记忆内容要求：
1. 事件线：按时间顺序保留关键事件、地点、冲突与悬念；
2. 角色状态：角色当前所在位置、目标、关系与实力变化；
3. 去除与新内容冲突的旧状态；
4. 全文约 {target} 字，信息密度优先，不要复述原文。"""


async def update_memory(
    llm,
    old_memory: str,
    outline: NovelOutline,
    chapter_label: str,
    content: str,
) -> str:
    """用一次轻量 LLM 调用增量更新记忆；失败时保留旧记忆。"""
    prompt = build_memory_update_prompt(old_memory, outline, chapter_label, content)
    try:
        data = await run_llm(llm.generate_json, prompt, system_prompt=MEMORY_SYSTEM_ROLE)
        updated = str(data.get("memory", "")).strip()
        return updated or old_memory
    except Exception:  # noqa: BLE001 - 记忆更新失败不阻断生成
        return old_memory
