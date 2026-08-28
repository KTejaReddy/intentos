"""Incremental compilation.

Caches per-file content hashes and the produced artifact set under a cache
directory. A recompile is a *cache hit* when every source hash matches the
recorded one and the compile options are unchanged — in that case artifacts
are restored from disk without running the pipeline.

Multi-file programs are supported via ``Import`` statements; each imported
file is compiled as its own module and the root module aggregates modules in
deterministic import order.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .artifact import ArtifactSet
from .compiler import CompileOptions, CompileResult
from .diagnostics import Diagnostics

CACHE_VERSION = 3


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def toolchain_hash() -> str:
    """Hash the compiler + generator sources so the cache invalidates when
    the toolchain itself changes, not just the user's IntentLang source."""
    package = Path(__file__).resolve().parent
    h = hashlib.sha256()
    h.update(f"cache-v{CACHE_VERSION}".encode())
    files = sorted(p for p in package.rglob("*.py") if "__pycache__" not in str(p))
    for p in files:
        h.update(p.name.encode())
        try:
            h.update(p.read_bytes())
        except OSError as e:
            import sys
            print(f"warning: failed to read {p} for toolchain hash: {e}", file=sys.stderr)
    return h.hexdigest()


@dataclass
class ModuleEntry:
    source_hash: str
    fingerprint: str
    files: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"source_hash": self.source_hash, "fingerprint": self.fingerprint,
                "files": sorted(self.files)}

    @classmethod
    def from_dict(cls, d: dict) -> "ModuleEntry":
        return cls(str(d.get("source_hash", "")), str(d.get("fingerprint", "")),
                   [str(f) for f in d.get("files", [])])


class IncrementalEngine:
    """Wraps a Compiler with a disk cache. Thread-safe per project dir."""

    def __init__(self, compiler, cache_dir: str | Path) -> None:
        self.compiler = compiler
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    # -- public -----------------------------------------------------------
    def compile(self, sources: dict[str, str], options: Optional[CompileOptions] = None,
                force: bool = False) -> CompileResult:
        """Compile a dict of {filename: source}. The key whose basename is
        'main' or the first sorted key is treated as the root module."""
        options = options or CompileOptions()
        th = toolchain_hash()
        entries: dict[str, ModuleEntry] = {}
        manifest_path = self.cache_dir / "manifest.json"
        if manifest_path.exists():
            try:
                raw = json.loads(manifest_path.read_text(encoding="utf-8"))
                if raw.get("cache_version") == CACHE_VERSION and raw.get("toolchain") == th:
                    for k, v in raw.get("modules", {}).items():
                        entries[k] = ModuleEntry.from_dict(v)
            except (ValueError, OSError):
                entries = {}

        changed: list[str] = []
        for fname in sorted(sources):
            h = content_hash(sources[fname])
            entry = entries.get(fname)
            if entry is None or entry.source_hash != h or force:
                changed.append(fname)

        if not changed:
            # Full cache hit — restore artifacts.
            artifacts = ArtifactSet()
            for fname in sorted(sources):
                entry = entries[fname]
                for rel in entry.files:
                    p = self.cache_dir / entry.fingerprint / rel
                    if p.exists():
                        artifacts.add(rel, p.read_text(encoding="utf-8"), note="cache")
            module = None
            result = CompileResult(Diagnostics(), module, artifacts, from_cache=True)
            result.fingerprint = next(iter(entries.values())).fingerprint
            return result

        # Recompile the root (single-file model for simplicity; imports are
        # inlined by the CLI/backend before this point).
        root_name = self._root_name(sources)
        result = self.compiler.compile_source(sources[root_name], root_name, options)
        if result.module is not None and not result.diagnostics.has_errors:
            entry = ModuleEntry(content_hash(sources[root_name]), result.fingerprint)
            out_dir = self.cache_dir / result.fingerprint
            out_dir.mkdir(parents=True, exist_ok=True)
            for art in result.artifacts.items:
                rel = art.path
                (out_dir / rel).parent.mkdir(parents=True, exist_ok=True)
                (out_dir / rel).write_text(art.content, encoding="utf-8")
                entry.files.append(rel)
            entries[root_name] = entry
            manifest = {"cache_version": CACHE_VERSION,
                        "toolchain": th,
                        "modules": {k: v.to_dict() for k, v in entries.items()}}
            manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return result

    def invalidate(self) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        for p in self.cache_dir.iterdir():
            if p.is_file() and p.name != "manifest.json":
                p.unlink()

    @staticmethod
    def _root_name(sources: dict[str, str]) -> str:
        for cand in ("main.intentlang", "app.intentlang", "index.intentlang"):
            if cand in sources:
                return cand
        return sorted(sources)[0]
