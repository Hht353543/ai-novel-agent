"""小说项目存储 API：保存 / 列出 / 读取 / 删除（大纲 + 章节整体）。"""

from fastapi import APIRouter, HTTPException

from app.schemas.project import (
    NovelProject,
    ProjectListResponse,
    ProjectSaveRequest,
    ProjectSaveResponse,
)
from app.services.project_service import (
    delete_project,
    get_project,
    list_projects,
    save_project,
)

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=ProjectListResponse)
async def list_all_projects() -> ProjectListResponse:
    """列出所有已保存的小说项目。"""
    return ProjectListResponse(projects=list_projects())


@router.post("", response_model=ProjectSaveResponse)
async def save_novel_project(request: ProjectSaveRequest) -> ProjectSaveResponse:
    """保存（新建或更新）一个小说项目。"""
    project = save_project(request)
    return ProjectSaveResponse(
        success=True,
        message="保存成功",
        project=project,
    )


@router.get("/{project_id}", response_model=NovelProject)
async def get_novel_project(project_id: str) -> NovelProject:
    """按 ID 读取完整项目（大纲 + 章节草稿）。"""
    project = get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"项目不存在: {project_id}")
    return project


@router.delete("/{project_id}")
async def delete_novel_project(project_id: str) -> dict:
    """删除指定项目。"""
    if not delete_project(project_id):
        raise HTTPException(status_code=404, detail=f"项目不存在: {project_id}")
    return {"success": True, "message": "已删除"}
