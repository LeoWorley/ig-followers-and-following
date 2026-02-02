$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $root "venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    Write-Error "venv Python not found. Run: .\setup.ps1"
    exit 1
}

Start-Process -FilePath $python -ArgumentList "main.py" -WorkingDirectory $root
