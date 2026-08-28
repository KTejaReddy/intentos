"""Next.js (App Router) frontend generator."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Optional

from ..artifact import ArtifactSet
from ..diagnostics import Diagnostics
from ._util import js_str, theme_color, theme_light
from .base import Generator

if TYPE_CHECKING:  # pragma: no cover
    from .. import ir as I
    from ..compiler import CompileOptions


class NextGenerator(Generator):
    name = "frontend/next"

    def validate_options(self, options: "CompileOptions") -> Optional[str]:
        if options.frontend not in ("next", "nextjs"):
            return "options.frontend must be 'next'"
        return None

    def generate(self, module: "I.ModuleIR", options: "CompileOptions",
                 artifacts: ArtifactSet, diags: Diagnostics) -> None:
        self.art = artifacts
        self.module = module
        pkg = {
            "name": f"intentos-web-{module.app.name.lower().replace(' ', '-')}",
            "private": True,
            "version": "1.0.0",
            "scripts": {"dev": "next dev", "build": "next build", "start": "next start"},
            "dependencies": {
                "next": "^14.2.5",
                "react": "^18.3.1",
                "react-dom": "^18.3.1",
            },
            "devDependencies": {
                "@types/node": "^20.14.15",
                "@types/react": "^18.3.3",
                "typescript": "^5.5.4",
            },
        }
        self.art.add("frontend/package.json", json.dumps(pkg, indent=2) + "\n", self.name)
        self.art.add("frontend/next.config.mjs",
                     "/** @type {import('next').NextConfig} */\n"
                     "const nextConfig = { reactStrictMode: true }\n"
                     "export default nextConfig\n", self.name)
        self.art.add("frontend/tsconfig.json",
                     '{\n'
                     '  "compilerOptions": {\n'
                     '    "target": "ES2020", "lib": ["dom", "dom.iterable", "esnext"],\n'
                     '    "allowJs": true, "skipLibCheck": true, "strict": true, "noEmit": true,\n'
                     '    "esModuleInterop": true, "module": "esnext", "moduleResolution": "bundler",\n'
                     '    "resolveJsonModule": true, "isolatedModules": true, "jsx": "preserve",\n'
                     '    "incremental": true, "plugins": [{ "name": "next" }], "paths": { "@/*": ["./*"] }\n'
                     '  },\n'
                     '  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],\n'
                     '  "exclude": ["node_modules"]\n'
                     '}\n', self.name)
        self.art.add("frontend/.env.local.example",
                     "NEXT_PUBLIC_API_BASE=http://localhost:8000\n", self.name)
        self._layout()
        self._api()
        for page in module.pages:
            self._page(page)
        self._globals()

    def _layout(self) -> None:
        self.art.add(
            "frontend/app/layout.tsx",
            "import type { Metadata } from 'next'\n"
            "import './globals.css'\n\n"
            f"export const metadata: Metadata = {{ title: {js_str(self.module.app.title)} }}\n\n"
            "export default function RootLayout({ children }: { children: React.ReactNode }) {\n"
            "  return (\n"
            "    <html lang=\"en\"><body>{children}</body></html>\n"
            "  )\n"
            "}\n", self.name,
        )

    def _api(self) -> None:
        lines = [
            "// Generated API client (Next.js)",
            "const BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000'",
            "export async function request(method: string, path: string, body?: any) {",
            "  const res = await fetch(BASE + path, {",
            "    method,",
            "    headers: { 'Content-Type': 'application/json' },",
            "    body: body ? JSON.stringify(body) : undefined,",
            "    cache: 'no-store',",
            "  })",
            "  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || res.statusText)",
            "  return res.json()",
            "}",
            "",
            "export const api = {",
        ]
        for a in self.module.apis:
            args = ["body: any"] if a.request_fields and a.method in ("POST", "PUT", "PATCH") else []
            call = "body" if args else "undefined"
            lines.append(f"  {a.slug}: ({', '.join(args)}) => request('{a.method}', {js_str(a.route)}, {call}),")
        lines.append("}")
        lines.append("")
        self.art.add("frontend/lib/api.ts", "\n".join(lines), self.name)

    def _page(self, page: "I.Page") -> None:
        path = page.route.rstrip("/") or "/"
        if path == "/":
            fpath = "frontend/app/page.tsx"
        else:
            fpath = "frontend/app" + path + "/page.tsx"
        lines = [
            "'use client'",
            "// @ts-nocheck",
            "import { useEffect, useState } from 'react'",
            "import { api } from '@/lib/api'",
            "",
            f"export default function {page.slug.replace('-', '_')}Page() {{",
        ]
        body: list[str] = []
        jsx: list[str] = []
        for w in page.widgets:
            self._widget(w, body, jsx)
        if body:
            lines.extend("  " + l for l in body)
        lines.append("  return (")
        lines.append("    <main className=\"page\">")
        for line in jsx:
            lines.append("      " + line)
        lines.append("    </main>")
        lines.append("  )")
        lines.append("}")
        lines.append("")
        self.art.add(fpath, "\n".join(lines), self.name)

    def _widget(self, w, body: list[str], jsx: list[str]) -> None:
        slug = w.slug.replace("-", "_")
        props = w.props
        if w.kind == "navbar":
            links = " ".join(f"<a key={json.dumps(p.route)} href={json.dumps(p.route)}>{p.title}</a>" for p in self.module.pages)
            jsx.append(f"<nav className=\"navbar\">{links}</nav>")
        elif w.kind == "text":
            tag = {"heading": "h2", "title": "h1", "subtitle": "h3"}.get(str(props.get("variant") or ""), "p")
            jsx.append(f"<{tag} className=\"text\">{js_str(str(props.get('text') or w.name))}</{tag}>")
        elif w.kind == "input":
            v = slug
            body.append(f"const [{v}, set{v[:1].upper() + v[1:]}] = useState('')")
            jsx.append(f"<label className=\"field\">{js_str(str(props.get('label') or w.name))}<input value={{{v}}} onChange={{e => set{v[:1].upper() + v[1:]}(e.target.value)}} /></label>")
        elif w.kind == "button":
            jsx.append(f"<button className=\"btn\">{js_str(str(props.get('label') or w.name))}</button>")
        elif w.kind == "table":
            api_name = str(props.get("api") or "")
            v = slug
            body.append(f"const [{v}, set{v[:1].upper() + v[1:]}] = useState<any[]>([])")
            body.append(f"useEffect(() => {{ api.{api_name.replace('-', '_')}().then(r => set{v[:1].upper() + v[1:]}(Array.isArray(r) ? r : r.items || [])) }}, [])")
            jsx.append(f"<div className=\"table-card\">{'{' + v + '.length'} rows</div>")
        elif w.kind == "form":
            inner = "".join(f"<input key={json.dumps(c.name)} placeholder={json.dumps(str(c.props.get('label') or c.name))} />" for c in w.children)
            jsx.append(f"<form className=\"card\">{inner}</form>")
        else:
            jsx.append(f"<div>{js_str(w.name)}</div>")

    def _globals(self) -> None:
        primary = theme_color(self.module.app.theme)
        light = theme_light(self.module.app.theme)
        self.art.add(
            "frontend/app/globals.css",
            f":root {{ --primary: {primary}; --primary-light: {light}; --bg: #0b0f1a; --border: rgba(255,255,255,.08); --text: #e6eaf3; }}\n"
            "body { margin: 0; background: var(--bg); color: var(--text); font-family: Inter, system-ui, sans-serif; }\n"
            ".page { max-width: 960px; margin: 0 auto; padding: 32px 20px; }\n"
            ".navbar { display: flex; gap: 12px; margin-bottom: 24px; }\n"
            ".navbar a { color: var(--text); text-decoration: none; }\n"
            ".field { display: flex; flex-direction: column; gap: 6px; margin-bottom: 14px; }\n"
            ".field input { padding: 10px; border-radius: 8px; border: 1px solid var(--border); background: rgba(255,255,255,.04); color: var(--text); }\n"
            ".btn { background: linear-gradient(135deg, var(--primary), var(--primary-light)); border: 0; border-radius: 8px; padding: 10px 18px; font-weight: 600; cursor: pointer; }\n"
            ".card { border: 1px solid var(--border); border-radius: 12px; padding: 20px; }\n",
            self.name,
        )
