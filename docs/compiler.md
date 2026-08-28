# The IntentLang Compiler

`compiler/intentlang/` is a complete, **zero-dependency** Python compiler.
Roughly 4,000 lines. No external packages — it runs on any Python ≥ 3.10.

## Compilation pipeline

```
 source ─► LEXER ─► PARSER ─► AST ─► SEMANTIC ─► IR ─► GENERATORS ─► artifacts
            │          │         │        │         │
            └──────────┴─────────┴────────┴─────────┴──► structured diagnostics
```

### 1. Lexer (`lexer.py`)

- Tokenizes identifiers, multi-word names, strings, numbers, booleans, lists,
  routes (including `/` and `{param}`), punctuation, and operators
  (`=`, `==`, `>`, `<`, `>=`, `<=`, `!=`).
- Tracks **indentation** per line and emits `INDENT`/`DEDENT` tokens, giving
  the parser block structure without braces.
- Strips `//` comments.
- **Error recovery**: on an unexpected character it emits a diagnostic and
  continues scanning, so one bad character never kills the whole lex.

### 2. Parser (`parser.py`)

- Recursive descent over a strictly ordered grammar:
  `Application → Role* → Page* → Model* → Api* → When* → Deploy*`.
- **Panic-mode error recovery**: on a parse error it skips to the next
  statement boundary (`Create`, `When`, `Deploy`, EOF), records a diagnostic
  with a line/column range, and continues — so an IDE can show *all* errors
  in one pass, not just the first.
- Produces a typed AST (`ast.py`): `ApplicationStmt`, `RoleStmt`, `PageStmt`,
  `ModelStmt`, `ApiStmt`, `RuleStmt`, `DeployStmt`, plus widget and action
  nodes (`InputWidget`, `TableWidget`, `CallApiAction`, `NavigateAction`, …).

### 3. Semantic analyzer (`semantic.py`)

- **Two-phase symbol resolution**: declarations are collected across the whole
  program first, then references are resolved — so a page may reference a
  model or API declared later in the file.
- Checks: duplicate declarations, unknown references (models, pages, APIs,
  roles, widget ids), **method-aware route collisions** (`GET /x` + `POST /x`
  is legal; two `GET /x` is not), invalid field types, invalid auth targets,
  unresolved event bindings.
- Normalizes names: lowercase property keys, `Title Case` matching for
  references, and case-insensitive roles.
- Emits `Diagnostic`s with severity (`error` / `warning`), source range, and a
  human-readable message — these power the IDE's Problems panel.

### 4. Optimizer (`optimizer.py`)

- **Dead-entity elimination**: models unreferenced by any API, page, or rule
  are dropped (a project with `Order` but no orders UI gets a leaner schema).
- **Unreachable-route elimination**: pages never reachable from any rule or
  navigation action are dropped.
- The reachability root is the set of rules (`When …`) — deterministic and
  conservative. Can be disabled via `CompileOptions(optimize=False)`.

### 5. IR (`ir.py`)

- A normalized, **versioned** (`IR_SCHEMA_VERSION`) intermediate
  representation: `Application`, `Role`, `Model`/`Field`, `Api`/`ApiSection`,
  `Page`/`Widget`, `Rule`, `DeployTarget`.
- Fully JSON-serializable — it is the stable contract between the compiler
  front end and all 14 generators.

### 6. Code generators (`codegen/`)

Each generator consumes the IR and emits files deterministically:

| Generator | Files |
|-----------|-------|
| `frontend_react.py` | Vite React + TS: pages, widgets, events, API client, styling |
| `frontend_next.py`  | Next.js App Router scaffold |
| `frontend_flutter.py` | Dart/Flutter project |
| `backend_fastapi.py` | FastAPI + SQLAlchemy + SQLite/Postgres/MySQL |
| `backend_express.py` | Express + better-sqlite3 |
| `backend_spring.py` | Java Spring Boot + JPA |
| `db_sql.py`         | DDL for SQLite / PostgreSQL / MySQL |
| `docker.py`         | Dockerfile + compose |
| `github_actions.py` | CI workflow |
| `docs.py`           | README + API reference |
| `tests.py`          | Backend pytest + frontend vitest suites |
| `deploy.py`         | Fly.io / Render / Heroku configs |
| `standalone.py`     | Single-file HTML preview, zero dependencies |
| `plugins/`          | PWA manifest, SEO metadata |

Generators are registered in `registry.py` by target id and selected via
`CompileOptions(targets=[...])`.

### 7. Incremental compilation (`incremental.py`)

- Source is split into sections at statement boundaries; each section is
  hashed. On recompile, only changed sections re-enter the pipeline; unchanged
  sections reuse cached IR, and diagnostics are re-merged by source range.
- Result: near-instant rebuilds in the IDE for all-but-tiny edits.

### 8. Driver (`compiler.py`, `cli.py`)

- `Compiler.compile(source, options)` returns `CompileResult` with `ok`,
  `diagnostics`, `ir`, and `artifacts`.
- `intentlang compile <file> -o <dir>` writes artifacts to disk.
- `intentlang run <file>` starts a live preview server of the generated
  standalone app.
- `intentlang fmt <file>` canonicalizes source formatting.

## Determinism

All generators iterate IR in declaration order, use stable name-mangling
(`to_pascal` / `to_snake` / `to_kebab` in `_util.py`), and never consult wall
clocks or randomness. Identical input ⇒ byte-identical output.

## Testing

`compiler/tests/test_compiler.py` covers the full pipeline: lexing, parsing,
error recovery, semantic errors (unknown refs, collisions, duplicates), the
optimizer, every generator, determinism, and end-to-end compiles of the sample
program. Run with `python -m unittest discover -s tests` from `compiler/`.
