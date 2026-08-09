"""小说生成接口的请求 / 响应数据模型。"""

from typing import Any

from pydantic import BaseModel, Field

from app.schemas.character import CharacterCard


class NovelGenerateRequest(BaseModel):
    """用户的小说创意需求。"""

    title: str = Field(default="", description="小说标题，可为空")
    genre: str = Field(default="武侠", description="小说类型，如：玄幻 / 仙侠 / 武侠 / 都市")
    theme: str = Field(default="无敌流", description="核心主题")
    keywords: str = Field(default="系统流,极道流", description="关键词，多个用逗号分隔")
    requirement: str = Field(default="100万字", description="字数规模或其它要求")
    extra_requirements: str = Field(
        default="",
        description="用户自由输入的其他要求，如风格、雷区、参考作品、剧情走向等",
    )
    attachment_name: str = Field(
        default="", description="用户上传的本地 txt 附件文件名（可空）"
    )
    attachment_text: str = Field(
        default="", description="用户上传的本地 txt 附件文本内容（可空）"
    )

    def to_query_text(self) -> str:
        """将需求转换为 RAG 检索查询文本。"""
        parts = [self.genre, self.theme]
        if self.title:
            parts.append(self.title)
        if self.keywords:
            parts.append(self.keywords)
        if self.extra_requirements:
            parts.append(self.extra_requirements)
        return " ".join(parts)


class ContextItem(BaseModel):
    """RAG 检索返回的单条上下文。"""

    source: str = Field(default="", description="资料来源文件")
    content: str = Field(default="", description="资料内容")
    category: str = Field(default="", description="资料所属板块（如 rag_chunks/世界观/人物侧写）")


class Character(BaseModel):
    """大纲中的角色。"""

    name: str = ""
    role: str = ""
    description: str = ""


class VolumePlan(BaseModel):
    """大纲中的卷计划。"""

    volume: str = ""
    chapters: list[str] = []


class NovelOutline(BaseModel):
    """AI 生成的完整小说大纲。"""

    title: str = ""
    summary: str = ""
    world: str = ""
    characters: list[Character] = []
    volume_plan: list[VolumePlan] = []

    class Config:
        """Pydantic v1 配置：容忍模型输出中的多余字段。"""

        extra = "ignore"


class NovelGenerateResponse(BaseModel):
    """生成接口响应：包含大纲与检索上下文。"""

    success: bool = True
    status: str = "success"  # success=成功 / demo=演示模式 / error=调用失败
    message: str = ""  # 提示信息（演示模式或错误原因）
    context: list[ContextItem] = Field(default_factory=list, description="RAG 检索到的资料")
    outline: NovelOutline = Field(default_factory=NovelOutline, description="AI 生成的大纲")
    raw: dict[str, Any] | None = Field(default=None, description="模型原始 JSON 输出")


class RetrieveResponse(BaseModel):
    """仅检索接口的响应。"""

    context: list[ContextItem] = Field(default_factory=list)


class ChapterGenerateRequest(BaseModel):
    """章节正文生成 / 续写 / 重写请求。

    mode 说明：
    - generate：首次生成章节正文（context_text 一般为空）；
    - continue：把 context_text（已编辑的全文）作为上文，从末尾继续追加；
    - rewrite：把 context_text（人工修改处之前的内容）作为上文，
      重新生成其后内容，前端会用 context_text + content 替换编辑器全文。
    """

    outline: NovelOutline = Field(default_factory=NovelOutline, description="小说大纲")
    volume_index: int = Field(default=0, description="卷索引（0 起）")
    chapter_index: int = Field(default=0, description="章索引（0 起）")
    chapter_title: str = Field(default="", description="当前章节标题")
    context_text: str = Field(default="", description="已确认/人工编辑过的上文")
    previous_chapter_text: str = Field(
        default="", description="前一章的正文结尾，用于跨章衔接（可空）"
    )
    mode: str = Field(default="generate", description="generate / continue / rewrite")
    target_length: int = Field(default=800, ge=100, le=5000, description="期望生成字数")
    character_cards: list[CharacterCard] = Field(
        default_factory=list,
        description="当前卷的角色卡，生成时按卡片定义角色",
    )
    extra_requirements: str = Field(
        default="", description="正文写作额外要求，如风格、雷区、节奏等"
    )
    attachment_name: str = Field(
        default="", description="用户上传的本地 txt 附件文件名（可空）"
    )
    attachment_text: str = Field(
        default="", description="用户上传的本地 txt 附件文本内容（可空）"
    )


class CharacterCardsGenerateRequest(BaseModel):
    """按卷生成角色卡的请求。"""

    outline: NovelOutline = Field(default_factory=NovelOutline, description="小说大纲")
    volume_index: int = Field(default=0, description="卷索引（0 起）")
    volume_label: str = Field(default="", description="卷名，便于模型理解该卷剧情")


class CharacterCardsGenerateResponse(BaseModel):
    """按卷生成角色卡的响应。"""

    success: bool = True
    status: str = "success"  # success / demo / error
    message: str = ""
    character_cards: list[CharacterCard] = Field(default_factory=list)


class TitlesGenerateRequest(BaseModel):
    """章节标题生成请求。

    mode 说明：
    - volume：按卷生成该卷前 10 章的具体标题（不一次性生成全部）；
    - chapter：根据已写正文重新生成当前章节的标题。
    """

    outline: NovelOutline = Field(default_factory=NovelOutline, description="小说大纲")
    volume_index: int = Field(default=0, description="卷索引（0 起）")
    volume_label: str = Field(default="", description="卷名")
    mode: str = Field(default="volume", description="volume / chapter")
    chapter_index: int = Field(default=0, description="mode=chapter 时当前章索引")
    chapter_text: str = Field(default="", description="mode=chapter 时已写正文")
    existing_titles: list[str] = Field(
        default_factory=list, description="mode=volume 时该卷已有的标题（可为空）"
    )


class TitlesGenerateResponse(BaseModel):
    """章节标题生成响应。"""

    success: bool = True
    status: str = "success"  # success / demo / error
    message: str = ""
    titles: list[str] = Field(
        default_factory=list, description="生成的标题（纯标题，不含序号）"
    )


class ChapterGenerateResponse(BaseModel):
    """章节正文生成接口响应。"""

    success: bool = True
    status: str = "success"  # success / demo / error
    message: str = ""
    content: str = Field(default="", description="本次新生成的正文")
    full_text: str = Field(
        default="", description="context_text + content，可直接替换编辑器全文"
    )
