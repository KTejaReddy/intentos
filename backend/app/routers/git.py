"""Read-only git endpoints for the IDE Git panel."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pathlib import Path

from .. import config
from ..services import git as git_svc
from ..services.workspace import get_project

router = APIRouter(prefix="/api/projects/{pid}/git", tags=["git"])


def _cwd(pid: str) -> Path:
    project = get_project(pid)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    return Path(project["root"])


@router.get("/status")
def status(pid: str):
    return {"items": git_svc.status(_cwd(pid))}


@router.get("/diff")
def diff(pid: str):
    return {"diff": git_svc.diff(_cwd(pid))}


@router.get("/log")
def log(pid: str, limit: int = 20):
    return {"commits": git_svc.log(_cwd(pid), limit)}
