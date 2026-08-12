"""大纲格式化工具：供章节 / 标题 / 角色卡 Prompt 复用。"""

from app.schemas.novel import NovelOutline

# 每卷最多列出的章节标题数（按调用场景区分）
DEFAULT_CHAPTERS_PER_VOLUME = 20
TITLE_CHAPTERS_PER_VOLUME = 10
CARD_CHAPTERS_PER_VOLUME = 30


def format_outline(
    outline: NovelOutline,
    chapters_per_volume: int = DEFAULT_CHAPTERS_PER_VOLUME,
    volume_index: int | None = None,
    characters_label: str = "主要角色",
) -> str:
    """把大纲格式化为模型容易消化的文本。

    Args:
        outline: 小说大纲。
        chapters_per_volume: 每卷最多列出的章节标题数（默认 20）。
        volume_index: 标记目标卷（追加「 ← 目标卷」）；None 表示不标记。
        characters_label: 角色区块标题（角色卡 Prompt 使用「大纲主要角色」）。
    """
    characters = "\n".join(
        f"- {c.name}（{c.role}）：{c.description}" for c in outline.characters
    ) or "（无）"
    volumes = []
    for vi, vol in enumerate(outline.volume_plan):
        marker = " ← 目标卷" if volume_index is not None and vi == volume_index else ""
        chapters = "、".join(vol.chapters[:chapters_per_volume])
        volumes.append(f"第{vi + 1}卷 {vol.volume}{marker}：{chapters}")
    return (
        f"【书名】{outline.title or '（未命名）'}\n"
        f"【全书梗概】{outline.summary or '（无）'}\n"
        f"【世界观】{outline.world or '（无）'}\n"
        f"【{characters_label}】\n{characters}\n"
        f"【分卷计划】\n" + "\n".join(volumes)
    )


def format_outline_for_chapter(
    outline: NovelOutline,
    volume_index: int,
    chapters_per_volume: int = DEFAULT_CHAPTERS_PER_VOLUME,
    characters_label: str = "主要角色",
) -> str:
    """章节 / 标题 / 角色卡 Prompt 用的大纲摘要。

    只展开当前卷的章节列表，不再携带其它卷目录，显著降低单次调用的 Token 用量。
    """
    characters = "\n".join(
        f"- {c.name}（{c.role}）：{c.description}" for c in outline.characters
    ) or "（无）"
    if 0 <= volume_index < len(outline.volume_plan):
        vol = outline.volume_plan[volume_index]
        chapters = "、".join(vol.chapters[:chapters_per_volume])
        volume_section = f"第{volume_index + 1}卷 {vol.volume}：{chapters}"
    else:
        volume_section = "（无）"
    return (
        f"【书名】{outline.title or '（未命名）'}\n"
        f"【全书梗概】{outline.summary or '（无）'}\n"
        f"【世界观】{outline.world or '（无）'}\n"
        f"【{characters_label}】\n{characters}\n"
        f"【当前卷】\n{volume_section}"
    )
