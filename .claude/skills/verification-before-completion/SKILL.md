---
name: verification-before-completion
description: "Use when about to claim work is complete, fixed, or passing, before committing or pushing. Requires running verification commands and confirming output before making any success claims. Trigger — EN: verify before done, verification, confirm tests pass, check before commit. Trigger — UA: перевірити перед закриттям, верифікація, підтвердити що працює, перевірити тести."
---

# Verification Before Completion

## Overview

Claiming work is complete without verification is dishonesty, not efficiency.

**Core principle:** Evidence before claims, always.

## The Iron Law

```
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

If you haven't run the verification command in this message, you cannot claim it passes.

## The Gate Function

```
BEFORE claiming any status or expressing satisfaction:

1. IDENTIFY: What command proves this claim?
2. RUN: Execute the FULL command (fresh, complete)
3. READ: Full output, check exit code, count failures
4. VERIFY: Does output confirm the claim?
   - If NO: State actual status with evidence
   - If YES: State claim WITH evidence
5. ONLY THEN: Make the claim

Skip any step = lying, not verifying
```

## Common Failures

| Claim | Requires | Not Sufficient |
|-------|----------|----------------|
| Tests pass | `python -m pytest backend/tests/ -v` → 0 failures | Previous run, "should pass" |
| Linter clean | `ruff check --no-fix backend/app/` → 0 errors | Partial check |
| Bug fixed | Test original symptom: passes | Code changed, assumed fixed |
| Requirements met | Line-by-line checklist | Tests passing |

## Verification Commands (mcbp-ai)

```bash
# Run all tests
python -m pytest backend/tests/ -v

# Lint check
ruff check --no-fix backend/app/ backend/tests/

# Syntax check a specific file
python -m py_compile backend/app/services/ai_orchestrator.py
```

## Red Flags — STOP

- Using "should", "probably", "seems to"
- Expressing satisfaction before verification ("Great!", "Perfect!", "Done!")
- About to commit/push without verification
- Trusting agent success reports
- Relying on partial verification

## Trigger phrases (UA)

перевірити перед закриттям, верифікація, підтвердити що працює, перевірити тести, verification-before-completion.
