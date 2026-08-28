# IntentOS Architecture

IntentOS implements a strict **intent → language → compiler → artifacts**
pipeline. The platform is organized as clean architecture: each ring depends
only on the ring inside it, and all cross-cutting concerns (AI providers,
workspaces, plugins) are injected through interfaces.

```
┌──────────────────────────────────────────────────────────────┐
│                         IDE (Electron)                       │
│  Monaco editor · chat · pipeline stepper · console · preview │
│  explorer · db viewer · git panel · plugin marketplace        │
└───────────────────────────┬──────────────────────────────────┘
                            │ REST / SSE
┌───────────────────────────▼──────────────────────────────────┐
│                     Backend (FastAPI)                        │
│                                                              │
│  ┌──────────┐  ┌───────────────┐  ┌───────────────────────┐  │
│  │ Intent   │→ │ Requirement   │→ │ Product Planner       │  │
│  │ Parser   │  │ Analyzer      │  │ (spec, scope, PRD)    │  │
│  └──────────┘  └───────────────┘  └───────────┬───────────┘  │
│       ▲               ▲                       │              │
│       │  AI providers (heuristic · ollama · openrouter)      │
│       │  — used ONLY for understanding & planning,           │
│       │    never for production code                         │
│                                               ▼              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │                IntentLang Generator                    │  │
│  └───────────────────────────────┬────────────────────────┘  │
└──────────────────────────────────┼───────────────────────────┘
                                   │ .il source
┌──────────────────────────────────▼───────────────────────────┐
│                    Compiler (pure Python)                    │
│  lexer → parser → AST → semantic analyzer → optimizer → IR  │
│                        │  versioned JSON                    │
│                        ▼                                    │
│               Code generators (14 targets)                  │
│  react · next · flutter · fastapi · express · spring · db    │
│  docker · ci · docs · tests · deploy · standalone · plugins  │
└──────────────────────────────────┬───────────────────────────┘
                                   │ artifacts
┌──────────────────────────────────▼───────────────────────────┐
│                 Workspace (project on disk)                  │
│  generated app · .intentos metadata · build cache · git      │
└──────────────────────────────────────────────────────────────┘
```

---

## 1. The pipeline

The full product pipeline lives in `backend/app/services/pipeline.py` and
streams progress events to the IDE over HTTP:

| Stage | Service | Responsibility |
|-------|---------|----------------|
| 1. Intent parsing | `services/ai` (heuristic or LLM provider) | Natural English → structured intent: domain, users, entities, features, location |
| 2. Requirement analysis | same | Detect missing requirements; produce follow-up questions the user can answer |
| 3. Product planning | same | Assemble scope estimate, competitor-style summary, PRD |
| 4. IntentLang generation | `heuristic.generate_intentlang` or LLM with constrained prompt | Produce a complete, compilable `.il` program |
| 5. Compilation | `compiler/intentlang` | The pipeline above, ending in generated artifacts |
| 6. Persistence | `services/workspace` | Write artifacts into the project directory |

Every stage emits structured events (`stage`, `status`, `message`,
`artifacts`), so the IDE stepper and console update live.

## 2. The AI policy

AI is used **exclusively** for:

- understanding natural-language intent,
- completing missing requirements,
- explaining compiler diagnostics,
- planning the product (scope, features, PRD),
- researching competitors,
- generating documentation.

AI **never** emits production code. The only artifact an LLM may produce is
IntentLang — and even then the pipeline validates it by compiling it; unusable
LLM output falls back to the deterministic heuristic planner. The heuristic
planner (`backend/app/services/ai/heuristic.py`) runs fully offline with no
model and no network: ten industry domains (food delivery, e-commerce,
education, booking, social, CRM, health, finance, productivity, content),
per-domain entities/pages, intent-keyword detection, and requirement
questions.

## 3. The compiler

`compiler/intentlang/` is a zero-dependency Python package:

| Module | Role |
|--------|------|
| `lexer.py` | Indentation-aware tokenizer with error recovery |
| `tokens.py` / `keywords.py` | Token model and keyword tables |
| `parser.py` | Recursive-descent parser; panic-mode recovery; produces the AST |
| `ast.py` | Typed AST node model |
| `semantic.py` | Two-phase symbol resolution, type checking, route-collision analysis, widget binding |
| `optimizer.py` | Dead-entity and unreachable-route elimination |
| `ir.py` | Versioned, JSON-serializable intermediate representation |
| `incremental.py` | Incremental recompilation by source-section hashing |
| `compiler.py` | Driver: orchestration + artifact materialization |
| `codegen/` | 14 deterministic generators, pluggable via `registry.py` |
| `cli.py` | `intentlang compile|run|fmt` CLI |

The IR is the contract between the compiler front end and every generator:
generators consume `CompileResult.ir` (models, pages, apis, roles, rules,
deploy config) and never touch the AST.

## 4. The backend

`backend/app/` — FastAPI with typed routers:

| Router | Endpoints |
|--------|-----------|
| `intent.py` | `/api/intent/analyze`, `/api/intent/questions` — parse an idea, list missing requirements |
| `pipeline.py` | `/api/pipeline` — the full streaming product pipeline |
| `compile.py` | `/api/compile`, `/api/compile/validate`, `/api/compile/artifacts` — compile IntentLang, return diagnostics & artifacts |
| `projects.py` | CRUD + file tree for workspaces |
| `chat.py` | `/api/chat` — conversational loop over the pipeline |
| `db.py` | `/api/projects/{id}/db/tables|schema|query` — database viewer |
| `git.py` | `/api/projects/{id}/git/status|commit|log|diff` |
| `plugins.py` | Plugin marketplace listing + install |
| `settings.py` | Provider & key configuration |

Cross-cutting: `services/workspace.py` (project files + build cache),
`services/git.py` (safe git ops), `services/ai/providers.py` (provider
abstraction: heuristic, ollama, openrouter), `config.py` (env-driven).

## 5. The IDE

`ide/` — React 18 + TypeScript + Tailwind + Monaco + zustand, wrapped in
Electron.

- **Workbench chrome**: custom title bar, activity bar (explorer, search, git,
  database, plugins, settings), status bar (provider, branch, diagnostics
  count, build state).
- **Editor**: Monaco with a custom IntentLang Monarch grammar, snippet
  autocomplete, hover docs, and live diagnostics pulled from
  `/api/compile/validate` on debounce.
- **Chat**: streaming chat that drives the pipeline; messages render the
  stepper, IntentLang source, and generated files inline.
- **Bottom panels**: compiler console (build output), problems (diagnostics),
  preview (generated standalone app in an iframe), output.
- **Database viewer**: lists tables and rows from the generated app via the
  backend DB router.
- **Git panel**: status, diff, commit, log.
- **Onboarding**: the pipeline stepper turns one English sentence into a
  running project in a few clicks.

## 6. Extensibility

- **Plugins** (`ide` marketplace + `codegen/plugins/`): generators can be
  registered by id; the PWA and SEO generators ship as examples. The backend
  plugin router lists and installs plugins into a workspace.
- **New code generators**: implement `CodeGenerator` from `codegen/base.py`
  and register in `codegen/registry.py` — no compiler changes needed.
- **New AI providers**: implement the provider interface in
  `services/ai/providers.py` and select it via `INTENTOS_AI_PROVIDER`.
