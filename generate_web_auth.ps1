param(
    [Parameter(Mandatory = $true)]
    [string]$Password
)

$ErrorActionPreference = "Stop"

$iterations = 260000
$saltBytes = New-Object byte[] 16
$rng = [Security.Cryptography.RandomNumberGenerator]::Create()
$rng.GetBytes($saltBytes)
$salt = [Convert]::ToBase64String($saltBytes).TrimEnd("=").Replace("+", "-").Replace("/", "_")

$derive = [Security.Cryptography.Rfc2898DeriveBytes]::new(
    $Password,
    [Text.Encoding]::UTF8.GetBytes($salt),
    $iterations,
    [Security.Cryptography.HashAlgorithmName]::SHA256
)
$hash = [Convert]::ToBase64String($derive.GetBytes(32)).TrimEnd("=").Replace("+", "-").Replace("/", "_")
$secretBytes = New-Object byte[] 48
$rng.GetBytes($secretBytes)
$rng.Dispose()
$secret = [Convert]::ToBase64String($secretBytes).TrimEnd("=").Replace("+", "-").Replace("/", "_")

Write-Host "WEB_AUTH_PASSWORD_HASH=pbkdf2_sha256`$$iterations`$$salt`$$hash"
Write-Host "WEB_SESSION_SECRET=$secret"
