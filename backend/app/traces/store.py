"""TraceStore：把 Pipeline/Sequence 运行摘要写入 JSON 文件。"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import settings


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


class TraceStore:
    """按 run_id 持久化运行摘要（原子写 + 进程级单例）。"""

    def __init__(self, directory: Path | None = None) -> None:
        self.directory = Path(
            directory or settings.traces_dir
        )
        self.directory.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _path(self, run_id: str) -> Path:
        return self.directory / f"{run_id}.json"

    def save(self, run_id: str, data: dict[str, Any]) -> None:
        payload = {
            "run_id": run_id,
            "saved_at": _now(),
            **data,
        }
        with self._lock:
            self._path(run_id).write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    def load(self, run_id: str) -> dict[str, Any] | None:
        path = self._path(run_id)
        with self._lock:
            if not path.exists():
                return None
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                return data if isinstance(data, dict) else None
            except (json.JSONDecodeError, OSError):
                return None

    def list_recent(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._lock:
            rows = []
            for path in self.directory.glob("*.json"):
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    if isinstance(data, dict):
                        rows.append(data)
                except (json.JSONDecodeError, OSError):
                    continue
            rows.sort(key=lambda r: r.get("saved_at", ""), reverse=True)
            return rows[:limit]


trace_store = TraceStore()


__all__ = ["TraceStore", "trace_store"]
