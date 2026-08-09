"""小说项目持久化服务。

把「大纲 + 对应章节草稿」作为一个整体保存到本地 JSON 文件
（默认 backend/data/projects.json），支持列表、读取、保存（upsert）、删除。
"""

import json
import logging
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.config import BASE_DIR
from app.schemas.project import (
    NovelProject,
    ProjectSaveRequest,
    ProjectSummary,
)

logger = logging.getLogger(__name__)

# 项目存储文件（默认 backend/data/projects.json）
PROJECTS_FILE = Path(
    os.getenv("PROJECTS_FILE", str(BASE_DIR / "data" / "projects.json"))
)

# 简单线程锁，防止并发读写文件
_lock = threading.Lock()


def _now() -> str:
    """返回当前时间的 ISO 格式字符串。"""
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _ensure_file() -> None:
    """确保存储文件存在。"""
    PROJECTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not PROJECTS_FILE.exists():
        PROJECTS_FILE.write_text("[]", encoding="utf-8")


def _read_all() -> list[dict]:
    """读取全部项目（内部使用，需在锁内调用）。"""
    _ensure_file()
    try:
        data = json.loads(PROJECTS_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("读取项目文件失败: %s", exc)
        return []


def _write_all(projects: list[dict]) -> None:
    """写回全部项目（内部使用，需在锁内调用）。"""
    _ensure_file()
    PROJECTS_FILE.write_text(
        json.dumps(projects, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _to_summary(project: dict) -> ProjectSummary:
    """把项目字典转换为列表摘要。"""
    chapters = project.get("chapters") or []
    return ProjectSummary(
        id=project.get("id", ""),
        title=project.get("title") or "未命名小说",
        chapter_count=len([c for c in chapters if (c.get("content") or "").strip()]),
        created_at=project.get("created_at", ""),
        updated_at=project.get("updated_at", ""),
    )


def list_projects() -> list[ProjectSummary]:
    """返回项目摘要列表（按更新时间倒序）。"""
    with _lock:
        projects = _read_all()
    summaries = [_to_summary(p) for p in projects]
    summaries.sort(key=lambda s: s.updated_at, reverse=True)
    return summaries


def get_project(project_id: str) -> NovelProject | None:
    """按 ID 获取完整项目。"""
    with _lock:
        projects = _read_all()
    for p in projects:
        if p.get("id") == project_id:
            return NovelProject(**p)
    return None


def save_project(request: ProjectSaveRequest) -> NovelProject:
    """保存项目（upsert）。

    - request.id 为空：创建新项目（生成 UUID）；
    - request.id 已存在：覆盖更新。
    """
    now = _now()
    with _lock:
        projects = _read_all()
        if request.id:
            target = next((p for p in projects if p.get("id") == request.id), None)
        else:
            target = None

        if target is None:
            project_id = request.id or uuid.uuid4().hex[:12]
            project = {
                "id": project_id,
                "title": (request.title or request.outline.title or "未命名小说"),
                "outline": request.outline.dict(),
                "chapters": [c.dict() for c in request.chapters],
                "character_cards": [c.dict() for c in request.character_cards],
                "created_at": now,
                "updated_at": now,
            }
            projects.append(project)
        else:
            target["title"] = request.title or request.outline.title or target.get("title", "")
            target["outline"] = request.outline.dict()
            target["chapters"] = [c.dict() for c in request.chapters]
            target["character_cards"] = [c.dict() for c in request.character_cards]
            target["updated_at"] = now
            project = target

        _write_all(projects)
    logger.info("已保存项目 %s（%s）", project["id"], project["title"])
    return NovelProject(**project)


def delete_project(project_id: str) -> bool:
    """删除项目，返回是否删除成功。"""
    with _lock:
        projects = _read_all()
        remaining = [p for p in projects if p.get("id") != project_id]
        if len(remaining) == len(projects):
            return False
        _write_all(remaining)
    logger.info("已删除项目 %s", project_id)
    return True
