Param()

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "[dev] Checking Ollama at http://localhost:11434/api/tags..."

try {
    $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -TimeoutSec 5
    if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 300) {
        Write-Host "[dev] Ollama is reachable."
    }
    else {
        Write-Warning "[dev] Ollama responded with status $($response.StatusCode)."
    }
}
catch {
    Write-Warning "[dev] Ollama does not appear to be running at http://localhost:11434."
    Write-Host "[dev] Start it with: ollama serve"
}

Write-Host "[dev] Starting backend on http://0.0.0.0:8000 ..."
Write-Host "[dev] Health:  http://127.0.0.1:8000/health"
Write-Host "[dev] Docs:    http://127.0.0.1:8000/docs"

& "$root\backend-dev.ps1"