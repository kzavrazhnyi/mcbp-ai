# Git Safety

Commit and push discipline. Conservative by default: the agent never mutates history or publishes
without an explicit request. Works whether or not the repo is initialized yet.

## Repository Not Yet Initialized

A generated config may land in a project that is not a git repo.

- **DO NOT run** `git init`, `git add`, `git commit` without explicit user confirmation.
- If the user asks to initialize — first show a plan: initial branch (`main`), confirm `.gitignore`
  covers secrets + logs + dependencies, whether to add a remote.
- Read-only git commands fail gracefully before init — they are safe to run anytime.

## Recommended .gitignore

Always ignore secrets and local artifacts:

```gitignore
# Secrets — NEVER commit
.env
.env.*
*.key
*.pem
*.crt
*.p12
credentials*

# Python
backend/.venv/
.venv/
__pycache__/
*.pyc
*.pyo
*.egg-info/
dist/
build/

# Logs & temp
*.log
logs/
tmp/
.scripts/

# Claude local settings
.claude/settings.local.json

# IDE / OS
.idea/
.vscode/
.DS_Store
Thumbs.db

# BAS vendor — 1C IP
bas/
```

## Once Initialized

- **NEVER** auto-commit — only when explicitly asked.
- **NEVER** push without an explicit request.
- **NEVER** force-push, `git reset --hard`, or `git clean -f` without explicit approval.
- Before committing, show `git status` + `git diff` for review.
- Branch off the default branch for non-trivial work rather than committing straight to it.

## Read-Only Git (allow-listed)

Safe anytime: `git status`, `git log`, `git diff`, `git show`, `git branch`, `git remote -v`,
`git ls-files`, `git rev-parse`, `git config --get`.

## Commit Message Conventions

- Subject ≤ 72 chars; optional body after a blank line.
- Focus on **what** changed and **why**, not how.
- No change statistics (file/line counts).
- **Do not mention AI / Claude** in commit messages.
- No test-plan checklist (no CI in this project).

Example:
```
Add search_catalog tool to mcbp client

Implements tool registration and httpx call with retry on 503.
```

## Trigger phrases (UA)

git, гіт, коміт, commit, push, гілка, merge, репозиторій, ініціалізація, gitignore, скинути, reset, форс-пуш, історія коммітів.
