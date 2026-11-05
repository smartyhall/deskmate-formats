# Offline, read-only audit of a Windows 10 lab VM

`Audit-LabDisk.py` is a **host-side diagnostic**, not a guest provisioning
script. It uses Python 3 and only Python's standard library. It can inspect
expected files in a Windows filesystem after installation, even if the guest
cannot finish OOBE or boot. No original Windows, DeskMate or private research
material is supplied with the script.

## Safety prerequisite

**Do not use `--vm` while any VirtualBox VM is running.** Shut down **all**
VirtualBox guests completely, especially the Windows 10 target and the original
Codex research VM. A *saved* or *suspended* VM is insufficient. The script checks
this and refuses to proceed if a VM is running or if the target is not powered
off. Do not force shutdowns or interrupt Codex work simply to run an audit.

The tool calls `VBoxManage showvminfo --machinereadable` to select the currently
attached **hard-disk image UUID**. This is deliberately not the filename of a
base `.vdi`: snapshot differencing images can hold the newest guest changes.
It then calls `vboximg-mount --guest-filesystem` **without** `--rw` and checks
for exactly one Windows filesystem. `vboximg-mount` is a FUSE-based VirtualBox
utility supporting snapshot chains and read-only NTFS file access. This
experimental guest-filesystem feature and its FUSE requirements vary by host
and VirtualBox version; **macOS execution has not yet been verified on the lab
host**. It does not install FUSE, macFUSE, or any other host dependency.

Oracle's reference: <https://docs.oracle.com/en/virtualization/virtualbox/7.1/user/storage.html>

## From macOS Terminal

Copy `Audit-LabDisk.py` to a directory on the Mac, then:

```sh
# List registered VM names first.
VBoxManage list vms

# ONLY after a clean shutdown of every VirtualBox VM:
python3 Audit-LabDisk.py \
  --vm "YOUR WINDOWS 10 VM NAME" \
  --json "$HOME/Desktop/deskmate-install-audit.json"
```

The JSON report is written **to the Mac** and refuses to overwrite an existing
file. Run it without `--json` to print only the report. Do not put the report
inside the VM's mounted filesystem.

On macOS the script addresses two observed VirtualBox/macFUSE incompatibilities:
`vboximg-mount` 7.2.22 requests `libosxfuse.dylib`, while macFUSE 5.5.0
provides `libfuse.2.dylib`; the script creates a **temporary, private symlink**
and supplies its directory using a **process-local** `DYLD_LIBRARY_PATH`.
It passes `--image UUID` with a space, not `--image=UUID`. Finally, `-o debug`
keeps the FUSE process in the foreground, avoiding the Objective-C unsafe-fork
failure. Debug output is kept in a temporary host-side log that is removed
after a successful unmount; raw output is never included in report JSON.

The host-side detector accepts both VirtualBox controller names such as
`SATA` and `SATA Controller`, including quoted storage keys in
`showvminfo --machinereadable`. It requires each selected image UUID to match
an attached virtual hard-disk file, not an installer ISO. An explicit
`--disk-uuid` is verified against this same current attachment list; it never
bypasses snapshot/attachment safeguards. The storage-key parser and manual mount commands have been confirmed on the Mac Pro.

If the VM has more than one attached hard disk, the script refuses to guess.
Use `VBoxManage showvminfo "YOUR WINDOWS 10 VM NAME" --machinereadable`
and specify the exact attached **hard-disk** image UUID using `--disk-uuid`.
Do not select the installer DVD's UUID or a base image when a differencing
snapshot is attached.

If the VM mount is unavailable, or if you have already mounted a guest volume
in foreground mode from another Terminal, inspect that existing, **read-only
NTFS Windows C: volume** instead:

```sh
python3 Audit-LabDisk.py --root "/path/to/mounted/Windows-volume" \
  --json "$HOME/Desktop/deskmate-install-audit.json"
```

This `--root` mode also supports testing and forensic review of a copied
filesystem tree; unlike `--vm` mode, it cannot verify the VM's runtime state.
If a FUSE unmount fails, the script prints the remaining mount point and a
manual `umount` instruction. It deliberately does not remove active mounts.

## What is checked

Only allowlisted files and locations are consulted:

| Area | Selected signals |
|---|---|
| Windows installed | `Windows/System32/config/SYSTEM` |
| Windows setup | `Windows/Panther/setupact.log`, `setuperr.log` |
| OOBE/unattended processing | `Windows/Panther/UnattendGC/setupact.log`, `setuperr.log` |
| OEM payload | `DeskMateLab/installation-mode.txt`, provisioning and verification scripts |
| Provisioning attempted | Count of `DeskMateLab/setup-logs/provision-*.log` |
| Provisioning reported an error | `setup-logs/last-error.txt`, `winget-missing.txt` |
| Provisioning declared complete | `DeskMateLab/provision-complete.txt` |
| Tool installation hints | Chrome, Git, Node.js, MSYS2 and Ghidra paths |

The report labels each check `present`, `absent` or `inaccessible`, plus a
provisioning-phase classification. The absent state is **not automatically a
failure**: FirstLogonCommands may not run until after OOBE and a successful
administrator logon; packages may be installed in different locations.

When `last-error.txt` exists, the audit reads at most its final 128 KiB and
returns **allowlisted classifications only**, such as `winget_unavailable` or
`ghidra_download_or_hash`. It does not emit raw log lines, account names,
user paths, usernames, passwords, answer-file content, or proprietary memory.

In particular, file existence cannot prove a successful OOBE, Windows Update
health, installed application versions, running services, telemetry registry
policy, or successful registration of the OpenAI Chrome extension. These
require a later in-guest check after the guest is stable.

## Interpretation for our first ISO test

The November 2026 first boot reached Windows Setup and then prompted for a
region and keyboard layout; these prompts were completed manually. The current
answer file specifies locale in `windowsPE` but omits the separate
`Microsoft-Windows-International-Core` component in `oobeSystem`. That is a
**candidate explanation**, not yet independently proven from the guest's setup
logs. The audit helps establish whether the `$OEM$` payload arrived and whether
the first-logon stage ever executed. It does not repair the answer file or
change the running installation.

## Local reproducible tests

```sh
python3 -m unittest discover -s tests -v
python3 -m py_compile Audit-LabDisk.py
```

All tests use synthetic, freshly created directories. They never open a VM,
original binary, personal database, Ghidra evidence corpus or actual Windows
installation. Automated VM mounting/unmounting on macOS remains a separate integration test.

This tool belongs in the public `deskmate-formats` deployment recipe, not in
private DOSLAB evidence. Reports generated from actual installations should be
reviewed for privacy before publication even though their content is restricted.
