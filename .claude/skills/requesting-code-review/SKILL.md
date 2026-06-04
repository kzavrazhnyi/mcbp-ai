---
name: requesting-code-review
description: "Use when completing tasks, implementing major features, or before pushing to verify work meets requirements. Dispatches the reviewer agent with precisely crafted context. Trigger — EN: code review, request review, review before push, review after feature. Trigger — UA: рев'ю коду, перевірити код, code review, попросити рев'ю, ревʼю перед пушем."
---

# Requesting Code Review

Dispatch the `reviewer` agent to catch issues before they compound. The reviewer gets precisely crafted context for evaluation.

**Core principle:** Review early, review often.

## When to Request Review

**Mandatory:**
- After completing a major feature
- Before push to `main`

**Optional but valuable:**
- When stuck (fresh perspective)
- After fixing a complex bug

## How to Request

**1. Get git SHAs:**
```powershell
$BASE_SHA = git rev-parse HEAD~1   # or origin/main
$HEAD_SHA = git rev-parse HEAD
```

**2. Dispatch `reviewer` agent** via `SendMessage` or `Agent` tool.

Fill template with:
- `{DESCRIPTION}` — brief summary of what you built
- `{PLAN_OR_REQUIREMENTS}` — what it should do
- `{BASE_SHA}` — starting commit
- `{HEAD_SHA}` — ending commit

**3. Act on feedback:**
- Fix 🔴 Critical issues immediately
- Fix 🟡 Important issues before proceeding
- Note 🔵 Suggestions for later

## Reviewer Context Template

```
Review the changes in this git range for mcbp-ai:

DESCRIPTION: {DESCRIPTION}
REQUIREMENTS: {PLAN_OR_REQUIREMENTS}

Git range: {BASE_SHA}..{HEAD_SHA}

Run: git diff {BASE_SHA} {HEAD_SHA}

Check:
1. Does implementation match requirements?
2. Layering: routers → services → clients, no upward imports?
3. Async: all I/O awaited, no sync httpx?
4. Types: full annotations, Pydantic v2 API?
5. Tests: mock/respx used, no live 1C or LLM calls?
6. Security: no hardcoded creds, no print() with sensitive data?

Report: Strengths / 🔴🟡🔵 Issues / Assessment
```

## Integration

- Use after every feature dispatch to `developer`, `api-client-engineer`, or `claude-integration-specialist`.
- Route 🔴/🟡 findings to the matching implementer; re-run reviewer after fixes. Max 2 retry cycles.

## Trigger phrases (UA)

рев'ю коду, перевірити код, code review, попросити рев'ю, ревʼю перед пушем, requesting-code-review.
