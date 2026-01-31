$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonw = Join-Path $root "venv\Scripts\pythonw.exe"
$python = Join-Path $root "venv\Scripts\python.exe"

if (Test-Path $pythonw) {
    $exe = $pythonw
} elseif (Test-Path $python) {
    $exe = $python
} else {
    Write-Error "venv Python not found. Run: python -m venv venv; pip install -r requirements.txt"
    exit 1
}

Start-Process -FilePath $exe -ArgumentList "tray_app.py" -WorkingDirectory $root
