"""Pipeline 运行状态与进程内 RunStore。

为前端提供真实进度：CREATED → PLANNING → CHARACTER_DESIGN → WRITING →
REVIEWING → REVISING → UPDATING_MEMORY → COMPLETED / FAILED。
"""

import threading
import time
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.agents.protocol import AgentErrorInfo
from app.traces.store import trace_store

RunStatus = Literal[
    "CREATED",
    "PLANNING",
    "CHARACTER_DESIGN",
    "WRITING",
    "REVIEWING",
    "REVISING",
    "UPDATING_MEMORY",
    "COMPLETED",
    "FAILED",
]


class RunProgressEntry(BaseModel):
    """单步进度记录。"""

    step: str = ""
    status: Literal["running", "done", "error"] = "running"
    agent: str = ""
    message: str = ""
    timestamp: str = ""


class PipelineRunState(BaseModel):
    """一次 Pipeline / Sequence 运行的完整状态。"""

    run_id: str = ""
    kind: Literal["pipeline", "sequence"] = "pipeline"
    status: RunStatus = "CREATED"
    current_agent: str = ""
    message: str = ""
    revision_attempts: int = 0
    progress: list[RunProgressEntry] = Field(default_factory=list)
    start_time: str = ""
    end_time: str = ""
    error: AgentErrorInfo | None = None
    result: dict[str, Any] | None = None


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


class RunStore:
    """进程内运行状态存储（线程安全，带 TTL 与上限清理）。"""

    def __init__(
        self,
        ttl_seconds: int = 3600,
        max_entries: int = 100,
    ) -> None:
        self._ttl_seconds = ttl_seconds
        self._max_entries = max_entries
        self._lock = threading.Lock()
        self._runs: dict[str, PipelineRunState] = {}

    def create(self, run_id: str, kind: str = "pipeline") -> PipelineRunState:
        state = PipelineRunState(
            run_id=run_id,
            kind=kind,
            status="CREATED",
            start_time=_now(),
        )
        with self._lock:
            self._cleanup_locked()
            self._runs[run_id] = state
        return state

    def get(self, run_id: str) -> PipelineRunState | None:
        with self._lock:
            state = self._runs.get(run_id)
            if state is None:
                return None
            if self._is_expired(state):
                self._runs.pop(run_id, None)
                return None
            return state.copy(deep=True)

    def update(self, run_id: str, **fields: Any) -> None:
        with self._lock:
            state = self._runs.get(run_id)
            if state is None:
                return
            for key, value in fields.items():
                if hasattr(state, key):
                    setattr(state, key, value)

    def add_progress(
        self,
        run_id: str,
        step: str,
        status: str = "running",
        agent: str = "",
        message: str = "",
    ) -> None:
        entry = RunProgressEntry(
            step=step,
            status=status,  # type: ignore[arg-type]
            agent=agent,
            message=message,
            timestamp=_now(),
        )
        with self._lock:
            state = self._runs.get(run_id)
            if state is None:
                return
            state.progress.append(entry)

    def list_recent(self, limit: int = 20) -> list[PipelineRunState]:
        with self._lock:
            self._cleanup_locked()
            ordered = sorted(
                self._runs.values(),
                key=lambda s: s.start_time,
                reverse=True,
            )
            return [s.copy(deep=True) for s in ordered[:limit]]

    def _is_expired(self, state: PipelineRunState) -> bool:
        if state.status in ("COMPLETED", "FAILED") and state.end_time:
            try:
                end = datetime.fromisoformat(state.end_time)
                return (time.time() - end.timestamp()) > self._ttl_seconds
            except ValueError:
                return False
        return False

    def _cleanup_locked(self) -> None:
        expired = [
            run_id
            for run_id, state in self._runs.items()
            if self._is_expired(state)
        ]
        for run_id in expired:
            self._runs.pop(run_id, None)
        if len(self._runs) > self._max_entries:
            ordered = sorted(
                self._runs.values(),
                key=lambda s: s.start_time,
            )
            for state in ordered[: len(self._runs) - self._max_entries]:
                self._runs.pop(state.run_id, None)


class RunTracker:
    """把编排器阶段变化写入 RunStore 的轻量辅助。"""

    def __init__(self, store: RunStore, run_id: str) -> None:
        self._store = store
        self.run_id = run_id

    def set(
        self,
        status: str,
        agent: str = "",
        message: str = "",
        step: str = "",
    ) -> None:
        self._store.update(
            self.run_id,
            status=status,
            current_agent=agent,
            message=message,
        )
        if step:
            self._store.add_progress(
                self.run_id,
                step=step,
                status="running",
                agent=agent,
                message=message,
            )

    def mark_step_done(self, step: str) -> None:
        with self._store._lock:
            state = self._store._runs.get(self.run_id)
            if state is None:
                return
            for entry in state.progress:
                if entry.step == step and entry.status == "running":
                    entry.status = "done"

    def finish(
        self,
        result: dict[str, Any] | None = None,
        error: AgentErrorInfo | None = None,
    ) -> None:
        self._store.update(
            self.run_id,
            status="FAILED" if error else "COMPLETED",
            end_time=_now(),
            error=error,
            result=result,
        )
        # 持久化 Trace：进程重启后仍可通过 GET /runs/{run_id} 查询
        state = self._store.get(self.run_id)
        if state is not None:
            trace_store.save(
                self.run_id,
                {
                    "kind": state.kind,
                    "status": state.status,
                    "message": state.message,
                    "start_time": state.start_time,
                    "end_time": state.end_time,
                    "error": error.dict() if error is not None else None,
                },
            )


# 进程级单例（与生成服务保持一致的模块级实例模式）
run_store = RunStore()
