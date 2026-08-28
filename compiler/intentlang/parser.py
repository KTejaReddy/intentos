"""Recursive-descent parser for IntentLang with panic-mode error recovery.

Recovery strategy
-----------------
On a syntax error the parser reports the diagnostic, discards tokens up to
the next line boundary (``NEWLINE``), and resumes dispatching at the parent
block level. INDENT/DEDENT tokens act as structural anchors, so a recovered
line can never corrupt the block nesting of later statements. Parsing always
produces a (possibly partial) AST.
"""

from __future__ import annotations

from .ast import (
    ActionStmt, ApiRequestStmt, ApiResponseStmt, CreateStmt, DeployStmt,
    EventStmt, FieldStmt, ImportStmt, ListVal, Module, Node, QueryStmt, Ref,
    RuleStmt, UseStmt, WidgetStmt,
)
from .diagnostics import Diagnostics
from .keywords import CREATE_KINDS, WIDGET_KINDS
from .tokens import (    BOOLEAN, COMMA, DEDENT, EOF, EQUALS, IDENT, INDENT, KEYWORD, LBRACKET,
    NEWLINE, NUMBER, OPERATOR, PATH, RBRACKET, STRING, Token,
)

_STATEMENT_HEADS = frozenset({"import", "use", "deploy", "when", "create"})
_ACTION_HEADS = frozenset(
    {"navigate", "open", "call", "show", "set", "submit", "reload", "close"}
)


class Parser:
    def __init__(self, tokens: list[Token], filename: str = "<string>",
                 diagnostics: Diagnostics | None = None) -> None:
        self.tokens = tokens
        self.filename = filename
        self.diags = diagnostics if diagnostics is not None else Diagnostics()
        self.i = 0

    # -- token navigation --------------------------------------------------
    def peek(self, offset: int = 0) -> Token:
        j = self.i + offset
        if j >= len(self.tokens):
            return self.tokens[-1]
        return self.tokens[j]

    def advance(self) -> Token:
        tok = self.tokens[self.i]
        if tok.type != EOF:
            self.i += 1
        return tok

    def at_newline(self) -> bool:
        return self.peek().type in (NEWLINE, EOF)

    def skip_newlines(self) -> None:
        while self.peek().type == NEWLINE:
            self.advance()

    def error(self, message: str, tok: Token | None = None,
              code: str = "IL-P001") -> None:
        tok = tok or self.peek()
        self.diags.error(code, message, tok.line, tok.col, self.filename)

    # -- public ------------------------------------------------------------
    def parse_module(self) -> Module:
        module = Module().locate(1, 1)
        self.skip_newlines()
        while self.peek().type != EOF:
            tok = self.peek()
            if tok.type in (KEYWORD, IDENT) and tok.value.lower() in _STATEMENT_HEADS:
                self.parse_statement(module)
            elif tok.type == DEDENT:
                self.error("unexpected dedent", tok, "IL-P002")
                self.advance()
            else:
                self.error(
                    f"expected a statement ('Create', 'When', 'Use', 'Deploy', "
                    f"'Import'), found {tok.describe()}", tok,
                )
                self.synchronize()
            self.skip_newlines()
        return module

    def parse_statement(self, module: Module) -> None:
        head = self.peek().value.lower()
        if head == "import":
            module.statements.append(self.parse_import())
        elif head == "use":
            module.statements.append(self.parse_use())
        elif head == "deploy":
            module.statements.append(self.parse_deploy())
        elif head == "when":
            module.statements.append(self.parse_event(EventStmt(kind="when")))
        elif head == "create":
            module.statements.append(self.parse_create())
        else:  # pragma: no cover - guarded by caller
            self.error("IL-P003", f"unhandled statement {head!r}")

    # -- specific statements ------------------------------------------------
    def parse_import(self) -> ImportStmt:
        start = self.advance()  # 'import'
        tok = self.peek()
        if tok.type != STRING:
            self.error(f"Import expects a quoted path, found {tok.describe()}", tok)
            self.synchronize()
            return ImportStmt().locate(start.line, start.col)
        self.advance()
        return ImportStmt(path=tok.value).locate(start.line, start.col)

    def parse_use(self) -> UseStmt:
        start = self.advance()  # 'use'
        tok = self.peek()
        if tok.type not in (IDENT, KEYWORD):
            self.error(f"Use expects a plugin name, found {tok.describe()}", tok)
            self.synchronize()
            return UseStmt().locate(start.line, start.col)
        self.advance()
        return UseStmt(name=tok.value).locate(start.line, start.col)

    def parse_deploy(self) -> DeployStmt:
        start = self.advance()  # 'deploy'
        target = self.peek()
        if target.type not in (IDENT, KEYWORD):
            self.error(f"Deploy expects a target (Docker, GithubActions, Vercal...), found {target.describe()}", target)
            self.synchronize()
            return DeployStmt().locate(start.line, start.col)
        self.advance()
        props: dict = {}
        if self.peek().type in (KEYWORD, IDENT) and self.peek().value.lower() == "with":
            props = self.parse_with_block()
        elif self._begin_indented_block():
            if self.peek().type in (KEYWORD, IDENT) and self.peek().value.lower() == "with":
                props = self.parse_with_block()
            else:
                props = self.parse_prop_block_lines()
            self._end_indented_block()
        return DeployStmt(target=target.value, props=props).locate(start.line, start.col)

    def parse_create(self) -> CreateStmt:
        start = self.advance()  # 'create'
        kind_tok = self.peek()
        kind = kind_tok.value.lower()
        if kind not in CREATE_KINDS:
            self.error(
                f"unknown Create kind {kind_tok.value!r}; expected one of "
                f"{', '.join(sorted(CREATE_KINDS))}", kind_tok,
            )
            self.synchronize()
            return CreateStmt(kind="").locate(start.line, start.col)
        self.advance()

        name = self._parse_name(f"Create {kind}")
        stmt = CreateStmt(kind=kind, name=name).locate(start.line, start.col)
        if self.peek().type in (KEYWORD, IDENT) and self.peek().value.lower() == "with":
            stmt.props = self.parse_with_block()
        if self._begin_indented_block():
            self.parse_child_loop(stmt)
            self._end_indented_block()
        return stmt

    def parse_child_loop(self, stmt: CreateStmt) -> None:
        while self.peek().type not in (DEDENT, EOF):
            self.skip_newlines()
            if self.peek().type in (DEDENT, EOF):
                break
            self.parse_child(stmt)

    def parse_child(self, stmt: CreateStmt) -> None:
        tok = self.peek()
        if tok.type not in (KEYWORD, IDENT):
            self.error(f"unexpected {tok.describe()} in {stmt.kind} block", tok)
            self.synchronize()
            return
        value = tok.value.lower()
        if value == "add":
            stmt.children.append(self.parse_widget())
        elif value == "field":
            stmt.children.append(self.parse_field())
        elif value in ("when", "on"):
            stmt.children.append(self.parse_event(EventStmt(kind=value)))
        elif value == "request" and stmt.kind == "api":
            stmt.children.append(self.parse_request_block())
        elif value == "response" and stmt.kind == "api":
            stmt.children.append(self.parse_response_block())
        elif value == "query" and stmt.kind == "api":
            stmt.children.append(self.parse_query_block())
        elif value == "with":
            props = self.parse_with_block()
            merged = dict(stmt.props)
            merged.update(props)
            stmt.props = merged
        else:
            self.error(
                f"'{tok.value}' is not valid inside Create {stmt.kind}; expected "
                f"Add / Field / When / On / Request / Response / Query", tok,
            )
            self.synchronize()

    # -- widgets -------------------------------------------------------------
    def parse_widget(self) -> WidgetStmt:
        start = self.advance()  # 'add'
        kind_tok = self.peek()
        kind = kind_tok.value.lower()
        if kind not in WIDGET_KINDS:
            self.error(
                f"unknown widget kind {kind_tok.value!r}; expected one of "
                f"{', '.join(sorted(WIDGET_KINDS))}", kind_tok,
            )
            self.synchronize()
            return WidgetStmt().locate(start.line, start.col)
        self.advance()
        name_tok = self.peek()
        name = name_tok.value
        if name_tok.type == STRING:
            self.advance()
        elif name_tok.type in (IDENT, KEYWORD):
            self.advance()
        else:
            name = kind
            self.error(f"Add {kind} expects a name, found {name_tok.describe()}", name_tok)

        widget = WidgetStmt(kind=kind, name=name).locate(start.line, start.col)
        if self._begin_indented_block():
            while self.peek().type not in (DEDENT, EOF):
                self.skip_newlines()
                if self.peek().type in (DEDENT, EOF):
                    break
                t = self.peek()
                if t.type in (KEYWORD, IDENT) and t.value.lower() in ("when", "on"):
                    widget.children.append(self.parse_event(EventStmt(kind=t.value.lower())))
                elif t.type in (KEYWORD, IDENT) and t.value.lower() == "with":
                    widget.props.update(self.parse_with_block())
                elif t.type in (KEYWORD, IDENT) and t.value.lower() == "add" and kind == "form":
                    widget.children.append(self.parse_widget())
                else:
                    self.error(f"unexpected {t.describe()} in widget block", t)
                    self.synchronize()
            self._end_indented_block()
        return widget

    # -- fields --------------------------------------------------------------
    def parse_field(self) -> FieldStmt:
        start = self.advance()  # 'field'
        name_tok = self.peek()
        name = name_tok.value
        if name_tok.type not in (IDENT, KEYWORD):
            self.error(f"Field expects a name, found {name_tok.describe()}", name_tok)
            name = "unnamed"
        else:
            self.advance()
        field = FieldStmt(name=name).locate(start.line, start.col)
        # Inline props:  Field Name Type string Required true  (same line)
        if not self.at_newline():
            field.props = self.parse_props_until_newline()
        # Indented prop block (without 'With'):  Field Id\n  Type id\n  Required true
        if self._begin_indented_block():
            field.props.update(self.parse_prop_block_lines())
            self._end_indented_block()
        # Optional explicit With block merges on top.
        if self.peek().type in (KEYWORD, IDENT) and self.peek().value.lower() == "with":
            field.props.update(self.parse_with_block())
        return field

    def parse_prop_block_lines(self) -> dict:
        props: dict = {}
        while self.peek().type not in (DEDENT, EOF):
            self.skip_newlines()
            if self.peek().type in (DEDENT, EOF):
                break
            key_tok = self.peek()
            if key_tok.type not in (IDENT, KEYWORD):
                self.error(f"expected a property key, found {key_tok.describe()}", key_tok)
                self.synchronize()
                break
            self.advance()
            value = self.parse_value()
            if value is _MISSING:
                self.error(f"expected a value for property {key_tok.value!r}", self.peek())
            else:
                props[key_tok.value] = value
        return props

    def parse_props_until_newline(self) -> dict:
        props: dict = {}
        while not self.at_newline():
            key_tok = self.peek()
            if key_tok.type not in (IDENT, KEYWORD):
                self.error(f"expected a property key, found {key_tok.describe()}", key_tok)
                self.synchronize()
                return props
            key = key_tok.value
            self.advance()
            value = self.parse_value()
            if value is _MISSING:
                self.error(f"expected a value for property {key!r}", self.peek())
                continue
            props[key] = value
        return props

    # -- events & actions -----------------------------------------------------
    def parse_event(self, stmt: EventStmt) -> EventStmt:
        start = self.advance()  # 'when' | 'on'
        stmt.locate(start.line, start.col)
        phrase = self.parse_phrase_until_newline()
        stmt.event = phrase
        if not phrase:
            self.error("expected an event description after 'When'", start)
        if self._begin_indented_block():
            self.parse_event_children(stmt)
            self._end_indented_block()
        return stmt

    def parse_event_children(self, container: Node) -> None:
        while self.peek().type not in (DEDENT, EOF):
            self.skip_newlines()
            if self.peek().type in (DEDENT, EOF):
                break
            tok = self.peek()
            if tok.type not in (KEYWORD, IDENT):
                self.error(f"unexpected {tok.describe()} in event block", tok)
                self.synchronize()
                continue
            value = tok.value.lower()
            if value in ("when", "on"):
                container.children.append(self.parse_event(EventStmt(kind=value)))
            elif value in _ACTION_HEADS:
                container.children.append(self.parse_action())
            elif value == "status":
                # Response-style status line inside an On-block.
                stmt = ActionStmt(kind="status").locate(tok.line, tok.col)
                self.advance()
                num = self.peek()
                if num.type == NUMBER:
                    self.advance()
                    stmt.value = int(float(num.value))
                container.children.append(stmt)
            elif value == "show" and self.peek(1).type in (KEYWORD, IDENT) and self.peek(1).value.lower() == "toast":
                container.children.append(self.parse_action())
            else:
                self.error(f"unexpected {tok.describe()} in event block", tok)
                self.synchronize()

    def parse_phrase_until_newline(self) -> str:
        """Consume a human-readable phrase (identifiers/strings) to end of line."""
        parts: list[str] = []
        while not self.at_newline():
            tok = self.peek()
            if tok.type in (IDENT, KEYWORD, STRING, NUMBER, BOOLEAN):
                self.advance()
                parts.append(tok.value)
            elif tok.type in (EQUALS, OPERATOR):
                self.advance()
                parts.append(tok.value)
            else:
                break
        return " ".join(parts).strip().lower()

    def parse_action(self) -> ActionStmt:
        start = self.peek()
        head = self.advance().value.lower()
        stmt = ActionStmt().locate(start.line, start.col)

        if head == "navigate":
            self._expect_word("to", "Navigate To")
            stmt.kind = "navigate_to"
            stmt.target = self._parse_word_or_string("page name")
        elif head == "open":
            stmt.kind = "open"
            stmt.target = self._parse_word_or_string("page name")
        elif head == "call":
            self._expect_word("api", "Call Api")
            stmt.kind = "call_api"
            stmt.target = self._parse_word_or_string("api name")
            if self._begin_indented_block():
                while self.peek().type not in (DEDENT, EOF):
                    self.skip_newlines()
                    if self.peek().type in (DEDENT, EOF):
                        break
                    t = self.peek()
                    if t.type in (KEYWORD, IDENT) and t.value.lower() in ("on", "when"):
                        stmt.children.append(self.parse_event(EventStmt(kind=t.value.lower())))
                    else:
                        self.error(f"unexpected {t.describe()} in Call Api block", t)
                        self.synchronize()
                self._end_indented_block()
        elif head == "show":
            self._expect_word("toast", "Show Toast")
            stmt.kind = "show_toast"
            tok = self.peek()
            if tok.type == STRING:
                self.advance()
                stmt.value = tok.value
            else:
                self.error(f"Show Toast expects a quoted message, found {tok.describe()}", tok)
        elif head == "set":
            stmt.kind = "set"
            name_tok = self.peek()
            if name_tok.type in (IDENT, KEYWORD):
                self.advance()
                stmt.target = name_tok.value
            else:
                self.error(f"Set expects a variable name, found {name_tok.describe()}", name_tok)
            if self.peek().type == EQUALS:
                self.advance()
                stmt.value = self.parse_value()
                if stmt.value is _MISSING:
                    self.error("Set expects a value after '='", self.peek())
        elif head == "submit":
            stmt.kind = "submit"
            stmt.target = self._parse_word_or_string("form name")
        elif head == "reload":
            stmt.kind = "reload"
            stmt.target = self._parse_word_or_string("table name")
        elif head == "close":
            stmt.kind = "close"
            stmt.target = self._parse_word_or_string("panel name")
        else:  # pragma: no cover - guarded
            self.error(f"unknown action {head!r}", start)
        return stmt

    # -- api blocks -----------------------------------------------------------
    def parse_request_block(self) -> ApiRequestStmt:
        start = self.advance()  # 'request'
        stmt = ApiRequestStmt().locate(start.line, start.col)
        if self._begin_indented_block():
            while self.peek().type not in (DEDENT, EOF):
                self.skip_newlines()
                if self.peek().type in (DEDENT, EOF):
                    break
                t = self.peek()
                if t.type in (KEYWORD, IDENT) and t.value.lower() == "field":
                    stmt.fields.append(self.parse_field())
                else:
                    self.error(f"unexpected {t.describe()} in Request block", t)
                    self.synchronize()
            self._end_indented_block()
        return stmt

    def parse_response_block(self) -> ApiResponseStmt:
        start = self.advance()  # 'response'
        stmt = ApiResponseStmt().locate(start.line, start.col)
        if self._begin_indented_block():
            while self.peek().type not in (DEDENT, EOF):
                self.skip_newlines()
                if self.peek().type in (DEDENT, EOF):
                    break
                t = self.peek()
                if t.type in (KEYWORD, IDENT) and t.value.lower() == "status":
                    self.advance()
                    num = self.peek()
                    if num.type == NUMBER:
                        self.advance()
                        stmt.status = int(float(num.value))
                    else:
                        self.error(f"Status expects a number, found {num.describe()}", num)
                elif t.type in (KEYWORD, IDENT) and t.value.lower() == "body":
                    self.advance()
                    body = self._parse_body_value()
                    stmt.body = body if body is not _MISSING else None
                elif t.type in (KEYWORD, IDENT) and t.value.lower() in ("on", "when"):
                    stmt.children.append(self.parse_event(EventStmt(kind=t.value.lower())))
                else:
                    self.error(f"unexpected {t.describe()} in Response block", t)
                    self.synchronize()
            self._end_indented_block()
        return stmt

    def _parse_body_value(self):
        tok = self.peek()
        if tok.type == STRING:
            self.advance()
            return tok.value
        if tok.type in (IDENT, KEYWORD):
            self.advance()
            low = tok.value.lower()
            if low == "list":
                # list [of] Model | list Model
                nxt = self.peek()
                if nxt.type in (IDENT, KEYWORD) and nxt.value.lower() == "of":
                    self.advance()
                model = self.peek()
                if model.type in (IDENT, KEYWORD):
                    self.advance()
                    return ("list", Ref(model.value))
                return ("list", None)
            return Ref(tok.value)
        return _MISSING

    def parse_query_block(self) -> QueryStmt:
        start = self.advance()  # 'query'
        stmt = QueryStmt().locate(start.line, start.col)
        if self._begin_indented_block():
            while self.peek().type not in (DEDENT, EOF):
                self.skip_newlines()
                if self.peek().type in (DEDENT, EOF):
                    break
                t = self.peek()
                if t.type not in (KEYWORD, IDENT):
                    self.error(f"unexpected {t.describe()} in Query block", t)
                    self.synchronize()
                    continue
                low = t.value.lower()
                if low == "select":
                    self.advance()
                    sel = self.peek()
                    if sel.type in (IDENT, KEYWORD, PATH) or sel.value == "*":
                        self.advance()
                        stmt.select = sel.value
                    else:
                        stmt.select = "*"
                elif low == "from":
                    self.advance()
                    tbl = self.peek()
                    if tbl.type in (IDENT, KEYWORD):
                        self.advance()
                        stmt.table = tbl.value
                    else:
                        self.error(f"From expects a table name, found {tbl.describe()}", tbl)
                elif low == "where":
                    self.advance()
                    stmt.where = self.parse_phrase_until_newline()
                elif low == "join":
                    self.advance()
                    stmt.joins.append(self.parse_phrase_until_newline())
                elif low == "order":
                    self.advance()
                    self._expect_word("by", "Order By")
                    stmt.order = self.parse_phrase_until_newline()
                elif low == "limit":
                    self.advance()
                    num = self.peek()
                    if num.type == NUMBER:
                        self.advance()
                        stmt.limit = int(float(num.value))
                else:
                    self.error(f"unexpected {t.describe()} in Query block", t)
                    self.synchronize()
            self._end_indented_block()
        return stmt

    # -- shared helpers -------------------------------------------------------
    def parse_with_block(self) -> dict:
        self.advance()  # 'with'
        props: dict = {}
        if self.peek().type == NEWLINE and self.peek(1).type == INDENT:
            self.advance()
            self.advance()
            while self.peek().type not in (DEDENT, EOF):
                if self.at_newline():
                    self.advance()
                    continue
                key_tok = self.peek()
                if key_tok.type not in (IDENT, KEYWORD):
                    self.error(f"expected a property key, found {key_tok.describe()}", key_tok)
                    self.synchronize()
                    break
                self.advance()
                value = self.parse_value()
                if value is _MISSING:
                    self.error(f"expected a value for property {key_tok.value!r}", self.peek())
                else:
                    props[key_tok.value] = value
            self._end_indented_block()
        else:
            # Allow inline:  With Title "X" Theme dark
            props = self.parse_props_until_newline()
        return props

    def parse_value(self):
        tok = self.peek()
        if tok.type == STRING:
            self.advance()
            return tok.value
        if tok.type == NUMBER:
            self.advance()
            try:
                return int(tok.value) if "." not in tok.value and "e" not in tok.value.lower() else float(tok.value)
            except ValueError:
                return tok.value
        if tok.type == BOOLEAN:
            self.advance()
            return tok.value == "true"
        if tok.type == PATH:
            self.advance()
            return tok.value
        if tok.type == LBRACKET:
            self.advance()
            items: list = []
            while self.peek().type not in (RBRACKET, EOF):
                v = self.parse_value()
                if v is _MISSING:
                    self.error(f"expected a list item, found {self.peek().describe()}", self.peek())
                    self.advance()
                    continue
                items.append(v)
                if self.peek().type == COMMA:
                    self.advance()
            if self.peek().type == RBRACKET:
                self.advance()
            return ListVal(tuple(items))
        if tok.type in (IDENT, KEYWORD):
            self.advance()
            return Ref(tok.value)
        return _MISSING

    def _begin_indented_block(self) -> bool:
        if self.peek().type == NEWLINE and self.peek(1).type == INDENT:
            self.advance()
            self.advance()
            return True
        return False

    def _end_indented_block(self) -> None:
        while self.peek().type not in (DEDENT, EOF):
            self.synchronize()
        if self.peek().type == DEDENT:
            self.advance()

    def _parse_name(self, what: str) -> str:
        """Parse a (possibly multi-word) entity name; stops at keywords like
        'with', at a newline, or at an indentation boundary."""
        tok = self.peek()
        if tok.type == STRING:
            self.advance()
            return tok.value
        parts: list[str] = []
        while self.peek().type in (IDENT, KEYWORD):
            word = self.peek().value
            if word.lower() in ("with", "on", "when", "deploy"):
                break
            parts.append(word)
            self.advance()
        if not parts:
            self.error(f"{what} expects a name, found {tok.describe()}", tok)
            return "unnamed"
        return " ".join(parts)

    def _expect_word(self, word: str, context: str) -> None:
        tok = self.peek()
        if tok.type in (IDENT, KEYWORD) and tok.value.lower() == word:
            self.advance()
        else:
            self.error(f"{context} expects {word!r}, found {tok.describe()}", tok)

    def _parse_word_or_string(self, what: str) -> str:
        tok = self.peek()
        if tok.type == STRING:
            self.advance()
            return tok.value
        if tok.type in (IDENT, KEYWORD):
            self.advance()
            return tok.value
        self.error(f"expected {what}, found {tok.describe()}", tok)
        return ""

    def synchronize(self) -> None:
        """Panic-mode recovery: skip to the next line boundary."""
        while self.peek().type not in (NEWLINE, EOF):
            self.advance()
        if self.peek().type == NEWLINE:
            self.advance()


class _Missing:
    pass


_MISSING = _Missing()
