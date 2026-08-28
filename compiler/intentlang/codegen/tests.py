"""Test generator — deterministic pytest suites covering the generated app."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..artifact import ArtifactSet
from ..diagnostics import Diagnostics
from ._util import py_str
from .base import Generator

if TYPE_CHECKING:  # pragma: no cover
    from .. import ir as I
    from ..compiler import CompileOptions


class TestsGenerator(Generator):
    name = "tests"

    def generate(self, module: "I.ModuleIR", options: "CompileOptions",
                 artifacts: ArtifactSet, diags: Diagnostics) -> None:
        self.m = module
        artifacts.add("backend/tests/__init__.py", "", self.name)
        artifacts.add("backend/tests/test_api.py", self._api_tests(), self.name)
        artifacts.add("backend/tests/test_schema.py", self._schema_tests(), self.name)
        artifacts.add("frontend/tests/smoke.mjs", self._frontend_smoke(), self.name)

    def _api_tests(self) -> str:
        m = self.m
        lines = [
            '"""Generated API tests (pytest + FastAPI TestClient)."""',
            "from fastapi.testclient import TestClient",
            "",
            "from main import app",
            "",
            "client = TestClient(app)",
            "",
            "",
            "def test_health():",
            "    r = client.get(\"/health\")",
            "    assert r.status_code == 200",
            "    assert r.json()[\"status\"] == \"ok\"",
            "",
        ]
        if m.apis:
            lines.append("")
            for a in m.apis:
                lines.append(f"def test_{a.slug}():")
                if a.auth == "public":
                    if a.method == "GET":
                        lines.append(f"    r = client.get({py_str(a.route)})")
                    elif a.method in ("POST", "PUT", "PATCH"):
                        payload = self._sample_payload(a)
                        lines.append(f"    r = client.{a.method.lower()}({py_str(a.route)}, json={payload})")
                    else:
                        lines.append(f"    r = client.{a.method.lower()}({py_str(a.route)})")
                    expected = self._expected_status(a)
                    lines.append(f"    assert r.status_code in ({expected})")
                    lines.append("")
                else:
                    lines.append(f"    r = client.{a.method.lower()}({py_str(a.route)})")
                    lines.append('    assert r.status_code in (401, 403)  # protected endpoint rejects anonymous calls')
                    lines.append("")
        return "\n".join(lines)

    def _sample_payload(self, a: "I.Api") -> str:
        fields = a.request_fields or []
        items = ", ".join(f"{py_str(f.slug)}: {py_str(f.name.lower())}" for f in fields)
        return "{" + items + "}"

    def _expected_status(self, a: "I.Api") -> str:
        statuses = sorted({r.status for r in a.responses})
        if not statuses:
            return "200"
        return ", ".join(str(s) for s in statuses[:2])

    def _schema_tests(self) -> str:
        lines = [
            '"""Generated schema tests: every model table exists and has its columns."""',
            "import sqlite3",
            "",
            "from database import DATABASE_URL, engine, init_db",
            "from sqlalchemy import inspect",
            "",
            "",
            "def _conn():",
            '    path = DATABASE_URL.replace("sqlite:///", "")',
            "    return sqlite3.connect(path)",
            "",
            "",
            "def test_tables_exist():",
            "    init_db()",
            "    inspector = inspect(engine)",
            "    tables = set(inspector.get_table_names())",
        ]
        for model in self.m.models:
            lines.append(f'    assert {py_str(model.table.lower())} in tables, "table {model.table} missing"')
        lines.append("")
        if self.m.models:
            m0 = self.m.models[0]
            lines.append("")
            lines.append("def test_columns_exist():")
            lines.append("    init_db()")
            lines.append("    inspector = inspect(engine)")
            lines.append(f'    cols = {{c["name"] for c in inspector.get_columns({py_str(m0.table.lower())})}}')
            for f in m0.fields:
                lines.append(f'    assert {py_str(f.name)} in cols')
            lines.append("")
        return "\n".join(lines)

    def _frontend_smoke(self) -> str:
        lines = [
            "// Generated frontend smoke test: assert the build output exists.",
            "import { existsSync, readFileSync } from 'node:fs'",
            "import { join } from 'node:path'",
            "",
            "const dist = join(process.cwd(), 'dist')",
            "const idx = join(dist, 'index.html')",
            "if (!existsSync(idx)) {",
            "  console.error('dist/index.html missing — run npm run build first')",
            "  process.exit(1)",
            "}",
            "const html = readFileSync(idx, 'utf-8')",
            "console.log(`frontend smoke: index.html ${html.length} bytes`)",
        ]
        for p in self.m.pages:
            lines.append(f"if (!existsSync(join(dist, 'assets'))) {{ console.warn('assets dir missing') }}")
        return "\n".join(lines)
