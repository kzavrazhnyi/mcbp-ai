# Pipeline Selector

One table that answers, for every incoming task: which pipeline runs, which agents on which models,
plan mode or auto, and when to escalate. The orchestrator consults this BEFORE dispatching. Models
below are written as `max-100 / pro-20` — the LIMITS.md model map is the ground truth for this
config's resolved tier.

## Task Type → Pipeline

| Task type | Pipeline (workflow preset) | Agents (model max-100 / pro-20) | Mode | Limit cost |
|---|---|---|---|---|
| New feature (production) | `orchestrator-strict` (+ `planning-team` if >5 files) | architect (opus/sonnet) → implementer (sonnet) → quality gate: tester+reviewer+security (parallel opus-mix / serial sonnet) | **Plan mode** for the design, auto for execution | L |
| New feature (MVP) | `mvp-fast-track` | ONE implementer (sonnet) → review-lite (sonnet) | Auto (plan mode only if the user asks) | M |
| Bug fix | `bug-fix-pipeline` | debugger (opus/sonnet) → implementer (sonnet) → tester+reviewer verify | Auto — diagnosis IS the plan | M |
| Hotfix (prod is down) | `bug-fix-pipeline`, verify phase compressed to tester only | debugger (opus/sonnet) → implementer (sonnet) → tester | Auto, single-track; full review follows post-incident | S |
| Refactor | `refactor-pipeline` | architect (opus/sonnet) → implementer (sonnet) per zone → tester → reviewer diff-only | **Plan mode** for the invariant charter, auto per zone | L |
| Research / spike | direct dispatch, read-only | ONE explorer or architect (sonnet; opus only if architectural verdict needed) | Auto, read-only tools | S |
| Docs / README / PR text | direct dispatch | docs-writer (haiku) | Auto | S |
| Test data / boilerplate | direct dispatch | implementer (sonnet) or local LLM offload if enabled (see `local-llm-offload` rule, if present) | Auto | S |

Limit cost: S = single short dispatch · M = 2-3 dispatches · L = full pipeline with gate. See
LIMITS.md "Task Playbook" for worked examples with this config's resolved models.

## Plan Mode vs Auto — The Decision

Use **plan mode** when the task needs a design the user should see before code changes:
- New production feature touching >2 files, any schema/API contract change, any refactor charter.
- On `max-100` with `opusplan`, plan mode is also WHERE Opus reasoning happens — that's the cheapest
  place to spend it.

Use **auto** when the path is mechanical once known:
- Bug fixes (the debugger's root cause is the plan), docs, test authoring, verification runs,
  MVP slices with a frozen scope list.
- On `pro-20` (no `opusplan`), plan mode buys review-ability, not extra model power — use it for
  big features only, run everything else auto to save turns.

## Quality Posture Cross-Check

Before picking the row, check `task-quality-modes`: an explicit MVP request reroutes "new feature
(production)" → "new feature (MVP)". Default with no trigger phrase = production. MVP NEVER skips
security on auth/payment/PII zones.

## Escalate Instead Of Pipelining

- Task reveals an architectural fork mid-flight → stop, `AskUserQuestion`.
- Same agent fails the same gate twice (max-2-retry rule) → stop, report findings.
- Scope grows past the confirmed list (>~3 extra files) → reconfirm before continuing.
- The task type isn't in the table → orchestrator picks the closest row, states the choice in one
  line, and proceeds — don't silently invent a new pipeline.

## Trigger phrases (UA)

який пайплайн, вибір пайплайну, план чи авто, режим плану, яка модель для задачі, як запускати задачу, маршрут задачі, тип задачі, що використовувати для фічі, що для багфіксу, скільки коштує задача, дорожня карта задачі.
