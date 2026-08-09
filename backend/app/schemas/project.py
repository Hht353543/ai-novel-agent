"""小说项目（大纲 + 章节草稿）存储数据模型。"""

from typing import Any

from pydantic import BaseModel, Field

from app.schemas.character import CharacterCard
from app.schemas.novel import NovelOutline


class ChapterDraft(BaseModel):
    """单个章节的草稿。"""

    volume_index: int = Field(default=0, description="卷索引（0 起）")
    chapter_index: int = Field(default=0, description="章索引（0 起）")
    chapter_title: str = Field(default="", description="章节标题")
    content: str = Field(default="", description="章节正文内容")


class NovelProject(BaseModel):
    """一个完整的小说项目：大纲 + 所有章节草稿。"""

    id: str = Field(default="", description="项目 ID；为空时由后端生成")
    title: str = Field(default="", description="项目标题（取自大纲书名）")
    outline: NovelOutline = Field(default_factory=NovelOutline)
    chapters: list[ChapterDraft] = Field(default_factory=list)
    character_cards: list[CharacterCard] = Field(
        default_factory=list, description="各卷角色卡"
    )
    created_at: str = Field(default="", description="创建时间 ISO 格式")
    updated_at: str = Field(default="", description="最后保存时间 ISO 格式")


class ProjectSummary(BaseModel):
    """项目列表中的摘要信息。"""

    id: str = ""
    title: str = ""
    chapter_count: int = 0
    created_at: str = ""
    updated_at: str = ""


class ProjectListResponse(BaseModel):
    """项目列表响应。"""

    projects: list[ProjectSummary] = Field(default_factory=list)


class ProjectSaveRequest(BaseModel):
    """保存项目请求体（upsert：id 存在则更新，否则新建）。"""

    id: str = Field(default="", description="项目 ID；空字符串表示新建")
    outline: NovelOutline = Field(default_factory=NovelOutline)
    chapters: list[ChapterDraft] = Field(default_factory=list)
    character_cards: list[CharacterCard] = Field(default_factory=list)
    # 兼容前端可能多传的字段，忽略即可
    title: str = ""

    class Config:
        """Pydantic v1 配置：忽略多余字段。"""

        extra = "ignore"


class ProjectSaveResponse(BaseModel):
    """保存项目响应。"""

    success: bool = True
    message: str = ""
    project: NovelProject | None = None
