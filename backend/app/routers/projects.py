"""Project workspace endpoints: CRUD, files, build/run, preview serving."""

from __future__ import annotations

import base64
import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response

from .. import config
from ..schemas import CompileRequest, FilePut, ProjectCreate
from ..services import workspace
from intentlang.compiler import CompileOptions, Compiler
from intentlang.incremental import IncrementalEngine

router = APIRouter(prefix="/api/projects", tags=["projects"])

_compiler = Compiler()


def _project(pid: str) -> dict:
    project = workspace.get_project(pid)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    return project


@router.get("")
def list_projects():
    return workspace.list_projects()


@router.post("")
def create_project(req: ProjectCreate):
    return workspace.create_project(req.name, req.idea)


@router.get("/{pid}")
def get_project(pid: str):
    return _project(pid)


@router.get("/{pid}/files")
def list_files(pid: str):
    _project(pid)
    return {"files": workspace.list_source_files(pid)}


@router.get("/{pid}/file")
def read_file(pid: str, path: str):
    _project(pid)
    content = workspace.read_file(pid, path)
    if content is None:
        raise HTTPException(status_code=404, detail="file not found")
    return {"path": path, "content": content}


@router.put("/{pid}/file")
def write_file(pid: str, req: FilePut):
    _project(pid)
    try:
        workspace.write_file(pid, req.path, req.content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"ok": True, "path": req.path}


@router.post("/{pid}/compile")
def compile_project(pid: str, req: CompileRequest):
    _project(pid)
    opts = req.options or {}
    state = config.get_plugin_state()
    plugins = [name for name, enabled in state.items() if enabled]
    opts.setdefault("plugins", plugins)
    options = CompileOptions.from_dict(opts)
    result = _compiler.compile_source(req.source, req.filename, options)
    if result.ok() and result.artifacts.items:
        artifact_dir = workspace.generated_dir(pid)
        result.artifacts.write_to(artifact_dir)
        schema = result.artifacts.get("db/schema.sql")
        if schema:
            try:
                workspace.apply_schema(pid, schema.content)
            except Exception as e:
                result.diagnostics.error("IL-B001", f"Database schema application failed: {e}", 0, 0, "backend/routers/projects.py")
    payload = result.to_dict()
    if result.ok() and result.artifacts.items:
        payload["zip_b64"] = base64.b64encode(
            result.artifacts.to_zip_bytes()).decode()
    return payload


@router.post("/{pid}/build")
def build_project(pid: str):
    """Deterministic build: compile every .intentlang file in the project."""
    _project(pid)
    sources = {}
    for f in workspace.list_source_files(pid):
        content = workspace.read_file(pid, f["path"])
        if content is not None:
            sources[f["path"].split("/")[-1]] = content
    if not sources:
        raise HTTPException(status_code=400, detail="no IntentLang sources")
    engine = IncrementalEngine(_compiler, workspace.generated_dir(pid) / ".cache")
    result = engine.compile(sources)
    if result.ok() and result.artifacts.items:
        result.artifacts.write_to(workspace.generated_dir(pid))
    return result.to_dict(include_artifacts=True)


@router.post("/{pid}/run")
def run_project(pid: str):
    """Run = build + return the preview URL."""
    _project(pid)
    sources = {}
    for f in workspace.list_source_files(pid):
        content = workspace.read_file(pid, f["path"])
        if content is not None:
            sources[f["path"].split("/")[-1]] = content
    if sources:
        engine = IncrementalEngine(_compiler, workspace.generated_dir(pid) / ".cache")
        result = engine.compile(sources)
        if result.ok() and result.artifacts.items:
            result.artifacts.write_to(workspace.generated_dir(pid))
    # The standalone generator writes its single-file app under preview/index.html.
    return {"ok": True,
            "preview_url": f"/api/projects/{pid}/preview/preview/index.html"}


@router.get("/{pid}/preview/{path:path}")
def preview_file(pid: str, path: str = "index.html"):
    """Serve generated artifacts (standalone preview / assets)."""
    _project(pid)
    gen = workspace.generated_dir(pid)
    candidate = (gen / path).resolve()
    if not str(candidate).startswith(str(gen.resolve())) or not candidate.is_file():
        raise HTTPException(status_code=404, detail="preview file not found")
    return FileResponse(candidate)
