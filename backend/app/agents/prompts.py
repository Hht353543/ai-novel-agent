"""多 Agent 专用 Prompt 构造器。

复用现有 novel_prompt 的上下文分组、附件、额外要求等公共片段，
不修改任何现有 Prompt 文件。
"""

from app.agents.protocol import (
    CharacterSystem,
    NovelPlan,
    PlannerRequest,
    StoryArc,
)
from app.prompts.novel_prompt import (
    build_volume_plan_section,
    format_attachment,
    format_extra_requirements,
    group_context,
)


def format_plan_for_prompt(
    plan: NovelPlan,
    arcs_limit: int = 8,
    chapters_per_arc: int = 12,
) -> str:
    """把规划格式化为模型容易消化的文本（只列卷名与章节标题，控制长度）。"""
    world = plan.world_setting
    lines = [
        f"【书名】{plan.title or '（未命名）'}",
        f"【类型】{plan.genre or '（未指定）'}",
        f"【核心创意】{plan.premise or plan.main_plot.premise or '（无）'}",
        f"【主线目标】{plan.main_plot.main_goal or '（无）'}",
        f"【核心冲突】{plan.main_plot.core_conflict or '（无）'}",
        f"【世界观】{world.overview or '（无）'}"
        + (f"；力量体系：{world.power_system}" if world.power_system else ""),
        f"【势力】{'、'.join(world.factions) or '（无）'}",
        f"【地点】{'、'.join(world.locations) or '（无）'}",
    ]
    for arc in plan.arcs[:arcs_limit]:
        chapters = "、".join(
            c.title or f"第{c.chapter_index + 1}章"
            for c in arc.chapters[:chapters_per_arc]
        )
        lines.append(
            f"第{arc.arc_index + 1}卷 {arc.name}（{arc.goal}）：{chapters}"
        )
    return "\n".join(lines)


def format_characters_for_prompt(
    characters: CharacterSystem,
    limit: int = 12,
) -> str:
    """把人物档案与当前状态格式化为 Prompt 片段。"""
    if not characters.profiles:
        return "（无人物设定）"
    lines = []
    for profile in characters.profiles[:limit]:
        state = next(
            (s for s in characters.states if s.name == profile.name),
            None,
        )
        state_text = ""
        if state:
            parts = []
            if state.current_location:
                parts.append(f"所在地：{state.current_location}")
            if state.cultivation:
                parts.append(f"境界/实力：{state.cultivation}")
            if state.plot_status:
                parts.append(f"剧情状态：{state.plot_status}")
            state_text = f"；当前状态：{'；'.join(parts)}" if parts else ""
        lines.append(
            f"- {profile.name}（{profile.role}）：性格 {profile.personality or '（未定义）'}；"
            f"目标 {profile.goals or '（未定义）'}；说话风格 {profile.speech_style or '（未定义）'}{state_text}"
        )
    return "\n".join(lines)


def _context_section(context: list[dict]) -> str:
    grouped = group_context(context)
    if not grouped:
        return "（知识库中未检索到相关资料）"
    return "\n\n".join(
        f"### 板块：{cat}\n" + "\n\n".join(items)
        for cat, items in grouped.items()
    )


PLANNER_OUTPUT_SCHEMA = """{
  "title": "拟定的小说书名",
  "genre": "小说类型",
  "premise": "核心创意（一句话）",
  "summary": "全书梗概（200字以内）",
  "world_setting": {
    "overview": "世界观总览（力量体系、地图、势力、背景）",
    "power_system": "力量体系说明",
    "factions": ["势力1", "势力2"],
    "locations": ["地点1", "地点2"]
  },
  "main_plot": {
    "premise": "故事前提",
    "main_goal": "主线目标",
    "core_conflict": "核心冲突",
    "theme": "主题"
  },
  "characters": [
    {"name": "角色名", "role": "角色定位", "description": "性格与成长线"}
  ],
  "arcs": [
    {
      "arc_index": 0,
      "name": "第一卷 卷名",
      "goal": "本卷目标",
      "chapters": [
        {
          "chapter_index": 0,
          "title": "第一章 标题",
          "goal": "本章目标",
          "beats": ["剧情节拍1", "剧情节拍2"],
          "key_characters": ["角色名"],
          "location": "地点"
        }
      ]
    }
  ]
}"""


def build_planner_prompt(request: PlannerRequest, context: list[dict]) -> str:
    """构建 Planner Agent 的完整提示词。"""
    return f"""请根据以下用户需求，创作一部网络小说的完整结构化规划。

## 用户需求
- 小说标题（可为空，由你拟定）：{request.title or "（未指定）"}
- 小说类型：{request.genre}
- 核心主题：{request.theme or "（未指定）"}
- 关键词：{request.keywords or "（无）"}
- 字数规模：{request.requirement}
- 其他要求：{format_extra_requirements(request.extra_requirements)}

{format_attachment(request.attachment_name, request.attachment_text)}

## 知识库参考资料
以下是从本地知识库中按板块读取的参考小说原文（txt）。请吸收可复用的设定、人物模型与剧情结构，但禁止照搬原文、书名与角色名：

{_context_section(context)}

## 卷章规划约束
{build_volume_plan_section(request.requirement)}

## 输出要求
只输出一个合法的 JSON 对象，不要包含任何解释文字、不要使用代码块标记，结构如下：
{PLANNER_OUTPUT_SCHEMA}

要求：
1. 世界观、人物、剧情要与「{request.genre}」题材和「{request.theme}」主题高度契合；
2. arcs 的卷数与每卷 chapters 数量必须与「卷章规划约束」完全一致；
3. 人物设定以用户输入与知识库参考文本为准：只设计明确出现或合理需要的人物，
   禁止凭空添加「女主」「导师」「老爷爷」等用户未要求的角色；
4. 每章 beats 给 2~4 个具体剧情节拍，key_characters 只列出真正出场的角色；
5. JSON 必须完整闭合：所有字符串用双引号，不得省略右引号、] 或 }}。"""


CHARACTER_OUTPUT_SCHEMA = """{
  "profiles": [
    {
      "name": "角色名",
      "role": "主角/反派/搭档/长辈/配角等",
      "age": "年龄或年龄段",
      "appearance": "外貌特征",
      "personality": "性格与行为习惯",
      "background": "身世背景",
      "goals": "目标与动机",
      "motivation": "深层动机",
      "speech_style": "说话风格与口头禅",
      "growth_arc": "成长路线（本阶段的变化）",
      "faction": "所属阵营"
    }
  ],
  "states": [
    {
      "name": "角色名（与 profiles 一一对应）",
      "current_location": "当前位置",
      "current_faction": "当前阵营",
      "current_identity": "当前身份",
      "cultivation": "当前境界/实力",
      "possessions": ["持有物"],
      "known_info": ["当前已知信息"],
      "relationships": ["与其他角色的当前关系摘要"],
      "plot_status": "当前剧情状态"
    }
  ],
  "relationships": [
    {"from_name": "角色A", "to_name": "角色B", "relation": "关系类型", "notes": "关系说明"}
  ]
}"""


def build_character_prompt(plan: NovelPlan, context: list[dict]) -> str:
    """构建 Character Agent 的完整提示词。"""
    return f"""请根据以下小说规划，建立完整的人物系统（档案 + 当前状态 + 关系网）。

## 小说规划
{format_plan_for_prompt(plan)}

## 知识库参考资料
{_context_section(context)}

## 输出要求
只输出一个合法的 JSON 对象，不要包含任何解释文字、不要使用代码块标记，结构如下：
{CHARACTER_OUTPUT_SCHEMA}

要求：
1. 本阶段主要人物 4~7 人，至少包含主角、重要配角、反派或关键对手；
2. states 与 profiles 按 name 一一对应，禁止缺漏；
3. 每个字段都要有具体内容（数组字段可为空列表），禁止空字符串；
4. 人物不能脸谱化：每个角色至少一个记忆点（怪癖、反差、执念或口头禅）；
5. states 描述的是「故事开始/当前卷」时的状态，为后续章节连续创作提供基础。"""


def build_writer_prompt(
    *,
    plan: NovelPlan,
    arc: StoryArc | None,
    chapter_outline,
    characters: CharacterSystem,
    memory: str,
    context_text: str,
    previous_chapter_text: str,
    rag_context: list[dict],
    extra_requirements: str,
    attachment_name: str,
    attachment_text: str,
    target_length: int,
    revision_instructions: str,
) -> str:
    """构建 Writer Agent 的完整提示词（纯文本输出）。"""
    chapter_title = (
        chapter_outline.title
        if chapter_outline is not None
        else "（未命名章节）"
    )
    arc_label = f"第{arc.arc_index + 1}卷 {arc.name}" if arc else "（未分卷）"
    beats = (
        "、".join(chapter_outline.beats)
        if chapter_outline is not None and chapter_outline.beats
        else "（无，由你自行把握节奏）"
    )
    revision_section = (
        f"\n## 修订意见（必须逐条落实）\n{revision_instructions}\n"
        if revision_instructions.strip()
        else ""
    )
    return f"""请为一部网络小说创作章节正文。

## 小说规划
{format_plan_for_prompt(plan)}

## 当前章节
- 卷：{arc_label}
- 章节：{chapter_title}
- 本章目标：{chapter_outline.goal if chapter_outline is not None else "（无）"}
- 剧情节拍：{beats}
- 期望字数：约 {target_length} 字

## 人物设定与当前状态（角色言行必须严格遵守）
{format_characters_for_prompt(characters)}

## 已知剧情记忆（跨章一致性依据）
{memory.strip() or "（无）"}

## 前一章结尾（跨章衔接依据，必须无缝衔接）
{previous_chapter_text.strip() or "（无，这是第一章或尚未提供前文）"}

{format_attachment(attachment_name, attachment_text)}

## 知识库参考资料
{_context_section(rag_context)}

## 上文（作者已确认，必须严格衔接）
{context_text.strip() or "（无，本章开头）"}
{revision_section}
## 写作要求
1. 直接输出小说正文，不要输出章节标题、不要输出 Markdown 标记、不要输出任何解释或大纲；
2. 严格衔接上文与前一章结尾，人物称呼、性格、实力必须与「人物设定与当前状态」一致，不得吃设定；
3. 按「本章目标」与「剧情节拍」推进剧情，场景与对话要具体，保持网文节奏，适当留钩子；
4. 本次只写到约 {target_length} 字为止，自然收在一个小节点上；
5. 额外要求：{format_extra_requirements(extra_requirements)}。"""


REVIEWER_OUTPUT_SCHEMA = """{
  "passed": true,
  "score": 80,
  "revision_required": false,
  "summary": "总体评价一句话",
  "issues": [
    {
      "type": "character_consistency",
      "severity": "high|medium|low",
      "description": "问题描述",
      "suggestion": "修改建议"
    }
  ]
}"""


def build_reviewer_prompt(
    *,
    plan: NovelPlan,
    chapter_title: str,
    chapter_text: str,
    characters: CharacterSystem,
    memory: str,
    rag_context: list[dict],
) -> str:
    """构建 Reviewer Agent 的完整提示词（JSON 输出）。"""
    excerpt = chapter_text.strip()[:6000]
    return f"""请审校下面的小说章节，只报告真实存在的问题。

## 章节信息
书名：{plan.title or "（未命名）"}
章节：{chapter_title or "（未命名）"}
全书梗概：{plan.summary or plan.main_plot.premise or "（无）"}
主线目标：{plan.main_plot.main_goal or "（无）"}
核心冲突：{plan.main_plot.core_conflict or "（无）"}
世界观：{plan.world_setting.overview or "（无）"}

## 人物设定与当前状态（一致性依据）
{format_characters_for_prompt(characters)}

## 已知剧情记忆（跨章一致性依据）
{memory.strip() or "（无）"}

## 知识库参考资料（设定依据）
{_context_section(rag_context)}

## 章节正文
{excerpt or "（空）"}

## 输出要求
只输出一个合法的 JSON 对象，不要包含任何解释文字、不要使用代码块标记，结构如下：
{REVIEWER_OUTPUT_SCHEMA}

检查清单（逐项核对，只报告真实问题）：
1. 剧情是否符合章节大纲与主线目标；
2. 人物行为是否符合人物设定与当前状态；
3. 世界观是否自洽；4. 时间线是否冲突；
5. 人物关系是否错误；6. 前后文是否矛盾；
7. 是否出现设定遗忘；8. 是否出现逻辑漏洞；
9. 是否存在明显水文；10. 是否存在重复内容；
11. 文风是否符合要求；12. 是否完成章节目标。

要求：
- score 为 0~100 的整数，与问题严重程度一致；通过标准：无明显 high 级问题且完成章节目标；
- issues 最多 10 条，每条必须具体、可操作；没有问题时返回空数组；
- revision_required=true 表示需要 Writer 修订后重新审校。"""
