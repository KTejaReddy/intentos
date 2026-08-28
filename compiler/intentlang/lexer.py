"""Lexer for IntentLang.

Produces a flat token stream with INDENT/DEDENT tokens so the parser is
indentation-driven (like Python). Tabs are rejected. Blank lines and
comment-only lines are skipped without affecting the indent stack.

Error handling: lexical problems never abort the lexer. They are reported
as diagnostics and the lexer recovers by skipping to a safe boundary.
"""

from __future__ import annotations

from .diagnostics import Diagnostics
from .keywords import KEYWORDS
from .tokens import (
    BOOLEAN, COMMA, DEDENT, EOF, EQUALS, IDENT, INDENT, KEYWORD, LBRACKET,
    NEWLINE, NUMBER, OPERATOR, PATH, RBRACKET, STRING, Token,
)

_SIMPLE_ESCAPES = {
    "n": "\n", "t": "\t", "r": "\r", "0": "\0", "\\": "\\",
    '"': '"', "'": "'", "/": "/",
}

_MAX_DEPTH = 64  # guard against pathological indentation


class Lexer:
    def __init__(self, source: str, filename: str = "<string>",
                 diagnostics: Diagnostics | None = None) -> None:
        self.src = source
        self.filename = filename
        self.diags = diagnostics if diagnostics is not None else Diagnostics()
        self.pos = 0
        self.line = 1
        self.col = 1
        self.tokens: list[Token] = []
        self.indents = [0]
        self._at_line_start = True

    # -- low-level helpers ------------------------------------------------
    def _peek(self, offset: int = 0) -> str:
        i = self.pos + offset
        return self.src[i] if i < len(self.src) else ""

    def _advance(self) -> str:
        ch = self.src[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def _emit(self, ttype: str, value: str, line: int, col: int) -> None:
        self.tokens.append(Token(ttype, value, line, col, self.pos))

    def _error(self, code: str, message: str, line: int, col: int,
               notes: list[str] | None = None) -> None:
        self.diags.error(code, message, line, col, self.filename, notes)

    # -- public API -------------------------------------------------------
    def tokenize(self) -> list[Token]:
        while self.pos < len(self.src):
            ch = self._peek()

            # Every line start (including column 0) must be checked for
            # indentation so INDENT/DEDENT stay in sync with the source.
            if self._at_line_start:
                if ch == "\n":  # blank line
                    self._advance()
                    self._emit(NEWLINE, "\n", self.line - 1, 1)
                    self._at_line_start = True
                    continue
                self._handle_indentation()
                if self._peek() == "\n" or self.pos >= len(self.src):
                    # Blank or comment-only line: emit its newline untouched.
                    if self._peek() == "\n":
                        self._advance()
                        self._emit(NEWLINE, "\n", self.line - 1, 1)
                    self._at_line_start = True
                    continue
                self._at_line_start = False
                continue

            if ch == "\n":
                self._advance()
                self._emit(NEWLINE, "\n", self.line - 1, 1)
                self._at_line_start = True
                continue

            if ch in " \t":  # separator between tokens
                self._advance()
                continue

            if ch == "/" and self._peek(1) == "/":
                self._skip_line_comment()
                continue
            if ch == "/" and self._peek(1) == "*":
                self._skip_block_comment()
                continue
            if ch in ('"', "'"):
                self._lex_string(ch)
                continue
            if ch.isdigit() or (ch == "-" and self._peek(1).isdigit()):
                self._lex_number()
                continue
            if ch.isalpha() or ch == "_":
                self._lex_ident()
                continue
            if ch == "/":
                self._lex_path()
                continue
            if ch == "=":
                self._emit(EQUALS, "=", self.line, self.col)
                self._advance()
                continue
            if ch in ("<", ">", "!"):
                op = ch
                if self._peek(1) == "=":
                    op += "="
                    self._advance()
                self._emit(OPERATOR, op, self.line, self.col)
                self._advance()
                continue
            if ch == ",":
                self._emit(COMMA, ",", self.line, self.col)
                self._advance()
                continue
            if ch == "[":
                self._emit(LBRACKET, "[", self.line, self.col)
                self._advance()
                continue
            if ch == "]":
                self._emit(RBRACKET, "]", self.line, self.col)
                self._advance()
                continue

            self._error("IL-E001", f"unexpected character {ch!r}", self.line, self.col)
            self._advance()

        # Close open indentation levels.
        while len(self.indents) > 1:
            self.indents.pop()
            self._emit(DEDENT, "", self.line, self.col)
        self._emit(EOF, "", self.line, self.col)
        return self.tokens

    # -- indentation ------------------------------------------------------
    def _handle_indentation(self) -> None:
        line = self.line
        col = self.col
        width = 0
        while self._peek() in (" ", "\t"):
            ch = self._peek()
            if ch == "\t":
                self._error("IL-E002", "tabs are not allowed; use spaces", self.line, self.col)
            self._advance()
            width += 1

        # Comment-only or blank line: skip without touching the indent stack.
        if self._peek() == "\n":
            return
        if self._peek() == "/" and self._peek(1) in ("/", "*"):
            self._skip_line_comment() if self._peek(1) == "/" else self._skip_block_comment()
            if self._peek() == "\n" or self.pos >= len(self.src):
                return
            # comment followed by code on the same line: fall through

        top = self.indents[-1]
        if width > top:
            if len(self.indents) >= _MAX_DEPTH:
                self._error("IL-E003", "maximum indentation depth exceeded", line, col)
                self.indents.append(width)
            else:
                self.indents.append(width)
                self._emit(INDENT, "", line, col)
        elif width < top:
            while self.indents and self.indents[-1] > width:
                self.indents.pop()
                self._emit(DEDENT, "", line, col)
            if self.indents[-1] != width:
                self._error(
                    "IL-E004",
                    f"inconsistent indentation: expected column {self.indents[-1]}, got {width}",
                    line, col,
                )
                self.indents.append(width)

    # -- comments ---------------------------------------------------------
    def _skip_line_comment(self) -> None:
        while self._peek() and self._peek() != "\n":
            self._advance()

    def _skip_block_comment(self) -> None:
        start_line, start_col = self.line, self.col
        self._advance()  # '/'
        self._advance()  # '*'
        while self.pos < len(self.src):
            if self._peek() == "*" and self._peek(1) == "/":
                self._advance()
                self._advance()
                return
            self._advance()
        self._error("IL-E005", "unterminated block comment", start_line, start_col)

    # -- token kinds ------------------------------------------------------
    def _lex_string(self, quote: str) -> None:
        line, col = self.line, self.col
        self._advance()  # opening quote
        buf: list[str] = []
        while self.pos < len(self.src):
            ch = self._peek()
            if ch == quote:
                self._advance()
                self._emit(STRING, "".join(buf), line, col)
                return
            if ch == "\n":
                self._error("IL-E006", "unterminated string literal", line, col)
                self._emit(STRING, "".join(buf), line, col)
                return
            if ch == "\\":
                self._advance()
                esc = self._peek()
                if esc in _SIMPLE_ESCAPES:
                    buf.append(_SIMPLE_ESCAPES[esc])
                    self._advance()
                elif esc == "u":
                    hex4 = self.src[self.pos + 1: self.pos + 5]
                    if len(hex4) == 4 and all(c in "0123456789abcdefABCDEF" for c in hex4):
                        buf.append(chr(int(hex4, 16)))
                        for _ in range(5):
                            self._advance()
                    else:
                        self._error("IL-E007", "invalid \\u escape", self.line, self.col)
                        self._advance()
                else:
                    self._error("IL-E007", f"unknown escape sequence \\{esc}", self.line, self.col)
                    self._advance()
                continue
            buf.append(ch)
            self._advance()
        self._error("IL-E006", "unterminated string literal", line, col)
        self._emit(STRING, "".join(buf), line, col)

    def _lex_number(self) -> None:
        line, col = self.line, self.col
        start = self.pos
        if self._peek() == "-":
            self._advance()
        while self._peek().isdigit():
            self._advance()
        if self._peek() == "." and self._peek(1).isdigit():
            self._advance()
            while self._peek().isdigit():
                self._advance()
        if self._peek() in ("e", "E"):
            nxt = self._peek(1)
            if nxt.isdigit() or (nxt in ("+", "-") and self._peek(2).isdigit()):
                self._advance()
                if self._peek() in ("+", "-"):
                    self._advance()
                while self._peek().isdigit():
                    self._advance()
        self._emit(NUMBER, self.src[start:self.pos], line, col)

    def _lex_ident(self) -> None:
        line, col = self.line, self.col
        start = self.pos
        while self._peek().isalnum() or self._peek() == "_":
            self._advance()
        word = self.src[start:self.pos]
        if word.lower() in KEYWORDS:
            self._emit(KEYWORD, word.lower(), line, col)
        elif word.lower() in ("true", "false"):
            self._emit(BOOLEAN, word.lower(), line, col)
        else:
            self._emit(IDENT, word, line, col)

    @staticmethod
    def _is_path_char(ch: str) -> bool:
        return ch.isalnum() or ch in "_-./{}:?&=*"

    def _lex_path(self) -> None:
        line, col = self.line, self.col
        start = self.pos
        self._advance()  # '/'
        while self._peek() and self._is_path_char(self._peek()) and self._peek() != " ":
            self._advance()
        self._emit(PATH, self.src[start:self.pos], line, col)
