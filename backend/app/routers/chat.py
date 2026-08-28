"""AI chat with SSE streaming.

The chat assistant explains the project, answers questions, and may suggest
IntentLang snippets — it never writes production code. In offline mode it
replies with the deterministic planner's guidance.
"""

from __future__ import annotations

import json
from typing import AsyncIterator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from .. import config
from ..schemas import ChatRequest
from ..services.ai import get_provider
from ..services.workspace import list_source_files, read_file

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _system_prompt(project_id: str | None) -> str:
    prompt = (
        "You are the IntentOS coding assistant inside a desktop IDE. "
        "You help users design software and write IntentLang — the "
        "deterministic intermediate language that the IntentOS compiler "
        "turns into the application. "
        "You NEVER produce production source code (React/Python/Java etc). "
        "Instead you explain the plan, ask clarifying questions, and suggest "
        "IntentLang snippets inside ```intentlang fences.\n\n"
        "IntentLang quick reference:\n"
        "- Create Application <Name> / Create Page <Name> / Create Model <Name> / Create Api <Name>\n"
        "- Widgets: Add Input, Add Button, Add Table, Add Form, Add NavBar, Add Text\n"
        "- Events: When Clicked -> Call Api X / Navigate To Y / Show Toast \"...\"\n"
        "- Api blocks: With (Method/Route/Auth), Request, Query, Response\n"
    )
    if project_id:
        files = list_source_files(project_id)
        if files:
            prompt += "\nCurrent project files:\n"
            for f in files:
                content = read_file(project_id, f["path"]) or ""
                prompt += f"\n--- {f['path']} ---\n{content[:2000]}\n"
    return prompt


@router.post("")
async def chat(req: ChatRequest) -> StreamingResponse:
    provider = get_provider(config.get_settings())
    messages = [{"role": "system", "content": _system_prompt(req.project_id)}]
    for m in req.messages:
        messages.append({"role": m.role, "content": m.content})

    async def event_stream() -> AsyncIterator[str]:
        yield _sse("meta", {"provider": provider.name})
        if provider.name == "offline":
            reply = provider.chat(messages)
            for chunk in _chunks(reply):
                yield _sse("delta", {"text": chunk})
            yield _sse("done", {"provider": "offline"})
            return
        try:
            reply = provider.chat(messages)
            for chunk in _chunks(reply):
                yield _sse("delta", {"text": chunk})
            yield _sse("done", {"provider": provider.name})
        except Exception as exc:  # pragma: no cover - network failures
            yield _sse("error", {"message": str(exc)})

    return StreamingResponse(event_stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no"})


def _chunks(text: str, size: int = 48) -> list[str]:
    return [text[i:i + size] for i in range(0, len(text), size)] or [""]


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"
