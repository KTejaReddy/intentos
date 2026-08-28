# Architecture — StudentHub

```
English description
      |  IntentOS AI planner (produces IntentLang only)
      v
app.intentlang
      |  IntentLang compiler
      v
IR  ->  code generators
      |
      +-- frontend/   (React SPA)
      +-- backend/    (FastAPI + SQLAlchemy)
      +-- db/         (schema.sql)
      +-- infra/      (Docker / Compose)
      +-- .github/    (CI/CD)
```

## Components


## Data flow

1. The React SPA calls the FastAPI backend via the generated `src/api` client.
2. Endpoints validate auth (`security.py`), run the generated query, and return pydantic schemas.
3. Tables and charts fetch on mount; forms submit through the same client.
