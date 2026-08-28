# IntentOS — The AI Development Operating System

Describe your software idea in plain English. IntentOS plans it, writes it in
**IntentLang** (a deterministic, human-readable, compiler-friendly language),
compiles it, and generates the entire application — backend, frontend,
database, tests, docs, Docker, and CI.

**The core rule:** AI *never* writes production code. AI understands intent,
completes requirements, and plans software. Everything concrete is expressed as
**IntentLang**, which is compiled by a deterministic compiler.

```
English
   │  AI Planner (heuristic by default, optional LLM provider)
   ▼
IntentLang
   │  IntentLang Compiler (lexer → parser → AST → semantic → IR → codegen)
   ▼
Application (React, Next.js, Flutter, FastAPI, Express, Spring Boot, SQL, Docker, CI)
```

---

## Monorepo layout

| Path            | What it is |
|-----------------|------------|
| `compiler/`     | The **IntentLang compiler** — pure Python, zero dependencies. Lexer, recursive-descent parser, AST, semantic analyzer, optimizer, IR, incremental engine, and 14 deterministic code generators. |
| `backend/`      | **FastAPI** backend: AI orchestration (heuristic + optional Ollama/OpenRouter/Qwen), the intent → IntentLang pipeline, workspace management, database viewer, git integration, plugin store. |
| `ide/`          | **Desktop IDE** — React + TypeScript + Tailwind + Monaco + Electron. Editor with syntax highlighting/autocomplete/live errors, AI chat, compiler console, build & run, preview, database viewer, git panel, plugin marketplace. |
| `docs/`         | Specification, architecture, language reference, compiler internals. |

---

## Quick start

### 1. Compiler (anywhere)

```bash
cd compiler
python -m intentlang compile samples/student-portal.il -o build
python -m intentlang run samples/student-portal.il      # preview server
python -m unittest discover -s tests                    # 28 tests
```

### 2. Backend

```bash
cd backend
python -m venv .venv && source .venv/Scripts/activate   # Windows: .venv/Scripts/activate
pip install -r requirements.txt
uvicorn app.main:app --port 8000
```

Full pipeline over HTTP:

```bash
curl -N -X POST http://localhost:8000/api/pipeline \
  -H "Content-Type: application/json" \
  -d '{"idea": "Create a food delivery startup for Hyderabad"}'
```

Heuristic mode runs **fully offline** — no model required. To use an LLM, set
`INTENTOS_AI_PROVIDER=openrouter` (or `ollama`) and add your key in
`backend/.env`.

### 3. IDE

```bash
cd ide
npm install
npm run dev          # browser (Vite)
npm run electron     # desktop app
npm run build        # typecheck + production bundle
```

### 4. Docker

```bash
docker compose up --build
# backend at http://localhost:8000, API docs at /docs
```

---

## Try it

The fastest way to see the whole platform work:

1. Start the backend (`uvicorn app.main:app --port 8000`).
2. Open the IDE and type into the chat: *"Create a food delivery startup for Hyderabad"*.
3. Watch the **pipeline stepper** walk intent → requirements → spec → IntentLang.
4. Click **Build** — the compiler writes the full app into the workspace.
5. Click **Run** — a live, dependency-free preview of your generated app opens.

---

## IntentLang in 30 seconds

```intentlang
Create Application Student Portal
  With
    Title "Student Portal"
    Database sqlite

Create Page Login
  With
    Route /login
    Layout auth
  Add Input Username
    With
      Label "Username"
      Required true
  Add Button "Sign In"
    When Clicked
      Call Api Login
        On Success
          Navigate To Home
        On Failure
          Show Toast "Invalid credentials"

Create Model Student
  With
    Table students
  Field Id
    Type id
  Field Name
    Type string
  Field Email
    Type email
    Unique true

Create Api ListStudents
  With
    Method GET
    Route /api/students
    Auth user
  Query
    Select
    From students
  Response
    Status 200
    Body List Student

When Login succeeds
  Open Home

Deploy Docker
  With
    Port 8000
```

The full reference is in [`docs/intentlang.md`](docs/intentlang.md).

---

## The compiler

`compiler/intentlang/` is a complete, zero-dependency compiler pipeline:

```
lexer → parser (recursive descent, panic-mode error recovery)
      → AST → semantic analyzer (two-phase symbol resolution, type check)
      → optimizer (dead-entity & unreachable-route elimination)
      → IR (versioned, JSON-serializable) → code generators
```

Every stage reports structured diagnostics with line/column ranges, and the
incremental engine recompiles only the changed sections of a program.
See [`docs/compiler.md`](docs/compiler.md).

### Generators

| Target            | Output |
|-------------------|--------|
| `react`           | Vite React + TS app with pages, widgets, events, API client |
| `next`            | Next.js App Router project |
| `flutter`         | Dart/Flutter project |
| `fastapi`         | Python FastAPI + SQLAlchemy backend |
| `express`         | Node + Express + better-sqlite3 backend |
| `spring`          | Java Spring Boot backend |
| `db`              | SQLite / PostgreSQL / MySQL DDL |
| `docker`          | Dockerfile + docker-compose |
| `ci`              | GitHub Actions workflow |
| `docs`            | README + API reference |
| `tests`           | Backend + frontend test suites |
| `deploy`          | Fly.io / Render / Heroku configs |
| `standalone`      | Zero-dependency single-file HTML preview |
| `plugins`         | PWA manifest, SEO metadata |

---

## Architecture

See [`docs/architecture.md`](docs/architecture.md) for the clean-architecture
breakdown: Intent Parser → Requirement Analyzer → Product Planner →
IntentLang Generator → Compiler → IR → Code Generators, plus the IDE
workbench and the AI policy.

## License

MIT.
