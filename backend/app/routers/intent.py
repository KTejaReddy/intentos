"""Intent analysis, requirements, and planning endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from .. import config
from ..schemas import (
    AnswersRequest, IdeaRequest, IntentResponse, PlanRequest, PlanResponse,
    RequirementsResponse,
)
from ..services import pipeline
from ..services.ai import get_provider

router = APIRouter(prefix="/api", tags=["intent"])


@router.post("/intent/analyze", response_model=IntentResponse)
def analyze_intent(req: IdeaRequest) -> IntentResponse:
    provider = get_provider(config.get_settings())
    intent = pipeline._analyze_intent(provider, req.idea)
    return IntentResponse(**intent)


@router.post("/requirements/analyze", response_model=RequirementsResponse)
def analyze_requirements(req: IdeaRequest) -> RequirementsResponse:
    provider = get_provider(config.get_settings())
    data = pipeline._requirements(provider, req.idea)
    return RequirementsResponse(**data)


@router.post("/requirements/answer", response_model=PlanResponse)
def answer_requirements(req: AnswersRequest) -> PlanResponse:
    return PlanResponse(spec={"answers": req.answers},
                        intentlang="// answers recorded", source="heuristic")


@router.post("/plan/generate", response_model=PlanResponse)
def generate_plan(req: PlanRequest) -> PlanResponse:
    provider = get_provider(config.get_settings())
    intent = req.intent.dict() if req.intent else pipeline._analyze_intent(provider, req.idea)
    spec = pipeline._plan(provider, req.idea, intent)
    source = pipeline._generate_intentlang(provider, req.idea, intent)
    return PlanResponse(spec=spec, intentlang=source,
                        source="heuristic" if provider.name == "offline" else "llm")
