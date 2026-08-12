"""项目存储 repository。

提供两种行为等价的实现：
- JsonProjectRepository：单 JSON 文件 + 原子写 + .bak 恢复（默认，向后兼容）；
- SqliteProjectRepository：SQLite 单表（id + JSON 数据），零新增依赖。

service 层通过 PROJECT_STORAGE 配置选择实现；切换到 SQLite 前请先运行迁移脚本。
"""

import json
import logging
import os
import shutil
import sqlite3
import threading
from pathlib import Path
from typing import Protocol

from app.config import settings

logger = logging.getLogger(__name__)


class ProjectRepository(Protocol):
    """项目存储接口：全部以项目 dict 为读写单位。"""

    def list_projects(self) -> list[dict]:
        ...

    def get_project(self, project_id: str) -> dict | None:
        ...

    def save_project(self, project: dict) -> None:
        ...

    def delete_project(self, project_id: str) -> bool:
        ...


class JsonProjectRepository:
    """单 JSON 文件实现：原子写 + .bak 备份恢复。"""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.backup_path = Path(str(file_path) + ".bak")
        # 可重入锁：save/delete 持锁时会调用 list_projects
        self._lock = threading.RLock()

    def _ensure_file(self) -> None:
        """确保存储文件存在；主文件缺失但备份存在时先从备份恢复。"""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if self.file_path.exists():
            return
        if self.backup_path.exists():
            backup = self._load_json(self.backup_path)
            if backup is not None:
                logger.error("项目文件缺失，已从备份恢复: %s", self.file_path)
                self._atomic_write(json.dumps(backup, ensure_ascii=False, indent=2))
                return
        self._atomic_write("[]")

    def _atomic_write(self, text: str) -> None:
        """先写临时文件再原子替换，避免写入中途崩溃损坏主文件。"""
        tmp_path = Path(str(self.file_path) + ".tmp")
        try:
            tmp_path.write_text(text, encoding="utf-8")
            os.replace(tmp_path, self.file_path)
        finally:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass

    def _backup_current(self) -> None:
        """把当前主文件复制为备份（尽力而为，失败只告警）。"""
        if not self.file_path.exists():
            return
        try:
            shutil.copyfile(self.file_path, self.backup_path)
        except OSError as exc:
            logger.warning("备份项目文件失败: %s", exc)

    def _load_json(self, path: Path) -> list[dict] | None:
        """读取 JSON 数组文件；损坏或内容不是数组时返回 None。"""
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else None
        except (json.JSONDecodeError, OSError, UnicodeError) as exc:
            logger.error("读取项目文件失败 %s: %s", path, exc)
            return None

    def list_projects(self) -> list[dict]:
        """读取全部项目；主文件损坏时自动尝试从备份恢复并回写。"""
        with self._lock:
            self._ensure_file()
            data = self._load_json(self.file_path)
            if data is not None:
                return data
            backup = self._load_json(self.backup_path)
            if backup is not None:
                logger.error("项目文件损坏，已从备份恢复: %s", self.file_path)
                self._atomic_write(json.dumps(backup, ensure_ascii=False, indent=2))
                return backup
            logger.error("项目文件与备份均不可读: %s", self.file_path)
            return []

    def get_project(self, project_id: str) -> dict | None:
        for project in self.list_projects():
            if project.get("id") == project_id:
                return project
        return None

    def save_project(self, project: dict) -> None:
        """按 id upsert：已存在则整体替换，否则追加。"""
        with self._lock:
            projects = self.list_projects()
            replaced = False
            for i, existing in enumerate(projects):
                if existing.get("id") == project.get("id"):
                    projects[i] = project
                    replaced = True
                    break
            if not replaced:
                projects.append(project)
            self._ensure_file()
            self._backup_current()
            self._atomic_write(json.dumps(projects, ensure_ascii=False, indent=2))

    def delete_project(self, project_id: str) -> bool:
        with self._lock:
            projects = self.list_projects()
            remaining = [p for p in projects if p.get("id") != project_id]
            if len(remaining) == len(projects):
                return False
            self._ensure_file()
            self._backup_current()
            self._atomic_write(json.dumps(remaining, ensure_ascii=False, indent=2))
            return True


class SqliteProjectRepository:
    """SQLite 实现：单表存储项目 JSON，按 id 精确读写。"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = self._connect()
        try:
            with conn:
                conn.execute(
                    "CREATE TABLE IF NOT EXISTS projects ("
                    " id TEXT PRIMARY KEY,"
                    " data TEXT NOT NULL,"
                    " created_at TEXT NOT NULL,"
                    " updated_at TEXT NOT NULL)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_projects_updated_at"
                    " ON projects(updated_at)"
                )
        finally:
            conn.close()

    def list_projects(self) -> list[dict]:
        conn = self._connect()
        try:
            with conn:
                rows = conn.execute("SELECT data FROM projects").fetchall()
        finally:
            conn.close()
        return [json.loads(row["data"]) for row in rows]

    def get_project(self, project_id: str) -> dict | None:
        conn = self._connect()
        try:
            with conn:
                row = conn.execute(
                    "SELECT data FROM projects WHERE id = ?", (project_id,)
                ).fetchone()
        finally:
            conn.close()
        return json.loads(row["data"]) if row is not None else None

    def save_project(self, project: dict) -> None:
        payload = json.dumps(project, ensure_ascii=False)
        conn = self._connect()
        try:
            with conn:
                conn.execute(
                    "INSERT INTO projects (id, data, created_at, updated_at)"
                    " VALUES (?, ?, ?, ?)"
                    " ON CONFLICT(id) DO UPDATE SET"
                    " data = excluded.data, updated_at = excluded.updated_at",
                    (
                        project["id"],
                        payload,
                        project["created_at"],
                        project["updated_at"],
                    ),
                )
        finally:
            conn.close()

    def delete_project(self, project_id: str) -> bool:
        conn = self._connect()
        try:
            with conn:
                cur = conn.execute(
                    "DELETE FROM projects WHERE id = ?", (project_id,)
                )
        finally:
            conn.close()
        return cur.rowcount > 0


def create_repository() -> ProjectRepository:
    """按配置创建存储实现：json（默认）或 sqlite。"""
    if settings.project_storage == "sqlite":
        return SqliteProjectRepository(settings.project_db)
    return JsonProjectRepository(settings.projects_file)
