"""Pydantic schemas for the IntentOS API."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


# -- intent pipeline ----------------------------------------------------------
class IdeaRequest(BaseModel):
    idea: str
    location: str = ""


class IntentResponse(BaseModel):
    idea: str
    app_name: str
    summary: str
    domain: str
    users: list[str] = []
    features: list[str] = []
    entities: list[str] = []
    source: str = "heuristic"  # heuristic | llm


class RequirementQuestion(BaseModel):
    id: str
    question: str
    options: list[str] = []
    reason: str = ""


class RequirementsResponse(BaseModel):
    questions: list[RequirementQuestion] = []
    missing: list[str] = []


class AnswersRequest(BaseModel):
    answers: dict[str, str] = {}


class PlanRequest(BaseModel):
    idea: str
    intent: Optional[IntentResponse] = None
    answers: dict[str, str] = {}


class PlanResponse(BaseModel):
    spec: dict[str, Any] = {}
    intentlang: str = ""
    source: str = "heuristic"


# -- compilation ---------------------------------------------------------------
class CompileRequest(BaseModel):
    source: str
    filename: str = "app.intentlang"
    options: dict[str, Any] = {}


class CompileResponse(BaseModel):
    ok: bool
    diagnostics: list[dict] = []
    module: Optional[dict] = None
    steps: list[dict] = []
    fingerprint: str = ""
    artifacts: Optional[dict] = None
    zip_b64: Optional[str] = None


class AutocompleteRequest(BaseModel):
    source: str
    line: int = 0
    col: int = 0


# -- chat ----------------------------------------------------------------------
class ChatMessage(BaseModel):
    role: str = "user"
    content: str = ""


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = []
    project_id: Optional[str] = None


# -- projects ------------------------------------------------------------------
class ProjectCreate(BaseModel):
    name: str
    idea: str = ""


class FilePut(BaseModel):
    path: str
    content: str


# -- misc ----------------------------------------------------------------------
class SettingsPut(BaseModel):
    provider: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None
    openrouter_model: Optional[str] = None
    cors_origins: Optional[list[str]] = None


class PipelineStep(BaseModel):
    name: str
    status: str = "running"   # running | done | error | skipped
    detail: str = ""
    data: Optional[dict] = None


class PipelineRun(BaseModel):
    idea: str
    project_name: str = ""
