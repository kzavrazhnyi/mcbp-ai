---
name: writing-plans
description: "Use when you have a spec or requirements for a multi-step task, before touching code. Writes comprehensive implementation plans with bite-sized steps, exact file paths, and complete code. Trigger — EN: writing plans, implementation plan, task breakdown, plan before coding. Trigger — UA: написати план, план реалізації, розбити на кроки, план розробки, планування задачі."
---

# Writing Plans

## Overview

Write comprehensive implementation plans assuming the engineer has zero context for the codebase and questionable taste. Document everything needed: which files to touch, code, how to test. DRY. YAGNI. TDD. Frequent commits.

**Announce at start:** "I'm using the writing-plans skill to create the implementation plan."

**Save plans to:** `docs/plans/YYYY-MM-DD-<feature-name>.md`

## Scope Check

If the spec covers multiple independent subsystems, suggest breaking into separate plans — one per subsystem. Each plan should produce working, testable software on its own.

## File Structure

Before defining tasks, map out which files will be created or modified:

- Design units with clear boundaries and well-defined interfaces
- Each file should have one clear responsibility
- Files that change together should live together — split by responsibility, not technical layer

## Bite-Sized Task Granularity

**Each step is one action (2-5 minutes):**
- "Write the failing test" → step
- "Run it to make sure it fails" → step
- "Implement the minimal code to make the test pass" → step
- "Run the tests and make sure they pass" → step
- "Commit" → step

## Plan Document Header

**Every plan MUST start with this header:**

```markdown
# [Feature Name] Implementation Plan

**Goal:** [One sentence describing what this builds]

**Architecture:** [2-3 sentences about approach]

**Tech Stack:** [Key technologies/libraries]

---
```

## Task Structure

````markdown
### Task N: [Component Name]

**Files:**
- Create: `exact/path/to/file.py`
- Modify: `exact/path/to/existing.py`
- Test: `backend/tests/test_<name>.py`

- [ ] **Step 1: Write the failing test**

```python
async def test_specific_behavior():
    result = await function(input)
    assert result == expected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/<file>.py::test_name -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

- [ ] **Step 4: Run test to verify it passes**

- [ ] **Step 5: Lint and commit**

```powershell
python -m pytest backend/tests/ -v
ruff check --no-fix backend/app/
git add <files>
git commit -m "feat: add specific feature"
```
````

## No Placeholders

Never write:
- "TBD", "TODO", "implement later"
- "Add appropriate error handling"
- "Write tests for the above" (without actual test code)
- Steps that describe what to do without showing how

## Self-Review

After writing the complete plan, check:

1. **Spec coverage:** Can you point to a task that implements each requirement?
2. **Placeholder scan:** Any red flags from the "No Placeholders" section?
3. **Type consistency:** Do types, method signatures, property names match across tasks?

## Trigger phrases (UA)

написати план, план реалізації, розбити на кроки, план розробки, планування задачі, writing plans.
