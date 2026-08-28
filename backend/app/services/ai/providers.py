"""AI provider abstraction.

IntentOS policy: AI may ONLY produce IntentLang, never production code.
Every provider here is used exclusively to generate IntentLang source,
structured intent, requirements, or research notes.

    OpenRouterProvider  -> https://openrouter.ai/api/v1/chat/completions
    OllamaProvider      -> http://localhost:11434/api/chat
    HeuristicProvider   -> deterministic offline planner (no network)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

import httpx


class Provider(ABC):
    name = "base"

    @abstractmethod
    def chat(self, messages: list[dict], temperature: float = 0.2) -> str:
        """Return the model's reply text for a chat message list."""

    def complete(self, system: str, user: str, temperature: float = 0.2) -> str:
        return self.chat([{"role": "system", "content": system},
                          {"role": "user", "content": user}], temperature)


class OpenRouterProvider(Provider):
    name = "openrouter"

    def __init__(self, api_key: str, model: str = "qwen/qwen-2.5-72b-instruct") -> None:
        self.api_key = api_key
        self.model = model

    def chat(self, messages: list[dict], temperature: float = 0.2) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        resp = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json=payload,
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"] or ""


class OllamaProvider(Provider):
    name = "ollama"

    def __init__(self, base_url: str = "http://localhost:11434",
                 model: str = "qwen2.5:7b") -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model

    def chat(self, messages: list[dict], temperature: float = 0.2) -> str:
        payload = {"model": self.model, "messages": messages,
                   "stream": False, "options": {"temperature": temperature}}
        resp = httpx.post(f"{self.base_url}/api/chat", json=payload, timeout=300)
        resp.raise_for_status()
        data = resp.json()
        return data.get("message", {}).get("content", "")


class HeuristicProvider(Provider):
    """Offline provider: deterministic planners, no LLM involved."""

    name = "offline"

    def __init__(self) -> None:
        from . import heuristic
        self._h = heuristic

    def chat(self, messages: list[dict], temperature: float = 0.2) -> str:
        # Deterministic response for generic chat with no network.
        last = messages[-1]["content"] if messages else ""
        return (
            "I'm running in offline mode, so I plan with deterministic rules "
            "instead of a language model. Use the IDE onboarding to generate a "
            "project, or connect Ollama/OpenRouter in Settings for richer plans. "
            f"\n(offline planner received: {last[:120]})"
        )

    def generate_intentlang(self, idea: str) -> str:
        return self._h.generate_intentlang(idea)

    def analyze_intent(self, idea: str) -> dict:
        return self._h.analyze_intent(idea)

    def missing_requirements(self, idea: str) -> list[dict]:
        return self._h.missing_requirements(idea)


def get_provider(settings: Optional[dict] = None) -> Provider:
    settings = settings or {}
    provider = settings.get("provider", "offline")
    if provider == "openrouter":
        return OpenRouterProvider(
            settings.get("api_key", ""),
            settings.get("openrouter_model", "qwen/qwen-2.5-72b-instruct"),
        )
    if provider == "ollama":
        return OllamaProvider(
            settings.get("base_url", "http://localhost:11434"),
            settings.get("model", "qwen2.5:7b"),
        )
    return HeuristicProvider()
