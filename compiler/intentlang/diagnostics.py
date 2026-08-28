"""Diagnostics: the single channel through which the compiler reports
problems at every stage (lexer, parser, semantic analysis, optimizer).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    HINT = "hint"


@dataclass
class Diagnostic:
    severity: Severity
    code: str
    message: str
    line: int = 0
    col: int = 0
    file: str = "<string>"
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "severity": self.severity.value,
            "code": self.code,
            "message": self.message,
            "line": self.line,
            "col": self.col,
            "file": self.file,
            "notes": list(self.notes),
        }

    def format(self) -> str:
        loc = f"{self.file}:{self.line}:{self.col}"
        head = f"{self.severity.value.upper()} [{self.code}]"
        out = f"{loc}: {head}: {self.message}"
        for note in self.notes:
            out += f"\n  note: {note}"
        return out


class Diagnostics:
    """Collects diagnostics across compilation stages."""

    def __init__(self) -> None:
        self.items: list[Diagnostic] = []

    def add(self, severity: Severity, code: str, message: str,
            line: int = 0, col: int = 0, file: str = "<string>",
            notes: Optional[list[str]] = None) -> None:
        self.items.append(
            Diagnostic(severity, code, message, line, col, file,
                       notes or [])
        )

    def error(self, code: str, message: str, line: int = 0, col: int = 0,
              file: str = "<string>", notes: Optional[list[str]] = None) -> None:
        self.add(Severity.ERROR, code, message, line, col, file, notes)

    def warning(self, code: str, message: str, line: int = 0, col: int = 0,
                file: str = "<string>", notes: Optional[list[str]] = None) -> None:
        self.add(Severity.WARNING, code, message, line, col, file, notes)

    def info(self, code: str, message: str, line: int = 0, col: int = 0,
             file: str = "<string>", notes: Optional[list[str]] = None) -> None:
        self.add(Severity.INFO, code, message, line, col, file, notes)

    def hint(self, code: str, message: str, line: int = 0, col: int = 0,
             file: str = "<string>", notes: Optional[list[str]] = None) -> None:
        self.add(Severity.HINT, code, message, line, col, file, notes)

    @property
    def errors(self) -> list[Diagnostic]:
        return [d for d in self.items if d.severity is Severity.ERROR]

    @property
    def has_errors(self) -> bool:
        return any(d.severity is Severity.ERROR for d in self.items)

    def merge(self, other: "Diagnostics") -> None:
        self.items.extend(other.items)

    def to_dict(self) -> list[dict]:
        return [d.to_dict() for d in self.items]

    def format_all(self) -> str:
        return "\n".join(d.format() for d in self.items)

    def __len__(self) -> int:
        return len(self.items)
