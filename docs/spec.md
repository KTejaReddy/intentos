# IntentOS — Product Specification

**Version 1.0** — "The AI Development Operating System"

## 1. Vision

Users describe a software idea in plain English. IntentOS plans the product,
transcribes it into **IntentLang**, compiles that language with a real
compiler, and generates a complete, runnable application — backend, frontend,
database, tests, docs, Docker, and CI — **without AI ever writing production
code directly**.

## 2. Users

| Persona | Needs |
|---------|-------|
| Non-technical founder | Turn an idea into a working prototype without hiring |
| Technical lead | Get a deterministic, reviewable, versionable starting point |
| Educator | Teach full-stack architecture through a transparent pipeline |

## 3. Product principles

1. **Determinism** — same idea, same IntentLang, same app. Always.
2. **AI constrained** — AI plans; the compiler builds.
3. **Transparency** — every pipeline stage is visible, editable, and auditable.
4. **Extensibility** — new code generators, providers, and IDE plugins without
   touching the core.

## 4. Functional requirements

### FR1 — Intent pipeline
- FR1.1 Parse English ideas into structured intent (domain, users, entities, features).
- FR1.2 Detect missing requirements and surface follow-up questions.
- FR1.3 Produce a product plan: scope, features, summary.
- FR1.4 Generate a complete, compilable IntentLang program.
- FR1.5 Work offline with zero configuration (heuristic provider).

### FR2 — IntentLang
- FR2.1 Human-readable, indentation-based, deterministic language.
- FR2.2 Statements: Application, Role, Model, Api, Page, Rule (When), Deploy.
- FR2.3 Widgets, events, actions, field types, auth, CRUD contracts.

### FR3 — Compiler
- FR3.1 Lexer, parser (error recovery), AST, semantic analyzer, optimizer, IR.
- FR3.2 Incremental recompilation.
- FR3.3 Code generators: React, Next, Flutter, FastAPI, Express, Spring Boot,
       SQLite/Postgres/MySQL, Docker, GitHub Actions, docs, tests, deploy,
       standalone preview, PWA/SEO plugins.
- FR3.4 Structured diagnostics with line/column ranges and severities.

### FR4 — Backend
- FR4.1 REST API for intent analysis, full pipeline, compile/validate, projects,
       chat, database viewer, git, plugins, settings.
- FR4.2 AI provider abstraction (heuristic, Ollama, OpenRouter/Qwen).
- FR4.3 Streaming pipeline events.

### FR5 — IDE
- FR5.1 Electron desktop app; Monaco editor with IntentLang highlighting,
       autocomplete, hover docs, live diagnostics.
- FR5.2 Project explorer, search, git panel, database viewer, plugin
       marketplace, settings.
- FR5.3 AI chat driving the pipeline; pipeline stepper onboarding.
- FR5.4 Compiler console, problems panel, output panel.
- FR5.5 Build → Run → live preview of generated apps.
- FR5.6 Dark glassmorphism theme, responsive layout.

### FR6 — Output quality
- FR6.1 Generated apps are valid, buildable, and dependency-minimal.
- FR6.2 Generated backend passes `py_compile`; generated frontend is
       syntactically valid JSX.
- FR6.3 Deterministic, byte-identical artifact regeneration.

## 5. Non-functional requirements

| Requirement | Target |
|-------------|--------|
| Performance | Full compile of a typical project < 1 s |
| Portability | Compiler: any Python ≥ 3.10, zero deps |
| Security | No secrets in repo; provider keys via env |
| Maintainability | Clean architecture, DI, typed routers, documented modules |
| Testability | 28 compiler tests + 9 backend tests, CI-ready |

## 6. Out of scope (v1)

- Multi-user auth on the platform API.
- Mobile packaging of generated Flutter apps.
- Production load-balancing of generated apps (deploy configs are provided).
- A WASM-compiled compiler running entirely in the browser (future work).

## 7. Success criteria

1. "Create a food delivery startup for Hyderabad" yields a working app in
   under a minute, offline.
2. The generated backend imports cleanly; the generated frontend typechecks.
3. The IDE supports the full loop: idea → IntentLang → build → run → preview.
4. No AI-generated code exists anywhere in the output path.
