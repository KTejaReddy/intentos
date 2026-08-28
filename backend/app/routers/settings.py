"""Provider/IDE settings endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from .. import config
from ..schemas import SettingsPut

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
def get_settings():
    s = config.get_settings()
    s.pop("api_key", None)  # never leak secrets back to the client
    return s


@router.put("")
def put_settings(req: SettingsPut):
    current = config.get_settings()
    changes = req.model_dump(exclude_none=True)
    if "api_key" in changes and not changes["api_key"]:
        changes.pop("api_key")
    current.update(changes)
    config.save_settings(current)
    out = dict(current)
    out.pop("api_key", None)
    return out
