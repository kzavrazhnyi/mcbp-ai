# Windows / PowerShell Workflow

This config runs on Windows 11 with PowerShell 7+ as the primary shell. Default to PowerShell syntax
(not bash). Selected by the `platform` dial = `windows`. Two policies below remove most of the
day-to-day friction: a long-command workflow that dodges the parser limit, and a project-scope edit
policy that stops asking for permission on every file write.

## Long-Command Policy (965-byte ceiling)

Claude Code's permission-prompt parser on Windows enforces a hard ceiling of approximately **965 bytes
per inline command**. Scripts longer than that fail with:

```
Command contains malformed syntax that cannot be parsed: Command too long for parsing (<N> bytes). Maximum supported length is 965 bytes.
```

**Rule:** if a PowerShell command would exceed ~900 bytes (give yourself a 65-byte safety margin), DO
NOT issue it inline. Instead:

1. **Write** the script to `./.scripts/<task-name>.ps1` via the `Write` tool. The `.scripts/` folder is
   by convention gitignored and is the standard parking spot for ad-hoc one-shot scripts.
2. **Execute** it via the canonical form:
   ```
   powershell -NoProfile -ExecutionPolicy Bypass -File .\.scripts\<task-name>.ps1
   ```
3. **(Optional)** Remove the file afterwards if it's truly one-shot. Keep it if the user may want to
   re-run.

### When to use which

| Script size | Form |
|---|---|
| < 400 bytes (single mkdir, single Move-Item) | Inline PowerShell call |
| 400–900 bytes (small batch — 2-5 file ops + a couple of variables) | Inline, but break long pipelines onto multiple `;`-separated calls only if it shortens parsing |
| > 900 bytes | ALWAYS `.scripts/<name>.ps1` + `-File` execution |

### Why a file is better than chunking

Splitting one 1500-byte operation into three 500-byte inline calls works mechanically, but produces a
worse audit trail (three separate Bash entries in the transcript), three permission prompts if any
cmdlet isn't allow-listed, and breaks atomicity. A single `.ps1` file is one logical unit, one
approval, one diff.

## Project-Scope Edit Policy

**Inside the project working directory, all of these are auto-accepted:**
- `Edit`, `Write`, `MultiEdit` (Claude tools)
- `New-Item`, `Move-Item`, `Copy-Item`, `Remove-Item`, `Rename-Item`
- `Set-Content`, `Add-Content`, `Out-File`, `Clear-Content`

Rationale: every change is captured by git. The diff and commit history is the audit trail.

**Outside the project working directory:** still requires user approval. Operations that touch
`C:\Windows\`, `$env:USERPROFILE\Documents\<other-project>\`, `$env:APPDATA\`, `$env:ProgramFiles\`,
etc. SHALL prompt — never silently. Glob patterns like `Edit(./**)` are project-relative, so this holds
automatically.

**Always-denied (regardless of scope):** `Read(./**/.env*)`, `Read(./**/*.key)`, `Read(./**/*.pem)`,
`Read(./**/*.crt)`, `Read(./**/dbconn.php)`. Deny rules always win over allow.

## PowerShell Allow-List

All PowerShell cmdlets are pre-allowed in `settings.json` via the canonical Windows block from
`_library/platforms/windows/permissions.md`.

## Encoding & Line Endings

- **PowerShell 7+ default:** UTF-8 without BOM. Safe for almost everything.
- **PowerShell 5.1 (legacy Windows servers):** `Set-Content` default is **UTF-16 LE with BOM** — that
  breaks Python and most Unix-targeting tools. If you must run on PS 5.1, pass `-Encoding utf8`
  explicitly.
- **Line endings:** Windows `\r\n` is fine for most file types. Python scripts shipped to Linux are an
  exception — may need `dos2unix` post-processing.

## PowerShell vs Bash Pitfalls

| Bash | PowerShell |
|---|---|
| `2>/dev/null` | `2>$null` |
| `[ -f file ]` | `Test-Path file` |
| `cmd1 && cmd2` | PS 7+ supports `&&`; PS 5.1 needs `if ($?) { cmd2 }` |
| `` `cmd` `` | `$(cmd)` — backtick is the escape character in PS |
| `VAR=x cmd` | `$env:VAR='x'; cmd` |
| `export VAR=x` | `$env:VAR = 'x'` |
| `head -n 5 file` | `Get-Content file -TotalCount 5` |
| `tail -n 5 file` | `Get-Content file -Tail 5` |
| `which cmd` | `(Get-Command cmd).Source` |
| `rm -rf dir` | `Remove-Item -Recurse -Force dir` |
| `mkdir -p dir` | `New-Item -ItemType Directory -Force dir` |
| `touch file` | `New-Item -ItemType File file` (only if missing — `-Force` truncates!) |

## Interactive Cmdlets to Avoid

These hang the harness because Claude Code runs PowerShell with `-NonInteractive`:
- `Read-Host`, `Get-Credential`
- `Out-GridView`, `pause`
- `$Host.UI.PromptForChoice`
- `Remove-Item` against read-only/hidden items WITHOUT `-Force` (silently prompts)

## Common-Mistake Bullets

- **Don't** use raw `HKEY_LOCAL_MACHINE\…` registry paths — use `HKLM:\…`.
- **Don't** invoke executables with spaces in their path bare — use the call operator: `& "C:\Program Files\app\app.exe" arg`.
- **Don't** use `Start-Sleep` to poll for background jobs Claude already tracks.
- **Don't** chain `Set-Location` (`cd`) before commands — the working directory is already set.
- **Don't** prefix PowerShell with `cmd /c …` — you get the worst of both shells.

## Trigger phrases (UA)

вінда, windows, powershell, командний рядок, скрипт powershell, .ps1, ограничение команди,
command too long, 965 байт, дозволи powershell, права powershell, обмеження довжини команди,
move-item, new-item, remove-item.
