"""SQL schema generator — produces deterministic schema.sql for the
configured database engine (sqlite / postgres / mysql)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from ..artifact import ArtifactSet
from ..diagnostics import Diagnostics
from ._util import sql_default, sql_type
from .base import Generator

if TYPE_CHECKING:  # pragma: no cover
    from .. import ir as I
    from ..compiler import CompileOptions


class SqlGenerator(Generator):
    name = "db/sql"

    def validate_options(self, options: "CompileOptions") -> Optional[str]:
        if options.database not in ("sqlite", "postgres", "mysql"):
            return f"unsupported database engine {options.database!r}"
        return None

    def generate(self, module: "I.ModuleIR", options: "CompileOptions",
                 artifacts: ArtifactSet, diags: Diagnostics) -> None:
        db = options.database
        lines = [
            f"-- IntentOS generated schema ({db})",
            f"-- application: {module.app.name}",
            "",
        ]
        for model in module.models:
            lines.extend(self._table(model, db))
            lines.append("")
        if not module.models:
            lines.append("-- no models declared")
        artifacts.add("db/schema.sql", "\n".join(lines), self.name)

    def _table(self, model: "I.Model", db: str) -> list[str]:
        cols: list[str] = []
        for f in model.fields:
            t = sql_type(f.ftype, db)
            col = f"    {f.name.lower()} {t}"
            if f.primary:
                if db == "sqlite":
                    col += " PRIMARY KEY" + (" AUTOINCREMENT" if f.ftype == "id" else "")
                elif db == "postgres":
                    col += " PRIMARY KEY" + (" GENERATED ALWAYS AS IDENTITY" if f.ftype == "id" else "")
                elif db == "mysql":
                    col += " PRIMARY KEY" + (" AUTO_INCREMENT" if f.ftype == "id" else "")
            if f.unique and not f.primary:
                col += " UNIQUE"
            if f.required and not f.primary:
                col += " NOT NULL"
            if f.default is not None:
                col += f" DEFAULT {self._default_literal(f, db)}"
            if f.reference:
                col += f" REFERENCES {f.reference[0].lower()} ({f.reference[1].lower()})"
            cols.append(col)
        table = [
            f"CREATE TABLE IF NOT EXISTS {model.table.lower()} (",
        ]
        table.extend(cols)
        table.append(");")
        return table

    @staticmethod
    def _default_literal(f: "I.Field", db: str) -> str:
        v = f.default
        if isinstance(v, bool):
            return "1" if (v and db in ("sqlite", "mysql")) else (str(v).lower())
        if isinstance(v, (int, float)):
            return repr(v)
        if v is None:
            return "NULL"
        return f"'{str(v)}'"
