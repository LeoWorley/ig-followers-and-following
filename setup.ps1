param(
    [switch]$SkipInstall,
    [switch]$RunLoginOnly
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvDir = Join-Path $root "venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"

function Resolve-PythonCommand {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        return "py -3"
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        return "python"
    }
    throw "Python not found. Please install Python 3.10+ first."
}

Write-Host "Project root: $root"

if (-not (Test-Path $venvPython)) {
    $pyCmd = Resolve-PythonCommand
    Write-Host "Creating virtual environment..."
    Invoke-Expression "$pyCmd -m venv `"$venvDir`""
}

if (-not $SkipInstall) {
    Write-Host "Installing dependencies..."
    & $venvPython -m pip install --upgrade pip
    & $venvPython -m pip install -r (Join-Path $root "requirements.txt")
}

$envExample = Join-Path $root ".env.example"
$envPath = Join-Path $root ".env"
if ((Test-Path $envExample) -and -not (Test-Path $envPath)) {
    Copy-Item $envExample $envPath
    Write-Host "Created .env from .env.example. Update credentials before running."
}

New-Item -ItemType Directory -Path (Join-Path $root "reports") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $root "exports") -Force | Out-Null

if ($RunLoginOnly) {
    Write-Host "Running login-only flow (visible browser)..."
    $env:LOGIN_ONLY_MODE = "true"
    $env:HEADLESS_MODE = "false"
    & $venvPython (Join-Path $root "main.py")
}

Write-Host ""
Write-Host "Setup complete."
Write-Host "Next steps:"
Write-Host "1) Edit .env with IG_USERNAME / IG_PASSWORD / TARGET_ACCOUNT"
Write-Host "2) First login: .\venv\Scripts\python.exe main.py (with LOGIN_ONLY_MODE=true, HEADLESS_MODE=false)"
Write-Host "3) Start GUI: .\start_gui.ps1"
