#requires -Version 5.1
# Offline mocks: no Task Scheduler or VM changes.
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\Get-LabCompatibilityAppraiserState.ps1')
$script:MockTasks = @()
$script:FailLookup = $false
function Get-ScheduledTask {
    [CmdletBinding()]
    param([string]$TaskPath)
    if ($TaskPath -ne '\Microsoft\Windows\Application Experience\') {
        throw 'Unexpected task directory requested.'
    }
    if ($script:FailLookup) { throw 'Simulated scheduler access failure.' }
    foreach ($task in $script:MockTasks) { $task }
}
function Assert-State([string]$Expected) {
    $actual = Get-LabCompatibilityAppraiserState
    if ($actual -cne $Expected) {
        throw "Expected $Expected; received $actual"
    }
}
$script:MockTasks = @([pscustomobject]@{ TaskName='ProgramDataUpdater'; State='Ready' })
Assert-State 'NotInstalled'
$script:MockTasks = @([pscustomobject]@{ TaskName='Microsoft Compatibility Appraiser'; State='Disabled' })
Assert-State 'Disabled'
foreach ($state in @('Ready','Running','Queued')) {
    $script:MockTasks = @([pscustomobject]@{ TaskName='Microsoft Compatibility Appraiser'; State=$state })
    Assert-State 'Enabled'
}
$script:MockTasks = @([pscustomobject]@{ TaskName='Microsoft Compatibility Appraiser'; State='Unknown' })
Assert-State 'Unknown'
$script:FailLookup = $true
Assert-State 'Unknown'
Write-Output 'Appraiser state query: absent, disabled, enabled, unknown and failed lookup passed.'
