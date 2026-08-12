"""章节标题生成 Prompt 模板。

两种模式：
- volume：根据大纲与卷剧情，生成该卷前 10 章的具体标题；
- chapter：根据已写正文，重新生成当前章节的标题。
"""

from app.schemas.novel import TitlesGenerateRequest

from app.prompts.outline_formatter import (
    TITLE_CHAPTERS_PER_VOLUME,
    format_outline_for_chapter,
)

# 单章标题生成时最多携带的正文节选字符数
TITLE_EXCERPT_MAX_CHARS = 2500

SYSTEM_ROLE = """你是一名拥有20年经验的网络小说白金作者，擅长设计有钩子、有网感的章节标题。"""


def build_volume_titles_prompt(
    request: TitlesGenerateRequest,
) -> str:
    """构建「按卷生成前 10 章标题」的 Prompt。"""
    volume_label = request.volume_label or (
        request.outline.volume_plan[request.volume_index].volume
        if 0 <= request.volume_index < len(request.outline.volume_plan)
        else f"第{request.volume_index + 1}卷"
    )
    existing = "、".join(request.existing_titles[:10]) or "（暂无，全部由你设计）"
    return f"""请为一部网络小说大纲中的「第 {request.volume_index + 1} 卷 {volume_label}」设计**前 10 章**的章节标题。

## 小说大纲
{format_outline_for_chapter(
    request.outline,
    request.volume_index,
    chapters_per_volume=TITLE_CHAPTERS_PER_VOLUME,
)}

## 本卷已有的标题（用于衔接与避免重复）
{existing}

## 输出要求
只输出一个合法的 JSON 对象，不要包含任何解释文字、不要使用代码块标记：
{{"titles": ["标题1", "标题2", ..., "标题10"]}}

## 设计要求
1. 正好 10 个标题，每个 8~15 字，**只写标题本身，不要加序号和章字**；
2. 标题要有钩子：突出本章核心事件、冲突或爽点，避免空泛的"初入江湖"式标题；
3. 10 个标题要构成该卷前 10 章的递进节奏：开局钩子→小事件→第一次冲突→小高潮；
4. 风格与书名、题材一致，不要剧透最终结局。"""


def build_chapter_title_prompt(
    request: TitlesGenerateRequest,
) -> str:
    """构建「根据正文生成单章标题」的 Prompt。"""
    volume_label = request.volume_label or (
        request.outline.volume_plan[request.volume_index].volume
        if 0 <= request.volume_index < len(request.outline.volume_plan)
        else f"第{request.volume_index + 1}卷"
    )
    text = request.chapter_text.strip()
    if not text:
        raise ValueError("正文为空，无法生成标题")
    excerpt = text[:TITLE_EXCERPT_MAX_CHARS]
    return f"""请根据一章小说的正文内容，为这一章重新设计一个章节标题。

## 所属信息
- 书名：{request.outline.title or '（未命名）'}
- 卷：{volume_label}
- 当前旧标题：{request.outline.volume_plan[request.volume_index].chapters[request.chapter_index] if 0 <= request.volume_index < len(request.outline.volume_plan) and 0 <= request.chapter_index < len(request.outline.volume_plan[request.volume_index].chapters) else '（无）'}

## 章节正文（节选）
{excerpt}

## 输出要求
只输出一个合法的 JSON 对象，不要包含任何解释文字、不要使用代码块标记：
{{"titles": ["新标题"]}}

## 设计要求
1. 只输出 1 个标题，8~15 字，**只写标题本身，不要加序号和章字**；
2. 抓住本章的核心事件、反转或钩子，不要用笼统的概括；
3. 与旧标题不同，避免重复。"""
