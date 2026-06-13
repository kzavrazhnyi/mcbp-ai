# Canonical Refs — Single Source for Domain Ground Truth

Domain ground truth — probe results, capability matrices, API endpoint gotchas, version facts,
"known-absent" lists — lives in **exactly one file** under `.claude/refs/`. Every other file
(rules, agents, skills, README) points at it instead of restating it. The same folder also hosts
**reference offload** — bulky static reference material moved out of always-loaded rules (see below).

> **Why this is a rule.** A fact restated in many files WILL go stale unevenly. Evidence
> (2026-06-10): a wrong "endpoint absent" claim duplicated across ~10 files of one config took
> 3 full fix cycles to hunt down. With one canonical body it would have been a one-file fix.

## The Pattern

- `.claude/refs/<topic>.md` — one canonical body per fact domain (e.g.
  `refs/onec-tool-contract.md`). Header carries the marker line:
  *"Canonical source — every other file references this; never restate these facts elsewhere."*
- Everywhere else: a one-line pointer — `Ground truth: see .claude/refs/<topic>.md` — plus at most
  a minimal inline mention needed for sentence flow. **No endpoints, parameters, dates, or version
  numbers outside the ref file.**
- New probe/discovery results are written into the ref file ONLY. Updating any other file with a
  raw fact is a defect.

## When to Create a Ref File

Create `.claude/refs/<topic>.md` as soon as the same factual content would otherwise appear in
**2+ files**. Typical candidates: external-API capability matrices, probe/verification results,
legacy-version constraints, environment quirks, internal naming registries.

Do NOT use refs for behavioral process guidance (that's a rule), agent behavior (that's the agent
body), or one-off facts referenced from a single file. EXCEPTION: a rule's bulky *static reference
block* is an offload candidate — see the next section.

## Reference Offload (context budget)

Rules `@import`ed from `CLAUDE.md` load into context on **every turn**; `refs/` files load only
when an agent `Read`s them. So heavy *static reference content* inside an always-loaded rule is
paid for on every message while being needed only occasionally.

- When a rule carries a large static block (≳20 lines of lookup tables, catalogs, templates,
  command/API matrices, version maps) consumed only in specific situations → move the block to
  `.claude/refs/<topic>.md` and leave behind: the behavioral guidance (lean) + a one-line pointer
  (`Full reference: see .claude/refs/<topic>.md`) + the WHEN-to-read trigger.
- Ref files created this way carry the same canonical-source marker line as ground-truth refs.
- Do NOT offload: trigger keywords, short behavioral checklists (≲10 lines), or anything an agent
  needs on EVERY task of its type — splitting those costs an extra `Read` round-trip for no saving.

## Maintenance Contract (for every agent in this config)

1. Before asserting an external-API/domain fact, `Read` the matching ref file — it overrides
   anything remembered from other files or training data.
2. Discovered a new fact or invalidated an old one? `Edit` the ref file, then verify nothing else
   restates the old value: `grep -rn "<key term>" .claude/ *.md`.
3. Reviewer-type agents flag any detailed fact restated outside `refs/` as a finding.

## Trigger phrases (UA)

канонічне джерело, єдине джерело правди, рефи, refs, дублювання фактів, де оновити факт,
матриця можливостей, результати проб, застарілий факт, розсинхрон документації, винести в refs,
офлоад довідки, полегшити правило, бюджет контексту правил.
