"""Agent 运行时上下文与遥测。

所有重要状态显式放入 AgentContext，禁止通过全局变量在 Agent 之间传数据。
"""

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field

from app.config import Settings, settings
from app.llm.provider import BaseLLM
from app.rag.base import RetrievalProvider
from app.agents.protocol import (
    ChapterOutline,
    CharacterProfile,
    CharacterRelation,
    CharacterState,
    NovelPlan,
    PlannerRequest,
)


class AgentStep(BaseModel):
    """单步 Agent 执行记录。"""

    agent: str = ""
    operation: str = ""
    status: str = ""  # ok / error
    duration_ms: float = 0
    input_type: str = ""
    output_type: str = ""


class AgentTelemetry(BaseModel):
    """Agent 运行遥测（随响应返回，供调试与观测）。"""

    run_id: str = ""
    llm_calls: int = 0
    rag_calls: int = 0
    revision_attempts: int = 0
    duration_ms: float = 0
    steps: list[AgentStep] = Field(default_factory=list)


@dataclass
class AgentContext:
    """Agent 运行时上下文：承载全部输入、中间状态与遥测。"""

    run_id: str
    llm: BaseLLM
    retriever: RetrievalProvider
    config: Settings = settings
    project_id: str = ""
    user_request: str = ""
    planner_request: PlannerRequest | None = None
    plan: NovelPlan | None = None
    characters: list[CharacterProfile] = field(default_factory=list)
    character_states: list[CharacterState] = field(default_factory=list)
    relationships: list[CharacterRelation] = field(default_factory=list)
    current_arc: int = 0
    current_chapter: int = 0
    chapter_outline: ChapterOutline | None = None
    previous_summary: str = ""
    context_text: str = ""
    previous_chapter_text: str = ""
    retrieved_context: list[dict] = field(default_factory=list)
    extra_requirements: str = ""
    attachment_name: str = ""
    attachment_text: str = ""
    memory: str = ""
    target_length: int = 800
    chapter_title: str = ""
    chapter_text: str = ""
    revision_instructions: str = ""
    telemetry: AgentTelemetry = field(default_factory=AgentTelemetry)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.telemetry.run_id:
            self.telemetry.run_id = self.run_id
