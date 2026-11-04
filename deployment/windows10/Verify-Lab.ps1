#requires -Version 5.1
[CmdletBinding()]param()
Set-StrictMode -Version Latest
$root='C:\DeskMateLab'
# Registry settings are optional and vary across Windows releases/editions.
# Under StrictMode, accessing a missing property with dotted syntax throws,
# even when Get-ItemProperty uses -ErrorAction SilentlyContinue.
function Get-OptionalRegistryValue {
    param([string]$Path,[string]$Name)
    $entry = Get-ItemProperty -LiteralPath $Path -ErrorAction SilentlyContinue
    if ($null -eq $entry) { return $null }
    $property = $entry.PSObject.Properties[$Name]
    if ($null -eq $property) { return $null }
    return $property.Value
}
# Report services as strings; bare, absent ServiceController objects can
# otherwise render as an unhelpful empty object in Windows PowerShell 5.1 JSON.
function Get-OptionalServiceStatus {
    param([string]$Name)
    $service = Get-Service -Name $Name -ErrorAction SilentlyContinue
    if ($null -eq $service) { return 'NotInstalled' }
    return [string]$service.Status
}
$report=[ordered]@{
    os=(Get-CimInstance Win32_OperatingSystem).Caption
    build=(Get-CimInstance Win32_OperatingSystem).BuildNumber
    provisioned=(Test-Path (Join-Path $root 'provision-complete.txt'))
    winget=[bool](Get-Command winget.exe -ErrorAction SilentlyContinue)
    deliveryOptimizationPolicy=(Get-OptionalRegistryValue -Path 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\DeliveryOptimization' -Name 'DODownloadMode')
    git=[bool](Get-Command git.exe -ErrorAction SilentlyContinue)
    python=[bool](Get-Command python.exe -ErrorAction SilentlyContinue)
    chrome=(Test-Path 'C:\Program Files\Google\Chrome\Application\chrome.exe')
    msys2=(Test-Path 'C:\msys64\ucrt64.exe')
    ghidra=[bool](Test-Path 'C:\Tools\ghidra_12.1.4_PUBLIC\support\analyzeHeadless.bat')
    sshd=(Get-OptionalServiceStatus -Name 'sshd')
    allowTelemetry=(Get-OptionalRegistryValue -Path 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\DataCollection' -Name 'AllowTelemetry')
    taskbarSearchMode=(Get-OptionalRegistryValue -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Search' -Name 'SearchboxTaskbarMode')
    taskbarNewsMode=(Get-OptionalRegistryValue -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Feeds' -Name 'ShellFeedsTaskbarViewMode')
    feedsPolicy=(Get-OptionalRegistryValue -Path 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\Windows Feeds' -Name 'EnableFeeds')
    guestAdditionsService=(Get-OptionalServiceStatus -Name 'VBoxService')
    vmwareToolsService=(Get-OptionalServiceStatus -Name 'VMTools')
    guestAdditionsStageRecorded=(Test-Path (Join-Path $root 'setup-logs\guest-additions-installed.txt'))
    guestAdditionsDeferred=(Test-Path (Join-Path $root 'setup-logs\guest-additions-deferred.txt'))
}
$report|ConvertTo-Json -Depth 3
