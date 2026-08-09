"""章节正文生成 Prompt 模板。

职责：把「大纲 + 知识库资料 + 已确认的上文」组合成正文写作指令。
支持三种模式：
- generate：首次生成整章正文（或开头部分）；
- continue：以用户编辑后的全文为上文，从末尾继续追加；
- rewrite：以用户修改处之前的内容为上文，重新生成其后内容。
"""

from app.schemas.novel import ChapterGenerateRequest, NovelOutline

from app.prompts.character_card_prompt import format_character_cards
from app.prompts.novel_prompt import format_attachment


SYSTEM_ROLE = """你是一名拥有20年经验的网络小说白金作者，擅长东方玄幻、仙侠、武侠、都市异能等题材，文笔成熟，节奏感强，能精准延续已有情节并保持人物言行一致。"""


MODE_GUIDE = {
    "generate": "这是本章首次生成，请从章节起点开始写，开篇要有钩子，直接进入事件。",
    "continue": "你拿到的是作者已写好的上文，请从末尾自然衔接，继续向下推进情节，不要重复上文内容。",
    "rewrite": "你拿到的是人工修改后的上文（修改处之前的内容）。请严格以此为基准，重新写出修改处之后的新内容，丢弃任何与上文冲突的旧设定，保证上下文连贯。",
}


def _format_outline(outline: NovelOutline) -> str:
    """把大纲格式化为模型容易消化的文本。"""
    characters = "\n".join(
        f"- {c.name}（{c.role}）：{c.description}" for c in outline.characters
    ) or "（无）"
    volumes = []
    for vi, vol in enumerate(outline.volume_plan):
        chapters = "、".join(vol.chapters[:20])
        volumes.append(f"第{vi + 1}卷 {vol.volume}：{chapters}")
    return (
        f"【书名】{outline.title or '（未命名）'}\n"
        f"【全书梗概】{outline.summary or '（无）'}\n"
        f"【世界观】{outline.world or '（无）'}\n"
        f"【主要角色】\n{characters}\n"
        f"【分卷计划】\n" + "\n".join(volumes)
    )


def build_chapter_prompt(
    request: ChapterGenerateRequest,
    rag_context: list[dict],
) -> str:
    """构建章节正文生成 Prompt。

    Args:
        request: 章节生成请求（含大纲、章节定位、上文、模式）。
        rag_context: 知识库检索结果（人物/世界观/剧情/写作技巧等）。

    Returns:
        可直接发送给 DeepSeek 的完整用户提示词。
    """
    volume = request.outline.volume_plan[request.volume_index].volume if (
        0 <= request.volume_index < len(request.outline.volume_plan)
    ) else ""
    chapter_title = request.chapter_title or f"第{request.chapter_index + 1}章"

    # 知识库按板块分组
    grouped: dict[str, list[str]] = {}
    for item in rag_context:
        grouped.setdefault(item.get("category", "other"), []).append(
            f"【来源：{item.get('source', '')}】\n{item.get('content', '')}"
        )
    context_section = (
        "\n\n".join(
            f"### 板块：{cat}\n" + "\n\n".join(items)
            for cat, items in grouped.items()
        )
        if grouped
        else "（知识库中未检索到相关资料）"
    )

    context_text = request.context_text.strip()
    if context_text:
        context_block = f"【上文（作者已确认，必须严格衔接）】\n{context_text}\n"
    else:
        context_block = "【上文】无（本章开头）\n"

    previous_text = request.previous_chapter_text.strip()
    if previous_text:
        previous_block = (
            "## 前一章结尾（跨章衔接依据，必须与其无缝衔接）\n"
            f"{previous_text}\n"
        )
    else:
        previous_block = "## 前一章结尾\n（无，这是第一章或尚未提供前文）\n"

    # 当前卷角色卡：角色言行必须符合卡片定义
    character_cards_section = format_character_cards(request.character_cards)
    attachment_section = format_attachment(
        request.attachment_name, request.attachment_text
    )

    return f"""请为一部网络小说创作章节正文。

## 小说大纲
{_format_outline(request.outline)}

## 当前章节
- 卷：{volume or "（未分卷）"}
- 章节：{chapter_title}
- 章节序号：第 {request.chapter_index + 1} 章
- 期望字数：约 {request.target_length} 字
- 模式：{request.mode}（{MODE_GUIDE.get(request.mode, MODE_GUIDE["generate"])}）

## 本卷角色卡（角色言行必须严格遵守，不得偏离角色设定）
{character_cards_section}

{attachment_section}

{previous_block}

## 知识库参考资料
以下是从本地知识库中按板块读取的参考小说原文（txt）：
- 世界观板块 → 用于保持新作世界观的设定一致；
- 人物角色卡板块 → 用于学习人物塑造，配合「本卷角色卡」保持人物言行一致；
- 剧情大纲板块 → 用于把握剧情节奏与爽点；
- other → 其它参考。
请合理吸收，不要照搬原文：

{context_section}

{context_block}
## 写作要求
1. 直接输出小说正文，不要输出章节标题、不要输出 Markdown 标记、不要输出任何解释或大纲；
2. 严格衔接上文，人物称呼、性格、武功/能力设定必须与大纲和知识库一致，不得吃设定；
3. 出场角色的外貌、性格、说话风格必须符合「本卷角色卡」定义，不得 OOC；
4. 必须与「前一章结尾」无缝衔接：承接上一章结束时的人物状态、地点、时间、悬念与局势，
   本章开篇先回应/延续上一章的收尾，再推进新事件；禁止出现与前一章矛盾的情节或人物状态；
5. 场景与对话要具体，避免空泛叙述；保持网文节奏，适当留钩子；
6. 本次只写到约 {request.target_length} 字为止，自然收在一个小节点上，不要一次性把整章写完；
7. 额外要求：{request.extra_requirements or "（无，由你自行把握）"}。"""
