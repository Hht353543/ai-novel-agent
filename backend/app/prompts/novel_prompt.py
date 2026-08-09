"""小说大纲生成 Prompt 模板。

设计目标：让模型明确知道「知识库里的每类总结分别该怎么用」，
同时通过输出约束降低 JSON 超长截断的概率。
"""

import re

from app.config import settings
from app.schemas.novel import NovelGenerateRequest


SYSTEM_ROLE = """你是一名拥有20年经验的网络小说白金作者，擅长东方玄幻、仙侠、武侠、都市异能等题材，深谙网文爽点节奏与商业化写作逻辑。"""


# 知识库板块 -> 使用指引。模型拿到分组资料后，按此消化而不是照抄。
CATEGORY_GUIDE = {
    "世界观": "这些是参考小说的世界观原文：从中吸收力量体系、地图设定、组织势力与背景逻辑，构建新作自洽的世界观；不要照搬原文。",
    "剧情大纲": "这些是参考小说的剧情原文：学习其分卷结构、节奏推进、爽点设计与悬念伏笔的写法；不要照搬原文。",
    "人物角色卡": "这些是参考小说的人物原文：学习人物性格、关系、成长弧光与对话风格的塑造方法；不要照搬原文。",
    "other": "其它参考资料：按需吸收其中合理设定。",
    "novel_info": "参考起点新书的真实卖点结构：开头钩子、身份设定、金手指与长线悬念如何搭配。",
    "rag_chunks": "这是从多本作品中提炼的知识切片，包含金手指与力量体系、主线剧情、人物群像、势力地理、爽点模板、写作技巧。优先吸收其中可复用的结构与方法，不要照搬书名和人物。",
    "主要人物侧写": "参考人物塑造方法：主角性格、配角关系、人物成长弧光，避免脸谱化。",
    "世界观": "参考世界观构建：力量体系、地图设定、组织势力与范围，保证新作世界观自洽。",
    "剧情大纲": "参考剧情结构：分卷规划、节奏要点、爽点设计、悬念伏笔。",
    "优秀情节": "参考优秀剧情设计：事件钩子、冲突推进、反转方式，并借鉴其文笔描写手法。",
    "作品借鉴": "参考借鉴要点：剧情设计、文风描写、商业化写法；保持新作剧情连贯与风格统一。",
    "灵感剧情添加": "用户临时添加的灵感剧情，按其中要求设计剧情走向。",
    "other": "作为背景资料参考，合理吸收其中设定。",
}

# 附件文本最大注入长度（超出截断，避免撑爆上下文）
MAX_ATTACHMENT_CHARS = 15000


def format_attachment(name: str, text: str) -> str:
    """把用户上传的 txt 附件格式化为 Prompt 片段（空附件返回空串）。"""
    content = (text or "").strip()
    if not content:
        return ""
    if len(content) > MAX_ATTACHMENT_CHARS:
        content = content[:MAX_ATTACHMENT_CHARS] + "\n……（附件过长，已截断）"
    return (
        "## 用户上传的附件（最高优先级：其中明确的要求与设定必须遵守，素材可直接采用）\n"
        f"【附件名】{name or '未命名.txt'}\n"
        f"{content}"
    )


def parse_total_words(requirement: str) -> int:
    """从字数规模解析总字数。

    支持格式：100万字 / 100万 / 1,000,000字 / 5000字 等；
    解析失败时按 100 万字处理。
    """
    text = (requirement or "").replace(",", "").strip()
    m = re.search(r"(\d+(?:\.\d+)?)\s*(万)?\s*字?", text)
    if not m:
        return settings.outline_default_total_words
    num = float(m.group(1))
    if m.group(2) == "万":
        num *= 10000
    return max(1, int(num))


def plan_volumes(total_words: int) -> tuple[int, list[int]]:
    """按总字数规划卷数与每卷章数。

    规则：
    - 总章数 = ceil(总字数 / 每章字数)，保证至少 1 章；
    - 卷数随总章数增加（每约 N 章一卷，范围由配置控制）；
    - 每卷章数均匀分配，余数从第一卷开始逐卷加 1。

    Returns:
        (总章数, 每卷章数列表)
    """
    chapter_words = settings.outline_chapter_words
    total_chapters = max(1, (total_words + chapter_words - 1) // chapter_words)
    volume_count = min(
        settings.outline_volume_max,
        max(
            settings.outline_volume_min,
            (total_chapters + settings.outline_chapters_per_volume - 1)
            // settings.outline_chapters_per_volume,
        ),
    )
    # 短篇作品不强行分卷：每卷至少 1 章
    volume_count = min(volume_count, total_chapters)
    base, extra = divmod(total_chapters, volume_count)
    per_volume = [base + (1 if i < extra else 0) for i in range(volume_count)]
    return total_chapters, per_volume


def build_volume_plan_section(requirement: str) -> str:
    """生成卷章规划约束文本，注入 Prompt。"""
    total_words = parse_total_words(requirement)
    total_chapters, per_volume = plan_volumes(total_words)
    distribution = "、".join(
        f"第{i + 1}卷 {n} 章" for i, n in enumerate(per_volume)
    )
    return (
        f"- 总字数：约 {total_words} 字（按用户填写的「{requirement or '未填写'}」解析）\n"
        f"- 每章按 {settings.outline_chapter_words} 字计算，全书共 **{total_chapters} 章**\n"
        f"- 全书分 **{len(per_volume)} 卷**，各卷章数：{distribution}\n"
        f"- 章节目录（chapters 字段）**不需要你生成具体标题**："
        f"你只需在每卷 chapters 中放 1~2 个示例条目，"
        f"系统会自动按上述规划生成完整编号目录（第一章～第{total_chapters}章），"
        f"你重点保证 volume_plan 的卷数与卷名设计即可。"
    )


def build_style_requirement_section(request: NovelGenerateRequest) -> str:
    """构建爽点设计约束。

    用户输入优先：只要用户填了主题或关键词，就严格按用户输入设计；
    只有两者都留空时，才使用默认流派（无敌流 / 系统流 / 极道流）。
    """
    theme = (request.theme or "").strip()
    keywords = (request.keywords or "").strip()
    if theme or keywords:
        return (
            f"严格围绕用户指定的主题「{theme or '（未填）'}」"
            f"与关键词「{keywords or '（未填）'}」设计爽点与剧情走向，"
            f"不要自行更换、添加或混入其他流派套路。"
        )
    # 用户没有输入时才使用默认预设
    return (
        "用户未指定主题与关键词，默认采用以下流派设计爽点：\n"
        "   - 无敌流：开局满级、碾压式爽感、实力与身份错位带来的反差打脸；\n"
        "   - 系统流：清晰的任务/奖励循环，完成事件即时获得武学或能力，"
        "形成\"接任务—执行—领奖\"的稳定节奏；\n"
        "   - 极道流：以命搏命、苦练破限、代价换力量，成长有重量感和压迫感。"
    )


def build_novel_prompt(
    request: NovelGenerateRequest,
    context: list[dict],
) -> str:
    """根据用户需求与 RAG 检索结果构建完整 Prompt。

    Args:
        request: 用户的小说创意需求。
        context: 知识库检索结果列表，元素含 source/content/category 字段。

    Returns:
        可直接发送给 DeepSeek 的完整用户提示词。
    """
    # 按板块分组展示检索结果，并附上「如何使用」指引
    grouped: dict[str, list[str]] = {}
    for item in context:
        category = item.get("category", "other")
        source = item.get("source", "")
        content = item.get("content", "")
        grouped.setdefault(category, []).append(
            f"【来源：{source}】\n{content}"
        )

    if grouped:
        context_section = "\n\n".join(
            f"### 板块：{category}\n使用指引：{CATEGORY_GUIDE.get(category, CATEGORY_GUIDE['other'])}\n\n"
            + "\n\n".join(items)
            for category, items in grouped.items()
        )
    else:
        context_section = "（知识库中未检索到相关资料）"

    attachment_section = format_attachment(
        request.attachment_name, request.attachment_text
    )

    return f"""{SYSTEM_ROLE}

请根据以下需求创作一部网络小说的完整大纲。

## 用户需求
- 小说标题（可为空，由你拟定）：{request.title or "（未指定）"}
- 小说类型：{request.genre}
- 核心主题：{request.theme or "（未指定）"}
- 关键词：{request.keywords or "（无）"}
- 字数规模：{request.requirement}
- 其他要求：{request.extra_requirements or "（无，由你自行把握）"}

{attachment_section}

## 知识库参考资料
以下是从本地知识库中按板块读取的参考小说原文（txt）。请严格按照每个板块的「使用指引」吸收其中可复用的设定、人物模型与剧情结构，但禁止照搬原文、书名与角色名：

{context_section}

## 输出要求
只输出一个合法的 JSON 对象，不要包含任何解释文字、不要使用代码块标记，结构如下：
{{
  "title": "拟定的小说书名",
  "summary": "全书核心梗概（200字以内）",
  "world": "世界观设定（力量体系、地图、势力、背景）",
  "characters": [
    {{"name": "角色名", "role": "角色定位", "description": "性格与成长线"}}
  ],
  "volume_plan": [
    {{
      "volume": "卷名（如：第一卷 觉醒）",
      "chapters": ["第一章", "第二章"]
    }}
  ]
}}

要求：
1. 世界观、人物、剧情要与「{request.genre}」题材和「{request.theme}」主题高度契合；
2. 核心爽点（用户输入优先）：
{build_style_requirement_section(request)}
   不要自行添加任何用户未指定的旧套路（如退婚流、随身老爷爷、天才陨落等）。
3. 卷章规划（系统按此生成完整目录）：
{build_volume_plan_section(request.requirement)}
4. 人物设定**完全以用户输入与知识库参考文本为准**：只设计知识库参考文本和用户输入中
   明确出现或合理需要的人物，禁止预设、强行添加任何角色类型（尤其禁止凭空添加
   「女主」「导师」「老爷爷」等用户未要求的角色）；角色数量与类型由剧情需要决定；
5. JSON 必须完整闭合：所有字符串用双引号，不得省略右引号、] 或 }}；
6. 控制篇幅：world 200~500 字，volume_plan 卷数必须与规划一致（每卷 chapters 只需 1~2 个示例）。"""
