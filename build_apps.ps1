param(
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
Set-Location -Path (Split-Path -Parent $MyInvocation.MyCommand.Path)

if (-not (Test-Path ".\venv\Scripts\python.exe")) {
    Write-Error "Virtual environment not found. Run .\setup.ps1 first."
}

$python = ".\venv\Scripts\python.exe"

if (-not $SkipInstall) {
    & $python -m pip install --upgrade pip
    & $python -m pip install pyinstaller
}

Write-Host "Building GUI app..."
& $python -m PyInstaller --noconfirm --clean --onefile --windowed --name ig-tracker-gui gui_app.py

Write-Host "Building tray app..."
& $python -m PyInstaller --noconfirm --clean --onefile --windowed --name ig-tracker-tray tray_app.py

Write-Host "Building tracker CLI..."
& $python -m PyInstaller --noconfirm --clean --onefile --name ig-tracker-cli main.py

Write-Host "Building report CLI..."
& $python -m PyInstaller --noconfirm --clean --onefile --name ig-tracker-report report.py

Write-Host "Building DB tools CLI..."
& $python -m PyInstaller --noconfirm --clean --onefile --name ig-tracker-db-tools db_tools.py

Write-Host "Build complete. Binaries are in .\dist"
