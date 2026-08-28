"""IntentLang compiler test suite (stdlib unittest)."""

from __future__ import annotations

import ast
import json
import re
import tempfile
import unittest
from pathlib import Path

from intentlang.artifact import ArtifactSet
from intentlang.compiler import CompileOptions, Compiler
from intentlang.diagnostics import Diagnostics
from intentlang.incremental import IncrementalEngine
from intentlang.ir import ModuleIR, canonical_json
from intentlang.lexer import Lexer
from intentlang.optimizer import Optimizer
from intentlang.parser import Parser
from intentlang.semantic import SemanticAnalyzer

SAMPLE = Path(__file__).parent.parent / "samples" / "student-portal.il"


def compile_ok(source: str, **opts):
    result = Compiler().compile_source(source, "test.il",
                                       CompileOptions(**opts))
    return result


class TestLexer(unittest.TestCase):
    def test_tokens(self):
        diags = Diagnostics()
        toks = Lexer('Create Page Login\n  With\n    Route /login\n', "t.il", diags).tokenize()
        values = [t.value for t in toks]
        self.assertIn("create", values)
        self.assertIn("/login", values)
        self.assertFalse(diags.has_errors)

    def test_indent_dedent(self):
        diags = Diagnostics()
        toks = Lexer("Create Page A\n  Add Input X\nAdd Text Y\n", "t.il", diags).tokenize()
        types = [t.type for t in toks]
        self.assertIn("INDENT", types)
        self.assertIn("DEDENT", types)
        self.assertEqual(types.count("INDENT"), types.count("DEDENT"))

    def test_comments_and_literals(self):
        diags = Diagnostics()
        src = "// line comment\n/* block\ncomment */\nWith Title \"hi\" Count 3 Flag true List [a, b]"
        toks = Lexer(src, "t.il", diags).tokenize()
        vals = [t.value for t in toks]
        self.assertIn("hi", vals)
        self.assertIn("3", vals)
        self.assertIn("true", vals)
        self.assertFalse(diags.has_errors)

    def test_bad_tab(self):
        diags = Diagnostics()
        Lexer("\tCreate Page A\n", "t.il", diags).tokenize()
        self.assertTrue(diags.has_errors)

    def test_unterminated_string(self):
        diags = Diagnostics()
        Lexer('With Title "oops\n', "t.il", diags).tokenize()
        self.assertTrue(diags.has_errors)


class TestParser(unittest.TestCase):
    def _parse(self, src):
        diags = Diagnostics()
        toks = Lexer(src, "t.il", diags).tokenize()
        return Parser(toks, "t.il", diags).parse_module(), diags

    def test_sample_parses(self):
        src = SAMPLE.read_text(encoding="utf-8")
        module, diags = self._parse(src)
        self.assertEqual(len(module.statements), 13)
        self.assertFalse(diags.has_errors)

    def test_error_recovery(self):
        src = "Create Page A\n  With\n    Route /x\nCreate Page !!!\n  With\n    Route /y\nCreate Page B\n"
        module, diags = self._parse(src)
        # Recovery must still parse surrounding statements.
        creates = [s for s in module.statements]
        self.assertTrue(diags.has_errors)
        self.assertGreaterEqual(len(creates), 2)

    def test_inline_props(self):
        src = "Create Model M With Table items\nField Id Type id Required true\n"
        module, _ = self._parse(src)
        self.assertEqual(len(module.statements), 1)


class TestSemantic(unittest.TestCase):
    def _analyze(self, src):
        diags = Diagnostics()
        toks = Lexer(src, "t.il", diags).tokenize()
        ast = Parser(toks, "t.il", diags).parse_module()
        return SemanticAnalyzer("t.il", diags).analyze(ast), diags

    def test_sample_ir(self):
        mod, diags = self._analyze(SAMPLE.read_text(encoding="utf-8"))
        self.assertFalse(diags.has_errors)
        self.assertEqual(len(mod.pages), 3)
        self.assertEqual(len(mod.models), 1)
        self.assertEqual(len(mod.apis), 4)
        self.assertEqual(mod.pages[0].route, "/login")
        student = mod.models[0]
        self.assertEqual(student.table, "students")
        ids = [f for f in student.fields if f.ftype == "id"]
        self.assertEqual(len(ids), 1)
        self.assertTrue(ids[0].primary)

    def test_duplicate_page(self):
        mod, diags = self._analyze(
            "Create Page A\nCreate Page A\n"
        )
        self.assertTrue(diags.has_errors)
        self.assertTrue(any(d.code == "IL-S020" for d in diags.items))

    def test_unknown_reference(self):
        _, diags = self._analyze(
            "Create Page A\n  Add Button \"Go\"\n    When Clicked\n      Navigate To Missing\n"
        )
        self.assertTrue(any(d.code == "IL-S040" for d in diags.items))

    def test_forward_reference_ok(self):
        _, diags = self._analyze(
            "Create Page A\n  Add Button \"Go\"\n    When Clicked\n      Navigate To B\n"
            "Create Page B\n"
        )
        self.assertFalse(diags.has_errors)

    def test_bad_field_type(self):
        _, diags = self._analyze(
            "Create Model M\n  Field X\n    Type totally_wrong\n"
        )
        self.assertTrue(any(d.code == "IL-S028" for d in diags.items))

    def test_unknown_auth_role(self):
        _, diags = self._analyze(
            "Create Api A\n  With\n    Method GET\n    Route /api/a\n    Auth superadmin\n"
        )
        self.assertTrue(any(d.code == "IL-S025" for d in diags.items))

    def test_known_role_ok(self):
        _, diags = self._analyze(
            "Create Role Staff\nCreate Api A\n  With\n    Auth staff\n    Route /api/a\n"
        )
        self.assertFalse(diags.has_errors)


class TestOptimizer(unittest.TestCase):
    def test_usage_diagnostics(self):
        mod = ModuleIR()
        from intentlang import ir as I
        mod.app.name = "X"
        mod.app.title = "X"
        mod.models.append(I.Model(name="Orphan", table="orphans"))
        mod.apis.append(I.Api(name="GetOrphans", route="/api/orphans"))
        diags = Diagnostics()
        Optimizer("t.il", diags).optimize(mod)
        codes = {d.code for d in diags.items}
        self.assertIn("IL-O020", codes)  # unused model
        self.assertIn("IL-O021", codes)  # unused api

    def test_deterministic_fingerprint(self):
        src = SAMPLE.read_text(encoding="utf-8")
        r1 = compile_ok(src)
        r2 = compile_ok(src)
        self.assertEqual(r1.fingerprint, r2.fingerprint)
        self.assertEqual(r1.module.to_json(), r2.module.to_json())


class TestCodegen(unittest.TestCase):
    def setUp(self):
        self.result = compile_ok(SAMPLE.read_text(encoding="utf-8"))

    def test_artifacts(self):
        self.assertTrue(self.result.ok())
        self.assertGreater(len(self.result.artifacts.items), 40)
        self.assertTrue(self.result.artifacts.has("frontend/package.json"))
        self.assertTrue(self.result.artifacts.has("backend/main.py"))
        self.assertTrue(self.result.artifacts.has("db/schema.sql"))
        self.assertTrue(self.result.artifacts.has("infra/Dockerfile"))
        self.assertTrue(self.result.artifacts.has(".github/workflows/ci.yml"))
        self.assertTrue(self.result.artifacts.has("preview/index.html"))

    def test_generated_python_is_valid(self):
        for path in ("backend/main.py", "backend/database.py",
                     "backend/security.py", "backend/models.py",
                     "backend/schemas.py", "backend/seed.py",
                     "backend/routers/login.py", "backend/routers/getcourses.py",
                     "backend/tests/test_api.py"):
            src = self.result.artifacts.get(path).content
            ast.parse(src)  # raises on syntax errors

    def test_determinism(self):
        src = SAMPLE.read_text(encoding="utf-8")
        a = compile_ok(src)
        b = compile_ok(src)
        for art_a in a.artifacts.items:
            art_b = b.artifacts.get(art_a.path)
            self.assertIsNotNone(art_b)
            self.assertEqual(art_a.content, art_b.content, art_a.path)

    def test_sql_schema(self):
        sql = self.result.artifacts.get("db/schema.sql").content
        self.assertIn("CREATE TABLE", sql)
        self.assertIn("students", sql)
        self.assertIn("email", sql)

    def test_other_targets(self):
        r = compile_ok(SAMPLE.read_text(encoding="utf-8"),
                       frontend="next", backend="express", database="postgres")
        self.assertTrue(r.ok())
        self.assertTrue(r.artifacts.has("frontend/app/page.tsx"))
        self.assertTrue(r.artifacts.has("backend/server.js"))
        self.assertIn("SERIAL", r.artifacts.get("db/schema.sql").content)

        r2 = compile_ok(SAMPLE.read_text(encoding="utf-8"),
                        frontend="flutter", backend="spring", database="mysql")
        self.assertTrue(r2.ok())
        self.assertTrue(r2.artifacts.has("frontend/pubspec.yaml"))
        self.assertTrue(r2.artifacts.has("backend/pom.xml"))
        self.assertIn("AUTO_INCREMENT", r2.artifacts.get("db/schema.sql").content)

    def test_plugins(self):
        src = "Use Pwa\nUse Seo\n" + SAMPLE.read_text(encoding="utf-8")
        r = compile_ok(src)
        self.assertTrue(r.ok())
        self.assertTrue(r.artifacts.has("frontend/public/manifest.webmanifest"))
        self.assertTrue(r.artifacts.has("frontend/public/sw.js"))
        self.assertTrue(r.artifacts.has("frontend/public/sitemap.xml"))
        self.assertTrue(r.artifacts.has("frontend/public/robots.txt"))

    def test_error_in_source_skips_codegen(self):
        r = compile_ok("Create Page A\nCreate Page A\n")
        self.assertFalse(r.ok())
        self.assertEqual(len(r.artifacts.items), 0)

    def test_ir_json_roundtrip(self):
        d = self.result.module.to_dict()
        self.assertIsInstance(d, dict)
        json_str = canonical_json(d)
        self.assertIn("pages", json_str)

    def test_standalone_js_is_valid(self):
        """The embedded preview script must be syntactically valid JS."""
        html = self.result.artifacts.get("preview/index.html").content
        m = re.search(r"<script>(.*?)</script>", html, re.S)
        self.assertIsNotNone(m)
        import subprocess, sys, shutil, tempfile, os
        node = shutil.which("node")
        if not node:
            self.skipTest("node not installed")
        with tempfile.TemporaryDirectory() as td:
            js = os.path.join(td, "preview.js")
            with open(js, "w", encoding="utf-8") as fh:
                fh.write(m.group(1))
            proc = subprocess.run([node, "--check", js],
                                  capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0,
                             f"generated preview JS is invalid: {proc.stderr}")


class TestIncremental(unittest.TestCase):
    def test_cache_hit_and_miss(self):
        compiler = Compiler()
        src = SAMPLE.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as td:
            engine = IncrementalEngine(compiler, Path(td))
            first = engine.compile({"app.intentlang": src})
            self.assertFalse(first.from_cache)
            self.assertGreater(len(first.artifacts.items), 0)
            second = engine.compile({"app.intentlang": src})
            self.assertTrue(second.from_cache)
            # change source -> cache miss
            changed = src.replace("Student Portal", "Student Portal 2")
            third = engine.compile({"app.intentlang": changed})
            self.assertFalse(third.from_cache)
            self.assertNotEqual(third.fingerprint, first.fingerprint)


    def test_toolchain_change_invalidates_cache(self):
        """A change in the compiler/codegen must bypass cached artifacts."""
        from intentlang.incremental import CACHE_VERSION, toolchain_hash
        compiler = Compiler()
        src = SAMPLE.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as td:
            engine = IncrementalEngine(compiler, Path(td))
            first = engine.compile({"app.intentlang": src})
            self.assertFalse(first.from_cache)
            # Rewrite the manifest with a different toolchain hash — simulating
            # a compiler upgrade — and confirm the next compile is a miss.
            manifest = Path(td) / "manifest.json"
            raw = json.loads(manifest.read_text(encoding="utf-8"))
            raw["toolchain"] = "stale"
            raw["cache_version"] = CACHE_VERSION
            manifest.write_text(json.dumps(raw), encoding="utf-8")
            second = engine.compile({"app.intentlang": src})
            self.assertFalse(second.from_cache)
            self.assertNotEqual(second.fingerprint, "")
            # And an untouched cache still hits.
            third = engine.compile({"app.intentlang": src})
            self.assertTrue(third.from_cache)


class TestE2E(unittest.TestCase):
    def test_cli_compile(self):
        import subprocess
        import sys
        out_dir = Path(tempfile.mkdtemp()) / "build"
        proc = subprocess.run(
            [sys.executable, "-m", "intentlang", "compile",
             str(SAMPLE), "--out", str(out_dir)],
            cwd=Path(__file__).parent.parent,
            capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue((out_dir / "backend" / "main.py").exists())
        self.assertTrue((out_dir / "preview" / "index.html").exists())

    def test_artifact_set_zip(self):
        r = compile_ok(SAMPLE.read_text(encoding="utf-8"))
        z = r.artifacts.to_zip_bytes()
        self.assertGreater(len(z), 1000)
        import io, zipfile
        with zipfile.ZipFile(io.BytesIO(z)) as zf:
            names = zf.namelist()
            self.assertIn("backend/main.py", names)


if __name__ == "__main__":
    unittest.main()
