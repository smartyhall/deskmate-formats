#requires -Version 5.1
# Query the Appraiser task's state without confusing lookup errors with absence.
# NotInstalled means the Application Experience task-path query succeeded, but
# did not contain the named task. Unknown means enumeration failed or was opaque.
function Get-LabCompatibilityAppraiserState {
    [CmdletBinding()]
    param()
    $taskPath = '\Microsoft\Windows\Application Experience\'
    $taskName = 'Microsoft Compatibility Appraiser'
    try {
        $tasks = @(Get-ScheduledTask -TaskPath $taskPath -ErrorAction Stop)
    } catch {
        return 'Unknown'
    }
    $matches = @($tasks | Where-Object { $_.TaskName -eq $taskName })
    if ($matches.Count -eq 0) { return 'NotInstalled' }
    if ($matches.Count -ne 1) { return 'Unknown' }
    $state = [string]$matches[0].State
    if ($state -eq 'Disabled') { return 'Disabled' }
    if ($state -in @('Ready', 'Running', 'Queued')) { return 'Enabled' }
    return 'Unknown'
}
