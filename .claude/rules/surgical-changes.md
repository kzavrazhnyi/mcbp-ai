# Surgical Changes

Touch only what the task requires. This rule expands Karpathy principle #3 (`karpathy-discipline`)
into a standing constraint for every implementer and debugger. The cheapest review is the diff that
contains nothing the task didn't need.

## The Rule

- Change only the lines the task requires. Do not reformat, re-order, or "tidy" untouched code.
- Match the existing style of the file you're editing — even if you'd personally write it differently.
- Only remove imports/variables/functions that **your** change orphaned — never pre-existing dead code
  (that's a separate, opt-in task).
- Do not refactor working code adjacent to your change. If it needs refactoring, say so; don't do it inline.
- No accidental behavior changes. A "cleanup" that alters behavior is a bug, not a cleanup.

## Scope Confirmation

- Before editing more than ~3 files, confirm the scope with the user (or the orchestrator).
- If the task reveals a larger problem, report it — don't silently expand the change to fix it.

## ✅ DO / ❌ DON'T

| ✅ DO | ❌ DON'T |
|---|---|
| Edit the function the task names | Rewrite the surrounding module "while you're there" |
| Keep the file's existing formatting | Run a formatter over the whole file |
| Remove an import your change orphaned | Delete unrelated pre-existing dead code |
| Note adjacent tech debt for later | Fix adjacent tech debt in this change |
| Add the one field the feature needs | Add speculative fields "for the future" |

## Why It Matters

Drive-by changes inflate the diff, hide the real change from reviewers, risk unrelated regressions,
and burn tokens. A surgical diff is faster to review, safer to merge, and cheaper to produce.

## Trigger phrases (UA)

хірургічні зміни, мінімальні правки, не рефактори зайве, не чіпай зайве, тільки потрібне, без drive-by, зберегти стиль, не форматувати весь файл, підтвердити обсяг змін.
