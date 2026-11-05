# Windows 10 lab integration status (November 2026)

This document distinguishes actual outcomes on the ESXi lab workstation
from remaining installer promises and unvalidated features. The Windows
image and proprietary software are never published here.

## Observed on the existing ESXi Windows 10 Pro 22H2 VM

- Windows build 19045 installed and usable through RDP.
- Initial unattended media reached OOBE but still prompted for region and
  keyboard. The later `oobeSystem` locale fix **needs a fresh ISO test**.
- WinGet needed a Microsoft App Installer update/registration. After
  correcting that prerequisite, first-login provisioning installed Chrome,
  Git, Python, MSYS2, Java, Node.js, 7-Zip, Ghidra and Codex CLI, and
  cloned the public project. The completion marker and `Verify-Lab.ps1`
  confirmed core components.
- ISO-copied scripts retained read-only attributes; deployment now clears
  those attributes. Early verifier builds failed on missing registry values;
  the revised verifier treats optional policies as absent rather than crashing.
- VMware Tools initially installed its VMXNET3 driver and authentication
  service without the main `VMTools` service. A subsequent Repair worked
  according to the operator. The ChatGPT Windows app was also installed
  and signed in; the Store GUI had stalled earlier.
- The automation-enabled 86Box 7.0 development build compiled successfully
  under MSYS2 UCRT64. Native loopback socket automation and restored Tandy
  MS-DOS 5.00 baseline are independently described under
  `docs/research/rsx-dos5-baseline.md` in the experimental research branch.
- An emulator harness launch with PowerShell `-WindowStyle Hidden` had no
  visible emulator window. GUI-driven Computer Use subsequently disrupted
  the RDP connection; avoid this method for routine emulator interaction.

## Scope and remaining work

This is a **source-only experimental deployment recipe**, not a finished
hands-free installer or a supported Windows product. Windows 10 is outside
general support and should remain isolated from untrusted networks.
The published default lab password is deliberately insecure; change it
on any network-reachable guest.

Unverified or incomplete features include fresh ISO/OOBE locale validation,
fully autonomous reboot/resume after installer interruptions, reliable
offline package caching and version pinning, unattended installation of
compatible VMware Tools and ChatGPT, ROM and consumer-app cleanup stages
on a fresh Windows image, and end-to-end VirtualBox Guest Additions tests.

The guest disk audit's report-path check originally failed on Windows.
Its canonical path containment fix and tests are tracked in CI, but host
mounting is intended for powered-off VirtualBox media on macOS, not a
live Windows ESXi guest.

For later research, prefer direct authenticated 86Box automation on
`127.0.0.1`, visible-window launches for interactive observation and
background mode only when explicitly requested. Never use host GUI
input injection to control the guest over RDP.
