"""章节标题生成 Prompt 模板。

两种模式：
- volume：根据大纲与卷剧情，生成该卷前 10 章的具体标题；
- chapter：根据已写正文，重新生成当前章节的标题。
"""

from app.schemas.novel import NovelOutline, TitlesGenerateRequest


SYSTEM_ROLE = """你是一名拥有20年经验的网络小说白金作者，擅长设计有钩子、有网感的章节标题。"""


def _format_outline(outline: NovelOutline) -> str:
    """把大纲压缩为标题设计所需的上下文。"""
    characters = "\n".join(
        f"- {c.name}（{c.role}）：{c.description}" for c in outline.characters
    ) or "（无）"
    volumes = []
    for vi, vol in enumerate(outline.volume_plan):
        chapters = "、".join(vol.chapters[:10])
        volumes.append(f"第{vi + 1}卷 {vol.volume}：{chapters}")
    return (
        f"【书名】{outline.title or '（未命名）'}\n"
        f"【全书梗概】{outline.summary or '（无）'}\n"
        f"【世界观】{outline.world or '（无）'}\n"
        f"【主要角色】\n{characters}\n"
        f"【分卷计划】\n" + "\n".join(volumes)
    )


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
    return f"""{SYSTEM_ROLE}

请为一部网络小说大纲中的「第 {request.volume_index + 1} 卷 {volume_label}」设计**前 10 章**的章节标题。

## 小说大纲
{_format_outline(request.outline)}

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
    excerpt = text[:2500]
    return f"""{SYSTEM_ROLE}

请根据一章小说的正文内容，为这一章重新设计一个章节标题。

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
