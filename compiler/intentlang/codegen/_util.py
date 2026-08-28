"""Shared helpers for code generators (string escaping, type maps, routing)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Optional

from ..ir import _camel, _pascal, _slug, _snake  # noqa: F401  (re-export)

if TYPE_CHECKING:  # pragma: no cover
    from .. import ir as I

INDENT = "    "


def indent(text: str, levels: int = 1) -> str:
    pad = INDENT * levels
    return "\n".join(pad + line if line.strip() else line for line in text.split("\n"))


def py_str(value: str) -> str:
    return json.dumps(str(value), ensure_ascii=True)


def js_str(value: str) -> str:
    return json.dumps(str(value), ensure_ascii=False)


def ts_quote(value: str) -> str:
    return json.dumps(str(value))


def dart_str(value: str) -> str:
    return json.dumps(str(value))


def java_str(value: str) -> str:
    return json.dumps(str(value))


def to_literal(value, language: str = "py") -> str:
    """Render a deterministic literal in the target language."""
    if value is None:
        return {"py": "None", "ts": "null", "dart": "null", "java": "null"}[language]
    if isinstance(value, bool):
        return {"py": str(value), "ts": str(value).lower(),
                "dart": str(value).lower(), "java": str(value).lower()}[language]
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, (list, tuple)):
        inner = ", ".join(to_literal(v, language) for v in value)
        return {"py": f"[{inner}]", "ts": f"[{inner}]",
                "dart": f"<dynamic>[{inner}]", "java": f"new Object[]{{{inner}}}"}[language]
    if isinstance(value, dict):
        pairs = ", ".join(f"{json.dumps(k)}: {to_literal(v, language)}" for k, v in value.items())
        return "{" + pairs + "}"
    return {"py": py_str(str(value)), "ts": js_str(str(value)),
            "dart": dart_str(str(value)), "java": java_str(str(value))}[language]


def py_type(ftype: str) -> str:
    t = {
        "string": "str", "text": "str", "email": "str", "password": "str",
        "url": "str", "phone": "str", "enum": "str", "date": "date",
        "datetime": "datetime", "int": "int", "integer": "int", "float": "float",
        "boolean": "bool", "bool": "bool", "id": "int", "money": "float",
        "json": "dict",
    }.get(ftype, "str")
    if t in ("date", "datetime"):
        return f"Optional[{t}]"
    return t


def ts_type(ftype: str) -> str:
    return {
        "string": "string", "text": "string", "email": "string",
        "password": "string", "url": "string", "phone": "string",
        "enum": "string", "date": "string", "datetime": "string",
        "int": "number", "integer": "number", "float": "number",
        "boolean": "boolean", "bool": "boolean", "id": "number",
        "money": "number", "json": "any",
    }.get(ftype, "string")


def dart_type(ftype: str) -> str:
    return {
        "string": "String", "text": "String", "email": "String",
        "password": "String", "url": "String", "phone": "String",
        "enum": "String", "date": "String", "datetime": "DateTime",
        "int": "int", "integer": "int", "float": "double",
        "boolean": "bool", "bool": "bool", "id": "int",
        "money": "double", "json": "Map<String, dynamic>",
    }.get(ftype, "String")


def sql_type(ftype: str, db: str) -> str:
    base = {
        "string": "VARCHAR(255)", "text": "TEXT", "email": "VARCHAR(255)",
        "password": "VARCHAR(255)", "url": "VARCHAR(512)", "phone": "VARCHAR(64)",
        "enum": "VARCHAR(64)", "date": "DATE", "datetime": "DATETIME",
        "int": "INTEGER", "integer": "INTEGER", "float": "REAL",
        "boolean": "BOOLEAN", "bool": "BOOLEAN", "id": "INTEGER",
        "money": "NUMERIC(12,2)", "json": "TEXT",
    }.get(ftype, "VARCHAR(255)")
    if db == "postgres":
        return {
            "text": "TEXT", "date": "DATE", "datetime": "TIMESTAMP",
            "int": "INTEGER", "integer": "INTEGER", "float": "DOUBLE PRECISION",
            "boolean": "BOOLEAN", "id": "SERIAL", "money": "NUMERIC(12,2)",
            "json": "JSONB", "string": "VARCHAR(255)", "email": "VARCHAR(255)",
            "password": "VARCHAR(255)", "url": "VARCHAR(512)", "phone": "VARCHAR(64)",
            "enum": "VARCHAR(64)",
        }.get(ftype, "VARCHAR(255)")
    if db == "mysql":
        return {
            "text": "TEXT", "date": "DATE", "datetime": "DATETIME",
            "int": "INT", "integer": "INT", "float": "DOUBLE",
            "boolean": "TINYINT(1)", "id": "INT AUTO_INCREMENT",
            "money": "DECIMAL(12,2)", "json": "JSON", "string": "VARCHAR(255)",
            "email": "VARCHAR(255)", "password": "VARCHAR(255)",
            "url": "VARCHAR(512)", "phone": "VARCHAR(64)", "enum": "VARCHAR(64)",
        }.get(ftype, "VARCHAR(255)")
    return base


def sql_default(ftype: str, db: str) -> str:
    if ftype == "boolean":
        return "0" if db in ("sqlite", "mysql") else "false"
    if ftype == "datetime" and db == "sqlite":
        return "CURRENT_TIMESTAMP"
    return ""


def path_params(route: str) -> list[str]:
    import re
    return re.findall(r"\{([A-Za-z0-9_]+)\}", route)


def route_express(route: str) -> str:
    import re
    return re.sub(r"\{([A-Za-z0-9_]+)\}", r":\1", route)


def route_fastapi(route: str) -> str:
    return route


def route_flutter(route: str) -> str:
    import re
    return re.sub(r"\{([A-Za-z0-9_]+)\}", r":\1", route)


def resolve_model(module: "I.ModuleIR", api: "I.Api") -> Optional["I.Model"]:
    """Deterministically pick the model an api operates on."""
    if api.query and api.query.table:
        return module.model_by_table(api.query.table)
    name = api.name.lower()
    stripped = name
    for prefix in ("get", "list", "fetch", "create", "add", "update", "edit",
                   "delete", "remove", "save", "register", "login", "logout",
                   "validate", "check", "search"):
        if name.startswith(prefix) and len(name) > len(prefix):
            stripped = name[len(prefix):]
            break
    for m in module.models:
        if m.name.lower() == stripped or m.slug == stripped:
            return m
    for m in module.models:
        if m.name.lower() == name or m.slug == name:
            return m
    return module.models[0] if module.models else None


def model_fields_non_id(model: "I.Model") -> list["I.Field"]:
    return [f for f in model.fields if f.ftype != "id"]


def response_body(api: "I.Api") -> Optional[tuple]:
    for resp in api.responses:
        if isinstance(resp.body, tuple):
            return resp.body
        if resp.body:
            return (resp.body, None)
    return None


def is_login(api: "I.Api") -> bool:
    return "login" in api.name.lower() or "signin" in api.name.lower()


def is_logout(api: "I.Api") -> bool:
    return "logout" in api.name.lower() or "signout" in api.name.lower()


def theme_color(theme: str) -> str:
    from ..optimizer import THEMES
    return THEMES.get(theme, THEMES["indigo"])[0]


def theme_light(theme: str) -> str:
    from ..optimizer import THEMES
    return THEMES.get(theme, THEMES["indigo"])[1]


def where_conditions(where: str, model: Optional["I.Model"]) -> list[str]:
    """Parse ``field op value`` triples into deterministic conditions."""
    import re
    out: list[tuple] = []
    for clause in [c.strip() for c in where.split(" and ") if c.strip()]:
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*(=|>|<|>=|<=|!=)\s*(.+)$", clause)
        if not m:
            out.append(("_raw", clause))
            continue
        field, op, raw = m.group(1), m.group(2), m.group(3).strip()
        out.append((field, op, raw))
    return out
