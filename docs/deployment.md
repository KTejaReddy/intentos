# Running & Deploying IntentOS

IntentOS itself ships as three services: the compiler (pure Python library),
the backend (FastAPI), and the desktop IDE (Electron).

## Local development

### Backend

```bash
cd backend
python -m venv .venv
# Windows:
.venv/Scripts/activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Environment (see `backend/.env.example`):

| Variable | Default | Meaning |
|----------|---------|---------|
| `INTENTOS_DATA_DIR` | `./data` | Where workspaces (projects) live |
| `INTENTOS_AI_PROVIDER` | `heuristic` | `heuristic` \| `ollama` \| `openrouter` |
| `OPENROUTER_API_KEY` | — | Required for the openrouter provider |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama endpoint |
| `OLLAMA_MODEL` | `qwen2.5:7b` | Default Qwen model |

### IDE

```bash
cd ide
npm install
npm run dev       # browser at http://localhost:5173
npm run electron  # native desktop window
```

The IDE expects the backend at `http://localhost:8000` (override with the
`VITE_API_BASE` env var if needed).

## Docker

The backend containerizes cleanly:

```bash
docker compose up --build
```

- API + docs: http://localhost:8000/docs
- Workspaces persist in the `intentos-data` volume.

## Tests

```bash
# Compiler (28 tests, no deps)
cd compiler && python -m unittest discover -s tests

# Backend (FastAPI test client)
cd backend && .venv/Scripts/python -m pytest tests -q

# IDE (typecheck + bundle)
cd ide && npm run build
```

## Production notes

- Run the backend behind a reverse proxy with TLS; the API is unauthenticated
  by design in v1 (single-user desktop deployment). Add auth middleware before
  exposing it publicly.
- The `heuristic` provider means no model infrastructure is required in
  production; if you enable an LLM provider, keep keys in the environment,
  never in the repo.
- Workspaces (`data/projects/*`) are plain directories — back them up with
  normal file-level tooling, and `git` inside each project works independently.
