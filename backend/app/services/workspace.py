"""Workspace service: projects, source files, generated artifacts,
runtime database for the DB viewer."""

from __future__ import annotations

import json
import re
import sqlite3
import uuid
from pathlib import Path
from typing import Optional

from .. import config

PROJECTS_DIR = config.DATA_DIR / "projects"


def _slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or "project"


def _pascal(name: str) -> str:
    return "".join(w[:1].upper() + w[1:] for w in _slug(name).split("-"))


def list_projects() -> list[dict]:
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    out = []
    for d in sorted(PROJECTS_DIR.iterdir()):
        if not d.is_dir():
            continue
        meta = _load_meta(d)
        out.append({
            "id": d.name,
            "name": meta.get("name", d.name),
            "idea": meta.get("idea", ""),
            "created": meta.get("created", ""),
            "files": _list_files(d),
        })
    return out


def create_project(name: str, idea: str = "") -> dict:
    pid = _slug(name) + "-" + uuid.uuid4().hex[:6]
    d = PROJECTS_DIR / pid
    (d / "source").mkdir(parents=True, exist_ok=True)
    (d / "generated").mkdir(parents=True, exist_ok=True)
    (d / "runtime").mkdir(parents=True, exist_ok=True)
    meta = {"name": name, "idea": idea, "created": "now"}
    (d / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return get_project(pid)


def get_project(pid: str) -> Optional[dict]:
    d = PROJECTS_DIR / pid
    if not d.exists():
        return None
    meta = _load_meta(d)
    return {
        "id": pid,
        "name": meta.get("name", pid),
        "idea": meta.get("idea", ""),
        "files": _list_files(d),
        "root": str(d),
    }


def _load_meta(d: Path) -> dict:
    try:
        return json.loads((d / "meta.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _list_files(d: Path) -> list[str]:
    files = []
    src_dir = d / "source"
    if src_dir.exists():
        for p in sorted(src_dir.rglob("*.intentlang")):
            files.append(str(p.relative_to(d)).replace("\\", "/"))
    return files


def list_source_files(pid: str) -> list[dict]:
    d = PROJECTS_DIR / pid
    out = []
    src_dir = d / "source"
    if src_dir.exists():
        for p in sorted(src_dir.rglob("*")):
            if p.is_file():
                out.append({
                    "path": str(p.relative_to(d)).replace("\\", "/"),
                    "size": p.stat().st_size,
                })
    return out


def read_file(pid: str, path: str) -> Optional[str]:
    d = PROJECTS_DIR / pid
    p = (d / path).resolve()
    if not p.is_relative_to(d.resolve()) or not p.exists():
        return None
    try:
        return p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def write_file(pid: str, path: str, content: str) -> None:
    d = PROJECTS_DIR / pid
    p = (d / path).resolve()
    if not p.is_relative_to(d.resolve()):
        raise ValueError("path escapes project")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def generated_dir(pid: str) -> Path:
    d = PROJECTS_DIR / pid
    (d / "generated").mkdir(parents=True, exist_ok=True)
    return d / "generated"


def runtime_db(pid: str, name: str = "app") -> Path:
    d = PROJECTS_DIR / pid
    (d / "runtime").mkdir(parents=True, exist_ok=True)
    return d / "runtime" / f"{_slug(name)}.db"


# -- DB viewer ---------------------------------------------------------------
def apply_schema(pid: str, schema_sql: str, name: str = "app") -> dict:
    db_path = runtime_db(pid, name)
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(schema_sql)
        conn.commit()
    finally:
        conn.close()
    return db_tables(pid, name)


def db_tables(pid: str, name: str = "app") -> list[dict]:
    db_path = runtime_db(pid, name)
    if not db_path.exists():
        return []
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        tables = []
        for (tname,) in rows:
            cols = [r[1] for r in conn.execute(f'PRAGMA table_info("{tname}")').fetchall()]
            count = conn.execute(f'SELECT COUNT(*) FROM "{tname}"').fetchone()[0]
            tables.append({"name": tname, "columns": cols, "rows": count})
        return tables
    finally:
        conn.close()


def db_rows(pid: str, table: str, name: str = "app") -> dict:
    db_path = runtime_db(pid, name)
    if not db_path.exists():
        return {"columns": [], "rows": []}
    conn = sqlite3.connect(db_path)
    try:
        cols = [r[1] for r in conn.execute(f'PRAGMA table_info("{table}")').fetchall()]
        rows = conn.execute(f'SELECT * FROM "{table}" LIMIT 200').fetchall()
        return {"columns": cols, "rows": rows}
    finally:
        conn.close()
