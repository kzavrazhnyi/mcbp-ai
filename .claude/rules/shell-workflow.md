# macOS / zsh Workflow

This config runs on macOS (Apple Silicon or Intel) with **zsh** as the default shell and **bash**
available for scripts. Default to POSIX shell syntax (not PowerShell). This is the **default platform**
for generated configs. Two policies below remove most day-to-day friction: a long-command workflow and
a project-scope edit policy that stops asking for permission on every file write.

## Long-Command Policy

macOS shells have **no inline command-length ceiling** (unlike Windows PowerShell's ~965-byte parser
limit). You can issue long pipelines inline. Still, for any multi-step batch (more than ~5 file ops, or
anything you may want to re-run), prefer a script file:

1. **Write** the script to `./.scripts/<task-name>.sh` via the `Write` tool. `.scripts/` is gitignored
   by convention and is the standard parking spot for ad-hoc one-shot scripts.
2. **Execute** it:
   ```bash
   bash ./.scripts/<task-name>.sh
   ```
3. **(Optional)** Remove it afterwards if truly one-shot; keep it if the user may re-run.

A single `.sh` file is one logical unit, one approval, one diff — better audit trail than many inline
calls.

## Project-Scope Edit Policy

**Inside the project working directory, all of these are auto-accepted:**
- `Edit`, `Write`, `MultiEdit` (Claude tools)
- `cp`, `mv`, `mkdir`, `touch`, `ln -s`, `chmod`, `rm` of project files

Rationale: every change is captured by git. The diff and commit history is the audit trail. Asking the
user to confirm a routine `mv ./old.py ./new.py` produces no safety, only latency.

**Outside the project working directory:** still requires user approval. Operations touching
`~/Library/`, `/usr/`, `/opt/homebrew/` (except via `brew`), another project under `~/projects/...`,
etc. SHALL prompt — never silently. Glob patterns like `Edit(./**)` are project-relative, so this
holds automatically.

**Always-denied (regardless of scope):** `Read(./**/.env*)`, `Read(./**/*.key)`, `Read(./**/*.pem)`,
`Read(./**/*.crt)`, `Read(./**/dbconn.php)`. Deny rules always win over allow.

## Shell Allow-List

The canonical macOS allow-list (bash cp/mv/mkdir/touch, bash .scripts/*.sh, uv/python, brew read-only)
is in `settings.json` → `permissions.allow`.

## Multi-Version Runtimes

This project uses Python 3.11+ managed via `uv` venv in `backend/.venv/`.

### Python — `uv`

`uv` manages Python versions and per-project environments:

```bash
uv python install 3.11 --default
uv venv backend/.venv
uv run python -m pytest backend/tests/
```

- **`uv run python -m py_compile <file>`** — uses the project's pinned interpreter (`.python-version`).
- **`python3.11` / `python3.12` / `python3.13`** — always-available version shims in `~/.local/bin`.
- **PATH note:** `~/.local/bin` must come before `/usr/bin` in `~/.zshrc`.

## zsh / bash vs PowerShell Pitfalls

These bite when you copy a PowerShell snippet. macOS uses POSIX shell:

| PowerShell (Windows) | macOS zsh / bash |
|---|---|
| `2>$null` | `2>/dev/null` |
| `Test-Path file` | `[ -f file ]` / `[ -e file ]` |
| `$env:VAR = 'x'` | `export VAR=x` |
| `New-Item -ItemType Directory -Force d` | `mkdir -p d` |
| `Move-Item a b` | `mv a b` |
| `Copy-Item -Recurse a b` | `cp -R a b` |
| `Remove-Item -Recurse -Force d` | `rm -rf d` |
| `Get-Content f -TotalCount 5` | `head -n 5 f` |
| `Get-Content f -Tail 5` | `tail -n 5 f` |
| `Get-ChildItem` | `ls` / `find` |
| `Select-String pat f` | `grep pat f` |
| `(Get-Command cmd).Source` | `which cmd` |

## Interactive Commands to Avoid

Claude Code runs the shell non-interactively. Avoid commands that block on input:
- `read` (bare prompt), `sudo` without cached credentials (prompts for password)
- `ssh`/`scp` to a host needing an interactive password
- anything that opens a pager (`less`, `man`) without `| cat` — pipe to `cat` or use `--no-pager`

If a step needs the user to authenticate interactively (e.g. `gcloud auth login`), suggest the user
run it themselves via `! <command>` in the Claude Code prompt.

## Common-Mistake Bullets

- **Don't** `cd` before commands — the working directory is already set by the harness, and `cd` can
  trigger permission prompts. Use absolute or project-relative paths.
- **Don't** use `Start-Sleep` / busy-poll for background jobs Claude already tracks.
- **Don't** assume GNU coreutils flags — macOS ships BSD `sed`/`grep`/`date`. Prefer portable flags.

## Encoding & Line Endings

- Default UTF-8, no BOM — safe for Python.
- Line endings: LF (`\n`).

## Trigger phrases (UA)

мак, macos, zsh, bash, оболонка мак, homebrew, brew, uv, python версії, .sh скрипт,
дозволи мак, перенесення файлів мак, mv cp mkdir, мультиверсійність.
