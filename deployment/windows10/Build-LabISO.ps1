#requires -Version 5.1
<#
.DESCRIPTION
    Build a Windows 10 Pro research-lab ISO from user-supplied Microsoft media.
    No Windows, DeskMate, Ghidra or other third-party binaries enter Git.
    For Lab mode this is DESTRUCTIVE TO DISK 0 in a UEFI VM.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$SourceISO,
    [Parameter(Mandatory=$true)][string]$OutputISO,
    [ValidateSet('Lab','VirtualBox')][string]$AccountMode = 'Lab',
    [string]$LabUser = 'DeskMateLab',
    [string]$LabPassword = 'DeskMateLab-ChangeMe!',
    [string]$WorkDir = (Join-Path $env:TEMP 'deskmate-win10-iso'),
    [string]$PackageDirectory,
    [string]$GuestAdditionsISO,
    [switch]$EnableAutoLogon,
    [ValidateSet('Lan','HttpOnly')][string]$DeliveryOptimizationMode = 'Lan',
    [switch]$EraseDisk0UEFI,
    [switch]$KeepWorkDir
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$kit = Split-Path -Parent $MyInvocation.MyCommand.Path
function Require([bool]$condition,[string]$message) { if (-not $condition) { throw $message } }
function Escape-Xml([string]$s) { return [System.Security.SecurityElement]::Escape($s) }
function Invoke-Checked([string]$exe,[string[]]$arguments,[int[]]$ok=@(0)) {
    & $exe @arguments
    if ($LASTEXITCODE -notin $ok) { throw "Failed ($LASTEXITCODE): $exe $($arguments -join ' ')" }
}
Require ($PSVersionTable.PSVersion.Major -ge 5) 'PowerShell 5.1+ required.'
$principal = [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
Require ($principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) 'Run as Administrator.'
$SourceISO = (Resolve-Path -LiteralPath $SourceISO).Path
Require ($SourceISO -match '\.iso$') 'Source must be an ISO.'
Require (Test-Path -LiteralPath $SourceISO -PathType Leaf) 'Source ISO not found.'
# System.IO.Path.GetFullPath(relative) uses the process working directory,
# which can differ from PowerShell's current provider location (notably when
# running elevated). Resolve relative paths against the caller's location.
$invocationDirectory = (Get-Location).ProviderPath
function Resolve-BuildPath([string]$path) {
    if ([IO.Path]::IsPathRooted($path)) { return [IO.Path]::GetFullPath($path) }
    return [IO.Path]::GetFullPath((Join-Path $invocationDirectory $path))
}
$OutputISO = Resolve-BuildPath $OutputISO
$WorkDir = Resolve-BuildPath $WorkDir
Require (-not $OutputISO.StartsWith($WorkDir.TrimEnd('\')+'\',[StringComparison]::OrdinalIgnoreCase)) 'Output ISO cannot be within staging directory.'
Require ($OutputISO -ne $SourceISO) 'Never overwrite the original Microsoft ISO.'
Require (-not (Test-Path -LiteralPath $OutputISO)) 'Refusing to overwrite an existing output ISO.'
if ($EnableAutoLogon -and $AccountMode -ne 'Lab') { throw '-EnableAutoLogon requires -AccountMode Lab.' }
if ($AccountMode -eq 'Lab') {
    Require ($EraseDisk0UEFI.IsPresent) 'Lab mode DESTROYS VM DISK 0. Specify -EraseDisk0UEFI explicitly.'
    Require ($LabUser -match '^[A-Za-z][A-Za-z0-9_-]{2,19}$') 'Use a simple account name (3-20 ASCII characters).'
    Require ($LabPassword.Length -ge 12) 'Lab password must have at least 12 characters.'
    Write-Warning 'A public/default password is INSECURE. Change it after the first successful build and keep the VM behind NAT.'
}
$oscdimg = Get-Command 'oscdimg.exe' -ErrorAction SilentlyContinue
if ($oscdimg) { $oscdimg = $oscdimg.Source } else {
    $oscdimg = Join-Path ${env:ProgramFiles(x86)} 'Windows Kits\10\Assessment and Deployment Kit\Deployment Tools\amd64\Oscdimg\oscdimg.exe'
}
Require (Test-Path $oscdimg) 'Install Windows ADK Deployment Tools (oscdimg.exe) before building the ISO.'
Require (-not (Test-Path -LiteralPath $WorkDir)) 'Working directory already exists; specify a fresh -WorkDir or remove it manually.'
$stage = Join-Path $WorkDir 'media'
New-Item -ItemType Directory -Path $stage -Force | Out-Null
$mounted = $false
try {
    $disk = Mount-DiskImage -ImagePath $SourceISO -StorageType ISO -PassThru -ErrorAction Stop
    $mounted = $true
    $volume = $disk | Get-Volume
    Require ($null -ne $volume.DriveLetter) 'ISO volume has no drive letter.'
    $drive = '{0}:\' -f $volume.DriveLetter
    Invoke-Checked 'robocopy.exe' @($drive,$stage,'/E','/R:2','/W:2','/NFL','/NDL','/NJH','/NJS') @(0,1,2,3,4,5,6,7)
} finally {
    if ($mounted) { Dismount-DiskImage -ImagePath $SourceISO -ErrorAction Continue | Out-Null }
}
$imageFile = if (Test-Path (Join-Path $stage 'sources\install.wim')) { Join-Path $stage 'sources\install.wim' } elseif (Test-Path (Join-Path $stage 'sources\install.esd')) { Join-Path $stage 'sources\install.esd' } else { throw 'Media must include sources/install.wim or install.esd.' }
$imageInfo = & dism.exe /English /Get-WimInfo "/WimFile:$imageFile"
Require ($LASTEXITCODE -eq 0) 'DISM could not inspect install image.'
Require (($imageInfo -join "`n") -match '(?m)^Name\s*:\s*Windows 10 Pro\s*$') 'No exact Windows 10 Pro edition found in the installation image; inspect DISM output.'
$payload = Join-Path $stage 'sources\$OEM$\$1\DeskMateLab'
$setupScripts = Join-Path $stage 'sources\$OEM$\$$\Setup\Scripts'
New-Item -ItemType Directory -Path $payload,$setupScripts -Force | Out-Null
foreach ($name in @('Provision-Lab.ps1','Privacy-Lab.ps1','Verify-Lab.ps1','Enable-LabSSH.ps1','Setup-86Box-UCRT64.sh',
        'Configure-LabWorkstation.ps1','Install-LabGuestAdditions.ps1','Set-LabLogon.ps1','Initialize-LabWinGet.ps1')) {
    Copy-Item -LiteralPath (Join-Path $kit $name) -Destination (Join-Path $payload $name)
}
Copy-Item -LiteralPath (Join-Path $kit 'SetupComplete.cmd') -Destination (Join-Path $setupScripts 'SetupComplete.cmd')
Set-Content -LiteralPath (Join-Path $payload 'installation-mode.txt') -Value $AccountMode -Encoding ASCII
Set-Content -LiteralPath (Join-Path $payload 'delivery-optimization-mode.txt') -Value $DeliveryOptimizationMode -Encoding ASCII
if ($PackageDirectory) {
    $PackageDirectory = (Resolve-Path -LiteralPath $PackageDirectory).Path
    Copy-Item -LiteralPath $PackageDirectory -Destination (Join-Path $payload 'Packages') -Recurse
}
# Optional user-provided Guest Additions ISO. Keep Oracle binaries OUT of Git;
# only the privately generated deployment ISO receives its contents.
$guestAdditionsHash = $null
if ($GuestAdditionsISO) {
    $GuestAdditionsISO = (Resolve-Path -LiteralPath $GuestAdditionsISO).Path
    Require ($GuestAdditionsISO -match '\.iso$') 'Guest Additions source must be an ISO.'
    Require ($GuestAdditionsISO -ne $SourceISO) 'Guest Additions source cannot be the Windows ISO.'
    $guestAdditionsHash = (Get-FileHash -LiteralPath $GuestAdditionsISO -Algorithm SHA256).Hash
    $guestMounted = $false
    try {
        $gaDisk = Mount-DiskImage -ImagePath $GuestAdditionsISO -StorageType ISO -PassThru -ErrorAction Stop
        $guestMounted = $true
        $gaVolume = $gaDisk | Get-Volume
        Require ($null -ne $gaVolume.DriveLetter) 'Guest Additions ISO has no drive letter.'
        $gaDrive = '{0}:\' -f $gaVolume.DriveLetter
        Require (Test-Path (Join-Path $gaDrive 'VBoxWindowsAdditions.exe')) `
            'Guest Additions ISO does not contain VBoxWindowsAdditions.exe.'
        $gaDest = Join-Path $payload 'Packages\VBoxGuestAdditions'
        New-Item -ItemType Directory -Path $gaDest -Force | Out-Null
        Invoke-Checked 'robocopy.exe' @($gaDrive,$gaDest,'/E','/R:2','/W:2','/NFL','/NDL','/NJH','/NJS') @(0,1,2,3,4,5,6,7)
    } finally {
        if ($guestMounted) { Dismount-DiskImage -ImagePath $GuestAdditionsISO -ErrorAction Continue | Out-Null }
    }
}
if ($AccountMode -eq 'Lab') {
    $template = Get-Content -LiteralPath (Join-Path $kit 'autounattend-uefi.xml.in') -Raw
    # One bootstrap login is used even when persistent auto-logon is disabled,
    # so the original FirstLogonCommands can run without OOBE interaction.
    # With the switch, Windows persists a deliberately high LogonCount;
    # Set-LabLogon.ps1 is the supported way to rotate/disable it later.
    $logonCount = if ($EnableAutoLogon) { '9999' } else { '1' }
    $template = $template.Replace('@USERNAME@',(Escape-Xml $LabUser)).Replace('@PASSWORD@',(Escape-Xml $LabPassword)).Replace('@AUTOLOGON_COUNT@',$logonCount)
    # Installation key selects Pro but DOES NOT license or activate the installation.
    Set-Content -LiteralPath (Join-Path $stage 'autounattend.xml') -Value $template -Encoding UTF8
} else {
    # VirtualBox will generate its own answer file, account and disk layout.
    Remove-Item -LiteralPath (Join-Path $stage 'autounattend.xml') -ErrorAction SilentlyContinue
}
$etfsboot = Join-Path $stage 'boot\etfsboot.com'
$efisys = Join-Path $stage 'efi\microsoft\boot\efisys.bin'
Require ((Test-Path $etfsboot) -and (Test-Path $efisys)) 'ISO is missing BIOS/UEFI boot images.'
New-Item -ItemType Directory -Path (Split-Path -Parent $OutputISO) -Force | Out-Null
$bootArg = '-bootdata:2#p0,e,b{0}#pEF,e,b{1}' -f $etfsboot,$efisys
Invoke-Checked $oscdimg @('-m','-o','-u2','-udfver102',$bootArg,$stage,$OutputISO)
$result = [ordered]@{
    built_utc=(Get-Date).ToUniversalTime().ToString('o')
    account_mode=$AccountMode
    source_iso_sha256=(Get-FileHash -LiteralPath $SourceISO -Algorithm SHA256).Hash
    output_iso_sha256=(Get-FileHash -LiteralPath $OutputISO -Algorithm SHA256).Hash
    output_iso=$OutputISO
    includes_password=($AccountMode -eq 'Lab')
    persistent_auto_logon=($AccountMode -eq 'Lab' -and $EnableAutoLogon.IsPresent)
    delivery_optimization_mode=$DeliveryOptimizationMode
    guest_additions_iso_sha256=$guestAdditionsHash
    notes='No activation key, original DeskMate media, ROMs or personal credentials are bundled.'
}
$result | ConvertTo-Json | Set-Content -LiteralPath "$OutputISO.build.json" -Encoding UTF8
Write-Host "Created $OutputISO ($($result.output_iso_sha256))" -ForegroundColor Green
Write-Warning 'The ISO contains a KNOWN, PLAINTEXT lab-account password in Lab mode. Do not share it as a secure image.'
if (-not $KeepWorkDir) { Remove-Item -LiteralPath $WorkDir -Force -Recurse }
