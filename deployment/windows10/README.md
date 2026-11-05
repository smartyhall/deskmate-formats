# Windows 10 Pro laboratory image (experimental deployment kit)

**Status: experimental, integration tests in progress (VirtualBox and ESXi).** This is
reproducible *source* for a research installation, **not** redistributable
Windows installation media. A contributor supplies a legitimately obtained
Windows 10 Pro x64 ISO and their own licensed third-party software/media.
No ISO, third-party installer, proprietary DeskMate file, ROM, real database,
password specific to a user, API token, activation key or lab snapshot belongs
in the public repo.

The builder uses Windows PowerShell 5.1, DISM to inspect the Windows image,
and Microsoft ADK `oscdimg` to construct a dual BIOS/UEFI bootable ISO. It does
**not** alter the Windows component store, strip components, or disable security
updates. Windows 10 Pro is out of general support; treat the installation as an
isolated research machine. Use a restricted VM network on ESXi or NAT on
VirtualBox, and avoid exposing the default-password account to the LAN.

## Before building

1. On a Windows 10 x64 host, install **Windows ADK Deployment Tools** (includes
   `oscdimg.exe`). Have enough free disk space for two copies of the original
   installation media and the output ISO.
2. Check you have official Windows 10 **Pro 22H2** x64 installation media.
   The builder rejects media without an exactly named `Windows 10 Pro` image.
3. Run elevated Windows PowerShell from this directory. Keep the build directory
   and output ISO **outside** your Git working tree.

### Recommended: known account / autonomous UEFI VM

For a **new, empty, disposable UEFI VM (ESXi or VirtualBox)**, select
Lab mode. The `-EraseDisk0UEFI` switch is an explicit acknowledgment that the
unattended Windows Setup **ERASES EVERYTHING ON GUEST DISK 0** and creates UEFI
EFI/MSR/Windows partitions. *Never attach your real data disks.*

```powershell
.\Build-LabISO.ps1 -SourceISO D:\Images\Win10_22H2_English_x64.iso `
    -OutputISO D:\Images\DeskMateLab-Win10-Pro.iso `
    -AccountMode Lab -EraseDisk0UEFI
```

Default local administrator: `DeskMateLab`; default password:
`DeskMateLab-ChangeMe!`. **This is a PUBLIC, insecure lab password** embedded
in plaintext in `autounattend.xml` on the ISO. Change it after setup (`net user
DeskMateLab *` in an elevated terminal) and keep guest networking on NAT. Build
with `-LabUser` and `-LabPassword` to supply different values, but the custom
password is still **embedded in the generated ISO**. Never store a real personal
password or secrets in the recipe or image. Windows Setup uses the public
non-activating Pro installation key; you supply a license/activation key later.

If you redistribute the *recipe*, not the generated ISO, there is no account
credential to leak beyond the intentionally published sample value.

### Optional persistent automatic login and password rotation

A first-login bootstrap is required by the existing `FirstLogonCommands`
provisioning, regardless of whether persistent auto-login is selected.
By default this bootstrap is limited to one automatic login; use
`-EnableAutoLogon` to request repeated automatic logins on subsequent reboots:

```powershell
.\Build-LabISO.ps1 -SourceISO D:\Images\Win10_22H2_English_x64.iso `
    -OutputISO D:\Images\DeskMateLab-Win10-Pro.iso `
    -AccountMode Lab -EraseDisk0UEFI -EnableAutoLogon
```

This uses Windows unattend `AutoLogon` with a large `LogonCount` rather than
installing an external executable. It is *not* indefinite: the count will
exhaust eventually. The generated ISO contains the selected password as
plaintext regardless of whether this option is enabled.

To rotate the password and update stored login settings together, run an
elevated **64-bit Windows PowerShell** session in the installed VM:

```powershell
# Secure password prompt; preserve existing autologon state if enabled.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\DeskMateLab\Set-LabLogon.ps1 -ChangePassword

# Rotate password and enable persistent login (prompts once).
powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\DeskMateLab\Set-LabLogon.ps1 -ChangePassword -AutoLogon Enable

# Disable automatic login and clear Winlogon's stored password.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\DeskMateLab\Set-LabLogon.ps1 -AutoLogon Disable
```

`Set-LabLogon.ps1` uses the Winlogon registry method, not Sysinternals
Autologon/LSA secrets. The password is **plaintext in Winlogon registry**
when persistent login is enabled. Treat even a customized password as a
lab-only password, not one reused for other systems. The script prompts for
passwords instead of putting them on command lines; it does not send them to
logs. No such password belongs in the repository. No Windows guest runtime
behavior has yet been tested with this new helper; validate on a snapshot.

This is independent of reboot-resilient provisioning. The current provisioning
script is **not** a durable reboot-resume orchestrator: Windows Update can
interrupt it, and failed downloads are not automatically resumed. That remains
an explicit follow-up task rather than a claimed capability.

### Alternative: VirtualBox-provided account

```powershell
.\Build-LabISO.ps1 -SourceISO D:\Images\Win10_22H2_English_x64.iso `
    -OutputISO D:\Images\DeskMateLab-Win10-VBox.iso `
    -AccountMode VirtualBox
```

**No** `autounattend.xml` is included in this mode. Use VirtualBox's
**Unattended Installation** controls to supply the name/password, locale,
partitioning and Windows product key (the public non-activating Pro setup key
if required). Avoid asking VirtualBox to inject a second unattended answer file
when using *Lab* mode. `SetupComplete.cmd` arranges a fallback first-logon
provisioning task in the VirtualBox mode. On Pro with an OEM key, Windows may
skip `SetupComplete.cmd`, so provisioning may require manually running
`C:\DeskMateLab\Provision-Lab.ps1` after first login; check logs. Don't promise
a headless deployment until you've validated your particular VirtualBox version.

### WinGet bootstrap on Windows 10

App Installer can be preinstalled on Windows 10 without the `winget.exe`
command being usable for the current account. Microsoft documents an
asynchronous first-login registration and the following repair command:

```powershell
Add-AppxPackage -RegisterByFamilyName -MainPackage Microsoft.DesktopAppInstaller_8wekyb3d8bbwe
winget.exe --version
```

`Initialize-LabWinGet.ps1` checks for a working executable, attempts registration
under the **interactive DeskMateLab user** (not LocalSystem), and then supports
an optional locally staged official `Microsoft.DesktopAppInstaller.msixbundle`.
Any required matching framework packages can be staged at
`Packages\WinGetDependencies`. `Add-AppxPackage` validates package signatures
and dependencies. The initial ISO does not download or embed these Microsoft
packages automatically. If the installed App Installer is too old, registration
alone cannot supply an updated WinGet executable; obtain App Installer via
Microsoft Store or an official Microsoft WinGet release, then rerun provisioning.
The script fails explicitly, rather than pretending all developer tools installed.
See the [Microsoft WinGet guidance](https://learn.microsoft.com/en-us/windows/package-manager/winget/)
and [MSIX dependency guidance](https://learn.microsoft.com/en-us/windows/msix/msix-troubleshooting-guide).

### Delivery Optimization (Windows Update / Store only)

The kit now defaults to LAN-only Windows Delivery Optimization peering, which
lets VMs behind the **same public NAT address** share eligible Microsoft update
content. This does not distribute Chrome, Ghidra or arbitrary installer files,
and VLAN/segment isolation may affect peer discovery. No Internet-wide peers
are permitted. To disable peers while retaining direct Microsoft downloads,
pass `-DeliveryOptimizationMode HttpOnly` to `Build-LabISO.ps1`. The default
is `-DeliveryOptimizationMode Lan` (Windows policy `DODownloadMode=1`).
The selected mode is recorded in the local build manifest and staged into
the installed VM, where `Privacy-Lab.ps1` applies the matching policy. The mode
is not a global change to ESXi or the Mac host.

For an existing VM built with an older ISO, in elevated PowerShell:

```powershell
New-Item 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\DeliveryOptimization' -Force | Out-Null
New-ItemProperty 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\DeliveryOptimization' -Name DODownloadMode -Value 1 -PropertyType DWord -Force | Out-Null
```

Note that rerunning the **older** `Privacy-Lab.ps1` from your original ISO will
restore its original HTTP-only policy until you also update that script.
See [Microsoft's Delivery Optimization documentation](https://learn.microsoft.com/en-us/windows/deployment/do/delivery-optimization-configure).

### Optional pre-bundled installers

`-PackageDirectory D:\BuildAssets\Packages` copies a private package cache to
`C:\DeskMateLab\Packages`. Only **Google's correctly named, validly signed**
`googlechromestandaloneenterprise64.msi` is currently consumed directly.
The rest of the initial toolchain uses `winget` after OOBE; WinGet is not always
present or registered on Windows 10 media. The new bootstrap checks it before
Chrome, but may require a newer pre-staged App Installer bundle. To avoid network dependence, additional offline
installer commands, SHA-256 pins and code-signature checks are still planned.
The current kit is therefore **not yet a fully offline, all-tools image**.

## VirtualBox Guest Additions and workstation preferences

The lab does not sleep or turn off the virtual monitor while on AC power.
Windows 10 taskbar Search and News and Interests are hidden for the current
account, and an Active Setup entry applies the per-user choices at later
interactive logons. Windows Search indexing, Windows Update and Defender remain
available. SysMain (Superfetch) is disabled and stopped during machine-wide
provisioning to reduce background disk contention. The optional
\`\\Microsoft\\Windows\\Application Experience\\Microsoft Compatibility Appraiser\`
scheduled task is also disabled alongside the existing CEIP tasks. The
verification report includes both settings, and Windows servicing may
re-enable optional tasks later. Neither change disables Windows Update,
Defender, SmartScreen or the Windows Search service. User interface changes
may require signing out and back in.

VirtualBox Guest Additions are **not** bundled in this public repository.
For a fully unattended installation, supply the official `VBoxGuestAdditions.iso`
from a compatible VirtualBox installation to the ISO builder:

```powershell
.\Build-LabISO.ps1 -SourceISO D:\Images\Win10_22H2_English_x64.iso `
    -OutputISO D:\Images\DeskMateLab-Win10-Pro.iso `
    -AccountMode Lab -EraseDisk0UEFI `
    -GuestAdditionsISO D:\Images\VBoxGuestAdditions.iso
```

The builder copies the contents of that user-supplied ISO to the *generated*
installer and records its SHA-256 in the local build manifest. This is meant
for privately constructed VM media, not redistribution of third-party binaries.
Match the Guest Additions release to the version of VirtualBox on the host.

If it was not bundled, after Windows Setup completes select **Devices → Insert
Guest Additions CD Image** in the VirtualBox menu and run an elevated shell:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
    -File C:\DeskMateLab\Install-LabGuestAdditions.ps1 -RequireMedia
```

The installer validates the Oracle Authenticode signature and uses Oracle's
`VBoxCertUtil` when present before invoking the documented silent `/S` option.
A missing ISO is recorded as deferred, not as a false success. Installer
failures are logged; neither the post-install scripts nor the Guest Additions
installer intentionally reboots the guest. Restart Windows afterward to load
the new Guest Additions drivers. If a certificate installer is absent or a
signature is untrusted, review the source instead of bypassing trust checks.

You can run the workstation preferences independently from an elevated shell:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
    -File C:\DeskMateLab\Configure-LabWorkstation.ps1
```

The public example account password is insecure; change it before enabling
SSH, shared folders, or bidirectional clipboard. These interoperability
features remain opt-in for the isolated lab.

## First-boot provisioning

`$OEM$` copies the setup files into `C:\DeskMateLab`. Early provisioning
sets the power/taskbar preferences and attempts Guest Additions when media is
available; a missing Guest Additions ISO does not stop third-party setup.
For Lab mode,
`FirstLogonCommands` runs an idempotent provisioning script after the one-time
auto-logon. In VirtualBox mode only, a `SetupComplete.cmd` hook registers a fallback
logon task under SYSTEM (where WinGet may not be available). Provisioning creates logs in
`C:\DeskMateLab\setup-logs`, applies conservative telemetry preferences,
installs Google Chrome Enterprise from its official URL (or a signed MSI
provided with the build); installs Git, GitHub CLI, Python 3.13, Temurin
JDK 21, 7-Zip, MSYS2 and Node.js LTS if WinGet is present; checks the
Ghidra 12.1.4 SHA-256 and extracts it; installs the Codex CLI (without
authentication); and clones the public deskmate-formats repository. It writes the
completion marker **only if these steps succeeded**. It does not fake success
on missing WinGet or install errors.

On Windows 10 Pro, setting diagnostic data policy to `1` requests the lowest
supported tier, **not no telemetry**. We also disable optional CEIP/feedback,
consumer suggestions, advertising ID, activity synchronization, Windows Error
Reporting and Chrome usage statistics; **Windows Update and Defender remain
intact**. Chrome's OpenAI extension is configured through a `normal_installed`
Chrome policy and can be disabled by the user. Chrome must fetch the extension
from the Web Store and the user must sign in, grant relevant site permissions,
and verify `chrome://policy`/`chrome://extensions`. Browser integration with
ChatGPT or Codex depends on app/account support and is **not** demonstrated by
this script alone. The extension has broad browser privileges; do not sign in
to sensitive services in this disposable VM without considering the risks.

OpenSSH is intentionally **not started or exposed** by unattended deployment.
After confirming VirtualBox NAT and localhost-only port forwarding, run
`C:\DeskMateLab\Enable-LabSSH.ps1` as Administrator; it installs/starts
SSH and restricts the guest firewall to the VirtualBox NAT host.
Do not publish port 22 through a bridged VM network. This is a deliberate
post-setup safety checkpoint, not a missing installer step.

Once MSYS2 is installed, open its UCRT64 shell, run `pacman -Syu`, restart the
shell if requested, and repeat until updated. The bundled
`Setup-86Box-UCRT64.sh` then installs libraries and compiles 86Box with
`AUTOMATION=ON`; use original third-party ROMs separately. Codex authentication and MCP configuration are follow-up stages, not yet
part of a verified unattended offline build.

### Verify or resume

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\DeskMateLab\Verify-Lab.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\DeskMateLab\Provision-Lab.ps1
```

The builder writes an output `.iso.build.json` file next to the ISO with SHA-256
hashes of original and modified media. Keep that local manifest with the VM
experiment records; do not commit ISO files or private environment content.

## Host-side read-only installation audit

If OOBE hangs or provisioning is uncertain, the optional
[`Audit-LabDisk.py`](Audit-LabDisk.py) can inspect an **entirely powered-off**
VirtualBox Windows disk using the snapshot-aware, read-only `vboximg-mount`
interface on a macOS host. It checks exact Windows Setup, OEM payload,
first-logon, provisioning and installation markers; it generates sanitized JSON
rather than copying raw logs, user information or credentials. A separately
mounted, read-only Windows C: filesystem can also be inspected with `--root`.

**Do not run the VM-mode audit while Codex or any other VirtualBox guest is
running.** See [AUDIT.md](AUDIT.md) for prerequisites, commands, interpretation
and limitations. The host-side mount has portable synthetic tests but still
requires validation against a powered-off VM on the actual Mac host.

## Testing status and limits

- [x] Python XML syntax check of answer-file template (not Windows SIM validation)
- [x] PowerShell and command-file source review (not PowerShell runtime execution)
- [ ] Validate unattended XML with Windows System Image Manager against original media
- [x] First UEFI boot reached Windows Setup and OOBE region prompt (November 2026)
- [ ] Confirm unattended locale, OOBE completion, logon and provisioning
- [ ] Boot VirtualBox unattended mode; verify `SetupComplete` task registration
- [ ] Validate Chrome policy and actual extension install on a user profile
- [ ] Verify WinGet/App Installer availability on exact Windows 10 Pro media
- [ ] Install, compile and smoke-test automation-enabled 86Box
- [ ] Pin third-party package versions/hashes and optionally service WIM offline
- [x] Portable synthetic tests for read-only host disk audit, including actual VirtualBox quoted storage keys
- [ ] Validate `vboximg-mount` snapshot-aware guest-FS access on the actual macOS host

Deployment artifacts are not code dependencies of the Python package and never
run in CI against private evidence. Preserve original Windows and DeskMate
software license requirements when reconstructing the lab.

Deployment customization note: taskbar, power and Guest Additions stages are
source-reviewed, but require a live Windows guest test before being described
as fully verified. They are not present in previously built ISO files.

## Pending ESXi finishing work: VMware Tools and ChatGPT desktop

These remain **unverified tasks**, not completed parts of the ISO recipe.

**VMware Tools.** On the ESXi Windows 10 Pro (19045) experiment, Tools
10.3.10.12406962 registered as installed, `vmtoolsd.exe` existed and
`VGAuthService` was running, but `Get-Service VMTools` found no service
and ESXi showed Tools as absent. The VMXNET3 driver itself worked. This is a
partially installed package, not a networking failure. After Windows Update
settles, take a VM snapshot and mount the VMware Tools installation media
from the host. Use **Programs and Features -> VMware Tools -> Change/Repair**
(or launch the matching installer and choose Repair), reboot, then check
`Get-Service VMTools` and ESXi guest-tools status. If Repair fails,
inspect `vminst.log` / `vmmsi.log` (normally in `C:\Windows\Temp`
or the installing user's `%TEMP%`) before considering a complete
uninstall/reboot/reinstall. For this 10.3.x release, VMware/Broadcom documents
Visual C++ prerequisite installation sometimes needing multiple reboots.
No service is to be created manually, and don't delete registry keys as a
first troubleshooting step. See:
https://knowledge.broadcom.com/external/article/315389/
and https://knowledge.broadcom.com/external/article/313512/ .

**ChatGPT Windows client.** Windows 10 Pro 19045 meets OpenAI's minimum
Windows 10 build 17763.0 requirement. The Microsoft Store GUI stalled during
install on the ESXi guest, although Store/App Installer updating and WinGet
registration previously enabled other packages. Try the documented Store
package ID from the interactive lab-user session:

```powershell
winget.exe install --id 9NT1R1C2HH7J --source msstore --accept-package-agreements --accept-source-agreements
```

This still uses Microsoft's Store backend; it is not an offline installer
or bypass of Windows Store restrictions. If it fails, run `wsreset.exe`,
check pending Windows Update/Store updates, and collect the WinGet error
and `Microsoft-Windows-AppXDeploymentServer/Operational` event logs.
Do not label the installation complete until the app launches and the
user can sign in. See https://help.openai.com/en/articles/9982051-using-the-chatgpt-windows-app
and https://learn.microsoft.com/troubleshoot/windows-client/shell-experience/troubleshooting-microsoft-store-apps-download-failure .

**Future automation:** Optional, user-enabled installation stages for a
VMware-compatible Tools package and the official ChatGPT Store app should
be isolated from the mandatory offline-compatible core provisioning. Neither
requires proprietary installers or private credentials in Git. The ESXi
host's exact version and the compatible Tools media still need recording.

## November 2026 ESXi / VirtualBox integration observations

- The same user-built ISO reached Windows 10 OOBE on both VirtualBox 7.2.22
  under macOS Sequoia/OCLP and on an ESXi host. Both prompted for **region
  and keyboard layout**, despite the earlier WinPE locale settings. An
  `oobeSystem` international-core component was added to the template but
  needs a clean Windows System Image Manager/live install validation.
- VirtualBox exhibited very low and variable transfer speeds. Controlled
  Mac-to-guest 128 MiB HTTP transfers averaged ~87 Mbps (Intel adapter) and
  ~40 Mbps (virtio-net) for Windows 10; an older Windows 11 VM reached
  ~211 Mbps. This is observational, not a universal VirtualBox limit.
- The ESXi Windows 10 guest using VMXNET3 reached ~597 Mbps down and
  ~541 Mbps up in a browser speed test *before VMware Tools integration
  completed*. Provisioning still appeared bottlenecked during the
  `Invoke-WebRequest` Chrome transfer, while Windows Update and PowerShell
  competed for CPU. The provisioning attempt later stopped because WinGet was
  missing or unregistered under the new Windows 10 account.
- VMware Tools 10.3.10 registered and installed drivers and `vmtoolsd.exe`,
  but the expected VMTools service was absent; investigate on the ESXi VM
  before claiming guest management integration works.
- The current build still lacks verified reboot-safe provisioning, fully
  pre-cached/updatable offline packages, validated clean OOBE, and a complete
  hands-free ESXi installation. A new WinGet registration/offline-bundle path
  addresses one known missing prerequisite but has not yet been tested in ESXi. Do not describe them as working features.

Original experiment logs, screenshots, proprietary media and user-specific
VM configuration details remain outside the public repository.
