#requires -Version 5.1
<#
.SYNOPSIS
    Configure narrowly scoped inbound loopback rules for Ghidra's Java runtime.
.DESCRIPTION
    Run elevated after installing Ghidra and a JDK. This script never modifies
    non-lab firewall rules, never grants LAN-wide inbound access and never
    changes Java or Ghidra settings. Use -WhatIf to inspect planned changes.
    A loopback-only rule may not suppress a firewall prompt if Ghidra binds
    or receives traffic on a non-loopback interface; investigate rather than
    silently broadening the rule.
#>
[CmdletBinding(SupportsShouldProcess=$true)]
param(
    [string]$JavaHome,
    [string]$GhidraInstallDir = 'C:\Tools\ghidra_12.2_PUBLIC'
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'GhidraToolchain.ps1')

# The installation's own record decides which Java it needs. A launcher's
# presence says nothing about the release, and a directory name says nothing
# about a JDK's major version.
$ghidra = Get-LabGhidraInstall -InstallDir $GhidraInstallDir
if ($ghidra.error) {
    throw ("Cannot use the Ghidra installation at {0}: {1}" -f $GhidraInstallDir, $ghidra.error)
}
if ($null -eq $ghidra.java_min) {
    throw ('Ghidra {0} records no application.java.min, so a compatible JDK cannot be proven.' -f $ghidra.version)
}

$candidates = New-Object System.Collections.Generic.List[string]
if ($JavaHome) { $candidates.Add($JavaHome) }
if ($env:GHIDRA_JAVA_HOME) { $candidates.Add($env:GHIDRA_JAVA_HOME) }
if ($env:JAVA_HOME) { $candidates.Add($env:JAVA_HOME) }
$machineHome = [Environment]::GetEnvironmentVariable('JAVA_HOME','Machine')
if ($machineHome) { $candidates.Add($machineHome) }
# Ghidra documents this override as winning over autodetection, so it is
# validated rather than assumed to be the right runtime.
$launch = Read-LabKeyValueFile -Path (Join-Path $GhidraInstallDir 'support\launch.properties')
if ($launch.ContainsKey('JAVA_HOME_OVERRIDE')) { $candidates.Add($launch['JAVA_HOME_OVERRIDE']) }
$javaOnPath = Get-Command java.exe -ErrorAction SilentlyContinue
if ($null -ne $javaOnPath -and $javaOnPath.Source) {
    $candidates.Add((Split-Path -Parent (Split-Path -Parent $javaOnPath.Source)))
}
foreach ($discoveredHome in (Find-LabJavaHomes -Roots @('C:\Tools', $env:ProgramFiles))) {
    $candidates.Add($discoveredHome)
}

$selection = Select-LabJavaHome -JavaMin $ghidra.java_min -Candidates $candidates
if (-not $selection.selected) {
    $reasons = ($selection.rejected | ForEach-Object { "{0}: {1}" -f $_.home, $_.reason }) -join '; '
    throw ('No usable Java home for Ghidra {0}, which requires Java {1} or newer. {2}' -f `
            $ghidra.version, $ghidra.java_min, $reasons)
}
if ($JavaHome -and $selection.selected -ne $JavaHome) {
    throw ('The requested Java home {0} is not compatible with Ghidra {1} (Java {2}+).' -f `
            $JavaHome, $ghidra.version, $ghidra.java_min)
}
$selected = (Resolve-Path -LiteralPath $selection.selected).Path

$principal = [Security.Principal.WindowsPrincipal]::new(
    [Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run from elevated 64-bit Windows PowerShell.'
}

function Test-OnlyAddress([object]$values,[string]$expected) {
    $addresses = @($values)
    return ($addresses.Count -eq 1 -and [string]$addresses[0] -eq $expected)
}

Write-Host ("Ghidra {0} (build {1}) JDK: {2} (major {3}, requires {4}+)" -f `
        $ghidra.version, $ghidra.build_date, $selected, $selection.major, $ghidra.java_min)
foreach ($leaf in @('java.exe','javaw.exe')) {
    $program = Join-Path $selected ("bin\" + $leaf)
    if (-not (Test-Path -LiteralPath $program -PathType Leaf)) { continue }
    $program = (Resolve-Path -LiteralPath $program).Path
    foreach ($family in @(
        @{ suffix = 'IPv4'; address = '127.0.0.1' },
        @{ suffix = 'IPv6'; address = '::1' }
    )) {
        $address = $family.address
        $name = 'DeskMateLab-Ghidra-' + $leaf + '-' + $family.suffix
        $existing = Get-NetFirewallRule -Name $name -ErrorAction SilentlyContinue
        if ($null -ne $existing) {
            $app = Get-NetFirewallApplicationFilter -AssociatedNetFirewallRule $existing
            $addr = Get-NetFirewallAddressFilter -AssociatedNetFirewallRule $existing
            $port = Get-NetFirewallPortFilter -AssociatedNetFirewallRule $existing
            if ($app.Program -ine $program -or
                -not (Test-OnlyAddress $addr.LocalAddress $address) -or
                -not (Test-OnlyAddress $addr.RemoteAddress $address) -or
                [string]$port.Protocol -ne 'TCP' -or
                [string]$existing.Direction -ne 'Inbound' -or
                [string]$existing.Action -ne 'Allow' -or
                [string]$existing.Enabled -ne 'True') {
                throw "Existing lab firewall rule has a different scope: $name. Review it manually."
            }
            Write-Host "Verified existing localhost-only firewall rule: $name"
        } elseif ($PSCmdlet.ShouldProcess($program, "Allow inbound TCP $address to $address ($name)")) {
            $rule = @{
                Name = $name
                DisplayName = $name
                Description = 'DeskMateLab Ghidra Java, inbound TCP localhost only'
                Group = 'DeskMateLab'
                Direction = 'Inbound'
                Action = 'Allow'
                Protocol = 'TCP'
                LocalAddress = $address
                RemoteAddress = $address
                Program = $program
                Profile = 'Any'
                EdgeTraversalPolicy = 'Block'
                PolicyStore = 'PersistentStore'
                ErrorAction = 'Stop'
            }
            New-NetFirewallRule @rule | Out-Null
            Write-Host "Created localhost-only firewall rule: $name"
        }
    }
}
Write-Warning 'This does not remove or narrow firewall rules previously created by Windows prompts. Review those separately.'
