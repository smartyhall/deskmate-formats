#requires -Version 5.1
<#
.SYNOPSIS
    Configure power and Windows 10 taskbar for a disposable research VM.
.DESCRIPTION
    Machine-wide settings are applied when elevated. Per-user taskbar settings
    are applied to the current user, and an Active Setup entry applies them to
    future interactive profiles. Search indexing is NOT disabled.
#>
[CmdletBinding()] param([switch]$UserOnly)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Set-Dword([string]$Path, [string]$Name, [int]$Value) {
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -Path $Path -Force | Out-Null
    }
    New-ItemProperty -Path $Path -Name $Name -Value $Value `
        -PropertyType DWord -Force | Out-Null
}

# Current interactive user's preferences. This does NOT disable indexing or
# eliminate the ability to search via Start. A logoff/login refreshes Explorer.
Set-Dword 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Search' `
    'SearchboxTaskbarMode' 0
Set-Dword 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Feeds' `
    'ShellFeedsTaskbarViewMode' 2
Set-Dword 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Feeds' `
    'ShellFeedsTaskbarOpenOnHover' 0

if ($UserOnly) { return }

# Do not disable password-required logon or the lock screen. Do not
# suppress host sleep; these settings affect only the Windows VM.
& powercfg.exe /change monitor-timeout-ac 0
if ($LASTEXITCODE -ne 0) { throw 'Could not disable the virtual display AC timeout.' }
& powercfg.exe /change standby-timeout-ac 0
if ($LASTEXITCODE -ne 0) { throw 'Could not disable the virtual machine AC sleep timeout.' }
& powercfg.exe /change hibernate-timeout-ac 0
if ($LASTEXITCODE -ne 0) { throw 'Could not disable the virtual machine AC hibernation timeout.' }

# Turn off Windows 10's News and Interests feature by machine policy, but
# leave the Windows Search service and Windows Update enabled.
Set-Dword 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\Windows Feeds' 'EnableFeeds' 0

# Active Setup is processed at interactive Explorer logon and applies HKCU
# settings for accounts created by VirtualBox or later added to this lab.
# It does not execute the machine power configuration in those accounts.
$activeSetup = 'HKLM:\SOFTWARE\Microsoft\Active Setup\Installed Components\{AFC6D297-EF3A-4A73-9AF7-C56CB67D96AB}'
New-Item -Path $activeSetup -Force | Out-Null
New-ItemProperty -Path $activeSetup -Name 'Version' -Value '1,0,0,0' `
    -PropertyType String -Force | Out-Null
$command = '"' + $env:SystemRoot + '\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "C:\DeskMateLab\Configure-LabWorkstation.ps1" -UserOnly'
New-ItemProperty -Path $activeSetup -Name 'StubPath' -Value $command `
    -PropertyType String -Force | Out-Null
Write-Host 'VM AC sleep/display disabled; Search and News taskbar settings registered for interactive profiles.'
