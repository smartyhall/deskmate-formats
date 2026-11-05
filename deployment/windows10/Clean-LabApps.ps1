#requires -Version 5.1
<#
.SYNOPSIS
    Remove a deliberately small allowlist of Windows 10 consumer applications.
.DESCRIPTION
    Intended for a NEW disposable DeskMate Lab VM. Requires an elevated
    Windows PowerShell session. Removes installed AppX packages for all users
    and their provisioned copies for future users; optionally uninstalls the
    traditional OneDrive client. Never deletes OneDrive files or user folders.
    The Microsoft Store, App Installer/WinGet, Edge/WebView2, Defender and
    Windows Update are intentionally untouched.
.EXAMPLE
    .\Clean-LabApps.ps1 -WhatIf
.EXAMPLE
    .\Clean-LabApps.ps1
#>
[CmdletBinding(SupportsShouldProcess=$true)]
param([switch]$KeepOneDrive)

Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$principal = [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run Clean-LabApps.ps1 in an elevated Windows PowerShell session.'
}

$root='C:\DeskMateLab'
$logDir=Join-Path $root 'setup-logs'
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$removed=New-Object 'System.Collections.Generic.List[string]'
$errors=New-Object 'System.Collections.Generic.List[string]'

# Exact package identities only: never use wildcards such as *Microsoft* or
# remove Store infrastructure, WinGet, Microsoft.VCLibs, or Windows components.
$consumerAppNames=@(
    'Microsoft.SkypeApp'
    'Microsoft.MicrosoftOfficeHub'
    'Microsoft.Office.OneNote'
    'Microsoft.MicrosoftSolitaireCollection'
    'Microsoft.XboxApp'
    'Microsoft.XboxGamingOverlay'
    'Microsoft.XboxGameOverlay'
    'Microsoft.XboxSpeechToTextOverlay'
    'Microsoft.ZuneMusic'
    'Microsoft.ZuneVideo'
    'Microsoft.BingWeather'
    'Microsoft.BingNews'
    'Microsoft.GetHelp'
    'Microsoft.Getstarted'
    'Microsoft.People'
    'Microsoft.YourPhone'
    'Microsoft.WindowsFeedbackHub'
    'Microsoft.WindowsMaps'
    'Microsoft.MixedReality.Portal'
    'Microsoft.Microsoft3DViewer'
    'Microsoft.549981C3F5F10'
    'Microsoft.OneDriveSync'
)
Write-Host 'Removing only explicitly allowlisted Windows consumer apps.'

# Removing apps for existing users and removing their provisioning are both
# necessary: the latter prevents automatic installation for new accounts.
$installed=@(Get-AppxPackage -AllUsers -ErrorAction Stop |
    Where-Object { $consumerAppNames -contains $_.Name })
foreach ($app in $installed) {
    $name=$app.Name
    $fullName=$app.PackageFullName
    if ($PSCmdlet.ShouldProcess($fullName,'Remove installed AppX package for all users')) {
        try {
            Remove-AppxPackage -Package $fullName -AllUsers -ErrorAction Stop
            $removed.Add("Installed: $name ($fullName)")
        } catch {
            $message="Could not remove installed $name ($fullName): $($_.Exception.Message)"
            $errors.Add($message)
            Write-Warning $message
        }
    }
}

$provisioned=@(Get-AppxProvisionedPackage -Online -ErrorAction Stop |
    Where-Object { $consumerAppNames -contains $_.DisplayName })
foreach ($app in $provisioned) {
    $name=$app.DisplayName
    $packageName=$app.PackageName
    if ($PSCmdlet.ShouldProcess($packageName,'Remove AppX provisioning for future users')) {
        try {
            Remove-AppxProvisionedPackage -Online -PackageName $packageName -ErrorAction Stop | Out-Null
            $removed.Add("Provisioned: $name ($packageName)")
        } catch {
            $message="Could not deprovision $name ($packageName): $($_.Exception.Message)"
            $errors.Add($message)
            Write-Warning $message
        }
    }
}

# OneDrive is generally a conventional installer, not an AppX app. Use the
# bundled uninstaller instead of deleting its files or registry keys.
if (-not $KeepOneDrive) {
    $candidates=@(
        (Join-Path $env:SystemRoot 'SysWOW64\OneDriveSetup.exe')
        (Join-Path $env:SystemRoot 'System32\OneDriveSetup.exe')
        (Join-Path $env:ProgramFiles 'Microsoft OneDrive\OneDriveSetup.exe')
    )
    $onedriveSetup=$candidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } |
        Select-Object -First 1
    if ($null -ne $onedriveSetup) {
        if ($PSCmdlet.ShouldProcess($onedriveSetup,'Uninstall Microsoft OneDrive application (preserve user files)')) {
            try {
                $process=Start-Process -FilePath $onedriveSetup -ArgumentList '/uninstall' -Wait -PassThru -ErrorAction Stop
                if ($process.ExitCode -ne 0) { throw "OneDrive uninstaller exited $($process.ExitCode)" }
                $removed.Add('Desktop client: Microsoft OneDrive')
            } catch {
                $message="OneDrive uninstall could not finish: $($_.Exception.Message)"
                $errors.Add($message)
                Write-Warning $message
            }
        }
    } else {
        Write-Host 'OneDrive installer not found; no desktop client action needed.'
    }
}

if (-not $WhatIfPreference) {
    $summary=[ordered]@{
        timestampUtc=(Get-Date).ToUniversalTime().ToString('o')
        removed=@($removed.ToArray())
        failures=@($errors.ToArray())
        keepOneDrive=$KeepOneDrive.IsPresent
        note='Only allowlisted applications and provisioning are removed; no user files or Store components are intentionally deleted.'
    }
    $summary | ConvertTo-Json -Depth 4 |
        Set-Content -LiteralPath (Join-Path $logDir 'consumer-app-cleanup.json') -Encoding UTF8
}
Write-Host "Consumer-app cleanup: $($removed.Count) changes; $($errors.Count) failures."
if ($errors.Count -gt 0) { Write-Warning "Review $logDir\consumer-app-cleanup.json; cleanup is not fully complete." }
