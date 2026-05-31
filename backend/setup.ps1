# Bootstrap venv for the backend (Windows / PowerShell).
# Run from the backend folder:  .\setup.ps1
# Then activate:                 .\.venv\Scripts\Activate.ps1
$ErrorActionPreference = 'Stop'
Set-Location -Path $PSScriptRoot

# 1. Create the venv if it does not exist yet
if (-not (Test-Path '.venv')) {
    Write-Host '==> Creating .venv ...' -ForegroundColor Cyan
    py -3 -m venv .venv
} else {
    Write-Host '==> .venv already exists - skipping creation.' -ForegroundColor Yellow
}

$py = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'

# 2. Upgrade pip and install the package with dev dependencies
Write-Host '==> Upgrading pip ...' -ForegroundColor Cyan
& $py -m pip install --upgrade pip
Write-Host '==> Installing dependencies (editable + dev) ...' -ForegroundColor Cyan
& $py -m pip install -e ".[dev]"

# 3. Create .env from the template if missing
if (-not (Test-Path '.env')) {
    Copy-Item '.env.example' '.env'
    Write-Host '==> Created .env from .env.example - edit it as needed.' -ForegroundColor Green
}

Write-Host ''
Write-Host 'Done. Activate the venv and start the server:' -ForegroundColor Green
Write-Host '  .\.venv\Scripts\Activate.ps1'
Write-Host '  uvicorn app.main:app --reload'
