"""Pipeline endpoint: idea -> steps, streamed over SSE."""

from __future__ import annotations

import json
from typing import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ..schemas import PipelineRun
from ..services.pipeline import PipelineError, run_pipeline

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("/run")
async def run(req: PipelineRun) -> StreamingResponse:
    async def stream() -> AsyncIterator[str]:
        try:
            result = run_pipeline(req.idea, req.project_name,
                                  emit=lambda step: None)
        except PipelineError as exc:
            yield _sse("error", {"message": str(exc)})
            return
        # The heavy work already ran synchronously; replay steps as events.
        for step in result["steps"]:
            yield _sse("step", step)
        yield _sse("done", {"result": {
            "project_id": result["project_id"],
            "intent": result["intent"],
            "requirements": result["requirements"],
            "spec": result["spec"],
            "intentlang": result["intentlang"],
            "fingerprint": result["fingerprint"],
        }})

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no"})
