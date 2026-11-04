#requires -Version 5.1
[CmdletBinding()]param()
Set-StrictMode -Version Latest
$root='C:\DeskMateLab'
$report=[ordered]@{
    os=(Get-CimInstance Win32_OperatingSystem).Caption
    build=(Get-CimInstance Win32_OperatingSystem).BuildNumber
    provisioned=(Test-Path (Join-Path $root 'provision-complete.txt'))
    winget=[bool](Get-Command winget.exe -ErrorAction SilentlyContinue)
    deliveryOptimizationPolicy=(Get-ItemProperty -Path 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\DeliveryOptimization' -Name DODownloadMode -ErrorAction SilentlyContinue).DODownloadMode
    git=[bool](Get-Command git.exe -ErrorAction SilentlyContinue)
    python=[bool](Get-Command python.exe -ErrorAction SilentlyContinue)
    chrome=(Test-Path 'C:\Program Files\Google\Chrome\Application\chrome.exe')
    msys2=(Test-Path 'C:\msys64\ucrt64.exe')
    ghidra=[bool](Test-Path 'C:\Tools\ghidra_12.1.4_PUBLIC\support\analyzeHeadless.bat')
    sshd=(Get-Service sshd -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Status -ErrorAction SilentlyContinue)
    allowTelemetry=(Get-ItemProperty -Path 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\DataCollection' -Name AllowTelemetry -ErrorAction SilentlyContinue).AllowTelemetry
    taskbarSearchMode=(Get-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Search' -Name SearchboxTaskbarMode -ErrorAction SilentlyContinue).SearchboxTaskbarMode
    taskbarNewsMode=(Get-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Feeds' -Name ShellFeedsTaskbarViewMode -ErrorAction SilentlyContinue).ShellFeedsTaskbarViewMode
    feedsPolicy=(Get-ItemProperty -Path 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\Windows Feeds' -Name EnableFeeds -ErrorAction SilentlyContinue).EnableFeeds
    guestAdditionsService=(Get-Service VBoxService -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Status -ErrorAction SilentlyContinue)
    guestAdditionsStageRecorded=(Test-Path (Join-Path $root 'setup-logs\guest-additions-installed.txt'))
    guestAdditionsDeferred=(Test-Path (Join-Path $root 'setup-logs\guest-additions-deferred.txt'))
}
$report|ConvertTo-Json -Depth 3
