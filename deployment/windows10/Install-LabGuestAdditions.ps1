#requires -Version 5.1
<#
.SYNOPSIS
    Install user-supplied Oracle VirtualBox Guest Additions when available.
.DESCRIPTION
    Sources: a locally bundled, unmodified VBoxGuestAdditions ISO payload,
    or a VirtualBox Guest Additions CD inserted after Windows Setup.
    No external downloads, system reboot, or VM configuration changes.
#>
[CmdletBinding()] param([switch]$RequireMedia)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$root = 'C:\DeskMateLab'
$logDir = Join-Path $root 'setup-logs'
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$exe = $null
$bundled = Join-Path $root 'Packages\VBoxGuestAdditions\VBoxWindowsAdditions.exe'
if (Test-Path -LiteralPath $bundled -PathType Leaf) {
    $exe = $bundled
} else {
    # Do not rely on a particular DVD drive letter after Windows Setup.
    foreach ($charCode in 68..90) {
        $letter = [char]$charCode
        $candidate = "${letter}:\VBoxWindowsAdditions.exe"
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            $exe = $candidate
            break
        }
    }
}
if (-not $exe) {
    $msg = 'VirtualBox Guest Additions media not supplied; installation deferred.'
    Set-Content -LiteralPath (Join-Path $logDir 'guest-additions-deferred.txt') -Value $msg
    if ($RequireMedia) { throw $msg }
    Write-Warning $msg
    return
}

# Do not execute arbitrary files from a mounted disc simply because the name
# matches. Require a trusted Oracle Authenticode publisher.
$signature = Get-AuthenticodeSignature -LiteralPath $exe
if ($signature.Status -ne 'Valid' -or
    $null -eq $signature.SignerCertificate -or
    $signature.SignerCertificate.Subject -notmatch 'Oracle') {
    throw "Guest Additions installer signature validation failed: $($signature.Status)"
}
$sourceDir = Split-Path -Parent $exe
$certDir = Join-Path $sourceDir 'cert'
$certTool = Join-Path $certDir 'VBoxCertUtil.exe'
if (Test-Path -LiteralPath $certTool) {
    # Oracle documents this step for driver trust in unattended installations.
    # It is scoped to certificates supplied alongside the signed installer.
    Push-Location $certDir
    try {
        & $certTool add-trusted-publisher 'vbox*.cer' --root 'vbox*.cer'
        if ($LASTEXITCODE -ne 0) {
            throw "VBoxCertUtil exited $LASTEXITCODE; refusing to continue silently."
        }
    } finally { Pop-Location }
} else {
    Write-Warning 'Driver certificate utility missing; Guest Additions may request confirmation.'
}

Write-Host "Installing signed VirtualBox Guest Additions from $exe"
$process = Start-Process -FilePath $exe -ArgumentList '/S' -Wait -PassThru
if ($process.ExitCode -notin @(0,3010,1641)) {
    throw "Guest Additions installer failed: $($process.ExitCode)"
}
Set-Content -LiteralPath (Join-Path $logDir 'guest-additions-installed.txt') `
    -Value ("Installer completed: {0}; reboot recommended: {1}" -f `
        $process.ExitCode, (Get-Date).ToUniversalTime().ToString('o'))
Remove-Item -LiteralPath (Join-Path $logDir 'guest-additions-deferred.txt') -ErrorAction SilentlyContinue
Write-Host 'Guest Additions installer finished; restart Windows after provisioning to load drivers.'
