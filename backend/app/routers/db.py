"""Database viewer: tables and rows from the project's runtime sqlite db."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..schemas import CompileRequest
from ..services import workspace
from intentlang.compiler import CompileOptions, Compiler

router = APIRouter(prefix="/api/projects/{pid}/db", tags=["db"])

_compiler = Compiler()


def _ensure(pid: str) -> None:
    if workspace.get_project(pid) is None:
        raise HTTPException(status_code=404, detail="project not found")


@router.post("/apply")
def apply(pid: str, req: CompileRequest):
    _ensure(pid)
    options = CompileOptions.from_dict(req.options or {})
    result = _compiler.compile_source(req.source, req.filename, options,
                                      collect_artifacts=False)
    if not result.ok() or result.module is None:
        raise HTTPException(status_code=422, detail="cannot apply invalid program")
    schema = result.artifacts.get("db/schema.sql")
    if schema is None:
        # compile with artifacts to obtain schema
        result = _compiler.compile_source(req.source, req.filename, options)
        schema = result.artifacts.get("db/schema.sql")
    if schema is None:
        raise HTTPException(status_code=422, detail="no schema generated")
    return {"tables": workspace.apply_schema(pid, schema.content)}


@router.get("/tables")
def tables(pid: str):
    _ensure(pid)
    return {"tables": workspace.db_tables(pid)}


@router.get("/table/{table}")
def table(pid: str, table: str):
    _ensure(pid)
    return workspace.db_rows(pid, table)
