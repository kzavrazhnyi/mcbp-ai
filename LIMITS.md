# LIMITS.md — Consumption Guide

This config is tuned for:

- **Team size:** `solo` (solo · small · large)
- **Plan tier:** `pro-20` (pro-20 · max-100)
- **Platform:** `windows` (macos · windows · linux) — selects the shell rule, permissions allow-list, and hook syntax
- **Effective model map:**

```text
orchestrator: sonnet
developer: sonnet
api-client-engineer: sonnet
claude-integration-specialist: sonnet
reviewer: sonnet
debugger: sonnet
```

Every `model:` field in every agent in `.claude/` matches this map. **NO opus anywhere in this config.**

---

## What Burns Limits Fastest

Roughly in descending cost order on the standard pricing:

1. **Opus dispatches.** ~5× the cost of Sonnet for the same work. Most-expensive role: `architect`
   in plan mode. Cheapest place to spend it: `reviewer` running once at the end of a cycle.
2. **Parallel agents.** N parallel agents = N× tokens/minute. A 3-member parallel quality-gate team
   on Opus is the single most expensive operation in this config.
3. **Large `@imports` in CLAUDE.md.** Every session loads everything `@import`ed in `CLAUDE.md` into
   the orchestrator's context. A 5-rule chain at 200 lines each = 1k lines loaded on EVERY message.
   Keep `CLAUDE.md` `@imports` lean; per-agent rules import inside the agent body, not globally.
4. **MCP-heavy agents.** Each MCP call costs both tokens and latency. Avoid speculative MCP calls;
   dispatch the agent only when the MCP server is needed.
5. **Long sessions without compaction.** Context grows linearly until compaction. A 4-hour session
   without `/compact` carries an inflated prompt on every turn.
6. **Re-reading files Claude already read.** Cheap but adds up. The harness caches; let it.

## Per-Tier Expectation Table

| Aspect | `pro-20` ($20/mo) | `max-100` ($100/mo) |
|---|---|---|
| Opus availability | Effectively none (caps fast) | Available, used selectively |
| Realistic concurrent agents | 2 | 4 |
| Quality-gate execution | Serial (one at a time) | Parallel team |
| Daily heavy-feature cycles | ~3-5 | ~12-20 |
| Best-fit team sizes | `solo`, `small` | `solo`, `small`, `large` |
| Long-running tasks at once | 1 | 2-3 |
| Recommended session length | ≤ 90 min, compact between features | ≤ 3 h, compact between features |
| When you hit the cap | Switch to read-only / triage work | Same, but rare |

## Practical Tips (apply to THIS config)

**On `pro-20`:**

- Run `reviewer`, `tester`, `security-scanner` **serially**, not as a parallel team.
- Prefer one quality-gate agent at a time — even when the workflow preset allows a team.
- Use `/compact` between features, not just between sessions.
- Avoid dispatching MCP-heavy agents speculatively — only when the task needs them.
- If a feature feels stuck, **stop and replan** instead of looping the same agent on Opus.
- Treat the orchestrator as Sonnet — don't ask it to write plans long enough to need Opus.

**Both tiers:**

- A change that touches > 5 files should go through `AskUserQuestion` for forks — cheaper than
  one wrong Opus dispatch.
- If `reviewer` returns 🟡 twice in a row on the same artifact, escalate to the user rather than
  running a third fix cycle.
- `karpathy-discipline` rule (already in `.claude/rules/`) is the single biggest token-saver —
  agents that obey it cut wasted tool calls roughly in half.

## How To Switch Tiers

Tier is the `plan-tier` dial. To regenerate this config on a different tier:

1. Re-run the interview (`/new-project` or `/wrap-project <path>`) for this archetype.
2. At the plan-tier question, pick the other value.
3. `config-author` will rewrite every `model:` field, the `settings.json` `model:`, and this
   `LIMITS.md` — the topology (which agents exist) does NOT change.

## Glossary

- **Opus / Sonnet / Haiku** — Claude model variants in descending cost order.
- **`opusplan`** — orchestrator default that uses Opus only in plan mode, Sonnet for execution.
- **Cache hit rate** — fraction of prompt tokens served from prompt cache. `/compact` reduces it
  briefly then it recovers as the new compacted context warms.
- **`TeamCreate`** — a quality-gate or planning team spawn. Each adds parallel agents + tokens.

## Trigger phrases (UA)

ліміти, limits, скільки витрачає, що з'їдає токени, дорогі дії, як економити, паралельні агенти,
opus витрати, max plan, pro plan, налаштування ліміту, як зменшити витрати, compact сесії,
порада економії, бюджет, $20, $100, перемкнути план.
