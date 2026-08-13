"""极简 Agent 注册表与工厂（避免 if/elif 硬编码 Agent 类型）。"""

from typing import Callable, TypeVar

from app.agents.base import BaseAgent
from app.agents.character_agent import CharacterAgent
from app.agents.memory_agent import MemoryAgent
from app.agents.planner_agent import PlannerAgent
from app.agents.reviewer_agent import ReviewerAgent
from app.agents.timeline_agent import TimelineAgent
from app.agents.writer_agent import WriterAgent

T = TypeVar("T", bound=BaseAgent)

# Agent 工厂签名：llm / retriever 由编排器统一注入
AgentFactory = Callable[..., BaseAgent]


class AgentRegistry:
    """按名称注册与创建 Agent。"""

    def __init__(self) -> None:
        self._factories: dict[str, AgentFactory] = {}

    def register(self, name: str, factory: AgentFactory) -> None:
        self._factories[name] = factory

    def create(self, name: str, **deps: object) -> BaseAgent:
        if name not in self._factories:
            raise KeyError(f"未知 Agent: {name}")
        return self._factories[name](**deps)

    def names(self) -> list[str]:
        return list(self._factories)


default_registry = AgentRegistry()
default_registry.register("planner", PlannerAgent)
default_registry.register("character", CharacterAgent)
default_registry.register("writer", WriterAgent)
default_registry.register("reviewer", ReviewerAgent)
default_registry.register("memory", MemoryAgent)
default_registry.register("timeline", TimelineAgent)


def create_agent(name: str, **deps: object) -> BaseAgent:
    """创建默认注册表中的 Agent。"""
    return default_registry.create(name, **deps)
