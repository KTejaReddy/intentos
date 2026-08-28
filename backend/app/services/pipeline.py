"""Pipeline orchestration.

Runs the IntentOS flow: idea -> intent -> requirements -> plan ->
IntentLang -> compile -> artifacts. Emits an ordered list of step events so
the IDE can render a live pipeline stepper.

AI is used only for planning (IntentLang generation, requirements, research).
The compiler is always the pure IntentLang compiler.
"""

from __future__ import annotations

import base64
import json
from typing import Callable, Optional

from .. import config
from .ai import get_provider
from .ai import heuristic
from .ai.prompts import (
    INTENT_SYSTEM, PLANNER_SYSTEM, REQUIREMENTS_SYSTEM, extract_intentlang,
    extract_json,
)
from . import workspace

try:
    from intentlang.compiler import CompileOptions, Compiler
except ImportError:  # pragma: no cover - compiler wiring in config
    from intentlang.compiler import CompileOptions, Compiler


class PipelineError(Exception):
    pass


def _step(name: str, status: str, detail: str = "", data: Optional[dict] = None,
          emit: Optional[Callable] = None) -> dict:
    event = {"name": name, "status": status, "detail": detail, "data": data}
    if emit:
        emit(event)
    return event


def run_pipeline(idea: str, project_name: str = "", emit: Optional[Callable] = None) -> dict:
    """Full pipeline. `emit(step)` receives one event at a time (SSE)."""
    settings = config.get_settings()
    provider = get_provider(settings)

    steps: list[dict] = []

    def emit_and_collect(step: dict) -> None:
        steps.append(step)
        if emit:
            emit(step)

    # 1. Intent analysis
    _step("intent", "running", "parsing intent", None, emit_and_collect)
    try:
        intent = _analyze_intent(provider, idea)
        _step("intent", "done",
              f"domain={intent.get('domain')}, users={', '.join(intent.get('users', []))}",
              intent, emit_and_collect)
    except Exception as exc:
        _step("intent", "error", str(exc), None, emit_and_collect)
        raise PipelineError(f"intent analysis failed: {exc}")

    # 2. Requirements
    _step("requirements", "running", "finding missing requirements", None, emit_and_collect)
    requirements = _requirements(provider, idea)
    _step("requirements", "done", f"{len(requirements.get('questions', []))} question(s) surfaced",
          requirements, emit_and_collect)

    # 3. Plan
    _step("plan", "running", "composing product specification", None, emit_and_collect)
    spec = _plan(provider, idea, intent)
    _step("plan", "done", f"{len(spec.get('entities', []))} entities, "
                          f"{len(spec.get('pages', []))} pages", spec, emit_and_collect)

    # 4. IntentLang generation
    _step("intentlang", "running", "generating IntentLang program", None, emit_and_collect)
    source = _generate_intentlang(provider, idea, intent)
    _step("intentlang", "done", f"{len(source.splitlines())} lines of IntentLang",
          {"source": source}, emit_and_collect)

    # 5. Compile
    _step("compile", "running", "compiling with the IntentLang compiler", None, emit_and_collect)
    result = Compiler().compile_source(source, "app.intentlang")
    module = result.module.to_dict() if result.module else None
    if result.ok():
        _step("compile", "done",
              f"{len(result.artifacts.items)} artifacts, fingerprint {result.fingerprint[:12]}…",
              {"fingerprint": result.fingerprint,
               "artifacts": result.artifacts.manifest(),
               "module": module}, emit_and_collect)
    else:
        _step("compile", "error",
              f"{len(result.diagnostics.errors)} error(s)", None, emit_and_collect)
        raise PipelineError("compile failed: " + result.diagnostics.format_all())

    # 6. Project materialization
    _step("project", "running", "materializing project workspace", None, emit_and_collect)
    name = project_name or intent.get("app_name") or "Project"
    project = workspace.create_project(name, idea)
    workspace.write_file(project["id"], "source/app.intentlang", source)
    artifact_dir = workspace.generated_dir(project["id"])
    written = result.artifacts.write_to(artifact_dir)
    # Apply the schema so the DB viewer has live tables.
    schema = result.artifacts.get("db/schema.sql")
    if schema:
        try:
            workspace.apply_schema(project["id"], schema.content)
        except Exception as e:
            import logging
            logging.error(f"Schema application failed: {e}")
    _step("project", "done", f"{len(written)} files -> {project['id']}",
          {"project_id": project["id"]}, emit_and_collect)

    return {
        "steps": steps,
        "project_id": project["id"],
        "intent": intent,
        "requirements": requirements,
        "spec": spec,
        "intentlang": source,
        "fingerprint": result.fingerprint,
    }


# ----------------------------------------------------------------------------
def _analyze_intent(provider, idea: str) -> dict:
    if provider.name == "offline":
        return provider.analyze_intent(idea)
    try:
        raw = provider.complete(INTENT_SYSTEM, f"Idea: {idea}\nReturn the JSON.")
        intent = extract_json(raw)
        if intent.get("app_name"):
            intent["source"] = "llm"
            intent["idea"] = idea
            return intent
    except Exception as e:
        raise PipelineError(f"LLM intent generation failed: {e}")
    return provider.analyze_intent(idea)


def _requirements(provider, idea: str) -> dict:
    if provider.name == "offline":
        questions = provider.missing_requirements(idea)
        return {"questions": questions,
                "missing": [q["question"] for q in questions]}
    try:
        raw = provider.complete(REQUIREMENTS_SYSTEM,
                                f"Idea: {idea}\nReturn the JSON.")
        data = extract_json(raw)
        if data.get("questions"):
            return data
    except Exception as e:
        raise PipelineError(f"LLM requirements generation failed: {e}")
    questions = provider.missing_requirements(idea)
    return {"questions": questions, "missing": [q["question"] for q in questions]}


def _plan(provider, idea: str, intent: dict) -> dict:
    return {
        "name": intent.get("app_name", "Project"),
        "summary": intent.get("summary", ""),
        "domain": intent.get("domain", ""),
        "users": intent.get("users", []),
        "features": intent.get("features", []),
        "entities": intent.get("entities", []),
        "tech": {"frontend": "react", "backend": "fastapi", "database": "sqlite"},
    }


def _generate_intentlang(provider, idea: str, intent: dict) -> str:
    if provider.name == "offline":
        return provider.generate_intentlang(idea)
    try:
        raw = provider.complete(PLANNER_SYSTEM, f"Idea: {idea}\nWrite the IntentLang program.")
        source = extract_intentlang(raw)
        # Validate it compiles; fall back to heuristic if not.
        result = Compiler().compile_source(source, "planner.intentlang",
                                           collect_artifacts=False)
        if result.ok() and result.module and result.module.pages:
            return source
    except Exception as e:
        raise PipelineError(f"LLM intentlang generation failed: {e}")
    return provider.generate_intentlang(idea)
