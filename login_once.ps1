$ErrorActionPreference = "Stop"
Set-Location -Path (Split-Path -Parent $MyInvocation.MyCommand.Path)

if (-not (Test-Path ".\venv\Scripts\python.exe")) {
    Write-Error "Virtual environment not found. Run .\setup.ps1 first."
}

$env:LOGIN_ONLY_MODE = "true"
$env:HEADLESS_MODE = "false"

Write-Host "Starting login-only flow (visible browser)..."
& .\venv\Scripts\python.exe .\main.py

if ($LASTEXITCODE -ne 0) {
    Write-Error "Login-only flow failed with exit code $LASTEXITCODE"
}

Write-Host "Done. Cookie should be stored in instagram_cookies.json."
