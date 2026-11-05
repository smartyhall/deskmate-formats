#requires -Version 5.1
<#
.SYNOPSIS
    Retrieve the current 86Box ROM tree into the supported per-user path.
.DESCRIPTION
    Downloads ROMs from the official upstream repository only when invoked.
    A pre-existing ZIP-extracted folder is never overwritten or silently
    converted into a Git checkout. Run as the 86Box interactive user, not SYSTEM.
    ROM copyrights remain with their respective owners; never ship in our ISO.
.EXAMPLE
    .\Setup-86Box-ROMs.ps1
.EXAMPLE
    .\Setup-86Box-ROMs.ps1 -Update
#>
[CmdletBinding()]param([switch]$Update)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
if ([Security.Principal.WindowsIdentity]::GetCurrent().User.Value -eq 'S-1-5-18') {
    throw 'Run as the interactive DeskMateLab account, not LocalSystem.'
}
$roms=Join-Path $env:LOCALAPPDATA '86Box\roms'
$git='C:\Program Files\Git\cmd\git.exe'
if (-not (Test-Path -LiteralPath $git -PathType Leaf)) {
    $command=Get-Command git.exe -ErrorAction SilentlyContinue
    if ($null -eq $command) { throw 'Git for Windows is not installed.' }
    $git=$command.Source
}
$originUrl='https://github.com/86Box/roms.git'
$parent=Split-Path -Parent $roms
New-Item -ItemType Directory -Path $parent -Force | Out-Null

if (Test-Path -LiteralPath (Join-Path $roms '.git')) {
    $origin=(& $git -C $roms remote get-url origin)
    if ($LASTEXITCODE -ne 0) { throw 'Cannot determine ROM repository origin.' }
    if (([string]$origin).Trim() -notmatch '(?i)^https://github\.com/86box/roms(?:\.git)?$') {
        throw "Existing ROM checkout has an unexpected origin: $origin"
    }
    if ($Update) {
        $changed=@(& $git -C $roms status --porcelain)
        if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect ROM checkout.' }
        if ($changed.Count -gt 0) { throw 'ROM checkout has local changes; refusing to update.' }
        & $git -C $roms pull --ff-only
        if ($LASTEXITCODE -ne 0) { throw 'ROM checkout update failed; nothing was reset.' }
    } else {
        Write-Host 'Existing Git ROM checkout preserved; use -Update to fetch newer ROMs.'
    }
} else {
    if (Test-Path -LiteralPath $roms) {
        $entries=@(Get-ChildItem -LiteralPath $roms -Force -ErrorAction Stop)
        if ($entries.Count -gt 0) {
            throw "A non-Git ROM folder already exists at $roms. Keep using it, or manually rename it before cloning; no files were overwritten."
        }
    }
    & $git clone --depth 1 $originUrl $roms
    if ($LASTEXITCODE -ne 0) { throw 'ROM Git clone failed.' }
}

$revision=(& $git -C $roms rev-parse HEAD)
if ($LASTEXITCODE -ne 0) { throw 'Cannot determine ROM Git revision.' }
$revision=([string]$revision).Trim()
if ($revision -notmatch '^[0-9a-fA-F]{40}$') { throw "Unexpected ROM revision: $revision" }

$logDir='C:\DeskMateLab\setup-logs'
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
Set-Content -LiteralPath (Join-Path $logDir '86box-roms-commit.txt') -Value $revision -Encoding ASCII
Write-Host "86Box ROM checkout: $roms"
Write-Host "ROM revision recorded: $revision"
