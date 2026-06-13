@.claude/rules/workflow.md
@.claude/rules/karpathy-discipline.md
@.claude/rules/shell-workflow.md
@.claude/rules/git-safety.md
@.claude/rules/surgical-changes.md
@.claude/rules/pipeline-selector.md
@.claude/rules/task-quality-modes.md
@.claude/rules/canonical-refs.md
@.claude/rules/code-style.md
@.claude/rules/architecture.md
@.claude/rules/testing.md

# mcbp-ai — Orchestrator

AI-driven FastAPI backend bridging a Ukrainian chat/REST UI to the BAS (1C) MCBP+ ERP over HTTP.

## Project Overview

**Core model-driven flow:**

```
User NL question
  → FastAPI receives request
  → feeds to LLM (Claude claude-opus-4-8 or OpenAI gpt-4o)
  → model picks data-fetch tool(s):
      search_catalog | get_documents | get_register_balance
      filter_catalog | list_metadata | describe_metadata
  → backend executes each tool against 1C MCBP_AI HTTP service
  → model loops until final answer is formed
  → SSE stream to frontend (/ui)
```

**No hardcoded query logic.** The LLM decides which tools to call and when. The backend is a pure executor.

## Stack

| Layer | Technology |
|---|---|
| Runtime | Python 3.11+ |
| Framework | FastAPI 0.115 + Uvicorn |
| HTTP client | httpx 0.27 (async pool) |
| Models | Pydantic 2.9 + pydantic-settings |
| LLM | anthropic 0.40 (claude-opus-4-8) + openai 1.54 (gpt-4o, lazy) |
| Tests | pytest 8.3 + pytest-asyncio (asyncio_mode=auto) + respx |
| Linter | ruff (line-length 100, py311) |
| Frontend | vanilla JS at /ui (no build step) |
| Deps | pip / pyproject.toml |

**NOT in stack:** mypy, Docker, ORM, Django.

## Project Layout

```
backend/
  app/
    core/          — config, settings, logging
    clients/       — mcbp.py (1C HTTP client), mock mode
    llm/           — provider Protocol, claude.py, openai.py, factory
    services/      — tools.py (tool registry), ai_orchestrator.py
    routers/       — chat.py (SSE endpoint), health.py
  frontend/        — vanilla JS UI served from /ui
  tests/           — pytest-asyncio test suite
  diagnose.py      — connectivity check script
  .env.example     — env var documentation
backend/
BACKEND_TECHNICAL.md   — full architecture reference
ANALYSIS_REPORT.md     — BAS HTTP service analysis
BAS_CODE_MAP.md        — 1C method name → purpose map
```

## Secrets (NEVER commit)

- `backend/.env` — `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `MCBP_ONEC_USER`, `MCBP_ONEC_PASSWORD`
- `backend/.venv/` — local Python virtualenv
- `bas/` — 1C vendor intellectual property
- `tmp/`, `logs/` — runtime artifacts

## Agent Topology (solo, sonnet-only)

| User intent | First agent | Description |
|---|---|---|
| Implement feature, add endpoint, fix logic | `developer` | FastAPI routers / services / core |
| Build/fix the 1C HTTP client or mock | `api-client-engineer` | backend/app/clients/ + tool registry |
| Build/fix LLM tool-use loop, SSE, provider | `claude-integration-specialist` | backend/app/llm/ + ai_orchestrator.py |
| Bug, crash, async race, test failure | `debugger` | root-cause + regression test |
| Code review before commit/PR | `reviewer` | read-only audit |

Max 2 parallel agents (pro-20 budget). Quality gate (`reviewer`) runs serially.

## 1C Tool Contract

Ground truth for the 6 data-fetch tools (endpoints, auth, retry, shapes): see `.claude/refs/onec-tool-contract.md`.

## MCP Stack

**context7 only.** All agents use `mcp__plugin_context7_context7__resolve-library-id` and `mcp__plugin_context7_context7__query-docs` for live framework docs lookup (FastAPI, httpx, Pydantic, Anthropic SDK).

## GitHub

Repo: `kzavrazhnyi/mcbp-ai`, branch `main`. No CI, no Docker, solo MVP.

## Orchestrator Hard Limits

- Do NOT open `backend/` files directly for implementation — dispatch the matching agent.
- Do NOT run `pip install`, `uvicorn`, or `pytest` yourself — that's the agents' job.
- Do NOT commit without explicit user request.
- Read `LIMITS.md` when usage feels tight.
