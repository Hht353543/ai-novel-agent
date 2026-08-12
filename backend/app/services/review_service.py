"""章节审校服务：一致性 / 爽点节奏 / 错字 / 设定冲突检查。"""

from app.llm.call import run_llm
from app.schemas.novel import NovelOutline

REVIEW_SYSTEM_ROLE = "你是一名资深网文编辑，负责审校章节的一致性、爽点节奏、错字与设定冲突。"


def build_review_prompt(
    outline: NovelOutline,
    chapter_title: str,
    chapter_text: str,
    memory: str,
) -> str:
    """构建审校 Prompt。"""
    excerpt = chapter_text[:6000]
    memory_section = memory.strip() or "（无）"
    return f"""请审校下面的小说章节，只报告真实存在的问题。

## 章节信息
书名：{outline.title or "（未命名）"}
章节：{chapter_title or "（未命名）"}
全书梗概：{outline.summary or "（无）"}
世界观：{outline.world or "（无）"}
主要角色：
{chr(10).join(f"- {c.name}（{c.role}）：{c.description}" for c in outline.characters) or "（无）"}

## 已知剧情记忆（跨章一致性依据）
{memory_section}

## 章节正文
{excerpt}

## 输出要求
只输出一个合法的 JSON 对象：
{{"issues": [
  {{"type": "一致性|爽点节奏|错字|设定冲突|其它", "severity": "high|medium|low",
    "description": "问题描述", "suggestion": "修改建议"}}
]}}
没有问题时返回 {{"issues": []}}。
要求：每条 issue 必须具体、可操作；不要无中生有；最多 10 条。"""


async def review_chapter(
    llm,
    outline: NovelOutline,
    chapter_title: str,
    chapter_text: str,
    memory: str,
) -> list[dict]:
    """审校章节，返回问题列表；失败或正文为空时返回空列表。"""
    if not chapter_text.strip():
        return []
    prompt = build_review_prompt(outline, chapter_title, chapter_text, memory)
    try:
        data = await run_llm(llm.generate_json, prompt, system_prompt=REVIEW_SYSTEM_ROLE)
        issues = data.get("issues") or []
        return [i for i in issues if isinstance(i, dict)][:10]
    except Exception:  # noqa: BLE001 - 审校失败不影响主流程
        return []
