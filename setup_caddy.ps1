param(
    [Parameter(Mandatory = $true)]
    [string]$JellyfinHost,

    [Parameter(Mandatory = $true)]
    [string]$IgHost,

    [string]$InstallDir = "C:\Caddy"
)

$ErrorActionPreference = "Stop"

function Test-Admin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Normalize-DuckDnsHost([string]$Value) {
    $hostValue = $Value.Trim().ToLowerInvariant()
    if ($hostValue.StartsWith("https://")) {
        $hostValue = $hostValue.Substring(8)
    }
    if ($hostValue.StartsWith("http://")) {
        $hostValue = $hostValue.Substring(7)
    }
    $hostValue = $hostValue.TrimEnd("/")
    if (-not $hostValue.EndsWith(".duckdns.org")) {
        $hostValue = "$hostValue.duckdns.org"
    }
    return $hostValue
}

if (-not (Test-Admin)) {
    Write-Error "Run this script from an Administrator PowerShell so it can install the Caddy service and firewall rules."
    exit 1
}

$caddy = (Get-Command caddy.exe -ErrorAction Stop).Source
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$nssm = Join-Path $root "nssm.exe"
$templatePath = Join-Path $root "caddy\Caddyfile.template"
$caddyfilePath = Join-Path $InstallDir "Caddyfile"
$logDir = Join-Path $InstallDir "logs"

if (-not (Test-Path $nssm)) {
    Write-Error "nssm.exe was not found at $nssm. It is required because this Caddy build does not include the 'caddy service' command."
    exit 1
}

$jellyfinHostName = Normalize-DuckDnsHost $JellyfinHost
$igHostName = Normalize-DuckDnsHost $IgHost

New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
New-Item -ItemType Directory -Path $logDir -Force | Out-Null

$config = Get-Content -Path $templatePath -Raw
$config = $config.Replace("JELLYFIN_DUCKDNS_NAME.duckdns.org", $jellyfinHostName)
$config = $config.Replace("IG_DUCKDNS_NAME.duckdns.org", $igHostName)
Set-Content -Path $caddyfilePath -Value $config -Encoding ascii

& $caddy fmt --overwrite $caddyfilePath
& $caddy validate --config $caddyfilePath --adapter caddyfile

foreach ($port in @(443, 8080)) {
    $ruleName = "Caddy HTTPS reverse proxy TCP $port"
    if (-not (Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue)) {
        New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Action Allow -Protocol TCP -LocalPort $port | Out-Null
    }
}

$existing = Get-Service -Name caddy -ErrorAction SilentlyContinue
if ($existing) {
    if ($existing.Status -ne "Stopped") {
        Stop-Service -Name caddy -Force
        Start-Sleep -Seconds 2
    }
    & $nssm remove caddy confirm | Out-Null
}

& $nssm install caddy $caddy run --config $caddyfilePath --adapter caddyfile | Out-Null
& $nssm set caddy AppDirectory $InstallDir | Out-Null
& $nssm set caddy AppStdout (Join-Path $logDir "caddy.out.log") | Out-Null
& $nssm set caddy AppStderr (Join-Path $logDir "caddy.err.log") | Out-Null
& $nssm set caddy AppRotateFiles 1 | Out-Null
& $nssm set caddy AppRotateOnline 1 | Out-Null
& $nssm set caddy AppRotateBytes 10485760 | Out-Null
& $nssm start caddy | Out-Null

Start-Sleep -Seconds 3
$service = Get-Service -Name caddy -ErrorAction Stop
if ($service.Status -ne "Running") {
    Write-Error "Caddy service was installed but is not running. Check $logDir for details."
    exit 1
}

Write-Host "Caddy is installed and started."
Write-Host "Jellyfin: https://$jellyfinHostName"
Write-Host "IG dashboard: https://$igHostName"
Write-Host "Router forwards needed: external 443 -> this PC 443, external 80 -> this PC 8080."
