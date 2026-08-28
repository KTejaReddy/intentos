# IntentOS AI Policy

IntentOS exists because AI-generated production code is non-deterministic,
unreviewable, and unmaintainable. The platform's core rule:

> **AI writes IntentLang. The compiler writes code. Never the reverse.**

## What AI may do

| Task | Where | Example |
|------|-------|---------|
| Understand intent | `services/ai` | "food delivery startup for Hyderabad" → domain, users, entities, features |
| Complete requirements | `missing_requirements()` | Ask "Should the app include online payments?" |
| Plan the product | pipeline stage 3 | Scope estimate, PRD, feature list |
| Improve/explain syntax | chat | Answer "what does `When Login succeeds` mean?" |
| Explain errors | chat | Turn compiler diagnostics into advice |
| Research competitors | chat | Summarize comparable products from the web |
| Generate documentation | `docs.py` generator | README + API reference |

## What AI may never do

- **Emit production source code directly.** No React components, no SQL, no
  FastAPI routes written by a model.
- **Edit generated artifacts by hand.** All concrete output flows through the
  compiler; artifacts are regenerated deterministically from IntentLang.
- **Skip the compiler.** Even when an LLM provider is used, its only output is
  a `.il` program that is then *compiled and validated*. If the LLM output
  fails to compile, the pipeline falls back to the heuristic planner.

## Enforcement

1. **Provider isolation** (`services/ai/providers.py`): every provider returns
   structured intent, never code. The LLM prompt (`prompts.py`) hard-constrains
   output to IntentLang syntax.
2. **Compile-gate**: the pipeline always runs the generator output through the
   compiler; diagnostics abort the stage and trigger fallback.
3. **Offline default**: the default provider is `heuristic` — a deterministic
   rule-based planner that needs no model, no key, no network. LLM providers
   (Ollama, OpenRouter/Qwen) are opt-in.

## The default: heuristic planner

`backend/app/services/ai/heuristic.py` implements intent parsing as pure
rules: keyword-based domain detection across 10 industries, entity/page
templates per domain, intent-keyword feature detection (login, payments,
notifications, search, reviews, tracking, admin, chat), location extraction,
and missing-requirement heuristics. Same idea → same IntentLang, always. This
is what makes IntentOS work out of the box with zero configuration.
