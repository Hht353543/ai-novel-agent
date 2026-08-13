"""Agent 基类与统一错误机制。"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from app.llm.call import LLMError, run_llm
from app.llm.deepseek_provider import DeepSeekProvider
from app.llm.provider import BaseLLM
from app.rag.base import RetrievalProvider
from app.rag.retriever import get_retriever
from app.agents.context import AgentContext, AgentStep
from app.agents.protocol import AgentErrorInfo

logger = logging.getLogger(__name__)

T = TypeVar("T")


class AgentError(Exception):
    """Agent 统一错误：包含 agent / operation / error_type / run_id / retry_count。"""

    def __init__(
        self,
        agent: str,
        operation: str,
        error_type: str,
        message: str,
        run_id: str = "",
        retry_count: int = 0,
    ) -> None:
        super().__init__(message)
        self.agent = agent
        self.operation = operation
        self.error_type = error_type
        self.message = message
        self.run_id = run_id
        self.retry_count = retry_count
        self.info = AgentErrorInfo(
            agent=agent,
            operation=operation,
            error_type=error_type,
            message=message,
            retry_count=retry_count,
            run_id=run_id,
        )

    def __str__(self) -> str:
        return f"[{self.agent}:{self.operation}] {self.error_type}: {self.message}"


class BaseAgent(ABC, Generic[T]):
    """Agent 抽象基类。

    子类实现 _run 与校验钩子；execute 负责统一遥测与错误包装。
    Agent 只能通过构造注入的 llm / retriever 访问基础设施。
    """

    name: str = "base"
    role: str = ""

    def __init__(
        self,
        llm: BaseLLM | None = None,
        retriever: RetrievalProvider | None = None,
    ) -> None:
        self.llm = llm or DeepSeekProvider()
        self.retriever = retriever or get_retriever()

    async def execute(self, ctx: AgentContext) -> T:
        """执行 Agent：校验输入 → 运行 → 校验输出，并记录遥测。"""
        start = time.perf_counter()
        step = AgentStep(
            agent=self.name,
            operation=self.name,
            input_type="AgentContext",
        )
        try:
            self.validate_input(ctx)
            result = await self._run(ctx)
            self.validate_output(ctx, result)
            step.status = "ok"
            step.output_type = type(result).__name__
            return result
        except AgentError:
            step.status = "error"
            raise
        except LLMError as exc:
            step.status = "error"
            raise AgentError(
                self.name,
                self.name,
                exc.kind,
                str(exc.message),
                run_id=ctx.run_id,
            ) from exc
        except Exception as exc:  # noqa: BLE001 - 统一包装，禁止静默
            step.status = "error"
            logger.exception("Agent %s 未预期异常", self.name)
            raise AgentError(
                self.name,
                self.name,
                "unknown",
                str(exc),
                run_id=ctx.run_id,
            ) from exc
        finally:
            step.duration_ms = (time.perf_counter() - start) * 1000
            ctx.telemetry.steps.append(step)

    @abstractmethod
    async def _run(self, ctx: AgentContext) -> T:
        """Agent 核心逻辑。"""

    def validate_input(self, ctx: AgentContext) -> None:
        """输入校验；失败抛 AgentError(error_type=validation)。"""

    def validate_output(self, ctx: AgentContext, result: T) -> None:
        """输出校验；失败抛 AgentError(error_type=validation)。"""

    async def _retrieve(
        self,
        ctx: AgentContext,
        query: str,
        categories: list[str] | None = None,
    ) -> list[dict]:
        """统一 RAG 调用：计数并将异常包装为 AgentError(rag)。"""
        ctx.telemetry.rag_calls += 1
        from app.services.knowledge_compress import default_categories

        cats = categories if categories is not None else default_categories()
        try:
            return await asyncio.to_thread(self.retriever.retrieve, query, cats)
        except Exception as exc:  # noqa: BLE001 - RAG 失败显式抛出
            raise AgentError(
                self.name,
                "retrieve",
                "rag",
                str(exc),
                run_id=ctx.run_id,
            ) from exc

    async def _llm_json(
        self,
        ctx: AgentContext,
        prompt: str,
        system_prompt: str,
    ) -> dict[str, Any]:
        """统一 LLM JSON 调用：计数；异常由 execute 包装。"""
        ctx.telemetry.llm_calls += 1
        return await run_llm(
            self.llm.generate_json,
            prompt,
            system_prompt=system_prompt,
        )

    async def _llm_text(
        self,
        ctx: AgentContext,
        prompt: str,
        system_prompt: str,
    ) -> str:
        """统一 LLM 文本调用：计数；异常由 execute 包装。"""
        ctx.telemetry.llm_calls += 1
        return await run_llm(
            self.llm.generate,
            prompt,
            json_mode=False,
            system_prompt=system_prompt,
        )
