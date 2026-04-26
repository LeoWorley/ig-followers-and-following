$ErrorActionPreference = "Stop"

function Test-Admin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-Admin)) {
    Write-Error "Run this script from an Administrator PowerShell so it can update and restart the IG Tracker Web service."
    exit 1
}

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$nssm = Join-Path $root "nssm.exe"
$python = Join-Path $root "venv\Scripts\python.exe"
$serviceName = "IG Tracker Web"

if (-not (Test-Path $nssm)) {
    Write-Error "nssm.exe was not found at $nssm"
    exit 1
}

if (-not (Test-Path $python)) {
    Write-Error "venv Python was not found at $python"
    exit 1
}

$service = Get-Service -Name $serviceName -ErrorAction Stop

& $nssm set $serviceName Application $python | Out-Null
& $nssm set $serviceName AppDirectory $root | Out-Null
& $nssm set $serviceName AppParameters "-m uvicorn web_app:app --host 127.0.0.1 --port 8088 --proxy-headers --forwarded-allow-ips=127.0.0.1" | Out-Null

if ($service.Status -ne "Stopped") {
    Restart-Service -Name $serviceName -Force
} else {
    Start-Service -Name $serviceName
}

Start-Sleep -Seconds 3

$service = Get-Service -Name $serviceName -ErrorAction Stop
if ($service.Status -ne "Running") {
    Write-Error "$serviceName is not running after restart."
    exit 1
}

Write-Host "$serviceName updated and running."
Write-Host "Expected listener: 127.0.0.1:8088"
Get-NetTCPConnection -State Listen -LocalPort 8088 -ErrorAction SilentlyContinue |
    Select-Object LocalAddress, LocalPort, OwningProcess |
    Format-Table -AutoSize
