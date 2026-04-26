$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $root "venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    Write-Error "venv Python not found. Run: .\setup.ps1"
    exit 1
}

$envPath = Join-Path $root ".env"
if (Test-Path $envPath) {
    Get-Content $envPath | ForEach-Object {
        if ($_ -match '^\s*#' -or $_ -match '^\s*$') { return }
        $parts = $_ -split '=', 2
        if ($parts.Count -eq 2) {
            [System.Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim())
        }
    }
}

$hostValue = if ($env:WEB_HOST) { $env:WEB_HOST } else { "0.0.0.0" }
$portValue = if ($env:WEB_PORT) { $env:WEB_PORT } else { "8088" }

Start-Process -FilePath $python -ArgumentList "-m uvicorn web_app:app --host $hostValue --port $portValue --proxy-headers --forwarded-allow-ips=127.0.0.1" -WorkingDirectory $root
