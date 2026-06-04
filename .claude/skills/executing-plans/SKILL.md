---
name: executing-plans
description: "Use when you have a written implementation plan to execute in a separate session with review checkpoints. Loads plan, reviews critically, executes all tasks, reports when complete. Trigger — EN: executing plans, implement plan, run plan, execute tasks from plan. Trigger — UA: виконати план, реалізувати план, імплементувати по кроках, запустити план."
---

# Executing Plans

## Overview

Load plan, review critically, execute all tasks, report when complete.

**Announce at start:** "I'm using the executing-plans skill to implement this plan."

## The Process

### Step 1: Load and Review Plan

1. Read plan file
2. Review critically — identify questions or concerns about the plan
3. If concerns: raise them before starting
4. If no concerns: proceed step by step

### Step 2: Execute Tasks

For each task:
1. Follow each step exactly
2. Run verifications as specified (tests, lint)
3. Mark as completed before moving to next

### Step 3: Final Verification

After all tasks:
- Run `python -m pytest backend/tests/ -v`
- Run `ruff check --no-fix backend/app/`
- Confirm all tests pass before reporting done

## When to Stop and Ask for Help

**STOP immediately when:**
- Hit a blocker (missing dependency, test fails, instruction unclear)
- Plan has critical gaps preventing starting
- You don't understand an instruction
- Verification fails repeatedly

**Ask for clarification rather than guessing.**

## Key Rules

- Review plan critically first
- Follow plan steps exactly
- Don't skip verifications
- Stop when blocked, don't guess
- Never start implementation on main branch without explicit user consent

## Trigger phrases (UA)

виконати план, реалізувати план, імплементувати по кроках, запустити план, executing plans.
