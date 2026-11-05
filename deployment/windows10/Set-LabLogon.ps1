#requires -Version 5.1
<#
.SYNOPSIS
    Rotate the DeskMateLab local password and keep persistent auto-logon in sync.
.DESCRIPTION
    Requires an elevated 64-bit Windows PowerShell session. Does not accept a
    plaintext password argument: any required password is prompted securely.
    Auto-logon uses the documented Winlogon registry mechanism, which stores
    its password as REG_SZ (readable by local administrators). It is deliberately
    opt-in; do not use a valuable or reused password on an auto-login lab VM.
.EXAMPLE
    .\Set-LabLogon.ps1 -ChangePassword
.EXAMPLE
    .\Set-LabLogon.ps1 -ChangePassword -AutoLogon Enable
.EXAMPLE
    .\Set-LabLogon.ps1 -AutoLogon Disable
#>
[CmdletBinding()]
param(
    [string]$LabUser='DeskMateLab',
    [switch]$ChangePassword,
    [ValidateSet('Keep','Enable','Disable')]
    [string]$AutoLogon='Keep'
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
if (-not $ChangePassword -and $AutoLogon -eq 'Keep') {
    throw 'Specify -ChangePassword and/or -AutoLogon Enable|Disable.'
}
$admin=[Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $admin.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run in an elevated Windows PowerShell session.'
}
$account=Get-LocalUser -Name $LabUser -ErrorAction Stop
if (-not $account.Enabled) { throw "The local account '$LabUser' is disabled." }
$winlogon='HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon'
$prior=Get-ItemProperty -LiteralPath $winlogon
$currentEnabled=($prior.AutoAdminLogon -eq '1' -and $prior.DefaultUserName -eq $LabUser)
$enable=($AutoLogon -eq 'Enable' -or ($AutoLogon -eq 'Keep' -and $ChangePassword -and $currentEnabled))
$secure=$null
if ($ChangePassword -or $enable) {
    $secure=Read-Host 'Enter the new/current lab account password' -AsSecureString
    if ($secure.Length -eq 0) { throw 'Empty password is not allowed.' }
}
if ($ChangePassword) {
    Set-LocalUser -Name $LabUser -Password $secure -ErrorAction Stop
    Write-Host "Updated the local password for $LabUser."
}
if ($AutoLogon -eq 'Disable') {
    Set-ItemProperty -LiteralPath $winlogon -Name AutoAdminLogon -Value '0' -Type String
    Remove-ItemProperty -LiteralPath $winlogon -Name DefaultPassword -ErrorAction SilentlyContinue
    Remove-ItemProperty -LiteralPath $winlogon -Name AutoLogonCount -ErrorAction SilentlyContinue
    Write-Host 'Persistent automatic login disabled; Winlogon DefaultPassword cleared.'
} elseif ($enable) {
    # Winlogon requires a plaintext REG_SZ. The secure input is never emitted
    # to the console or passed as a command-line argument.
    $ptr=[IntPtr]::Zero
    try {
        $ptr=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
        $plain=[Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
        Set-ItemProperty -LiteralPath $winlogon -Name DefaultUserName -Value $LabUser -Type String
        Set-ItemProperty -LiteralPath $winlogon -Name DefaultDomainName -Value $env:COMPUTERNAME -Type String
        Set-ItemProperty -LiteralPath $winlogon -Name DefaultPassword -Value $plain -Type String
        Set-ItemProperty -LiteralPath $winlogon -Name AutoAdminLogon -Value '1' -Type String
        # Setup's one-time or high-count autologon must not take precedence
        # over a later manual switch to indefinite local lab auto-login.
        Remove-ItemProperty -LiteralPath $winlogon -Name AutoLogonCount -ErrorAction SilentlyContinue
        Write-Warning 'Auto-logon enabled. Winlogon stores the lab password as plaintext in the registry.'
    } finally {
        if ($ptr -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
        Remove-Variable plain -ErrorAction SilentlyContinue
    }
} else {
    Write-Host 'Automatic-login setting left unchanged.'
}
Write-Host 'Changes take effect at the next interactive sign-in or reboot.'
