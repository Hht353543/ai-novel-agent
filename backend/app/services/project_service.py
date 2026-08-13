"""小说项目持久化服务。

存储层委托给 project_repository（JSON 文件或 SQLite），
本模块负责业务编排，对外函数签名保持不变。
"""

import logging
import uuid
from datetime import datetime, timezone

from app.schemas.project import (
    NovelProject,
    ProjectSaveRequest,
    ProjectSummary,
)
from app.services.project_repository import (
    ProjectRepository,
    create_repository,
)

logger = logging.getLogger(__name__)

# 新项目 ID 的长度（uuid4 的十六进制前缀）
PROJECT_ID_LENGTH = 12

# 存储实现：json（默认）或 sqlite，由 PROJECT_STORAGE 配置决定
_repository: ProjectRepository = create_repository()


def _now() -> str:
    """返回当前时间的 ISO 格式字符串。"""
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


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
    summaries = [_to_summary(p) for p in _repository.list_projects()]
    summaries.sort(key=lambda s: s.updated_at, reverse=True)
    return summaries


def get_project(project_id: str) -> NovelProject | None:
    """按 ID 获取完整项目。"""
    project = _repository.get_project(project_id)
    return NovelProject(**project) if project else None


def save_project(request: ProjectSaveRequest) -> NovelProject:
    """保存项目（upsert）。

    - request.id 为空：创建新项目（生成 UUID）；
    - request.id 已存在：覆盖更新，保留原 created_at。
    """
    now = _now()
    existing = _repository.get_project(request.id) if request.id else None

    if existing is None:
        project_id = request.id or uuid.uuid4().hex[:PROJECT_ID_LENGTH]
        project = {
            "id": project_id,
            "title": (request.title or request.outline.title or "未命名小说"),
            "outline": request.outline.dict(),
            "chapters": [c.dict() for c in request.chapters],
            "character_cards": [c.dict() for c in request.character_cards],
            "memory": request.memory,
            "plan": request.plan.dict() if request.plan else None,
            "character_profiles": [
                p.dict() for p in request.character_profiles
            ],
            "character_states": [
                s.dict() for s in request.character_states
            ],
            "character_relations": [
                r.dict() for r in request.character_relations
            ],
            "latest_review": (
                request.latest_review.dict() if request.latest_review else None
            ),
            "created_at": now,
            "updated_at": now,
        }
    else:
        project = dict(existing)
        project["title"] = request.title or request.outline.title or existing.get("title", "")
        project["outline"] = request.outline.dict()
        project["chapters"] = [c.dict() for c in request.chapters]
        project["character_cards"] = [c.dict() for c in request.character_cards]
        project["memory"] = request.memory
        project["plan"] = request.plan.dict() if request.plan else None
        project["character_profiles"] = [
            p.dict() for p in request.character_profiles
        ]
        project["character_states"] = [
            s.dict() for s in request.character_states
        ]
        project["character_relations"] = [
            r.dict() for r in request.character_relations
        ]
        project["latest_review"] = (
            request.latest_review.dict() if request.latest_review else None
        )
        project["updated_at"] = now

    _repository.save_project(project)
    logger.info("已保存项目 %s（%s）", project["id"], project["title"])
    return NovelProject(**project)


def delete_project(project_id: str) -> bool:
    """删除项目，返回是否删除成功。"""
    deleted = _repository.delete_project(project_id)
    if deleted:
        logger.info("已删除项目 %s", project_id)
    return deleted
