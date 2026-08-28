# IntentOS Release Audit

Below is the comprehensive audit report detailing the current state of the IntentOS codebase, specifically targeting technical debt, stubs, security risks, and architectural limitations.

## 1. TODOs & FIXMEs
*No active `TODO` or `FIXME` comments were found in the core Python compiler or TypeScript IDE source files (excluding `node_modules`).*

## 2. Placeholders & Mocked Implementations

| File Path | Description | Severity | Recommendation |
| :--- | :--- | :--- | :--- |
| `backend/app/services/pipeline.py` | Extensive LLM fallbacks (`except Exception: pass`) wrapping every AI generator step. If the LLM output is malformed, it silently falls back to a hardcoded "offline" heuristic, suppressing the real error. | **High** | Remove `pass` blocks. Surface LLM generation errors to the IDE Pipeline Visualizer. |
| `backend/app/services/pipeline.py` | Database schema initialization swallows SQL application errors via `except Exception: pass` (Line 113). | **Medium** | Log schema application errors and inject them into project diagnostics. |
| `compiler/intentlang/codegen/backend_fastapi.py` | Generation for non-CRUD APIs produces Python functions containing only `pass` (Line 198). | **Medium** | Generate a proper `raise HTTPException(status_code=501)` instead of an empty `pass` stub. |
| `compiler/intentlang/codegen/base.py` | Base `Generator.generate()` method relies on `raise NotImplementedError`. | **Low** | Replace with explicit `abc.abstractmethod` to enforce implementation at import-time. |

## 3. Hard-coded Values

| File Path | Description | Severity | Recommendation |
| :--- | :--- | :--- | :--- |
| `compiler/intentlang/codegen/docker.py` | Hardcoded database credentials in generated `docker-compose.yml` (`POSTGRES_PASSWORD: postgres`, `MYSQL_ROOT_PASSWORD: root`). | **Critical** | Inject `.env` variables or securely generate random secrets during Docker setup. |
| `compiler/intentlang/codegen/backend_fastapi.py` | JWT signing secret defaults to `change-me-in-production`. | **High** | Force the user to supply an environment variable via `.env` in the compiled artifact instead of a fallback string. |
| `compiler/intentlang/codegen/backend_spring.py` | Hardcoded fallback database passwords. | **High** | Require explicit datasource password configurations. |

## 4. Unsupported IntentLang Features

| Feature | Description | Severity |
| :--- | :--- | :--- |
| **Control Flow (If/Else)** | IntentLang currently lacks support for explicit `If/Else` blocks or conditional branching within `When Clicked` rules. | **Medium** |
| **Loops & Iterators** | No syntax exists for mapping over lists or executing arbitrary loops within the IntentLang action scope. | **Medium** |
| **Complex Data Types** | Arrays, nested JSON objects, and NoSQL document structures are not supported by the SQL schema IR generators. | **Low** |
| **Token Invalidation** | Backend generators do not emit Redis-backed token blacklist infrastructure, relying entirely on client-side logout. | **High** |

## 5. Failing or Skipped Tests

* **Compiler Test Suite:** 30 / 30 Tests Passing `[0 Skipped, 0 Failed]`
* **Backend API Test Suite:** 9 / 9 Tests Passing `[0 Skipped, 0 Failed]`

*The platform maintains a 100% test pass rate across all automated pipelines.*

## 6. Known Bugs & Technical Debt

| File Path | Description | Severity | Recommendation |
| :--- | :--- | :--- | :--- |
| `compiler/intentlang/parser.py` | **Debt:** Abstract Syntax Tree (AST) nodes are constructed dynamically without strict Python `dataclass` types. This requires heavy reliance on `hasattr` and `__dict__` for serialization. | **Medium** | Migrate `ast.py` to strict `dataclasses` (like `ir.py`) for enhanced compiler safety and automated JSON schema generation. |
| `compiler/intentlang/incremental.py` | **Debt:** The incremental cache hashes whole file contents. A single line change invalidates the entire file's AST and IR cache. | **Low** | Hash at the statement/node level to allow sub-file incremental compilation. |
| `compiler/intentlang/codegen/db_sql.py` | **Bug:** Changes to a model in IntentLang result in full `CREATE TABLE` dumps. There is no diffing engine to generate safe `ALTER TABLE` migrations. | **Critical** | Implement an Alembic/Prisma style migration generator to prevent data loss. |
