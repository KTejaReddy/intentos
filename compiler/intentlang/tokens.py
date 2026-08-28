"""Token model for the IntentLang lexer."""

from __future__ import annotations

from dataclasses import dataclass

NEWLINE = "NEWLINE"
INDENT = "INDENT"
DEDENT = "DEDENT"
IDENT = "IDENT"
KEYWORD = "KEYWORD"
STRING = "STRING"
NUMBER = "NUMBER"
BOOLEAN = "BOOLEAN"
PATH = "PATH"
EQUALS = "EQUALS"
OPERATOR = "OPERATOR"
COMMA = "COMMA"
LBRACKET = "LBRACKET"
RBRACKET = "RBRACKET"
EOF = "EOF"


@dataclass(frozen=True)
class Token:
    type: str
    value: str
    line: int
    col: int
    offset: int

    def describe(self) -> str:
        if self.type in (IDENT, KEYWORD, STRING, NUMBER, BOOLEAN, PATH):
            return f"{self.type.lower()} {self.value!r}"
        return self.type.lower()

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "value": self.value,
            "line": self.line,
            "col": self.col,
        }
