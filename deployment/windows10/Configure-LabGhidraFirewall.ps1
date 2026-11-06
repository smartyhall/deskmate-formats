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
    [string]$GhidraInstallDir = 'C:\Tools\ghidra_12.1.4_PUBLIC'
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath (Join-Path $GhidraInstallDir 'support\analyzeHeadless.bat'))) {
    throw 'The expected Ghidra installation is missing. Install it before adding firewall rules.'
}

$candidates = New-Object System.Collections.Generic.List[string]
if ($JavaHome) {
    $candidates.Add($JavaHome)
} else {
    # Ghidra documents this override as taking precedence over autodetection.
    $launchProperties = Join-Path $GhidraInstallDir 'support\launch.properties'
    if (Test-Path -LiteralPath $launchProperties) {
        $line = @(Get-Content -LiteralPath $launchProperties |
            Where-Object { $_ -match '^\s*JAVA_HOME_OVERRIDE\s*=' } |
            Select-Object -First 1)
        if ($line.Count -gt 0) {
            $override = (($line[0] -split '=',2)[1]).Trim().Trim('"')
            if ($override) { $candidates.Add($override) }
        }
    }
    if ($env:JAVA_HOME) { $candidates.Add($env:JAVA_HOME) }
    $machineHome = [Environment]::GetEnvironmentVariable('JAVA_HOME','Machine')
    if ($machineHome) { $candidates.Add($machineHome) }
    $javaOnPath = Get-Command java.exe -ErrorAction SilentlyContinue
    if ($null -ne $javaOnPath -and $javaOnPath.Source) {
        $candidates.Add((Split-Path -Parent (Split-Path -Parent $javaOnPath.Source)))
    }
    $adoptium = Join-Path $env:ProgramFiles 'Eclipse Adoptium'
    if (Test-Path -LiteralPath $adoptium) {
        Get-ChildItem -LiteralPath $adoptium -Directory -Filter 'jdk-21*' |
            Sort-Object Name -Descending | ForEach-Object { $candidates.Add($_.FullName) }
    }
}

$selected = $null
foreach ($candidateHome in $candidates) {
    $exe = Join-Path $candidateHome 'bin\java.exe'
    if (Test-Path -LiteralPath $exe -PathType Leaf) {
        $selected = (Resolve-Path -LiteralPath $candidateHome).Path
        break
    }
}
if (-not $selected) {
    throw 'No usable Java home found. Provide -JavaHome with the Ghidra JDK installation directory.'
}

$principal = [Security.Principal.WindowsPrincipal]::new(
    [Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run from elevated 64-bit Windows PowerShell.'
}

function Test-OnlyAddress([object]$values,[string]$expected) {
    $addresses = @($values)
    return ($addresses.Count -eq 1 -and [string]$addresses[0] -eq $expected)
}

Write-Host "Ghidra JDK: $selected"
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
