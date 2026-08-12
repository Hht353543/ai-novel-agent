"""项目存储迁移脚本（projects.json <-> projects.db）。

用法（在 backend/ 目录下执行）：
    python migrate_projects.py to-sqlite [--force]   # JSON -> SQLite
    python migrate_projects.py to-json                # SQLite -> projects.json.restored

迁移前请先确认已有 projects.json.bak 备份；迁移后做数量与字段抽样校验。
"""

import argparse
import json
import sys
from pathlib import Path

from app.config import settings
from app.services.project_repository import (
    JsonProjectRepository,
    SqliteProjectRepository,
)


def _verify(projects: list[dict], repo, label: str) -> None:
    rows = repo.list_projects()
    if len(rows) != len(projects):
        raise RuntimeError(f"{label} 数量不一致: 源 {len(projects)} / 目标 {len(rows)}")
    for project in rows:
        if "id" not in project or "title" not in project or "outline" not in project:
            raise RuntimeError(f"{label} 字段缺失: {project.get('id', '<no-id>')}")
    print(f"{label} 校验通过：{len(rows)} 个项目，字段抽样正常。")


def to_sqlite(args) -> int:
    json_repo = JsonProjectRepository(settings.projects_file)
    sqlite_repo = SqliteProjectRepository(settings.project_db)
    projects = json_repo.list_projects()

    if not args.force and sqlite_repo.list_projects():
        print("目标数据库已有数据；如需覆盖请加 --force。")
        return 1

    for project in projects:
        sqlite_repo.save_project(project)
    _verify(projects, sqlite_repo, "SQLite")
    print(f"迁移完成：projects.json -> {settings.project_db}")
    return 0


def to_json(_args) -> int:
    sqlite_repo = SqliteProjectRepository(settings.project_db)
    rows = sqlite_repo.list_projects()
    target = Path(str(settings.projects_file) + ".restored")
    target.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _verify(rows, JsonProjectRepository(target), "JSON 恢复文件")
    print(f"回滚完成：SQLite -> {target}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="项目存储迁移")
    sub = parser.add_subparsers(dest="command", required=True)
    to_sqlite_parser = sub.add_parser("to-sqlite", help="JSON -> SQLite")
    to_sqlite_parser.add_argument("--force", action="store_true")
    sub.add_parser("to-json", help="SQLite -> projects.json.restored")
    args = parser.parse_args()
    if args.command == "to-sqlite":
        return to_sqlite(args)
    return to_json(args)


if __name__ == "__main__":
    sys.exit(main())
