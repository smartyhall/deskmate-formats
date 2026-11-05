#requires -Version 5.1
# Minimize nonessential telemetry without breaking Windows Update, Defender,
# SmartScreen, TLS, the network stack, browser/extension updates or licensing.
[CmdletBinding()]param()
$ErrorActionPreference='Stop'
function Set-Dword([string]$path,[string]$name,[int]$value) {
    New-Item -Path $path -Force | Out-Null
    New-ItemProperty -Path $path -Name $name -Value $value -PropertyType DWord -Force | Out-Null
}
# Windows 10 Pro's effective minimum is Required/basic telemetry, NOT zero.
Set-Dword 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\DataCollection' 'AllowTelemetry' 1
Set-Dword 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\CloudContent' 'DisableWindowsConsumerFeatures' 1
Set-Dword 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\CloudContent' 'DisableSoftLanding' 1
Set-Dword 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\System' 'EnableActivityFeed' 0
Set-Dword 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\System' 'PublishUserActivities' 0
Set-Dword 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\System' 'UploadUserActivities' 0
Set-Dword 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\Windows Error Reporting' 'Disabled' 1
Set-Dword 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\AdvertisingInfo' 'DisabledByGroupPolicy' 1
Set-Dword 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\DataCollection' 'DoNotShowFeedbackNotifications' 1
Set-Dword 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\Explorer' 'DisableSearchBoxSuggestions' 1
Set-Dword 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\Windows Search' 'AllowCortana' 0
Set-Dword 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\CloudContent' 'DisableTailoredExperiencesWithDiagnosticData' 1
# Windows Update/Store peer delivery only among PCs sharing the same public
# network address (LAN mode); never permit Internet peer uploads/downloads.
# An ISO builder can stage HttpOnly (no peers) instead for isolated guests.
$doMode='Lan'
$doConfig='C:\DeskMateLab\delivery-optimization-mode.txt'
if (Test-Path -LiteralPath $doConfig -PathType Leaf) {
    $doMode=(Get-Content -LiteralPath $doConfig -Raw).Trim()
}
if ($doMode -notin @('Lan','HttpOnly')) { throw "Invalid Delivery Optimization mode: $doMode" }
$doValue=if ($doMode -eq 'Lan') { 1 } else { 0 }
Set-Dword 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\DeliveryOptimization' 'DODownloadMode' $doValue
Write-Host "Delivery Optimization policy: $doMode (mode $doValue)."
# Chrome: disable its optional usage metrics and background browser process.
Set-Dword 'HKLM:\SOFTWARE\Policies\Google\Chrome' 'MetricsReportingEnabled' 0
Set-Dword 'HKLM:\SOFTWARE\Policies\Google\Chrome' 'BackgroundModeEnabled' 0
# Offer an install that users can disable, rather than a forced immutable extension.
# Official OpenAI ChatGPT extension ID and Google's Chrome Web Store update URL.
$policy = @{ 'hehggadaopoacecdllhhajmbjkdcmajg' = @{
    installation_mode='normal_installed'
    update_url='https://clients2.google.com/service/update2/crx'
} } | ConvertTo-Json -Compress -Depth 5
New-Item -Path 'HKLM:\SOFTWARE\Policies\Google\Chrome' -Force | Out-Null
New-ItemProperty -Path 'HKLM:\SOFTWARE\Policies\Google\Chrome' -Name 'ExtensionSettings' -PropertyType String -Value $policy -Force | Out-Null
# Nonessential CEIP/feedback tasks; if absent on a particular build, ignore.
foreach ($task in @(
    '\Microsoft\Windows\Customer Experience Improvement Program\Consolidator',
    '\Microsoft\Windows\Customer Experience Improvement Program\UsbCeip',
    '\Microsoft\Windows\Application Experience\ProgramDataUpdater',
    '\Microsoft\Windows\Application Experience\Microsoft Compatibility Appraiser',
    '\Microsoft\Windows\Feedback\Siuf\DmClient',
    '\Microsoft\Windows\Feedback\Siuf\DmClientOnScenarioDownload'
)) {
    & schtasks.exe /Change /TN $task /Disable 2>$null | Out-Null
}
# Verify the specific compatibility-assessment task rather than trusting
# schtasks.exe's exit status or assuming it exists on every Windows build.
# Windows servicing may recreate/re-enable optional scheduled tasks.
try {
    $appraiser = Get-ScheduledTask -TaskPath '\Microsoft\Windows\Application Experience\' `
        -TaskName 'Microsoft Compatibility Appraiser' -ErrorAction SilentlyContinue
    if ($null -ne $appraiser -and [string]$appraiser.State -ne 'Disabled') {
        Write-Warning 'Microsoft Compatibility Appraiser remains enabled; check task permissions.'
    }
} catch {
    Write-Warning ('Could not verify Compatibility Appraiser task: ' + $_.Exception.Message)
}
Write-Host 'Applied reduced-telemetry policies (not zero telemetry). Windows Update/Defender preserved.'
