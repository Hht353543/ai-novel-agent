"""项目存储 repository 测试。"""

import json
from types import SimpleNamespace

from app.config import settings
from app.services import project_service as ps
from app.services.project_repository import (
    JsonProjectRepository,
    SqliteProjectRepository,
)
from app.schemas.project import ProjectSaveRequest
import migrate_projects as mp


def _project(pid, title="Book", created="2026-01-01T00:00:00+08:00", updated="2026-01-01T00:00:00+08:00"):
    return {
        "id": pid,
        "title": title,
        "outline": {"title": title, "summary": "s", "world": "w", "characters": [], "volume_plan": []},
        "chapters": [{"volume_index": 0, "chapter_index": 0, "chapter_title": "c", "content": "body"}],
        "character_cards": [],
        "memory": "",
        "created_at": created,
        "updated_at": updated,
    }


def test_json_repository_crud_and_backup_recovery(tmp_path):
    repo = JsonProjectRepository(tmp_path / "projects.json")
    p1 = _project("id1")
    repo.save_project(p1)
    assert repo.get_project("id1")["title"] == "Book"
    p2 = _project("id2", title="Book2")
    repo.save_project(p2)
    assert len(repo.list_projects()) == 2
    assert repo.delete_project("nope") is False
    assert repo.delete_project("id1") is True
    assert len(repo.list_projects()) == 1
    # 备份恢复：损坏主文件后恢复到上一完整版本
    repo.save_project(p1)
    repo.save_project(p2)
    repo.file_path.write_text("{bad", encoding="utf-8")
    recovered = repo.list_projects()
    assert {p["id"] for p in recovered} == {"id1", "id2"}


def test_sqlite_repository_crud_and_upsert(tmp_path):
    repo = SqliteProjectRepository(tmp_path / "projects.db")
    p1 = _project("id1")
    repo.save_project(p1)
    assert repo.get_project("id1")["title"] == "Book"
    p1_updated = _project(
        "id1", title="Book2", updated="2026-02-01T00:00:00+08:00"
    )
    repo.save_project(p1_updated)
    rows = repo.list_projects()
    assert len(rows) == 1
    assert rows[0]["title"] == "Book2"
    assert rows[0]["created_at"] == p1["created_at"]
    assert repo.delete_project("nope") is False
    assert repo.delete_project("id1") is True
    assert repo.list_projects() == []


def test_project_service_save_get_delete(tmp_path, monkeypatch):
    for repo in (
        JsonProjectRepository(tmp_path / "svc.json"),
        SqliteProjectRepository(tmp_path / "svc.db"),
    ):
        monkeypatch.setattr(ps, "_repository", repo)
        saved = ps.save_project(
            ProjectSaveRequest(title="T", outline={"title": "T"}, chapters=[], character_cards=[], memory="M")
        )
        assert saved.memory == "M"
        assert ps.get_project(saved.id).title == "T"
        assert len(ps.list_projects()) == 1
        assert ps.delete_project(saved.id) is True
        assert ps.get_project(saved.id) is None


def test_migration_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "projects_file", tmp_path / "migrate.json")
    monkeypatch.setattr(settings, "project_db", tmp_path / "migrate.db")
    repo = JsonProjectRepository(settings.projects_file)
    repo.save_project(_project("m1"))
    repo.save_project(_project("m2", title="Book2"))
    assert mp.to_sqlite(SimpleNamespace(force=False)) == 0
    assert mp.to_sqlite(SimpleNamespace(force=False)) == 1
    assert mp.to_sqlite(SimpleNamespace(force=True)) == 0
    assert mp.to_json(None) == 0
    restored = json.loads((tmp_path / "migrate.json.restored").read_text(encoding="utf-8"))
    assert {p["id"] for p in restored} == {"m1", "m2"}
