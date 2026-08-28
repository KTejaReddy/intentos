"""FastAPI backend generator.

Produces a complete, runnable FastAPI project:

    backend/
      requirements.txt      pinned runtime deps
      main.py               app factory, CORS, routers
      database.py           SQLAlchemy engine / session
      security.py           signed bearer tokens (stdlib hmac)
      models.py             SQLAlchemy models from the IR
      schemas.py            pydantic v2 schemas
      seed.py               deterministic seed data
      routers/<slug>.py     one router per Api
      run.sh                launch script

Runs with:  pip install -r requirements.txt && uvicorn main:app --reload
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Optional

from ..artifact import ArtifactSet
from ..diagnostics import Diagnostics
from ._util import (
    indent, is_login, is_logout, py_str, py_type, resolve_model, route_fastapi,
    where_conditions,
)
from .base import Generator

if TYPE_CHECKING:  # pragma: no cover
    from .. import ir as I
    from ..compiler import CompileOptions

DB_URLS = {
    "sqlite": "sqlite:///./app.db",
    "postgres": "postgresql+psycopg2://postgres:postgres@localhost:5432/app",
    "mysql": "mysql+pymysql://root:@localhost:3306/app",
}
DB_DEPS = {"sqlite": "", "postgres": "psycopg2-binary", "mysql": "pymysql"}

_SA_TYPES = {
    "string": "String(255)", "email": "String(255)", "password": "String(255)",
    "url": "String(512)", "phone": "String(64)", "enum": "String(64)",
    "text": "Text", "date": "Date", "datetime": "DateTime",
    "int": "Integer", "integer": "Integer", "id": "Integer", "float": "Float",
    "boolean": "Boolean", "bool": "Boolean", "money": "Numeric(12, 2)",
    "json": "JSON",
}


class FastApiGenerator(Generator):
    name = "backend/fastapi"

    def validate_options(self, options: "CompileOptions") -> Optional[str]:
        if options.backend not in ("fastapi", "python"):
            return "options.backend must be 'fastapi'"
        return None

    def generate(self, module: "I.ModuleIR", options: "CompileOptions",
                 artifacts: ArtifactSet, diags: Diagnostics) -> None:
        self.art = artifacts
        self.module = module
        db = options.database
        self._requirements(db)
        self._database(db)
        self._security()
        self._models()
        self._schemas()
        self._seed()
        for api in module.apis:
            self._router(api)
        self._main()
        self._run_sh()

    # ------------------------------------------------------------------
    def _requirements(self, db: str) -> None:
        reqs = [
            "fastapi>=0.111,<1",
            "uvicorn[standard]>=0.30,<1",
            "sqlalchemy>=2.0,<3",
            "pydantic>=2.7,<3",
            "pydantic[email]>=2.7,<3",
            "passlib[bcrypt]>=1.7.4,<2",
        ]
        if DB_DEPS[db]:
            reqs.append(DB_DEPS[db])
        self.art.add("backend/requirements.txt", "\n".join(reqs) + "\n", self.name)

    def _database(self, db: str) -> None:
        src = f'''"""Database engine, session factory and declarative base."""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", {py_str(DB_URLS[db])})

engine = create_engine(
    DATABASE_URL,
    connect_args={{"check_same_thread": False}} if DATABASE_URL.startswith("sqlite") else {{}},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from . import models  # noqa: F401  (registers tables)
    Base.metadata.create_all(bind=engine)
'''
        self.art.add("backend/database.py", src, self.name)

    def _security(self) -> None:
        self.art.add("backend/security.py", _SECURITY_SRC, self.name)

    # -- ORM ------------------------------------------------------------
    def _models(self) -> None:
        lines = [
            '"""SQLAlchemy models generated from IntentLang IR."""',
            "from datetime import date, datetime  # noqa: F401",
            "",
            "from sqlalchemy import (",
            "    JSON, Boolean, Column, Date, DateTime, Float, ForeignKey,",
            "    Integer, Numeric, String, Text,",
            ")",
            "",
            "from .database import Base",
            "",
        ]
        for model in self.module.models:
            lines.append(f"class {model.pascal}(Base):")
            lines.append(f'    __tablename__ = "{model.table.lower()}"')
            for f in model.fields:
                coltype = _SA_TYPES.get(f.ftype, "String(255)")
                args = []
                if f.primary:
                    args.append("primary_key=True")
                if f.unique and not f.primary:
                    args.append("unique=True")
                if not f.required and not f.primary:
                    args.append("nullable=True")
                if f.default is not None:
                    args.append(f"default={self._default(f)}")
                if f.reference:
                    args.append(f'ForeignKey("{f.reference[0].lower()}.{f.reference[1].lower()}")')
                suffix = f", {', '.join(args)}" if args else ""
                lines.append(f"    {f.name} = Column({coltype}{suffix})")
            lines.append("")
        self.art.add("backend/models.py", "\n".join(lines), self.name)

    def _default(self, f: "I.Field") -> str:
        v = f.default
        if isinstance(v, bool):
            return str(v)
        if isinstance(v, (int, float)):
            return repr(v)
        if v is None:
            return "None"
        low = str(v).lower()
        if f.ftype == "datetime" and low in ("now", "today"):
            return "datetime.utcnow"
        if f.ftype == "date" and low in ("now", "today"):
            return "date.today"
        return py_str(str(v))

    # -- pydantic -------------------------------------------------------
    def _schemas(self) -> None:
        lines = [
            '"""Pydantic schemas generated from IntentLang IR."""',
            "from datetime import date, datetime",
            "from typing import Any, Optional",
            "",
            "from pydantic import BaseModel, ConfigDict",
            "",
        ]
        for model in self.module.models:
            fields = [f for f in model.fields if f.ftype != "id"]
            lines.append(f"class {model.pascal}Base(BaseModel):")
            for f in fields:
                ann = py_type(f.ftype)
                if not f.required:
                    ann = f"{ann} | None = None"
                lines.append(f"    {f.name}: {ann}")
            lines.append("")
            lines.append(f"class {model.pascal}Create({model.pascal}Base):")
            lines.append("    pass")
            lines.append("")
            lines.append(f"class {model.pascal}Response({model.pascal}Base):")
            lines.append("    model_config = ConfigDict(from_attributes=True)")
            lines.append("    id: int")
            lines.append("")
        for api in self.module.apis:
            if not api.request_fields:
                continue
            lines.append(f"class {api.pascal}Request(BaseModel):")
            for f in api.request_fields:
                lines.append(f"    {f.name}: {py_type(f.ftype)}")
            lines.append("")
        self.art.add("backend/schemas.py", "\n".join(lines), self.name)

    # -- routers ----------------------------------------------------------
    def _router(self, api: "I.Api") -> None:
        model = resolve_model(self.module, api)
        lines = [
            f'"""Router for {api.name} (generated)."""',
            "from typing import Any",
            "",
            "from fastapi import APIRouter, Depends, HTTPException, Path, Query",
            "from sqlalchemy import select",
            "from sqlalchemy.orm import Session",
            "",
            "from ..database import get_db",
            "from .. import models, schemas",
            "",
        ]
        if api.auth != "public":
            lines.append("from ..security import require_auth")
            lines.append("")
        lines.append(f'router = APIRouter(tags=["{api.slug}"])')
        lines.append("")

        # -- signature ----------------------------------------------------
        # Non-default parameters must precede defaulted ones in Python.
        sig: list[str] = []
        body = None
        if api.request_fields and api.method in ("POST", "PUT", "PATCH"):
            body = f"schemas.{api.pascal}Request"
            sig.append(f"body: {body}")
        sig.append("db: Session = Depends(get_db)")
        path_params = re.findall(r"\{([A-Za-z0-9_]+)\}", api.route)
        for p in path_params:
            sig.append(f"{p}: int = Path(...)")
        conditions = self._conditions(api, model)
        param_names = [c.field for c in conditions if c.param]
        for p in param_names:
            sig.append(f"{p}: Any = Query(default=None)")
        if api.auth != "public":
            sig.append(f'_auth: dict = Depends(require_auth([{py_str(api.auth)}]))')

        lines.append(f'@{api.method.lower()}({py_str(api.route)})')
        lines.append(f"def {api.slug}({', '.join(sig)}):")
        lines.append(indent(self._body(api, model, conditions, path_params, body)))
        lines.append("")
        self.art.add(f"backend/routers/{api.slug}.py", "\n".join(lines), self.name)

    # -- endpoint body -----------------------------------------------------
    def _body(self, api: "I.Api", model, conditions, path_params, body) -> str:
        b: list[str] = []
        if is_login(api):
            b.append("from ..security import sign_token, verify_password")
            b.append("username = getattr(body, 'username', getattr(body, 'email', '')) if body else ''")
            b.append("password = getattr(body, 'password', '') if body else ''")
            b.append('if not username or not password:')
            b.append('    raise HTTPException(status_code=400, detail="Missing credentials")')
            if model is not None:
                login_f = next((f.name for f in model.fields if f.name.lower() in ("email", "username")), None)
                if login_f:
                    b.append(f"user = db.execute(select(models.{model.pascal}).where(models.{model.pascal}.{login_f} == username)).scalars().first()")
                    b.append("if not user or not getattr(user, 'password', None) or not verify_password(password, getattr(user, 'password')):")
                    b.append('    raise HTTPException(status_code=401, detail="Invalid credentials")')
                    b.append('token = sign_token({"sub": username, "id": getattr(user, "id", None), "role": "user"})')
                    b.append('return {"token": token, "user": {"id": getattr(user, "id", None), "username": username}}')
                    return "\n".join(b)
            # fallback
            b.append('if not username:')
            b.append('    raise HTTPException(status_code=401, detail="Invalid credentials")')
            b.append('token = sign_token({"sub": username, "role": "user"})')
            b.append('return {"token": token, "user": {"username": username}}')
            return "\n".join(b)
        if is_logout(api):
            return 'return {"ok": True}'
        if model is None:
            return f'return {{"ok": True, "service": {py_str(api.slug)}}}'

        mcls = model.pascal
        method = api.method
        if method == "GET":
            b.append(f"q = select(models.{mcls})")
            for c in conditions:
                if c.param:
                    b.append(f"if {c.field} is not None:")
                    b.append(f"    q = q.where(models.{mcls}.{c.field}.op({py_str(c.op)})({c.field}))")
                else:
                    b.append(f"q = q.where(models.{mcls}.{c.field}.op({py_str(c.op)})({c.literal}))")
            if api.query and api.query.order:
                b.append(f"q = q.order_by(models.{mcls}.{api.query.order})")
            if api.query and api.query.limit:
                b.append(f"q = q.limit({api.query.limit})")
            b.append("rows = db.execute(q).scalars().all()")
            b.append(f'return [schemas.{mcls}Response.model_validate(r) for r in rows]')
            return "\n".join(b)

        if method in ("POST", "PUT", "PATCH"):
            b.append(f"row = models.{mcls}()")
            b.append(f"for _k, _v in ({body} or {{}}).model_dump(exclude_unset=True).items():" if body else "for _k, _v in ({}).items():")
            b.append('    if _k != "id" and hasattr(row, _k):')
            b.append("        setattr(row, _k, _v)")
            b.append("db.add(row)")
            b.append("db.commit()")
            b.append("db.refresh(row)")
            b.append(f'return schemas.{mcls}Response.model_validate(row)')
            return "\n".join(b)

        if method == "DELETE":
            pname = path_params[0] if path_params else "id"
            b.append(f"row = db.get(models.{mcls}, {pname})")
            b.append("if row is None:")
            b.append('    raise HTTPException(status_code=404, detail="not found")')
            b.append("db.delete(row)")
            b.append("db.commit()")
            b.append(f'return {{"ok": True, "deleted": {pname}}}')
            return "\n".join(b)
        return 'raise HTTPException(status_code=501, detail="Not Implemented")'

    # -- where conditions ---------------------------------------------------
    class _Condition:
        def __init__(self, field: str, op: str, raw: str):
            self.field = field
            self.op = op
            self.raw = raw
            low = raw.lower()
            self.param = low not in ("true", "false", "null") and not self._is_num(raw)
            self.literal = self._literal(low)

        @staticmethod
        def _is_num(raw: str) -> bool:
            try:
                float(raw)
                return True
            except ValueError:
                return False

        @staticmethod
        def _literal(low: str) -> str:
            if low == "true":
                return "True"
            if low == "false":
                return "False"
            if low == "null":
                return "None"
            return low

    def _conditions(self, api: "I.Api", model) -> list:
        out: list = []
        if not (api.query and api.query.where and model is not None):
            return out
        for field, op, raw in where_conditions(api.query.where, model):
            if any(f.name == field for f in model.fields):
                out.append(self._Condition(field, op, raw))
        return out

    # -- main / run ---------------------------------------------------------
    def _main(self) -> None:
        lines = [
            '"""IntentOS-generated FastAPI application."""',
            "",
            "from fastapi import FastAPI",
            "from fastapi.middleware.cors import CORSMiddleware",
            "",
            "from .database import init_db",
            "",
        ]
        for api in self.module.apis:
            lines.append(f"from .routers.{api.slug} import router as {api.slug}_router")
        lines.append("")
        lines.append(f'app = FastAPI(title={py_str(self.module.app.title)}, version="1.0.0")')
        lines.append('app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])')
        lines.append("")
        lines.append('@app.on_event("startup")')
        lines.append("def _startup():")
        lines.append("    init_db()")
        lines.append("")
        lines.append('@app.get("/health")')
        lines.append("def health():")
        lines.append(f'    return {{"status": "ok", "app": {py_str(self.module.app.title)}}}')
        lines.append("")
        for api in self.module.apis:
            lines.append(f"app.include_router({api.slug}_router)")
        self.art.add("backend/main.py", "\n".join(lines) + "\n", self.name)

    def _seed(self) -> None:
        lines = [
            '"""Seed script: python -m seed"""',
            "from .database import SessionLocal, init_db",
            "from . import models",
            "",
            "def seed():",
            "    init_db()",
            "    db = SessionLocal()",
        ]
        if self.module.models:
            m0 = self.module.models[0]
            lines.append(f"    if db.query(models.{m0.pascal}).count() == 0:")
            for i in range(3):
                assigns = ", ".join(
                    f"{f.name}={self._seed_value(f, i)}"
                    for f in m0.fields if f.ftype != "id"
                )
                if assigns:
                    lines.append(f"        db.add(models.{m0.pascal}({assigns}))")
            lines.append("        db.commit()")
        lines.append('    print("seeded")')
        lines.append("")
        lines.append('if __name__ == "__main__":')
        lines.append("    seed()")
        self.art.add("backend/seed.py", "\n".join(lines), self.name)

    def _seed_value(self, f: "I.Field", i: int) -> str:
        if f.ftype in ("string", "email", "password", "url", "phone", "enum"):
            return py_str(f"{f.name.lower()}{i + 1}")
        if f.ftype in ("int", "integer", "id"):
            return str(i + 1)
        if f.ftype == "float":
            return f"{i + 1}.5"
        if f.ftype in ("boolean", "bool"):
            return "True" if i % 2 == 0 else "False"
        return py_str("")

    def _run_sh(self) -> None:
        self.art.add(
            "backend/run.sh",
            "#!/usr/bin/env bash\n"
            "set -e\n"
            'cd "$(dirname "$0")"\n'
            "python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --reload\n",
            self.name,
        )


_SECURITY_SRC = '''"""Signed-token auth and bcrypt password hashing."""
import base64
import json
import os
import time

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext

SECRET = os.environ["INTENTOS_SECRET"]
_bearer = HTTPBearer(auto_error=False)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

def _unb64(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def sign_token(payload: dict, ttl_seconds: int = 86400) -> str:
    body = dict(payload)
    body["exp"] = int(time.time()) + ttl_seconds
    encoded = _b64(json.dumps(body, separators=(",", ":")).encode())
    import hashlib
    import hmac
    sig = hmac.new(SECRET.encode(), encoded.encode(), hashlib.sha256).hexdigest()
    return f"{encoded}.{sig}"


def decode_token(token: str) -> dict | None:
    try:
        encoded, sig = token.split(".", 1)
        expected = hmac.new(SECRET.encode(), encoded.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(_unb64(encoded).decode())
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None


def require_auth(roles: list[str] | None = None):
    def _dep(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> dict:
        if credentials is None:
            raise HTTPException(status_code=401, detail="missing bearer token")
        payload = decode_token(credentials.credentials)
        if payload is None:
            raise HTTPException(status_code=401, detail="invalid or expired token")
        if roles and payload.get("role") not in roles:
            raise HTTPException(status_code=403, detail="insufficient role")
        return payload
    return _dep
'''
