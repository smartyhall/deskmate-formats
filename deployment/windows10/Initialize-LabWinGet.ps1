#requires -Version 5.1
<#
.SYNOPSIS
    Recover WinGet after first login or install an optionally staged official App Installer bundle.
.DESCRIPTION
    WinGet is a per-user packaged application and is not supported in the
    LocalSystem context. Registration is often asynchronous on a fresh Win10
    user profile. No unpinned packages are downloaded by this helper.
    To bootstrap truly offline, the builder can stage a Microsoft-provided
    Microsoft.DesktopAppInstaller.msixbundle plus required, matching
    dependency packages in Packages\WinGetDependencies.
#>
[CmdletBinding()]
param([string]$PackageRoot='C:\DeskMateLab\Packages')
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'

if ([Security.Principal.WindowsIdentity]::GetCurrent().User.Value -eq 'S-1-5-18') {
    throw 'WinGet CLI requires an interactive user account; it is not supported under NT AUTHORITY\SYSTEM.'
}

function Find-WinGet {
    $candidate=Get-Command winget.exe -ErrorAction SilentlyContinue
    if ($null -eq $candidate) { return $null }
    try {
        $version=& $candidate.Source --version 2>$null
        if ($LASTEXITCODE -eq 0 -and $version) { return $candidate.Source }
    } catch { }
    return $null
}

$executable=Find-WinGet
if ($executable) { Write-Host "WinGet available: $executable"; return }

$package=Get-AppxPackage -Name Microsoft.DesktopAppInstaller -ErrorAction SilentlyContinue
if ($null -ne $package) {
    Write-Host "App Installer $($package.Version) is registered; requesting WinGet registration."
    try {
        Add-AppxPackage -RegisterByFamilyName -MainPackage Microsoft.DesktopAppInstaller_8wekyb3d8bbwe -ErrorAction Stop
    } catch {
        Write-Warning ('WinGet registration attempt failed: ' + $_.Exception.Message)
    }
    for ($attempt=1; $attempt -le 4; $attempt++) {
        $executable=Find-WinGet
        if ($executable) { Write-Host "WinGet available: $executable"; return }
        Start-Sleep -Seconds 3
    }
}

$bundle=Join-Path $PackageRoot 'Microsoft.DesktopAppInstaller.msixbundle'
if (Test-Path -LiteralPath $bundle -PathType Leaf) {
    $depsDir=Join-Path $PackageRoot 'WinGetDependencies'
    $deps=@()
    if (Test-Path -LiteralPath $depsDir -PathType Container) {
        $deps=@(Get-ChildItem -LiteralPath $depsDir -File |
            Where-Object { $_.Extension -in @('.appx','.msix','.appxbundle','.msixbundle') } |
            Select-Object -ExpandProperty FullName)
    }
    # Add-AppxPackage enforces the Windows package trust and dependency checks.
    # Only explicitly staged, user-provided media are installed; no unknown URLs.
    if ($deps.Count -gt 0) {
        Add-AppxPackage -Path $bundle -DependencyPath $deps -ErrorAction Stop
    } else {
        Add-AppxPackage -Path $bundle -ErrorAction Stop
    }
    for ($attempt=1; $attempt -le 5; $attempt++) {
        $executable=Find-WinGet
        if ($executable) { Write-Host "WinGet installed: $executable"; return }
        Start-Sleep -Seconds 3
    }
}

throw @'
WinGet is unavailable. Install/update Microsoft App Installer from Microsoft
Store or the Microsoft WinGet GitHub release, then run this helper again.
For offline builds, supply Packages\Microsoft.DesktopAppInstaller.msixbundle and
any matching framework packages under Packages\WinGetDependencies.
See https://learn.microsoft.com/windows/package-manager/winget/ .
'@
