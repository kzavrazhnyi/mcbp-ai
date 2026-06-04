---
name: brainstorming
description: "You MUST use this before any creative work — creating features, building components, adding functionality, or modifying behavior. Explores user intent, requirements and design before implementation. Trigger — EN: brainstorming, design before code, feature design, requirements exploration, what to build. Trigger — UA: мозковий штурм, планування фічі, дизайн перед кодом, що будуємо, генерація ідей, обговорення задачі."
---

# Brainstorming Ideas Into Designs

Help turn ideas into fully formed designs and specs through natural collaborative dialogue.

Start by understanding the current project context, then ask questions one at a time to refine the idea. Once you understand what you're building, present the design and get user approval.

<HARD-GATE>
Do NOT invoke any implementation skill, write any code, scaffold any project, or take any implementation action until you have presented a design and the user has approved it. This applies to EVERY project regardless of perceived simplicity.
</HARD-GATE>

## Anti-Pattern: "This Is Too Simple To Need A Design"

Every project goes through this process. A todo list, a single-function utility, a config change — all of them. The design can be short (a few sentences for truly simple projects), but you MUST present it and get approval.

## Checklist

You MUST complete these in order:

1. **Explore project context** — check files, docs, recent commits
2. **Offer visual companion** (if topic involves visual questions) — own message only
3. **Ask clarifying questions** — one at a time, understand purpose/constraints/success criteria
4. **Propose 2-3 approaches** — with trade-offs and your recommendation
5. **Present design** — in sections scaled to complexity, get user approval after each section
6. **Write design doc** — save to `docs/specs/YYYY-MM-DD-<topic>-design.md` and commit
7. **Spec self-review** — check for placeholders, contradictions, ambiguity, scope
8. **User reviews written spec** — ask user to review before proceeding
9. **Transition to implementation** — invoke writing-plans skill

**The terminal state is invoking writing-plans.** Do NOT invoke any other implementation skill.

## The Process

**Understanding the idea:**

- Check current project state first (files, docs, recent commits)
- Assess scope early — if multiple independent subsystems, flag for decomposition
- Ask questions one at a time; prefer multiple choice; one question per message
- Focus on: purpose, constraints, success criteria

**Exploring approaches:**

- Propose 2-3 different approaches with trade-offs
- Lead with your recommended option and explain why

**Presenting the design:**

- Scale each section to its complexity
- Ask after each section whether it looks right
- Cover: architecture, components, data flow, error handling, testing

**Design principles:**

- Break into units with one clear purpose each
- Smaller, well-bounded units are easier for reasoning and editing
- In existing codebases, explore structure first, follow existing patterns

## After the Design

**Documentation:**

- Write validated design to `docs/specs/YYYY-MM-DD-<topic>-design.md`
- Commit to git

**Spec Self-Review:**

1. **Placeholder scan:** Any "TBD", "TODO", incomplete sections? Fix them.
2. **Internal consistency:** Do sections contradict each other?
3. **Scope check:** Focused enough for a single plan?
4. **Ambiguity check:** Any requirement interpretable two ways? Pick one.

**User Review Gate:**

> "Spec written and committed to `<path>`. Please review it and let me know if you want any changes before we write the implementation plan."

**Implementation:** Invoke the `writing-plans` skill.

## Key Principles

- **One question at a time** — don't overwhelm
- **Multiple choice preferred** — easier to answer
- **YAGNI ruthlessly** — remove unnecessary features
- **Explore alternatives** — always propose 2-3 approaches
- **Incremental validation** — present design, get approval before moving on

## Trigger phrases (UA)

мозковий штурм, планування фічі, дизайн перед кодом, що будуємо, генерація ідей, обговорення задачі, brainstorming.
