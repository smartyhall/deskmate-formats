#requires -Version 5.1
<#
Enable SSH ONLY after configuring the VM's NAT network.  The guest firewall rule
restricts ingress to VirtualBox NAT host 10.0.2.2 by default.  The host must
forward 127.0.0.1:2222 to the guest port 22; never bridge/expose this lab.
#>
[CmdletBinding()]param([switch]$UseWindowsCapability)
$ErrorActionPreference='Stop'
$principal=[Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Run as Administrator.' }
if (-not (Get-Service sshd -ErrorAction SilentlyContinue)) {
    if ($UseWindowsCapability) {
        Add-WindowsCapability -Online -Name 'OpenSSH.Server~~~~0.0.1.0' -ErrorAction Stop | Out-Host
    } else {
        $winget=Get-Command winget.exe -ErrorAction SilentlyContinue
        if (-not $winget) { throw 'WinGet unavailable. Try -UseWindowsCapability or install Microsoft OpenSSH Preview manually.' }
        & $winget.Source install --exact --id Microsoft.OpenSSH.Preview --source winget --silent --accept-package-agreements --accept-source-agreements
        if ($LASTEXITCODE -ne 0) { throw "OpenSSH installation failed ($LASTEXITCODE)" }
    }
}
if (-not (Get-Service sshd -ErrorAction SilentlyContinue)) { throw 'sshd service not found after installation.' }
Set-Service -Name sshd -StartupType Automatic
Start-Service sshd
# Remove broad default OpenSSH SSH Server rule created by the OS, if present.
Get-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -ErrorAction SilentlyContinue | Disable-NetFirewallRule
$rule='DeskMateLab SSH from VirtualBox NAT host'
Get-NetFirewallRule -DisplayName $rule -ErrorAction SilentlyContinue | Remove-NetFirewallRule
New-NetFirewallRule -DisplayName $rule -Direction Inbound -Action Allow -Protocol TCP -LocalPort 22 -RemoteAddress 10.0.2.2 -Profile Any | Out-Null
Write-Host 'SSH running; restrict VirtualBox host forwarding to 127.0.0.1:2222 -> guest :22.'
Write-Warning 'Check for other SSH allow rules; switch accounts away from the known default password before using SSH.'
