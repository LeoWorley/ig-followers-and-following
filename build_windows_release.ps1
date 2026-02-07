param(
    [string]$Version = "0.1.0",
    [switch]$SkipBuild,
    [switch]$SkipInstall,
    [switch]$NoInstaller
)

$ErrorActionPreference = "Stop"
Set-Location -Path (Split-Path -Parent $MyInvocation.MyCommand.Path)

function Get-IsccPath {
    $cmd = Get-Command iscc.exe -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }

    $common = @(
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        "C:\Program Files\Inno Setup 6\ISCC.exe"
    )
    foreach ($path in $common) {
        if (Test-Path $path) {
            return $path
        }
    }
    return $null
}

if (-not $SkipBuild) {
    Write-Host "Building application executables..."
    $buildArgs = @()
    if ($SkipInstall) {
        $buildArgs += "-SkipInstall"
    }
    & .\build_apps.ps1 @buildArgs
}

$distDir = Join-Path $PWD "dist"
$releaseRoot = Join-Path $PWD "release\windows"
$stageDir = Join-Path $releaseRoot "stage"
$docsStageDir = Join-Path $stageDir "docs"

New-Item -ItemType Directory -Path $releaseRoot -Force | Out-Null
if (Test-Path $stageDir) {
    Remove-Item -Path $stageDir -Recurse -Force
}
New-Item -ItemType Directory -Path $stageDir -Force | Out-Null
New-Item -ItemType Directory -Path $docsStageDir -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $stageDir "reports") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $stageDir "exports") -Force | Out-Null

$requiredExes = @(
    "ig-tracker-gui.exe",
    "ig-tracker-tray.exe",
    "ig-tracker-cli.exe",
    "ig-tracker-report.exe",
    "ig-tracker-db-tools.exe"
)

foreach ($exe in $requiredExes) {
    $sourceExe = Join-Path $distDir $exe
    if (-not (Test-Path $sourceExe)) {
        throw "Missing executable: $sourceExe. Run .\build_apps.ps1 first."
    }
    Copy-Item -Path $sourceExe -Destination (Join-Path $stageDir $exe) -Force
}

$filesToCopy = @(
    ".env.example",
    "README.md",
    "LICENSE"
)
foreach ($file in $filesToCopy) {
    if (Test-Path $file) {
        Copy-Item -Path $file -Destination (Join-Path $stageDir $file) -Force
    }
}

$docsToCopy = @(
    "docs\QUICK_START.md",
    "docs\TROUBLESHOOTING.md",
    "docs\ADVANCED.md"
)
foreach ($doc in $docsToCopy) {
    if (Test-Path $doc) {
        Copy-Item -Path $doc -Destination (Join-Path $docsStageDir ([System.IO.Path]::GetFileName($doc))) -Force
    }
}

$portableZip = Join-Path $releaseRoot "ig-tracker-windows-v$Version-portable.zip"
if (Test-Path $portableZip) {
    Remove-Item -Path $portableZip -Force
}
Compress-Archive -Path (Join-Path $stageDir "*") -DestinationPath $portableZip -CompressionLevel Optimal -Force
Write-Host "Portable package created: $portableZip"

if (-not $NoInstaller) {
    $isccPath = Get-IsccPath
    if (-not $isccPath) {
        Write-Warning "Inno Setup (ISCC.exe) not found. Install Inno Setup 6 to generate the installer EXE."
        Write-Warning "Portable zip is available and can be uploaded as a release artifact."
    } else {
        $issPath = Join-Path $PWD "installer\windows\ig-tracker.iss"
        Write-Host "Building installer using Inno Setup..."
        & $isccPath "/DAppVersion=$Version" "/DSourceDir=$stageDir" $issPath | Out-Host
        Write-Host "Installer build finished in: $releaseRoot"
    }
}

Write-Host "Release staging complete."
