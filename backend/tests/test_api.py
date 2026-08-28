"""Backend API smoke tests (requires the backend venv)."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# Ensure the compiler is importable (mirrors config.py wiring).
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "compiler"))
sys.path.insert(0, str(ROOT / "backend"))

os.environ.setdefault("INTENTOS_DATA_DIR", tempfile.mkdtemp(prefix="intentos-test-"))

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_intent_analyze_offline():
    r = client.post("/api/intent/analyze",
                    json={"idea": "Create a food delivery startup for Hyderabad"})
    assert r.status_code == 200
    data = r.json()
    assert data["source"] == "heuristic"
    assert "delivery" in data["domain"]
    assert "Hyderabad" in data.get("app_name", "") or data["app_name"]


def test_requirements():
    r = client.post("/api/requirements/analyze",
                    json={"idea": "food delivery app with payments"})
    assert r.status_code == 200
    assert "questions" in r.json()


def test_plan_generates_intentlang():
    r = client.post("/api/plan/generate",
                    json={"idea": "Build a student portal for a college"})
    assert r.status_code == 200
    data = r.json()
    assert "Create Application" in data["intentlang"]
    assert "Create Page" in data["intentlang"]


def test_compile_endpoint():
    source = """Create Application Demo
Create Page Home
  With
    Route /
  Add Text Hello
    With
      Text "Hi"
"""
    r = client.post("/api/compile", json={"source": source})
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["artifacts"]["count"] > 10
    assert data["zip_b64"]


def test_compile_diagnostics():
    r = client.post("/api/compile/check", json={"source": "Create Page A\nCreate Page A\n"})
    data = r.json()
    assert data["ok"] is False
    assert any(d["severity"] == "error" for d in data["diagnostics"])


def test_pipeline_creates_project():
    r = client.post("/api/pipeline/run",
                    json={"idea": "A task tracker for small teams"})
    assert r.status_code == 200
    # StreamingResponse — read the SSE body.
    body = r.text
    assert "project_id" in body or "done" in body
    assert "event: step" in body


def test_plugins():
    r = client.get("/api/plugins")
    assert r.status_code == 200
    assert len(r.json()["plugins"]) >= 2


def test_settings_roundtrip():
    r = client.put("/api/settings", json={"provider": "offline"})
    assert r.status_code == 200
    assert r.json()["provider"] == "offline"
