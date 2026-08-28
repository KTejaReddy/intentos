"""Read-only git integration.

Runs git subprocesses against a project's *parent* repository (or the repo
root) and returns status/diff/log. No writes are performed from the API.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def _run(cwd: Path, args: list[str], timeout: int = 15) -> str:
    try:
        proc = subprocess.run(
            ["git", *args], cwd=str(cwd), capture_output=True,
            text=True, timeout=timeout,
        )
        return proc.stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return ""


def _repo_root(cwd: Path) -> Path:
    out = _run(cwd, ["rev-parse", "--show-toplevel"])
    if out:
        return Path(out)
    return cwd


def status(cwd: Path) -> list[dict]:
    out = _run(cwd, ["status", "--porcelain=v1", "-b"])
    items = []
    for line in out.splitlines():
        if not line:
            continue
        if line.startswith("##"):
            items.append({"kind": "branch", "status": "info", "path": line[3:]})
            continue
        code, path = line[:2], line[3:]
        items.append({"kind": "file", "status": code.strip(), "path": path})
    return items


def diff(cwd: Path) -> str:
    return _run(cwd, ["diff", "--stat"])


def log(cwd: Path, limit: int = 20) -> list[dict]:
    out = _run(cwd, ["log", f"-{limit}", "--pretty=format:%h|%an|%s"])
    return [dict(zip(("hash", "author", "subject"), line.split("|", 2)))
            for line in out.splitlines() if "|" in line]


def is_repo(cwd: Path) -> bool:
    return bool(_run(cwd, ["rev-parse", "--is-inside-work-tree"]))
