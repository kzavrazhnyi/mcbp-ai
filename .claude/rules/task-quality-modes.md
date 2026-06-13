# Task Quality Modes: MVP vs Production

Quality posture is decided **per task**, not per project. The same config serves "перевір ідею за
годину" and "це піде в прод під навантаження" — this rule defines how the orchestrator tells them
apart and what each posture changes. It is NOT a dial: nothing in the topology or model map changes,
only which ceremony runs for this one task.

## Detecting The Posture

| Posture | Trigger phrases (EN) | Trigger phrases (UA) |
|---|---|---|
| **MVP** | "MVP", "quick prototype", "proof of concept", "spike it", "throwaway", "just make it work", "demo for tomorrow" | "мвп", "швидкий прототип", "прототип", "зроби швидко", "на швидку руку", "перевірити ідею", "демо на завтра", "тимчасове рішення" |
| **Production** (DEFAULT) | everything else — production is the default when no trigger phrase is present | все інше — без тригер-фрази постава завжди production |

Ambiguous ("зроби простенько")? Ask one short question — a wrong posture guess wastes a full
pipeline either way.

## What Each Posture Means

| Aspect | MVP (`mvp-fast-track`) | Production (standard pipeline) |
|---|---|---|
| Architecture | Concrete code, no speculative abstraction; patterns only where they remove duplication NOW | Stack preset's architecture rules apply in full (layers, patterns, boundaries) |
| Tests | One happy-path test or smoke check | Per the stack preset's `testing.md` — units + the matrix the change warrants |
| Review | Single lite pass, 🔴-only fixes; 🟡/🔵 logged to `TODO-mvp.md` | Full review; 🔴 and 🟡 fixed before done |
| Devil / planning team | Skipped | Per workflow preset (team-size dependent) |
| Pace | One implementer, vertical slice, scope frozen up front | Pipeline per `pipeline-selector` |

## NEVER Relaxed (either posture)

- **Security on critical zones** — auth, payments, PII, file uploads, raw queries: `security-scanner`
  (or the reviewer's security checklist on `pro-20`) runs even on an MVP slice.
- **`git-safety`** — no force-push, no secrets in diffs, commit hygiene.
- **Input validation on public boundaries** — every new endpoint/form validates its input.
- **Type safety on public APIs** — exported/public contracts stay typed even if internals are loose.
- **`surgical-changes`** — neither posture authorizes drive-by edits.

## MVP Debt Is Explicit

Every MVP task ends with a one-paragraph debt note in the report (and `TODO-mvp.md` if the project
keeps one): what was consciously skipped, what must happen before production traffic. Promoting an
MVP slice later = `refactor-pipeline` with that note as the charter input. An MVP that silently
becomes production code without that pass is how prototypes end up in prod — flag it when you see it.

## Trigger phrases (UA)

мвп, mvp, прототип, швидкий прототип, якість коду, продакшн якість, рівень якості, зроби швидко, на швидку руку, перевірити ідею, демо, тимчасове рішення, технічний борг, повноцінна реалізація.
