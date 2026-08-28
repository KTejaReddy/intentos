"""Intermediate Representation (IR).

The semantic analyzer lowers the AST into this normalized model. The IR is
the contract between analysis and code generation:

* Deterministic — ``to_dict`` emits sorted keys, so the same program always
  hashes to the same fingerprint.
* Versionable — ``IR_FORMAT_VERSION`` bumps on incompatible changes.
* Serializable — the whole IR round-trips through JSON, which powers the
  incremental compiler cache and the IDE's data endpoints.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Optional

IR_FORMAT_VERSION = 1


def _slug(name: str) -> str:
    """Deterministic kebab-case slug."""
    out: list[str] = []
    prev_dash = False
    for ch in name.lower():
        if ch.isalnum():
            out.append(ch)
            prev_dash = False
        elif not prev_dash and out:
            out.append("-")
            prev_dash = True
    return "".join(out).strip("-")


def _snake(name: str) -> str:
    return _slug(name).replace("-", "_")


def _pascal(name: str) -> str:
    return "".join(part[:1].upper() + part[1:] for part in _slug(name).split("-"))


def _camel(name: str) -> str:
    s = _pascal(name)
    return s[:1].lower() + s[1:] if s else s


# Type -> (sql_type, python_type, js_type, ts_type)
TYPE_MAP: dict[str, dict[str, str]] = {
    "string":   {"sql": "VARCHAR(255)",  "py": "str",  "ts": "string"},
    "text":     {"sql": "TEXT",          "py": "str",  "ts": "string"},
    "int":      {"sql": "INTEGER",       "py": "int",  "ts": "number"},
    "integer":  {"sql": "INTEGER",       "py": "int",  "ts": "number"},
    "float":    {"sql": "REAL",          "py": "float", "ts": "number"},
    "boolean":  {"sql": "BOOLEAN",       "py": "bool", "ts": "boolean"},
    "bool":     {"sql": "BOOLEAN",       "py": "bool", "ts": "boolean"},
    "date":     {"sql": "DATE",          "py": "date", "ts": "string"},
    "datetime": {"sql": "DATETIME",      "py": "datetime", "ts": "string"},
    "email":    {"sql": "VARCHAR(255)",  "py": "str",  "ts": "string"},
    "password": {"sql": "VARCHAR(255)",  "py": "str",  "ts": "string"},
    "id":       {"sql": "INTEGER",       "py": "int",  "ts": "number"},
    "money":    {"sql": "NUMERIC(12,2)", "py": "float", "ts": "number"},
    "url":      {"sql": "VARCHAR(512)",  "py": "str",  "ts": "string"},
    "phone":    {"sql": "VARCHAR(64)",   "py": "str",  "ts": "string"},
    "enum":     {"sql": "VARCHAR(64)",   "py": "str",  "ts": "string"},
    "json":     {"sql": "TEXT",          "py": "dict", "ts": "any"},
}


def canonical_json(obj: Any) -> str:
    def _norm(v: Any):
        if isinstance(v, dict):
            return {k: _norm(val) for k, val in sorted(v.items())}
        if isinstance(v, (list, tuple)):
            return [_norm(x) for x in v]
        return v
    return json.dumps(_norm(obj), sort_keys=True, separators=(",", ":"))


def fingerprint(obj: Any) -> str:
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


@dataclass
class IRNode:
    line: int = 0
    col: int = 0

    def to_dict(self) -> dict:
        import dataclasses
        d = dataclasses.asdict(self)
        d.pop("line", None)
        d.pop("col", None)
        return d


@dataclass
class Action(IRNode):
    kind: str = ""          # navigate_to | open | call_api | show_toast | set | submit | reload
    target: str = ""
    value: Any = None
    handlers: list["Event"] = field(default_factory=list)  # for call_api

    def to_dict(self) -> dict:
        d = {"kind": self.kind, "target": self.target}
        if self.value is not None:
            d["value"] = self.value
        if self.handlers:
            d["handlers"] = [h.to_dict() for h in self.handlers]
        return d


@dataclass
class Event(IRNode):
    event: str = ""         # canonical phrase, e.g. "clicked", "login succeeds"
    actions: list[Action] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"event": self.event, "actions": [a.to_dict() for a in self.actions]}


@dataclass
class Widget(IRNode):
    kind: str = ""
    name: str = ""
    props: dict[str, Any] = field(default_factory=dict)
    events: list[Event] = field(default_factory=list)
    children: list["Widget"] = field(default_factory=list)

    @property
    def slug(self) -> str:
        return _slug(self.name)

    def to_dict(self) -> dict:
        d = {"kind": self.kind, "name": self.name, "props": self.props}
        if self.events:
            d["events"] = [e.to_dict() for e in self.events]
        if self.children:
            d["children"] = [c.to_dict() for c in self.children]
        return d


@dataclass
class Page(IRNode):
    name: str = ""
    route: str = ""
    layout: str = "default"
    title: str = ""
    widgets: list[Widget] = field(default_factory=list)
    events: list[Event] = field(default_factory=list)

    @property
    def slug(self) -> str:
        return _slug(self.name)

    def to_dict(self) -> dict:
        return {
            "name": self.name, "slug": self.slug, "route": self.route,
            "layout": self.layout, "title": self.title,
            "widgets": [w.to_dict() for w in self.widgets],
            "events": [e.to_dict() for e in self.events],
        }


@dataclass
class Field(IRNode):
    name: str = ""
    ftype: str = "string"
    required: bool = False
    unique: bool = False
    primary: bool = False
    default: Any = None
    reference: Optional[tuple[str, str]] = None  # (model, field)

    @property
    def slug(self) -> str:
        return _slug(self.name)

    @property
    def pascal(self) -> str:
        return _pascal(self.name)

    def to_dict(self) -> dict:
        d = {"name": self.name, "type": self.ftype, "required": self.required,
             "unique": self.unique, "primary": self.primary}
        if self.default is not None:
            d["default"] = self.default
        if self.reference:
            d["reference"] = list(self.reference)
        return d


@dataclass
class Model(IRNode):
    name: str = ""
    table: str = ""
    fields: list[Field] = field(default_factory=list)

    @property
    def slug(self) -> str:
        return _snake(self.name)

    @property
    def pascal(self) -> str:
        return _pascal(self.name)

    def to_dict(self) -> dict:
        return {"name": self.name, "table": self.table,
                "fields": [f.to_dict() for f in self.fields]}


@dataclass
class Database(IRNode):
    name: str = ""
    engine: str = "sqlite"

    def to_dict(self) -> dict:
        return {"name": self.name, "engine": self.engine}


@dataclass
class ResponseSpec(IRNode):
    status: int = 200
    body: Any = None        # Ref(name) or ("list", name or None)
    handlers: list[Event] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = {"status": self.status}
        if isinstance(self.body, tuple):
            d["body"] = {"list_of": self.body[1]}
        elif self.body is not None:
            d["body"] = self.body
        if self.handlers:
            d["handlers"] = [h.to_dict() for h in self.handlers]
        return d


@dataclass
class Query(IRNode):
    select: str = "*"
    table: str = ""
    where: str = ""
    joins: list[str] = field(default_factory=list)
    order: str = ""
    limit: Optional[int] = None

    def to_dict(self) -> dict:
        d = {"select": self.select, "table": self.table}
        if self.where:
            d["where"] = self.where
        if self.joins:
            d["joins"] = self.joins
        if self.order:
            d["order"] = self.order
        if self.limit is not None:
            d["limit"] = self.limit
        return d


@dataclass
class Api(IRNode):
    name: str = ""
    method: str = "GET"
    route: str = ""
    auth: str = "public"
    request_fields: list[Field] = field(default_factory=list)
    query: Optional[Query] = None
    responses: list[ResponseSpec] = field(default_factory=list)
    events: list[Event] = field(default_factory=list)

    @property
    def slug(self) -> str:
        return _snake(self.name)

    @property
    def pascal(self) -> str:
        return _pascal(self.name)

    def to_dict(self) -> dict:
        d = {"name": self.name, "method": self.method, "route": self.route,
             "auth": self.auth}
        if self.request_fields:
            d["request_fields"] = [f.to_dict() for f in self.request_fields]
        if self.query:
            d["query"] = self.query.to_dict()
        if self.responses:
            d["responses"] = [r.to_dict() for r in self.responses]
        if self.events:
            d["events"] = [e.to_dict() for e in self.events]
        return d


@dataclass
class Role(IRNode):
    name: str = ""
    permissions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"name": self.name, "permissions": self.permissions}


@dataclass
class Application(IRNode):
    name: str = ""
    title: str = ""
    description: str = ""
    theme: str = "indigo"
    language: str = "typescript"
    frontend: str = "react"
    backend: str = "fastapi"
    database: str = "sqlite"

    def to_dict(self) -> dict:
        return {
            "name": self.name, "title": self.title, "description": self.description,
            "theme": self.theme, "language": self.language, "frontend": self.frontend,
            "backend": self.backend, "database": self.database,
        }


@dataclass
class DeployTarget(IRNode):
    target: str = ""
    props: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"target": self.target, "props": self.props}


@dataclass
class ModuleIR:
    """The compiled IR for one application module."""
    name: str = ""
    app: Application = field(default_factory=Application)
    pages: list[Page] = field(default_factory=list)
    models: list[Model] = field(default_factory=list)
    databases: list[Database] = field(default_factory=list)
    apis: list[Api] = field(default_factory=list)
    roles: list[Role] = field(default_factory=list)
    rules: list[Event] = field(default_factory=list)
    deploys: list[DeployTarget] = field(default_factory=list)
    plugins: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    format_version: int = IR_FORMAT_VERSION

    # -- derivation -------------------------------------------------------
    def all_models(self) -> list[Model]:
        return self.models

    def model_by_table(self, table: str) -> Optional[Model]:
        for m in self.models:
            if m.table == table or m.slug == table:
                return m
        return None

    def api_by_name(self, name: str) -> Optional[Api]:
        for a in self.apis:
            if a.name.lower() == name.lower():
                return a
        return None

    def page_by_name(self, name: str) -> Optional[Page]:
        for p in self.pages:
            if p.name.lower() == name.lower():
                return p
        return None

    def resolve_ref(self, ref: Any) -> str:
        """Turn an AST Ref/ListVal into a JSON-safe value."""
        if isinstance(ref, (list, tuple)):
            return [self.resolve_ref(x) for x in ref]
        if isinstance(ref, dict):
            return {k: self.resolve_ref(v) for k, v in ref.items()}
        if isinstance(ref, str) and ref.startswith("$"):
            name = ref[1:]
            if self.model_by_table(name) or any(m.name == name for m in self.models):
                return {"model": name}
            if self.api_by_name(name):
                return {"api": name}
            if self.page_by_name(name):
                return {"page": name}
        return ref

    def to_dict(self) -> dict:
        return {
            "format_version": self.format_version,
            "name": self.name,
            "app": self.app.to_dict(),
            "pages": [p.to_dict() for p in self.pages],
            "models": [m.to_dict() for m in self.models],
            "databases": [d.to_dict() for d in self.databases],
            "apis": [a.to_dict() for a in self.apis],
            "roles": [r.to_dict() for r in self.roles],
            "rules": [r.to_dict() for r in self.rules],
            "deploys": [d.to_dict() for d in self.deploys],
            "plugins": sorted(self.plugins),
            "imports": self.imports,
        }

    def fingerprint(self) -> str:
        return fingerprint(self.to_dict())

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)
