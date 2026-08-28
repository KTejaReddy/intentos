"""Node.js Express backend generator."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Optional

from ..artifact import ArtifactSet
from ..diagnostics import Diagnostics
from ._util import (
    is_login, is_logout, js_str, resolve_model, route_express, where_conditions,
)
from .base import Generator

if TYPE_CHECKING:  # pragma: no cover
    from .. import ir as I
    from ..compiler import CompileOptions

_DRIVER = {"sqlite": "better-sqlite3", "postgres": "pg", "mysql": "mysql2"}
_DSN = {
    "sqlite": "new Database('./app.db')",
    "postgres": "new Pool({ host: process.env.DB_HOST || 'localhost', port: 5432, user: process.env.DB_USER || 'postgres', password: process.env.DB_PASSWORD || 'postgres', database: process.env.DB_NAME || 'app' })",
    "mysql": "new Pool({ host: process.env.DB_HOST || 'localhost', port: 3306, user: process.env.DB_USER || 'root', password: process.env.DB_PASSWORD || '', database: process.env.DB_NAME || 'app' })",
}


class ExpressGenerator(Generator):
    name = "backend/express"

    def validate_options(self, options: "CompileOptions") -> Optional[str]:
        if options.backend not in ("express", "node", "javascript"):
            return "options.backend must be 'express'"
        return None

    def generate(self, module: "I.ModuleIR", options: "CompileOptions",
                 artifacts: ArtifactSet, diags: Diagnostics) -> None:
        self.art = artifacts
        self.module = module
        db = options.database
        self.db = db
        pkg = {
            "name": f"intentos-api-{module.app.name.lower().replace(' ', '-')}",
            "version": "1.0.0",
            "type": "module",
            "scripts": {"start": "node server.js", "seed": "node seed.js", "test": "node --test tests/"},
            "dependencies": {
                "cors": "^2.8.5",
                "express": "^4.19.2",
                "bcryptjs": "^2.4.3",
                _DRIVER[db]: "^1.0.0" if db == "sqlite" else ("^8.12.0" if db == "postgres" else "^3.11.0"),
            },
        }
        self.art.add("backend/package.json", json.dumps(pkg, indent=2) + "\n", self.name)
        self._db()
        self._security()
        self._server()
        for api in module.apis:
            self._route(api)
        self._seed()

    def _db(self) -> None:
        src = f"""// Database driver (generated)
import {{ {self._import()} }} from {js_str(self._driver_import())}

export const db = {_DSN[self.db]}
"""
        self.art.add("backend/db.js", src, self.name)

    def _import(self) -> str:
        return "Database" if self.db == "sqlite" else "Pool"

    def _driver_import(self) -> str:
        return "better-sqlite3" if self.db == "sqlite" else _DRIVER[self.db]

    def _security(self) -> None:
        self.art.add("backend/security.js", _SECURITY_JS, self.name)

    def _server(self) -> None:
        lines = [
            "// Express server (generated)",
            "import express from 'express'",
            "import cors from 'cors'",
            "",
            "import { db } from './db.js'",
        ]
        for a in self.module.apis:
            lines.append(f"import {a.slug}Router from './routes/{a.slug}.js'")
        lines.append("")
        lines.append("const app = express()")
        lines.append("app.use(cors())")
        lines.append("app.use(express.json())")
        lines.append("")
        lines.append('app.get("/health", (_req, res) => res.json({ status: "ok" }))')
        for a in self.module.apis:
            lines.append(f"app.use({a.slug}Router)")
        lines.append("")
        lines.append("const PORT = process.env.PORT || 8000")
        lines.append("app.listen(PORT, () => console.log(`api listening on :${PORT}`))")
        lines.append("")
        self.art.add("backend/server.js", "\n".join(lines), self.name)

    def _route(self, api: "I.Api") -> None:
        model = resolve_model(self.module, api)
        lines = [
            "// Generated route",
            "import { Router } from 'express'",
            "import { db } from '../db.js'",
            "import { requireAuth } from '../security.js'",
            "",
            f"const router = Router()",
            "",
        ]
        if api.auth != "public":
            lines.append(f"const guard = requireAuth([{js_str(api.auth)}])")
        conditions = []
        if api.query and api.query.where and model:
            conditions = where_conditions(api.query.where, model)
            conditions = [c for c in conditions if any(f.name == c[0] for f in model.fields)]
        route = route_express(api.route)
        sig = ["req", "res"]
        if api.auth != "public":
            sig.append("guard")
        lines.append(f"router.{api.method.lower()}({js_str(route)}, ({', '.join(sig)}) => {{")
        body = self._body(api, model, conditions, route)
        lines.append(body)
        lines.append("})")
        lines.append("")
        lines.append("export default router")
        lines.append("")
        self.art.add(f"backend/routes/{api.slug}.js", "\n".join(lines), self.name)

    def _body(self, api: "I.Api", model, conditions, route) -> str:
        if is_login(api):
            q_exec = "db.prepare(`SELECT * FROM ${tbl} WHERE ${loginF} = ?`).get(username)" if self.db == "sqlite" else "(await db.query(`SELECT * FROM ${tbl} WHERE ${loginF} = $1`, [username])).rows[0]"
            return (
                "  const { username, password } = req.body || {}\n"
                "  if (!username || !password) return res.status(400).json({ detail: 'Missing credentials' })\n"
                + (f"  const loginF = {js_str(next((f.name for f in model.fields if f.name.lower() in ('email', 'username')), 'username')) if model else '\"username\"'}\n"
                   f"  const tbl = {js_str(model.table) if model else '\"users\"'}\n"
                   f"  const user = {q_exec}\n"
                   "  if (!user || !user.password || !(await verifyPassword(password, user.password))) return res.status(401).json({ detail: 'Invalid credentials' })\n"
                   "  const token = signToken({ sub: username, id: user.id, role: 'user' })\n"
                   "  return res.json({ token, user: { id: user.id, username } })" if model else 
                   "  return res.status(401).json({ detail: 'Invalid credentials' }) // No model bound\n")
            )
        if is_logout(api):
            return "  return res.json({ ok: true })"
        if model is None:
            return f"  return res.json({{ ok: true, service: {js_str(api.slug)} }})"
        tbl = model.table
        if api.method == "GET":
            out = [f"  let rows = db.prepare(`SELECT * FROM {tbl}`).all()" if self.db == "sqlite" else f"  let rows = (await db.query(`SELECT * FROM {tbl}`)).rows"]
            for field, op, raw in conditions:
                out.append(f"  const {field} = req.query.{field}")
                out.append(f"  if ({field} !== undefined) {{")
                out.append(f"    rows = rows.filter(r => String(r.{field}) {op} String({field}))")
                out.append(f"  }}")
            out.append("  return res.json(rows)")
            return "\n".join(out)
        if api.method in ("POST", "PUT", "PATCH"):
            out = [f"  const body = req.body || {{}}"]
            cols = [f.name for f in model.fields if f.ftype != "id"]
            out.append(f"  const keys = {json.dumps(cols)}.filter(k => body[k] !== undefined)")
            out.append("  const vals = keys.map(k => body[k])")
            placeholders = ", ".join("?" for _ in cols)
            out.append(f"  const sql = `INSERT INTO {tbl} (${{keys.join(', ')}}) VALUES ({placeholders})`")
            out.append(f"  const info = db.prepare(sql).run(vals)" if self.db == "sqlite" else f"  const {{ rows }} = await db.query(`SELECT * FROM {tbl}`)")
            out.append("  return res.status(201).json({ id: Number(info.lastInsertRowid), ...body })" if self.db == "sqlite" else "  return res.json({ ok: true, ...body })")
            return "\n".join(out)
        if api.method == "DELETE":
            out = ["  const id = Number(req.params.id)"]
            out.append(f"  db.prepare(`DELETE FROM {tbl} WHERE id = ?`).run(id)" if self.db == "sqlite" else f"  await db.query(`DELETE FROM {tbl} WHERE id = $1`, [id])")
            out.append("  return res.json({ ok: true, deleted: id })")
            return "\n".join(out)
        return "  return res.json({ ok: true })"

    def _seed(self) -> None:
        lines = [
            "// Seed script (generated)",
            "import { db } from './db.js'",
            "import { signToken } from './security.js'",
            "",
        ]
        if self.module.models:
            m0 = self.module.models[0]
            cols = [f.name for f in m0.fields if f.ftype != "id"]
            lines.append("const count = db.prepare('SELECT COUNT(*) AS n FROM " + m0.table + "').get().n")
            lines.append("if (count === 0) {")
            for i in range(3):
                vals = ", ".join(js_str(f"{f.name.lower()}{i+1}") if f.ftype != "int" else str(i + 1) for f in self.module.models[0].fields if f.ftype != "id")
                lines.append(f"  db.prepare('INSERT INTO {m0.table} ({', '.join(cols)}) VALUES ({', '.join('?' for _ in cols)})').run({vals})")
            lines.append("  console.log('seeded')")
            lines.append("}")
        lines.append("")
        self.art.add("backend/seed.js", "\n".join(lines), self.name)


_SECURITY_JS = """// Signed-token auth and bcrypt password hashing (generated). Replace SECRET before production.
import crypto from 'node:crypto'
import bcrypt from 'bcryptjs'

const SECRET = process.env.INTENTOS_SECRET || 'change-me-in-production'

export async function hashPassword(password) {
  return bcrypt.hash(password, 10)
}

export async function verifyPassword(plain, hashed) {
  return bcrypt.compare(plain, hashed)
}

function b64(data) {
  return Buffer.from(data).toString('base64url')
}
function unb64(data) {
  return Buffer.from(data, 'base64url').toString('utf-8')
}

export function signToken(payload, ttlSeconds = 86400) {
  const body = { ...payload, exp: Math.floor(Date.now() / 1000) + ttlSeconds }
  const encoded = b64(JSON.stringify(body))
  const sig = crypto.createHmac('sha256', SECRET).update(encoded).digest('hex')
  return `${encoded}.${sig}`
}

export function decodeToken(token) {
  try {
    const [encoded, sig] = token.split('.')
    const expected = crypto.createHmac('sha256', SECRET).update(encoded).digest('hex')
    if (sig !== expected) return null
    const payload = JSON.parse(unb64(encoded))
    if (payload.exp < Math.floor(Date.now() / 1000)) return null
    return payload
  } catch {
    return null
  }
}

export function requireAuth(roles) {
  return (req, res, next) => {
    const header = req.headers.authorization || ''
    const token = header.startsWith('Bearer ') ? header.slice(7) : null
    const payload = token && decodeToken(token)
    if (!payload) return res.status(401).json({ detail: 'missing or invalid token' })
    if (roles && !roles.includes(payload.role)) return res.status(403).json({ detail: 'insufficient role' })
    req.user = payload
    next()
  }
}
"""
