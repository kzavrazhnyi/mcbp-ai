Generator: v2.5 (2026-06-10)

Config: **mcbp-ai** · team_size=`solo` · plan_tier=`pro-20` · platform=`macos`

A practical guide: which **session model** and **permission mode** to pick per command and
situation in THIS config. For cost details (model map, playbook, what burns limits) see `LIMITS.md`.

## Core Principle

The session model you pick affects only the **orchestrator** — triage, dispatch, and report
synthesis. Every agent in `.claude/agents/` carries its own `model:` in frontmatter and uses it
regardless of the session model. So a cheap session model does not weaken the pipeline agents,
and an expensive one does not upgrade them.

Permission modes (Shift+Tab cycles):

- **plan** — propose first, edit after approval. For multi-file features and refactor charters.
- **default** — ask before each edit. For careful one-off changes.
- **acceptEdits / auto** — edits apply automatically. For routine implementation inside the repo.

## Session Model Default

This config ships `settings.json` with `model: sonnet` — the right default for the
`pro-20` tier. Change it per-session with `/model` when a situation below calls for it;
the agents' own models stay as mapped in `LIMITS.md`.

## Per-Command Guide

This config ships no slash commands. All work is driven by natural-language dispatch to the
five specialized agents. The orchestrator (main CLAUDE.md session) handles triage and routing.

| Agent | What it does | Recommended session model | Mode | When |
|---|---|---|---|---|
| `developer` | FastAPI routers, services, core, frontend | sonnet | acceptEdits | Building or changing app features |
| `api-client-engineer` | 1C HTTP client, tool registry (the 6 tools) | sonnet | acceptEdits | Anything touching McbpClient or services/tools.py |
| `claude-integration-specialist` | LLM tool-use loop, SSE stream, providers | sonnet | acceptEdits | Changes to backend/app/llm/ or ai_orchestrator.py |
| `debugger` | Root-cause analysis, regression tests | sonnet | acceptEdits | Bug, crash, async race, test failure |
| `reviewer` | Read-only code review | sonnet | default | Before committing or PR; read-only, no writes |

## Situations & Limit-Saving

- **Stay on `sonnet` as the session model.** No `opusplan` on this tier — plan mode would burn
  the Pro Opus cap silently. Plan mode still buys review-ability; use it only for features
  touching >5 files and refactor charters.
- **Quality gates run serially** (reviewer → tester → security-scanner), one pipeline at a time.
- **Usage above ~70%?** Postpone L-cost pipelines (full feature + gate); run S/M tasks or wait
  for the reset.
- **`/clear` between unrelated tasks, `/compact` between features** — a long session re-reads
  its whole history on every turn.
- **Don't re-dispatch what an agent already answered** — reuse its report; re-runs are the
  silent budget leak.

| Situation | Do this |
|---|---|
| Big feature (>5 files) | Plan mode, then auto for execution |
| Bug fix / small change | Auto, no plan mode |
| Many small questions in a row | Stay on sonnet, `/clear` between topics |
| Usage > 70% before a big task | Postpone, or split into S/M chunks |
| Long session, context creeping up | `/compact` at a task boundary — never mid-task |

## Cost Details

Model map, Task Playbook, per-tier expectations, and what burns limits fastest: see `LIMITS.md`.
This guide does not duplicate them.

## One-Line Cheat-Sheet

| Agent | Session model | Mode |
|---|---|---|
| developer | sonnet | acceptEdits |
| api-client-engineer | sonnet | acceptEdits |
| claude-integration-specialist | sonnet | acceptEdits |
| debugger | sonnet | acceptEdits |
| reviewer | sonnet | default |

## What Ships Where

These files were copied from the generator's `projects/mcbp-ai/` output. The config's
`README.md` documents the config itself and stays in the generator archive — it is never copied
here. Everything that WAS copied (`.claude/`, `CLAUDE.md`, `.mcp.json`, `LIMITS.md`, this guide,
optional `ROADMAP.md`/`STATE.md`/`lessons.md`) is ignored by the `.gitignore` "Claude Code
configuration" block, so two configs never conflict in one repo. If your team decides to track
any of these in git, delete its line in `.gitignore`.

## Trigger phrases (UA)

гайд, як працювати з конфігом, яка модель, який режим, що обрати, шпаргалка, режим plan,
сесійна модель, економія лімітів, інструкція по конфігу.
