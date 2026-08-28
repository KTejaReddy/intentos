"""Artifact model: files produced by code generators."""

from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Artifact:
    path: str
    content: str
    binary: bool = False
    note: str = ""  # generator that produced it

    def to_dict(self) -> dict:
        return {"path": self.path, "note": self.note}

    def __hash__(self) -> int:  # pragma: no cover - used by cache manifest
        return hash((self.path, self.content))


@dataclass
class ArtifactSet:
    items: list[Artifact] = field(default_factory=list)

    def add(self, path: str, content: str, note: str = "") -> Artifact:
        art = Artifact(path=path, content=content, note=note)
        self.items.append(art)
        return art

    def get(self, path: str) -> Optional[Artifact]:
        for art in self.items:
            if art.path == path:
                return art
        return None

    def has(self, path: str) -> bool:
        return self.get(path) is not None

    def paths(self) -> list[str]:
        return sorted(a.path for a in self.items)

    def write_to(self, out_dir) -> list[str]:
        """Materialize artifacts into a directory; returns written paths."""
        written: list[str] = []
        for art in self.items:
            full = out_dir / art.path
            full.parent.mkdir(parents=True, exist_ok=True)
            if art.binary:
                full.write_bytes(art.content.encode("latin-1"))
            else:
                full.write_text(art.content, encoding="utf-8")
            written.append(art.path)
        return written

    def to_zip_bytes(self) -> bytes:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for art in self.items:
                zf.writestr(art.path, art.content)
        return buf.getvalue()

    def manifest(self) -> dict:
        return {"files": [a.to_dict() for a in self.items],
                "count": len(self.items)}
