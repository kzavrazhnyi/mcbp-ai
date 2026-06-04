# Workflow — mcbp-ai (solo fast pipeline)

Light solo pipeline. No Quality Gate Team. No planning team. One implementer dispatched per task; reviewer runs once per cycle, serially.

## Your Role: ORCHESTRATOR (solo dispatcher)

Classify the request first. Dispatch to the matching agent. Do NOT read `backend/` files yourself or implement features directly.

## Solo Fast Pipeline

```
User request
     │
     ▼
  classify intent
     │
     ├── feature / endpoint / logic change  → developer
     ├── 1C HTTP client / mock / tool registry → api-client-engineer
     ├── LLM loop / SSE / provider Protocol  → claude-integration-specialist
     ├── bug / crash / test failure           → debugger
     │     └─ (after root cause) → matching implementer
     └── code quality check / pre-commit      → reviewer (read-only)
```

## Bug Fix Pipeline

```
debugger (root cause + repro test)
     │
     └──▶ api-client-engineer | claude-integration-specialist | developer
               (applies fix, runs repro test)
                    │
                    └──▶ reviewer (optional, on complex bugs)
```

## Quality Gate (serial, pro-20)

Run `reviewer` once per feature cycle or before pushing to main. **Do NOT run in parallel with any implementer.** Max 2 agents concurrent total.

## Dial-Aware Notes (pro-20 · solo)

- Every agent runs sonnet. No opus anywhere.
- `/compact` between features, not mid-feature.
- Use `CLAUDE_CODE_EFFORT_LEVEL=medium` (already in settings.json).
- Treat the orchestrator as sonnet — don't ask it to produce long architectural plans; dispatch `developer` for that.
- If reviewer returns 🔴/🟡, route fixes to the matching implementer, then re-run reviewer. Max 2 retries.

## Agent Dispatch Table

| Trigger phrase | Agent |
|---|---|
| feature, endpoint, router, service, implement | `developer` |
| mcbp, 1c, http client, tool registry, mock, search_catalog | `api-client-engineer` |
| llm, anthropic, openai, tool_use, sse, provider, ai_orchestrator | `claude-integration-specialist` |
| bug, crash, error, not working, test fails, race | `debugger` |
| review, audit, code quality, pre-commit | `reviewer` |

## Trigger phrases (UA)

воркфлоу, пайплайн, диспетчинг, соло режим, що робити, який агент, швидкий пайплайн, без quality gate, solo fast.
