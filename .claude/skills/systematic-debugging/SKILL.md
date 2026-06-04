---
name: systematic-debugging
description: "Use when encountering any bug, test failure, or unexpected behavior, before proposing fixes. Four-phase process: root cause investigation → pattern analysis → hypothesis → implementation. Trigger — EN: debugging, bug fix, test failure, unexpected behavior, root cause. Trigger — UA: дебаг, знайти помилку, баг, помилка тесту, несподівана поведінка, корінь проблеми, налагодження."
---

# Systematic Debugging

## Overview

Random fixes waste time and create new bugs. Quick patches mask underlying issues.

**Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.

## The Iron Law

```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```

If you haven't completed Phase 1, you cannot propose fixes.

## The Four Phases

You MUST complete each phase before proceeding to the next.

### Phase 1: Root Cause Investigation

**BEFORE attempting ANY fix:**

1. **Read Error Messages Carefully** — don't skip errors; read stack traces completely; note line numbers, file paths, error codes

2. **Reproduce Consistently** — can you trigger it reliably? What are the exact steps? If not reproducible → gather more data, don't guess

3. **Check Recent Changes** — git diff, recent commits, new dependencies, config changes, environmental differences

4. **Gather Evidence in Multi-Component Systems** — add diagnostic instrumentation at each component boundary; run once to gather evidence showing WHERE it breaks; THEN analyze to identify failing component

5. **Trace Data Flow** — where does the bad value originate? What called this with the bad value? Keep tracing up until you find the source. Fix at source, not at symptom.

### Phase 2: Pattern Analysis

1. **Find Working Examples** — locate similar working code in the same codebase
2. **Compare Against References** — read reference implementation COMPLETELY before applying
3. **Identify Differences** — list every difference between working and broken, however small
4. **Understand Dependencies** — what settings, config, environment assumptions?

### Phase 3: Hypothesis and Testing

1. **Form Single Hypothesis** — "I think X is the root cause because Y"
2. **Test Minimally** — smallest possible change to test hypothesis; one variable at a time
3. **Verify Before Continuing** — worked? → Phase 4. Didn't work? → NEW hypothesis, don't stack more fixes
4. **When You Don't Know** — say "I don't understand X"; ask for help; don't pretend

### Phase 4: Implementation

1. **Create Failing Test Case** — simplest possible reproduction; MUST have before fixing
2. **Implement Single Fix** — address the root cause; ONE change at a time; no "while I'm here" improvements
3. **Verify Fix** — test passes? No other tests broken? Issue actually resolved?
4. **If Fix Doesn't Work** — STOP. Count: how many fixes tried?
   - < 3: return to Phase 1, re-analyze with new information
   - ≥ 3: STOP and question the architecture

## Red Flags — STOP and Follow Process

If you catch yourself thinking:
- "Quick fix for now, investigate later"
- "Just try changing X and see if it works"
- "It's probably X, let me fix that"
- "I don't fully understand but this might work"
- "One more fix attempt" (when already tried 2+)

**ALL of these mean: STOP. Return to Phase 1.**

## Quick Reference

| Phase | Key Activities | Success Criteria |
|-------|---------------|------------------|
| **1. Root Cause** | Read errors, reproduce, check changes, gather evidence | Understand WHAT and WHY |
| **2. Pattern** | Find working examples, compare | Identify differences |
| **3. Hypothesis** | Form theory, test minimally | Confirmed or new hypothesis |
| **4. Implementation** | Create test, fix, verify | Bug resolved, tests pass |

## Trigger phrases (UA)

дебаг, знайти помилку, баг, помилка тесту, несподівана поведінка, корінь проблеми, налагодження, systematic-debugging.
