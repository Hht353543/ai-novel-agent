"""多 Agent 协议与数据结构。

全部为 Pydantic v1 模型：可序列化、可保存、可在 Agent 之间传递。
复用了现有 app.schemas.novel 中的 Character / NovelOutline / ReviewIssue。
"""

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.novel import Character, NovelOutline, ReviewIssue, VolumePlan

# Agent 响应统一状态
AgentStatus = Literal["success", "demo", "error", "revision_exhausted"]


class AgentRequest(BaseModel):
    """Agent 请求信封（各端点请求模型可继承）。"""

    project_id: str = Field(default="", description="项目 ID（可空）")
    run_id: str = Field(default="", description="运行 ID；为空时由编排器生成")


class AgentErrorInfo(BaseModel):
    """结构化错误信息（随 AgentResponse 返回）。"""

    agent: str = ""
    operation: str = ""
    error_type: str = ""
    message: str = ""
    retry_count: int = 0
    run_id: str = ""


class AgentResponse(BaseModel):
    """Agent 统一响应基类。"""

    success: bool = True
    status: AgentStatus = "success"
    agent: str = ""
    run_id: str = ""
    message: str = ""
    error: AgentErrorInfo | None = None
    telemetry: dict[str, Any] = Field(default_factory=dict)


class WorldSetting(BaseModel):
    """世界观设定。"""

    overview: str = Field(default="", description="世界观总览")
    power_system: str = Field(default="", description="力量体系")
    factions: list[str] = Field(default_factory=list, description="势力列表")
    locations: list[str] = Field(default_factory=list, description="主要地点")


class MainPlot(BaseModel):
    """故事主线。"""

    premise: str = Field(default="", description="故事前提")
    main_goal: str = Field(default="", description="主线目标")
    core_conflict: str = Field(default="", description="核心冲突")
    theme: str = Field(default="", description="主题")


class ChapterOutline(BaseModel):
    """章节大纲。"""

    chapter_index: int = Field(default=0, description="章索引（0 起）")
    title: str = Field(default="", description="章节标题")
    goal: str = Field(default="", description="本章目标")
    beats: list[str] = Field(default_factory=list, description="剧情节拍")
    key_characters: list[str] = Field(default_factory=list, description="出场关键角色")
    location: str = Field(default="", description="主要地点")


class StoryArc(BaseModel):
    """卷纲（故事阶段）。"""

    arc_index: int = Field(default=0, description="卷索引（0 起）")
    name: str = Field(default="", description="卷名")
    goal: str = Field(default="", description="本卷目标")
    chapters: list[ChapterOutline] = Field(default_factory=list)


class NovelPlan(BaseModel):
    """结构化小说规划（PlannerAgent 输出）。"""

    title: str = ""
    genre: str = ""
    premise: str = Field(default="", description="核心创意")
    summary: str = Field(default="", description="全书梗概")
    world_setting: WorldSetting = Field(default_factory=WorldSetting)
    main_plot: MainPlot = Field(default_factory=MainPlot)
    arcs: list[StoryArc] = Field(default_factory=list)
    characters: list[Character] = Field(default_factory=list)
    requirement: str = Field(default="", description="字数规模/要求")
    extra_requirements: str = Field(default="", description="用户额外要求")

    def to_outline(self) -> NovelOutline:
        """转换为现有 NovelOutline，兼容旧存储与旧 UI。"""
        volumes: list[VolumePlan] = []
        for arc in self.arcs:
            chapters = [
                c.title or f"第{n + 1}章"
                for n, c in enumerate(arc.chapters)
            ]
            if not chapters:
                chapters = [f"第{n + 1}章" for n in range(8)]
            volumes.append(
                VolumePlan(
                    volume=arc.name or f"第{arc.arc_index + 1}卷",
                    chapters=chapters,
                )
            )
        if not volumes:
            volumes = [VolumePlan(volume="第一卷", chapters=["第一章"])]
        world_parts = [self.world_setting.overview]
        if self.world_setting.power_system:
            world_parts.append(f"力量体系：{self.world_setting.power_system}")
        return NovelOutline(
            title=self.title,
            summary=self.summary or self.main_plot.premise,
            world="\n".join(p for p in world_parts if p),
            characters=list(self.characters),
            volume_plan=volumes,
        )


class CharacterProfile(BaseModel):
    """人物设定（静态档案）。"""

    name: str = ""
    role: str = ""
    age: str = ""
    appearance: str = ""
    personality: str = ""
    background: str = ""
    goals: str = ""
    motivation: str = ""
    speech_style: str = ""
    growth_arc: str = ""
    faction: str = ""


class CharacterState(BaseModel):
    """人物当前状态（动态，随剧情推进更新）。"""

    name: str = ""
    current_location: str = ""
    current_faction: str = ""
    current_identity: str = ""
    cultivation: str = Field(default="", description="当前境界/实力")
    possessions: list[str] = Field(default_factory=list)
    known_info: list[str] = Field(default_factory=list)
    relationships: list[str] = Field(default_factory=list)
    plot_status: str = ""


class CharacterRelation(BaseModel):
    """人物关系。"""

    from_name: str = ""
    to_name: str = ""
    relation: str = ""
    notes: str = ""


class CharacterSystem(BaseModel):
    """人物系统（CharacterAgent 输出）。"""

    profiles: list[CharacterProfile] = Field(default_factory=list)
    states: list[CharacterState] = Field(default_factory=list)
    relationships: list[CharacterRelation] = Field(default_factory=list)


class ReviewResult(BaseModel):
    """审校结果（ReviewerAgent 输出）。"""

    passed: bool = False
    score: int = Field(default=0, ge=0, le=100)
    issues: list[ReviewIssue] = Field(default_factory=list)
    summary: str = ""
    revision_required: bool = False


class ChapterResult(BaseModel):
    """章节写作结果（WriterAgent 输出）。"""

    attempt: int = Field(default=1, description="第几次写作（初始=1）")
    content: str = Field(default="", description="本次新生成正文")
    full_text: str = Field(default="", description="context_text + content")
    memory: str = Field(default="", description="生成后记忆")
    review: ReviewResult | None = Field(default=None, description="对应审校结果")


class RevisionAttempt(BaseModel):
    """一次审校-修订记录。"""

    attempt: int = 0
    instructions: str = Field(default="", description="审校给出的修改意见")
    content: str = ""
    review: ReviewResult | None = None


class PipelineResult(BaseModel):
    """完整 Pipeline 运行结果。"""

    run_id: str = ""
    project_id: str = ""
    status: AgentStatus = "success"
    message: str = ""
    plan: NovelPlan | None = None
    characters: CharacterSystem | None = None
    chapter: ChapterResult | None = None
    latest_review: ReviewResult | None = None
    revision_history: list[RevisionAttempt] = Field(default_factory=list)
    telemetry: dict[str, Any] = Field(default_factory=dict)


# ---------- 端点请求模型 ----------


class PlannerRequest(BaseModel):
    """Planner Agent 请求（字段与 NovelGenerateRequest 对齐）。"""

    project_id: str = ""
    title: str = ""
    genre: str = "武侠"
    theme: str = "无敌流"
    keywords: str = "系统流,极道流"
    requirement: str = "100万字"
    extra_requirements: str = ""
    attachment_name: str = ""
    attachment_text: str = ""


class CharacterRequest(BaseModel):
    """Character Agent 请求。"""

    project_id: str = ""
    plan: NovelPlan = Field(default_factory=NovelPlan)


class WriterRequest(BaseModel):
    """Writer Agent 请求。"""

    project_id: str = ""
    plan: NovelPlan = Field(default_factory=NovelPlan)
    volume_index: int = 0
    chapter_index: int = 0
    context_text: str = ""
    previous_chapter_text: str = ""
    target_length: int = Field(default=800, ge=100, le=5000)
    extra_requirements: str = ""
    attachment_name: str = ""
    attachment_text: str = ""
    memory: str = ""
    revision_instructions: str = ""


class ReviewRequest(BaseModel):
    """Reviewer Agent 请求。"""

    project_id: str = ""
    plan: NovelPlan = Field(default_factory=NovelPlan)
    chapter_title: str = ""
    chapter_text: str = ""
    memory: str = ""


class PipelineRequest(BaseModel):
    """完整 Pipeline 请求。"""

    project_id: str = ""
    save: bool = Field(default=False, description="是否把结果持久化到项目")
    title: str = ""
    genre: str = "武侠"
    theme: str = "无敌流"
    keywords: str = "系统流,极道流"
    requirement: str = "100万字"
    extra_requirements: str = ""
    attachment_name: str = ""
    attachment_text: str = ""
    volume_index: int = 0
    chapter_index: int = 0
    target_length: int = Field(default=800, ge=100, le=5000)
    with_review: bool = True
    max_revisions: int | None = Field(
        default=None, description="审校失败最大修订次数；缺省取配置 AGENT_MAX_REVISIONS"
    )


# ---------- 端点响应模型 ----------


class PlannerResponse(AgentResponse):
    plan: NovelPlan | None = None


class CharacterResponse(AgentResponse):
    characters: CharacterSystem | None = None


class WriterResponse(AgentResponse):
    chapter: ChapterResult | None = None


class ReviewerResponse(AgentResponse):
    review: ReviewResult | None = None


class PipelineResponse(AgentResponse):
    result: PipelineResult | None = None


__all__ = [
    "AgentStatus",
    "AgentRequest",
    "AgentErrorInfo",
    "AgentResponse",
    "WorldSetting",
    "MainPlot",
    "ChapterOutline",
    "StoryArc",
    "NovelPlan",
    "CharacterProfile",
    "CharacterState",
    "CharacterRelation",
    "CharacterSystem",
    "ReviewResult",
    "ChapterResult",
    "RevisionAttempt",
    "PipelineResult",
    "PlannerRequest",
    "CharacterRequest",
    "WriterRequest",
    "ReviewRequest",
    "PipelineRequest",
    "PlannerResponse",
    "CharacterResponse",
    "WriterResponse",
    "ReviewerResponse",
    "PipelineResponse",
]
