"""角色卡生成 Prompt 模板。

输入：大纲 + 指定卷（含该卷章节标题），
输出：该卷主要人物的角色卡 JSON 数组。
"""

from app.schemas.character import CharacterCard
from app.schemas.novel import CharacterCardsGenerateRequest

from app.prompts.outline_formatter import (
    CARD_CHAPTERS_PER_VOLUME,
    format_outline_for_chapter,
)

SYSTEM_ROLE = """你是一名拥有20年经验的网络小说白金作者，擅长塑造有记忆点、不脸谱化的角色。"""


def build_character_card_prompt(
    request: CharacterCardsGenerateRequest,
) -> str:
    """构建角色卡生成 Prompt。

    Args:
        request: 生成请求（大纲 + 卷索引 + 卷名）。

    Returns:
        可直接发送给 DeepSeek 的完整用户提示词。
    """
    volume_label = request.volume_label or (
        request.outline.volume_plan[request.volume_index].volume
        if 0 <= request.volume_index < len(request.outline.volume_plan)
        else f"第{request.volume_index + 1}卷"
    )
    fields = "、".join(
        [
            "name 角色名",
            "role 角色定位（按剧情实际需要，如主角/反派/搭档/长辈/配角等，不要预设类型）",
            "age 年龄或年龄段",
            "appearance 外貌特征",
            "personality 性格与行为习惯",
            "background 身世背景",
            "goals 目标与动机",
            "speech_style 说话风格与口头禅",
            "notes 备注（与其他角色的关系、本卷成长线）",
        ]
    )
    return f"""请为小说大纲中的「第 {request.volume_index + 1} 卷 {volume_label}」设计主要人物角色卡。

## 小说大纲
{format_outline_for_chapter(
    request.outline,
    request.volume_index,
    chapters_per_volume=CARD_CHAPTERS_PER_VOLUME,
    characters_label='大纲主要角色',
)}

## 输出要求
只输出一个合法的 JSON 对象，不要包含任何解释文字、不要使用代码块标记，结构如下：
{{"character_cards": [
  {{
    "volume_index": {request.volume_index},
    "name": "角色名",
    "role": "角色定位",
    "age": "年龄",
    "appearance": "外貌特征",
    "personality": "性格与行为习惯",
    "background": "身世背景",
    "goals": "目标与动机",
    "speech_style": "说话风格与口头禅",
    "notes": "备注"
  }}
]}}

## 设计要求
1. 本卷主要人物 4~7 人，至少包含主角、重要配角、反派或关键对手；
2. 每个字段都要有具体内容，禁止空字符串；外貌要具体（身形、服饰、标志性细节），
   性格要给出行为习惯与典型反应，背景要有事件支撑，说话风格要能直接模仿；
3. 人物不能脸谱化：每个角色至少有一个记忆点（怪癖、反差、执念或口头禅）；
4. 角色必须贴合本卷章节剧情（见上方分卷计划），为后续冲突与成长留出空间；
5. 字段内容每项 20~100 字，整体不要啰嗦。"""


def format_character_cards(cards: list[CharacterCard]) -> str:
    """把角色卡格式化为章节 Prompt 可直接使用的文本。"""
    if not cards:
        return "（本卷暂无角色卡，请以大纲角色设定为准）"
    lines = []
    for card in cards:
        lines.append(
            f"- {card.name or '未命名'}（{card.role or '角色'}）"
            + (f"，{card.age}" if card.age else "")
            + "\n"
            + f"  外貌：{card.appearance or '（未定义）'}\n"
            + f"  性格：{card.personality or '（未定义）'}\n"
            + f"  背景：{card.background or '（未定义）'}\n"
            + f"  目标：{card.goals or '（未定义）'}\n"
            + f"  说话风格：{card.speech_style or '（未定义）'}\n"
            + (f"  备注：{card.notes}" if card.notes else "")
        )
    return "\n".join(lines)
