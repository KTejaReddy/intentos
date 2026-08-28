"""AST for IntentLang.

The AST is a faithful, lossless representation of the concrete syntax
(declarations, blocks, properties). The semantic analyzer lowers it to the
normalized IR in :mod:`intentlang.ir`.

Property values are plain Python literals (str/int/float/bool), :class:`Ref`
for identifier references, :class:`ListVal` for ``[a, b, c]`` lists, or
:data:`NULL` for ``null``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Ref:
    """An identifier reference used as a property value."""
    name: str


@dataclass(frozen=True)
class ListVal:
    values: tuple[Any, ...]

    def __iter__(self):
        return iter(self.values)


NULL = Ref("null")


class Node:
    line: int = 0
    col: int = 0

    def locate(self, line: int, col: int) -> "Node":
        self.line, self.col = line, col
        return self


@dataclass
class Module(Node):
    statements: list[Node] = field(default_factory=list)


@dataclass
class ImportStmt(Node):
    path: str = ""


@dataclass
class UseStmt(Node):
    name: str = ""


@dataclass
class DeployStmt(Node):
    target: str = ""
    props: dict[str, Any] = field(default_factory=dict)


@dataclass
class RuleStmt(Node):
    """Top-level ``When <event>`` rule with actions."""
    event: str = ""
    actions: list[Node] = field(default_factory=list)


@dataclass
class CreateStmt(Node):
    kind: str = ""          # application | page | database | model | api | role | job
    name: str = ""
    props: dict[str, Any] = field(default_factory=dict)
    children: list[Node] = field(default_factory=list)


@dataclass
class WidgetStmt(Node):
    kind: str = ""          # input | button | text | ... (see keywords.WIDGET_KINDS)
    name: str = ""
    props: dict[str, Any] = field(default_factory=dict)
    children: list[Node] = field(default_factory=list)  # EventStmt only


@dataclass
class FieldStmt(Node):
    name: str = ""
    props: dict[str, Any] = field(default_factory=dict)


@dataclass
class EventStmt(Node):
    """``When <phrase>`` or ``On <phrase>`` block."""
    kind: str = "when"      # when | on
    event: str = ""         # canonical lowercased phrase, e.g. "login succeeds"
    children: list[Node] = field(default_factory=list)  # ActionStmt / EventStmt


@dataclass
class ActionStmt(Node):
    kind: str = ""          # navigate_to | open | call_api | show_toast | set | submit | reload | close
    target: str = ""
    value: Any = None
    children: list[Node] = field(default_factory=list)  # EventStmt for call_api handlers


@dataclass
class ApiRequestStmt(Node):
    fields: list[FieldStmt] = field(default_factory=list)


@dataclass
class ApiResponseStmt(Node):
    status: int = 200
    body: Any = None        # Ref to model or ("list", Ref)
    children: list[Node] = field(default_factory=list)  # EventStmt


@dataclass
class QueryStmt(Node):
    select: str = "*"
    table: str = ""
    where: str = ""
    joins: list[str] = field(default_factory=list)
    order: str = ""
    limit: int | None = None
