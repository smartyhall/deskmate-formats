#requires -Version 5.1
<#
.SYNOPSIS
    Idempotent installation and configuration of the Windows 10 research lab.
    Designed to run once after OOBE, and also be safely resumed manually.
#>
[CmdletBinding()]param([switch]$SkipOnlinePackages)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
$root='C:\DeskMateLab'
$logDir=Join-Path $root 'setup-logs'
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$done=Join-Path $root 'provision-complete.txt'
if (Test-Path $done) { Write-Host 'Already provisioned.'; exit 0 }
$mutex = New-Object System.Threading.Mutex($false,'Global\DeskMateLabProvisionV1')
if (-not $mutex.WaitOne(10000)) { Write-Host 'Provisioning in progress in another session.'; exit 0 }
try {
    if (Test-Path $done) { exit 0 }
    $log=Join-Path $logDir ('provision-'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'.log')
    Start-Transcript -Path $log | Out-Null
    try {
        & (Join-Path $root 'Privacy-Lab.ps1')
        # Apply workstation ergonomics before network downloads, so they remain
        # configured even if a later package installer fails.
        & (Join-Path $root 'Configure-LabWorkstation.ps1')
        # Guest Additions are optional: a user-supplied ISO may be bundled with
        # the installer or inserted as the guest CD. Never download them from a
        # random third-party mirror or misreport an absent image as installed.
        try {
            & (Join-Path $root 'Install-LabGuestAdditions.ps1')
        } catch {
            $_ | Out-String | Set-Content -LiteralPath (Join-Path $logDir 'guest-additions-error.txt')
            Write-Warning 'Guest Additions stage could not finish; inspect private setup logs and retry separately.'
        }
        foreach ($d in @('sources','builds','private-evidence','downloads','Packages')) {
            New-Item -ItemType Directory -Path (Join-Path $root $d) -Force | Out-Null
        }
        # WinGet requires user-profile registration on fresh Windows 10 installs.
        # Check/repair this prerequisite before long downloads. The helper can
        # consume a user-provided offline MSIX bundle staged in Packages.
        if (-not $SkipOnlinePackages) {
            & (Join-Path $root 'Initialize-LabWinGet.ps1')
        }
        # Chrome Enterprise's official, Google-hosted MSI. Verify publisher.
        if (-not (Test-Path 'C:\Program Files\Google\Chrome\Application\chrome.exe')) {
            $msi=Join-Path $root 'Packages\googlechromestandaloneenterprise64.msi'
            if (-not (Test-Path $msi)) {
                $url='https://dl.google.com/dl/chrome/install/googlechromestandaloneenterprise64.msi'
                Invoke-WebRequest -Uri $url -OutFile $msi -UseBasicParsing
            }
            $sig=Get-AuthenticodeSignature -FilePath $msi
            if ($sig.Status -ne 'Valid' -or $sig.SignerCertificate.Subject -notmatch 'Google') {
                throw 'Chrome MSI signature/publisher verification failed. Do not execute installer.'
            }
            & msiexec.exe /i $msi /qn /norestart
            if ($LASTEXITCODE -notin @(0,3010,1641)) { throw "Chrome MSI failed: $LASTEXITCODE" }
        }
        # WinGet was checked/registered above, in the interactive user's context.
        $winget=Get-Command winget.exe -ErrorAction SilentlyContinue
        if (-not $SkipOnlinePackages -and $null -ne $winget) {
            foreach ($id in @('Git.Git','GitHub.cli','Python.Python.3.13',
                    'EclipseAdoptium.Temurin.21.JDK','7zip.7zip','MSYS2.MSYS2',
                    'OpenJS.NodeJS.LTS')) {
                Write-Host "Installing $id via WinGet"
                & $winget.Source install --exact --id $id --source winget --silent --disable-interactivity --accept-package-agreements --accept-source-agreements
                if ($LASTEXITCODE -ne 0) { throw "WinGet failed for $id ($LASTEXITCODE)" }
            }
        } elseif (-not $SkipOnlinePackages) {
            Write-Warning 'WinGet is not installed/visible. Update Microsoft App Installer then rerun.'
            Set-Content -Path (Join-Path $logDir 'winget-missing.txt') -Value 'Install Microsoft App Installer, then rerun provision script.'
            throw 'WinGet missing: cannot claim the lab is fully provisioned.'
        }
        # Exact Ghidra version used by our 2026 reverse-engineering reports.
        $ghidraDir='C:\Tools\ghidra_12.1.4_PUBLIC'
        if (-not (Test-Path (Join-Path $ghidraDir 'support\analyzeHeadless.bat'))) {
            $ghidraZip=Join-Path $root 'Packages\ghidra_12.1.4_PUBLIC_20260921.zip'
            if (-not (Test-Path $ghidraZip)) {
                $url='https://github.com/NationalSecurityAgency/ghidra/releases/download/Ghidra_12.1.4_build/ghidra_12.1.4_PUBLIC_20260921.zip'
                Invoke-WebRequest -Uri $url -OutFile $ghidraZip -UseBasicParsing
            }
            $expected='ddac49f903da9d5bac833e5cc79395098b9c33cfd3279be5f31bd00387d2d4db'
            $actual=(Get-FileHash -LiteralPath $ghidraZip -Algorithm SHA256).Hash.ToLowerInvariant()
            if ($actual -ne $expected) { throw 'Ghidra zip SHA-256 verification failed.' }
            New-Item -ItemType Directory -Path 'C:\Tools' -Force | Out-Null
            Expand-Archive -LiteralPath $ghidraZip -DestinationPath 'C:\Tools' -Force
        }
        if (-not (Test-Path (Join-Path $ghidraDir 'support\analyzeHeadless.bat'))) { throw 'Ghidra extraction did not produce expected headless tool.' }
        [Environment]::SetEnvironmentVariable('GHIDRA_INSTALL_DIR',$ghidraDir,'Machine')
        # Codex CLI installs without authentication or storing ChatGPT secrets.
        $npm='C:\Program Files\nodejs\npm.cmd'
        if (-not (Test-Path $npm)) { throw 'Node.js/npm missing: cannot install Codex CLI.' }
        & $npm install --global '@openai/codex'
        if ($LASTEXITCODE -ne 0) { throw "npm Codex CLI install failed ($LASTEXITCODE)" }
        # Clone only the public, independently-authored source; never fetch DOSLAB.
        $git='C:\Program Files\Git\cmd\git.exe'
        $checkout=Join-Path $root 'sources\deskmate-formats'
        if (-not (Test-Path (Join-Path $checkout '.git'))) {
            if (-not (Test-Path $git)) { throw 'Git was not installed where expected.' }
            & $git clone https://github.com/smartyhall/deskmate-formats.git $checkout
            if ($LASTEXITCODE -ne 0) { throw 'deskmate-formats clone failed.' }
        }
        if (Test-Path $git) {
            & $git -C $checkout rev-parse HEAD | Set-Content (Join-Path $logDir 'source-commit.txt')
        }
        # OpenSSH Server is deliberately not enabled/exposed by unattended setup.
        # Run SSH setup only after checking the VM NAT/firewall configuration.
        # 86Box needs the MSYS2 UCRT64 pacman base update before its build stage.
        Set-Content -Path $done -Value (Get-Date).ToUniversalTime().ToString('o')
        Write-Host 'Core provisioning complete (including Ghidra and Codex CLI). Update MSYS2 then build 86Box.'
    } finally { Stop-Transcript | Out-Null }
} catch {
    $_ | Out-String | Add-Content -Path (Join-Path $logDir 'last-error.txt')
    throw
} finally {
    # Do not create an unending auto-retry loop on failed installers.
    # SetupComplete registers this fallback task only for VirtualBox; ESXi
    # and other environments normally have no task to delete. Do not let
    # optional task cleanup turn a successful provisioning run into an error.
    try {
        $task = Get-ScheduledTask -TaskName 'DeskMateLab-FirstLogon' -ErrorAction SilentlyContinue
        if ($null -ne $task) {
            Unregister-ScheduledTask -TaskName 'DeskMateLab-FirstLogon' -Confirm:$false -ErrorAction Stop
        }
    } catch {
        Write-Warning ('Optional first-logon task cleanup failed: ' + $_.Exception.Message)
    }
    $mutex.ReleaseMutex(); $mutex.Dispose()
}
