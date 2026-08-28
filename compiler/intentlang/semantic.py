"""Semantic Analyzer.

Two-pass lowering of the AST into IR:

* Pass 1 (``_declare``) registers every declaration (application, pages,
  models, databases, apis, roles) so references may point at declarations
  that appear *later* in the file.
* Pass 2 (``_populate``) fills bodies (widgets, fields, queries, responses,
  events) and resolves every reference.

Property keys are normalized to lowercase at the IR boundary so all
consumers (semantic checks and code generators) read ``type``, ``route``,
``method``, ``label`` ... regardless of source casing.
"""

from __future__ import annotations

from typing import Any, Optional

from . import ir as I
from .ast import (
    ActionStmt, ApiRequestStmt, ApiResponseStmt, CreateStmt, DeployStmt,
    EventStmt, FieldStmt, ImportStmt, ListVal, Module, QueryStmt, Ref, RuleStmt,
    UseStmt, WidgetStmt,
)
from .diagnostics import Diagnostics
from .ir import _slug

AUTH_ROLES = {"public", "user", "admin"}
EVENT_ALIASES = {
    "clicked": "clicked", "click": "clicked",
    "submit": "submitted", "submitted": "submitted",
    "form valid": "submitted", "form submitted": "submitted",
    "login succeeds": "login_succeeded", "login success": "login_succeeded",
    "login fails": "login_failed", "login failure": "login_failed",
    "load": "loaded", "on load": "loaded", "page load": "loaded",
    "change": "changed", "changed": "changed",
    "logout": "logout", "logout clicked": "logout",
    "success": "success", "on success": "success",
    "failure": "failure", "on failure": "failure", "error": "failure",
    "save": "submitted", "save clicked": "submitted",
    "open": "opened", "opened": "opened",
}


def canonical_event(phrase: str) -> str:
    return EVENT_ALIASES.get(phrase.strip().lower(), phrase.strip().lower())


class SemanticAnalyzer:
    def __init__(self, filename: str = "<string>",
                 diagnostics: Diagnostics | None = None) -> None:
        self.filename = filename
        self.diags = diagnostics if diagnostics is not None else Diagnostics()
        self.module = I.ModuleIR()
        self._pages: dict[str, I.Page] = {}
        self._models: dict[str, I.Model] = {}
        self._databases: dict[str, I.Database] = {}
        self._apis: dict[str, I.Api] = {}
        self._roles: dict[str, I.Role] = {
            "public": I.Role("public"), "user": I.Role("user"),
            "admin": I.Role("admin"),
        }  # keys are lowercase
        self._routes: dict[str, str] = {}
        self._api_routes: dict[tuple[str, str], str] = {}

    @staticmethod
    def _role_key(name: str) -> str:
        return name.strip().lower()

    # -- entry ---------------------------------------------------------------
    def analyze(self, ast: Module) -> I.ModuleIR:
        for stmt in ast.statements:
            if isinstance(stmt, ImportStmt):
                if stmt.path not in self.module.imports:
                    self.module.imports.append(stmt.path)
            elif isinstance(stmt, UseStmt):
                if stmt.name and stmt.name not in self.module.plugins:
                    self.module.plugins.append(stmt.name)
            elif isinstance(stmt, DeployStmt):
                self.module.deploys.append(I.DeployTarget(
                    target=stmt.target, props=self._literals(stmt.props),
                    line=stmt.line, col=stmt.col,
                ))
            elif isinstance(stmt, CreateStmt):
                self._declare(stmt)

        for stmt in ast.statements:
            if isinstance(stmt, CreateStmt):
                self._populate(stmt)
            elif isinstance(stmt, (RuleStmt, EventStmt)):
                ev = self._to_event(stmt)
                if ev is not None:
                    self.module.rules.append(ev)

        self._post_checks()
        self.module.name = self.module.app.name or "untitled"
        return self.module

    # -- value helpers ----------------------------------------------------------
    def _literals(self, props: dict[str, Any]) -> dict[str, Any]:
        return {k.lower(): self._value(v) for k, v in props.items()}

    def _value(self, v: Any) -> Any:
        if isinstance(v, Ref):
            return v.name if v.name != "null" else None
        if isinstance(v, ListVal):
            return [self._value(x) for x in v.values]
        return v

    # -- pass 1: declarations -----------------------------------------------------
    def _declare(self, stmt: CreateStmt) -> None:
        kind, name = stmt.kind, stmt.name
        props = self._literals(stmt.props)
        if kind == "application":
            self._declare_application(stmt.name, props)
        elif kind == "page":
            self._declare_page(stmt, props)
        elif kind in ("model", "collection"):
            self._declare_model(stmt, props)
        elif kind == "database":
            self._declare_database(stmt, props)
        elif kind == "api":
            self._declare_api(stmt, props)
        elif kind == "role":
            self._declare_role(stmt, props)
        elif kind == "job":
            self.diags.info("IL-S010", f"job '{name}' recorded; jobs run on schedule in deployment",
                            stmt.line, stmt.col, self.filename)
        else:
            self.diags.warning("IL-S011", f"unknown Create kind {kind!r} ignored",
                               stmt.line, stmt.col, self.filename)

    def _declare_application(self, name: str, props: dict) -> None:
        app = self.module.app
        if not app.name or app.name == "untitled":
            app.name = name or "untitled"
        app.title = str(props.get("title") or props.get("label") or app.name)
        app.description = str(props.get("description") or "")
        app.theme = str(props.get("theme") or app.theme)
        app.language = str(props.get("language") or app.language)
        fe = str(props.get("frontend") or "").lower()
        be = str(props.get("backend") or "").lower()
        db = str(props.get("database") or "").lower()
        if fe:
            app.frontend = "nextjs" if fe in ("next", "nextjs") else fe
        if be:
            app.backend = "express" if be in ("node", "express") else \
                ("springboot" if be in ("spring", "springboot") else be)
        if db:
            app.database = "postgres" if db in ("postgres", "postgresql") else db

    def _declare_page(self, stmt: CreateStmt, props: dict) -> None:
        if stmt.name in self._pages:
            self.diags.error("IL-S020", f"duplicate page '{stmt.name}'",
                             stmt.line, stmt.col, self.filename)
            return
        route = str(props.get("route") or ("/" + _slug(stmt.name)))
        if not route.startswith("/"):
            route = "/" + route
        if route in self._routes:
            self.diags.error("IL-S021", f"duplicate route {route!r} (already used by {self._routes[route]!r})",
                             stmt.line, stmt.col, self.filename)
        self._routes[route] = stmt.name
        page = I.Page(name=stmt.name, route=route, line=stmt.line, col=stmt.col)
        page.layout = str(props.get("layout") or "default")
        page.title = str(props.get("title") or stmt.name)
        self._pages[stmt.name] = page
        self.module.pages.append(page)

    def _declare_model(self, stmt: CreateStmt, props: dict) -> None:
        if stmt.name in self._models:
            self.diags.error("IL-S022", f"duplicate model '{stmt.name}'",
                             stmt.line, stmt.col, self.filename)
            return
        model = I.Model(name=stmt.name, line=stmt.line, col=stmt.col)
        model.table = str(props.get("table") or _slug(stmt.name))
        self._models[stmt.name] = model
        self.module.models.append(model)

    def _declare_database(self, stmt: CreateStmt, props: dict) -> None:
        if stmt.name in self._databases:
            self.diags.error("IL-S023", f"duplicate database '{stmt.name}'",
                             stmt.line, stmt.col, self.filename)
            return
        engine = str(props.get("engine") or "sqlite").lower()
        engine = "postgres" if engine in ("postgres", "postgresql") else \
            ("mysql" if engine == "mysql" else engine)
        db = I.Database(name=stmt.name, engine=engine, line=stmt.line, col=stmt.col)
        self._databases[stmt.name] = db
        self.module.databases.append(db)
        self.module.app.database = engine

    def _declare_api(self, stmt: CreateStmt, props: dict) -> None:
        if stmt.name in self._apis:
            self.diags.error("IL-S024", f"duplicate api '{stmt.name}'",
                             stmt.line, stmt.col, self.filename)
            return
        api = I.Api(name=stmt.name, line=stmt.line, col=stmt.col)
        method = str(props.get("method") or "GET").upper()
        api.method = method if method in ("GET", "POST", "PUT", "PATCH", "DELETE") else "GET"
        route = str(props.get("route") or ("/api/" + _slug(stmt.name)))
        if not route.startswith("/"):
            route = "/" + route
        api.route = route
        api.auth = str(props.get("auth") or "public").lower()
        if api.auth not in AUTH_ROLES and self._role_key(api.auth) not in self._roles:
            self.diags.error("IL-S025",
                             f"auth role '{api.auth}' is not defined (create it with 'Create Role {api.auth}' or use public/user/admin)",
                             stmt.line, stmt.col, self.filename)
        conflict_key = (api.method, route)
        if conflict_key in self._api_routes:
            self.diags.error("IL-S026",
                             f"duplicate route {api.method} {route!r} (already used by {self._api_routes[conflict_key]!r})",
                             stmt.line, stmt.col, self.filename)
        self._api_routes[conflict_key] = stmt.name
        self._apis[stmt.name] = api
        self.module.apis.append(api)

    def _declare_role(self, stmt: CreateStmt, props: dict) -> None:
        if self._role_key(stmt.name) in AUTH_ROLES:
            self.diags.warning("IL-S027", f"role '{stmt.name}' is implicit and cannot be redefined",
                               stmt.line, stmt.col, self.filename)
            return
        role = I.Role(name=stmt.name, line=stmt.line, col=stmt.col)
        perms = props.get("permissions")
        if isinstance(perms, list):
            role.permissions = [str(p) for p in perms]
        self._roles[self._role_key(stmt.name)] = role
        self.module.roles.append(role)

    # -- pass 2: bodies -----------------------------------------------------------
    def _populate(self, stmt: CreateStmt) -> None:
        kind, name = stmt.kind, stmt.name
        if kind == "page":
            page = self._pages.get(name)
            if page is None:
                return
            for child in stmt.children:
                if isinstance(child, WidgetStmt):
                    page.widgets.append(self._analyze_widget(child))
                elif isinstance(child, EventStmt):
                    ev = self._to_event(child)
                    if ev is not None:
                        page.events.append(ev)
        elif kind in ("model", "collection"):
            model = self._models.get(name)
            if model is None:
                return
            for child in stmt.children:
                if isinstance(child, FieldStmt):
                    model.fields.append(self._analyze_field(child))
        elif kind == "api":
            api = self._apis.get(name)
            if api is None:
                return
            for child in stmt.children:
                if isinstance(child, ApiRequestStmt):
                    for f in child.fields:
                        api.request_fields.append(self._analyze_field(f))
                elif isinstance(child, ApiResponseStmt):
                    api.responses.append(self._analyze_response(child))
                elif isinstance(child, QueryStmt):
                    api.query = I.Query(select=child.select or "*",
                                        table=child.table or "",
                                        where=child.where,
                                        joins=list(child.joins),
                                        order=child.order, limit=child.limit,
                                        line=child.line, col=child.col)
                elif isinstance(child, EventStmt):
                    ev = self._to_event(child)
                    if ev is not None:
                        api.events.append(ev)
                elif isinstance(child, FieldStmt):
                    api.request_fields.append(self._analyze_field(child))
            if not api.responses:
                api.responses.append(I.ResponseSpec(status=200))

    def _analyze_widget(self, stmt: WidgetStmt) -> I.Widget:
        w = I.Widget(kind=stmt.kind, name=stmt.name, line=stmt.line, col=stmt.col)
        w.props = self._literals(stmt.props)
        for child in stmt.children:
            if isinstance(child, EventStmt):
                ev = self._to_event(child)
                if ev is not None:
                    w.events.append(ev)
            elif isinstance(child, WidgetStmt):
                w.children.append(self._analyze_widget(child))
        return w

    def _analyze_field(self, stmt: FieldStmt) -> I.Field:
        props = self._literals(stmt.props)
        f = I.Field(name=stmt.name, line=stmt.line, col=stmt.col)
        ftype = str(props.get("type") or "string").lower()
        ftype = {"integer": "int", "bool": "boolean"}.get(ftype, ftype)
        if ftype not in I.TYPE_MAP:
            self.diags.error("IL-S028",
                             f"unknown field type {ftype!r}; expected one of {', '.join(sorted(I.TYPE_MAP))}",
                             stmt.line, stmt.col, self.filename)
        f.ftype = ftype
        f.required = bool(props.get("required") or f.ftype == "id")
        f.unique = bool(props.get("unique"))
        f.primary = bool(props.get("primary") or f.ftype == "id")
        f.default = props.get("default")
        ref = props.get("reference")
        if ref:
            parts = str(ref).split(".")
            if len(parts) == 2:
                f.reference = (parts[0], parts[1])
            else:
                self.diags.error("IL-S029", f"reference must be 'Model.Field', got {ref!r}",
                                 stmt.line, stmt.col, self.filename)
        return f

    def _analyze_response(self, stmt: ApiResponseStmt) -> I.ResponseSpec:
        spec = I.ResponseSpec(status=stmt.status, line=stmt.line, col=stmt.col)
        if isinstance(stmt.body, Ref):
            spec.body = stmt.body.name
        elif isinstance(stmt.body, tuple):
            spec.body = ("list", stmt.body[1].name if isinstance(stmt.body[1], Ref) else None)
        elif isinstance(stmt.body, str):
            spec.body = stmt.body
        for child in stmt.children:
            if isinstance(child, EventStmt):
                ev = self._to_event(child)
                if ev is not None:
                    spec.handlers.append(ev)
        return spec

    # -- events & actions --------------------------------------------------------
    def _to_event(self, stmt: EventStmt) -> Optional[I.Event]:
        ev = I.Event(event=canonical_event(stmt.event), line=stmt.line, col=stmt.col)
        for child in stmt.children:
            if isinstance(child, ActionStmt):
                act = self._to_action(child)
                if act is not None:
                    ev.actions.append(act)
            elif isinstance(child, EventStmt):
                nested = self._to_event(child)
                if nested is not None:
                    ev.actions.append(I.Action(kind="on", target=nested.event,
                                               handlers=[nested],
                                               line=child.line, col=child.col))
        return ev

    def _to_action(self, stmt: ActionStmt) -> Optional[I.Action]:
        act = I.Action(kind=stmt.kind, target=stmt.target, value=stmt.value,
                       line=stmt.line, col=stmt.col)
        if stmt.kind in ("navigate_to", "open") and stmt.target:
            if not (self._pages.get(stmt.target) or self.module.page_by_name(stmt.target)):
                self.diags.error("IL-S040",
                                 f"'{stmt.kind}' references unknown page '{stmt.target}'",
                                 stmt.line, stmt.col, self.filename)
        elif stmt.kind == "call_api" and stmt.target:
            if not (self._apis.get(stmt.target) or self.module.api_by_name(stmt.target)):
                self.diags.error("IL-S041", f"'Call Api' references unknown api '{stmt.target}'",
                                 stmt.line, stmt.col, self.filename)
            for child in stmt.children:
                if isinstance(child, EventStmt):
                    nested = self._to_event(child)
                    if nested is not None:
                        act.handlers.append(nested)
        elif stmt.kind == "status":
            if stmt.value is None:
                self.diags.error("IL-S061", "HTTP status code must be an integer, got empty", stmt.line, stmt.col, self.filename)
            else:
                try:
                    code = int(stmt.value)
                    if not (100 <= code <= 599):
                        self.diags.error("IL-S060", f"HTTP status code {code} out of range (100-599)", stmt.line, stmt.col, self.filename)
                except (ValueError, TypeError):
                    self.diags.error("IL-S061", f"HTTP status code must be an integer, got '{stmt.value}'", stmt.line, stmt.col, self.filename)
        return act

    # -- post checks --------------------------------------------------------------
    def _post_checks(self) -> None:
        for model in self.module.models:
            seen: dict[str, str] = {}
            for f in model.fields:
                if f.name.lower() in seen:
                    self.diags.error("IL-S052",
                                     f"duplicate field '{f.name}' in model '{model.name}' (first at line {seen[f.name.lower()]})",
                                     f.line, f.col, self.filename)
                seen[f.name.lower()] = str(f.line)
                if f.reference:
                    tm = self._models.get(f.reference[0])
                    if tm is None:
                        self.diags.error("IL-S050",
                                         f"field '{model.name}.{f.name}' references unknown model '{f.reference[0]}'",
                                         f.line, f.col, self.filename)
                    elif f.reference[1] != "id" and not any(x.name == f.reference[1] for x in tm.fields):
                        self.diags.error("IL-S051",
                                         f"field '{model.name}.{f.name}' references unknown field '{f.reference[0]}.{f.reference[1]}'",
                                         f.line, f.col, self.filename)
        if not self.module.pages and self.module.app.name != "untitled":
            self.diags.warning("IL-S060", "no pages defined; the generated app will be empty",
                               0, 0, self.filename)
