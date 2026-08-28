"""IntentOS backend — FastAPI application."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import config
from .routers import chat, compile as compile_router, db, git, intent, pipeline, plugins, projects, settings

app = FastAPI(
    title="IntentOS",
    description="The AI Development Operating System — intent -> IntentLang -> compiled application.",
    version=config.VERSION,
)

origins = config.get_settings().get("cors_origins") or ["http://localhost:5173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins + ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(intent.router)
app.include_router(compile_router.router)
app.include_router(chat.router)
app.include_router(projects.router)
app.include_router(db.router)
app.include_router(git.router)
app.include_router(plugins.router)
app.include_router(settings.router)
app.include_router(pipeline.router)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "intentos",
        "version": config.VERSION,
        "compiler": "intentlang 1.0.0",
        "provider": config.get_settings().get("provider", "offline"),
        "endpoints": [
            "intent", "requirements", "plan", "pipeline", "compile",
            "chat", "projects", "db", "git", "plugins", "settings", "preview",
        ],
    }


@app.get("/")
def root():
    return {"service": "IntentOS", "docs": "/docs", "health": "/api/health"}
