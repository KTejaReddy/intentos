"""Compilation endpoints backed by the pure IntentLang compiler."""

from __future__ import annotations

import base64
import re

from fastapi import APIRouter

from .. import config
from ..schemas import AutocompleteRequest, CompileRequest, CompileResponse
from ..services.workspace import generated_dir, write_file
from intentlang.compiler import CompileOptions, Compiler
from intentlang.keywords import KEYWORDS, CREATE_KINDS, WIDGET_KINDS
from intentlang.lexer import Lexer
from intentlang.parser import Parser

router = APIRouter(prefix="/api/compile", tags=["compile"])

_compiler = Compiler()

COMPLETION_KEYWORDS = sorted(
    {k.title() for k in KEYWORDS}
    | {k.title() for k in CREATE_KINDS}
    | {k.title() for k in WIDGET_KINDS}
    | {"Create", "With", "Type", "Route", "Method", "Auth", "Label",
       "Required", "Unique", "Api", "Field", "Database", "Model", "Page",
       "Request", "Response", "Query", "From", "Select", "Where", "Body",
       "Status", "List", "Of", "When", "On", "Call", "Navigate", "To",
       "Show", "Toast", "Deploy", "Docker", "Use", "Theme", "Title"}
)


def _options(req: CompileRequest) -> CompileOptions:
    opts = req.options or {}
    state = config.get_plugin_state()
    plugins = [name for name, enabled in state.items() if enabled]
    opts.setdefault("plugins", plugins)
    return CompileOptions.from_dict(opts)


@router.post("", response_model=CompileResponse)
def compile_source(req: CompileRequest) -> CompileResponse:
    result = _compiler.compile_source(req.source, req.filename, _options(req))
    payload = result.to_dict()
    if result.ok() and result.artifacts.items:
        payload["zip_b64"] = base64.b64encode(
            result.artifacts.to_zip_bytes()).decode()
    return CompileResponse(**payload)


@router.post("/check", response_model=CompileResponse)
def check_source(req: CompileRequest) -> CompileResponse:
    result = _compiler.compile_source(req.source, req.filename, _options(req),
                                      collect_artifacts=False)
    return CompileResponse(**result.to_dict())


@router.post("/autocomplete")
def autocomplete(req: AutocompleteRequest) -> list[dict]:
    """Context-aware completions: keywords plus symbols from the source."""
    source = req.source
    symbols = _symbols(source)
    line_prefix = _prefix_at(source, req.line, req.col).lower()

    completions: list[dict] = []
    for word in COMPLETION_KEYWORDS:
        if not line_prefix or word.lower().startswith(line_prefix):
            completions.append({"label": word, "kind": "keyword",
                                "detail": "IntentLang keyword"})
    for name, kind in symbols:
        if not line_prefix or name.lower().startswith(line_prefix):
            completions.append({"label": name, "kind": kind,
                                "detail": f"defined {kind}"})
    return _dedupe(completions)[:80]


def _dedupe(items: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for item in items:
        if item["label"] in seen:
            continue
        seen.add(item["label"])
        out.append(item)
    return out


def _prefix_at(source: str, line: int, col: int) -> str:
    try:
        lines = source.splitlines()
        if line < len(lines):
            return lines[line][:col]
        return ""
    except IndexError:
        return ""


def _symbols(source: str) -> list[tuple[str, str]]:
    """Extract declared names for autocomplete via a light lexical pass."""
    try:
        toks = Lexer(source, "<live>").tokenize()
        ast = Parser(toks, "<live>").parse_module()
    except Exception:
        return []
    symbols = []
    for stmt in ast.statements:
        kind = getattr(stmt, "kind", "")
        name = getattr(stmt, "name", "")
        if kind in ("page", "model", "api", "role", "database", "application"):
            symbols.append((name, kind))
            # Extract nested fields if model
            if kind == "model":
                for child in getattr(stmt, "children", []):
                    if getattr(child, "kind", "") == "field":
                        symbols.append((f"{name}.{getattr(child, 'name', '')}", "field"))
    return symbols
