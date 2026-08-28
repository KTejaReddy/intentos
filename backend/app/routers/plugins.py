"""Plugin marketplace: list registry plugins and toggle enable state."""

from __future__ import annotations

from fastapi import APIRouter

from .. import config

router = APIRouter(prefix="/api/plugins", tags=["plugins"])

# Built-in registry. Community plugins can be appended at runtime.
_BUILTIN = [
    {
        "id": "pwa",
        "name": "PWA",
        "description": "Installable web app: manifest, service worker, offline shell.",
        "type": "codegen",
        "author": "IntentOS",
        "version": "1.0.0",
    },
    {
        "id": "seo",
        "name": "SEO",
        "description": "Sitemap, robots.txt and per-page meta tags for search engines.",
        "type": "codegen",
        "author": "IntentOS",
        "version": "1.0.0",
    },
]


@router.get("")
def list_plugins():
    state = config.get_plugin_state()
    return {"plugins": [{**p, "enabled": state.get(p["id"], False)}
                        for p in _BUILTIN]}


@router.post("/{plugin_id}/toggle")
def toggle_plugin(plugin_id: str):
    state = config.get_plugin_state()
    if plugin_id not in state:
        state[plugin_id] = False
    state[plugin_id] = not state[plugin_id]
    config.save_plugin_state(state)
    return {"id": plugin_id, "enabled": state[plugin_id]}
