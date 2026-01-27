Param()

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $root "..\backend"

Set-Location $backendDir

if (-not (Test-Path ".venv")) {
    Write-Host "[backend-dev] Creating virtualenv in backend\.venv"
    python -m venv .venv
}

$venvActivate = Join-Path ".venv" "Scripts\Activate.ps1"
if (-not (Test-Path $venvActivate)) {
    throw "[backend-dev] Could not find virtualenv activation script at $venvActivate"
}

Write-Host "[backend-dev] Activating virtualenv"
. $venvActivate

Write-Host "[backend-dev] Installing dependencies from requirements.txt (if needed)"
pip install --upgrade pip
pip install -r requirements.txt

Write-Host "[backend-dev] Starting uvicorn on http://0.0.0.0:8000"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload