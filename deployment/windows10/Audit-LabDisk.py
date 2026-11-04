#!/usr/bin/env python3
"""Read-only deployment audit for a powered-off VirtualBox Windows guest.

No disk writes, no guest execution, no copies of Setup logs or registry hives.
No third-party Python dependencies. Read-only FUSE mounting is opt-in via --vm.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

SCHEMA_VERSION = 1
WINDOWS_SIGNATURE = ("Windows", "System32", "config", "SYSTEM")
WINDOWS_FILES = {
    "windows_setup_log": ("Windows", "Panther", "setupact.log"),
    "windows_setup_error_log": ("Windows", "Panther", "setuperr.log"),
    "oobe_setup_log": ("Windows", "Panther", "UnattendGC", "setupact.log"),
    "oobe_error_log": ("Windows", "Panther", "UnattendGC", "setuperr.log"),
    "oem_setup_hook": ("Windows", "Setup", "Scripts", "SetupComplete.cmd"),
}
LAB_FILES = {
    "payload_mode_marker": ("DeskMateLab", "installation-mode.txt"),
    "provision_script": ("DeskMateLab", "Provision-Lab.ps1"),
    "privacy_script": ("DeskMateLab", "Privacy-Lab.ps1"),
    "verification_script": ("DeskMateLab", "Verify-Lab.ps1"),
    "ssh_script": ("DeskMateLab", "Enable-LabSSH.ps1"),
    "emulator_build_script": ("DeskMateLab", "Setup-86Box-UCRT64.sh"),
    "completion_marker": ("DeskMateLab", "provision-complete.txt"),
    "provision_error_marker": ("DeskMateLab", "setup-logs", "last-error.txt"),
    "winget_missing_marker": ("DeskMateLab", "setup-logs", "winget-missing.txt"),
}
APP_FILES = {
    "chrome": ("Program Files", "Google", "Chrome", "Application", "chrome.exe"),
    "git": ("Program Files", "Git", "cmd", "git.exe"),
    "nodejs": ("Program Files", "nodejs", "npm.cmd"),
    "msys2": ("msys64", "ucrt64.exe"),
    "ghidra_12_1_4": ("Tools", "ghidra_12.1.4_PUBLIC", "support", "analyzeHeadless.bat"),
}
ERROR_CLASSES = {
    "winget_unavailable": re.compile(r"winget\s+(?:missing|is not installed|not found)", re.I),
    "ghidra_download_or_hash": re.compile(r"ghidra|SHA-256 verification failed", re.I),
    "chrome_install": re.compile(r"Chrome MSI|Chrome.*signature", re.I),
    "codex_or_node": re.compile(r"npm|Codex CLI|Node\.js", re.I),
    "git_checkout": re.compile(r"git clone|deskmate-formats clone|Git was not installed", re.I),
}


class AuditError(Exception):
    """User-actionable audit preflight or mount error."""


def status_for(path: Path) -> str:
    try:
        return "present" if path.is_file() else "absent"
    except OSError:
        return "inaccessible"


def list_provision_transcripts(root: Path) -> int | None:
    d = root / "DeskMateLab" / "setup-logs"
    try:
        if not d.is_dir():
            return 0
        # Don't open files or include guest filenames in the report.
        return sum(p.is_file() for p in d.glob("provision-*.log"))
    except OSError:
        return None


def classified_error(path: Path) -> list[str]:
    """Read a bounded tail; return ONLY allowlisted categories, never source text."""
    try:
        with path.open("rb") as fh:
            fh.seek(0, os.SEEK_END)
            fh.seek(max(0, fh.tell() - 128 * 1024))
            tail = fh.read().decode("utf-8", "replace")
    except (OSError, UnicodeError):
        return ["unreadable_error_marker"]
    found = [name for name, pattern in ERROR_CLASSES.items() if pattern.search(tail)]
    return found or ["unclassified_error_marker_review_privately"]


def inspect_root(root: Path) -> dict:
    """Analyze only allowlisted, expected locations; no recursive guest scan."""
    if not root.is_dir():
        raise AuditError("Guest root is not an accessible directory.")
    signature = root.joinpath(*WINDOWS_SIGNATURE)
    if status_for(signature) != "present":
        raise AuditError("Selected filesystem does not contain a Windows SYSTEM hive; choose the Windows volume.")

    win = {name: status_for(root.joinpath(*parts)) for name, parts in WINDOWS_FILES.items()}
    lab = {name: status_for(root.joinpath(*parts)) for name, parts in LAB_FILES.items()}
    apps = {name: status_for(root.joinpath(*parts)) for name, parts in APP_FILES.items()}
    transcript_count = list_provision_transcripts(root)

    mode = "unknown"
    if lab["payload_mode_marker"] == "present":
        try:
            # This marker is a fixed, non-secret value from the deployment kit.
            value = root.joinpath(*LAB_FILES["payload_mode_marker"]).read_text(
                encoding="ascii", errors="replace"
            ).strip()
            if value in ("Lab", "VirtualBox"):
                mode = value
        except OSError:
            pass

    error_categories: list[str] = []
    if lab["provision_error_marker"] == "present":
        error_categories = classified_error(root.joinpath(*LAB_FILES["provision_error_marker"]))

    if lab["completion_marker"] == "present":
        provisioning = "completion_marker_present"
        next_check = "Run the in-guest Verify-Lab.ps1 to confirm installed applications and settings."
    elif lab["provision_error_marker"] == "present" or lab["winget_missing_marker"] == "present":
        provisioning = "failure_marker_present"
        next_check = "Investigate provisioning failure in the guest; do not publish unredacted setup logs."
    elif transcript_count:
        provisioning = "started_not_confirmed_complete"
        next_check = "Wait for provisioning to finish or inspect its running processes inside the guest."
    else:
        provisioning = "no_execution_evidence"
        next_check = "Confirm OOBE and first administrator logon occurred; provisioning may not have begun."

    if lab["provision_script"] != "present":
        next_check = "OEM payload was not observed; check ISO contents and the guest's Windows Setup logs."

    return {
        "schema_version": SCHEMA_VERSION,
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "windows_system_hive": "present",
        "windows_setup_files": win,
        "lab_payload_files": lab,
        "lab_account_mode": mode,
        "provisioning_phase": provisioning,
        "provision_transcript_count": transcript_count,
        "provision_error_categories": error_categories,
        "next_check": next_check,
        "application_location_hints": apps,
        "limitations": [
            "File existence does not prove that OOBE completed, that a service runs, or that an application works.",
            "Application paths are hints; alternate per-user installs are not exhaustively checked.",
            "The Chrome extension, telemetry policies, registry, installed packages and user credentials are not inspected.",
            "The first-logon script may not have started if OOBE has not reached an administrative logon.",
            "Setup and provisioning logs may contain secrets; this report does not copy or quote them.",
        ],
    }


def parse_machine_info(output: str) -> tuple[str | None, list[str]]:
    """Parse active image UUIDs, including VirtualBox's quoted storage keys.

    Typical showvminfo lines have quoted *keys* for storage attachments:
      "SATA Controller-0-0"=".../Snapshots/{id}.vdi"
      "SATA Controller-ImageUUID-0-0"="active-snapshot-uuid"
    Controller names are user-configurable and need not be SATA/IDE/etc.
    Only UUIDs paired with a virtual *hard disk* path count; ISO UUIDs do not.
    """
    kv: dict[str, str] = {}
    for line in output.splitlines():
        m = re.fullmatch(
            r'\s*(?:"(?P<quoted_key>[^"]+)"|(?P<key>[^="\s]+))="(?P<value>.*)"\s*',
            line,
        )
        if m:
            kv[m.group("quoted_key") or m.group("key")] = m.group("value")
    state = kv.get("VMState")
    media: list[str] = []
    seen: set[str] = set()
    for key, value in kv.items():
        match = re.fullmatch(r"(.+)-ImageUUID-(\d+)-(\d+)", key)
        if not match or not re.fullmatch(r"[0-9a-fA-F-]{36}", value):
            continue
        attachment = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
        medium_path = kv.get(attachment, "")
        # The companion path identifies the currently attached disk, which
        # may itself be a snapshot/differencing image. Ignore installation ISOs.
        if not re.search(r"\.(?:vdi|vmdk|vhdx?|hdd|qcow2?)(?:$|\s+\()", medium_path, re.I):
            continue
        if value.lower() not in seen:
            seen.add(value.lower())
            media.append(value)
    return state, media


def call_tool(args: list[str], timeout: int = 45) -> str:
    try:
        p = subprocess.run(args, check=False, text=True, capture_output=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AuditError(f"VirtualBox command unavailable or timed out: {Path(args[0]).name}") from exc
    if p.returncode != 0:
        # Never embed raw output: VirtualBox may include private local paths.
        raise AuditError(f"VirtualBox command failed: {Path(args[0]).name} (exit {p.returncode}).")
    return p.stdout


def find_utility(name: str) -> str:
    installed = shutil.which(name)
    if installed:
        return installed
    mac_app = Path("/Applications/VirtualBox.app/Contents/MacOS") / name
    if mac_app.is_file():
        return str(mac_app)
    raise AuditError(f"Cannot find {name}; install VirtualBox tools or specify a mounted guest root.")


def choose_disk_uuid(vm: str, explicit: str | None, manage: str) -> str:
    running = call_tool([manage, "list", "runningvms"])
    if running.strip():
        raise AuditError("At least one VirtualBox VM is running. Shut down ALL VMs cleanly before mounting.")
    state, disks = parse_machine_info(call_tool([manage, "showvminfo", vm, "--machinereadable"]))
    if state != "poweroff":
        raise AuditError(f"Target VM must be fully powered off, not saved/suspended (state: {state or 'unknown'}).")
    if explicit:
        if not re.fullmatch(r"[0-9a-fA-F-]{36}", explicit):
            raise AuditError("--disk-uuid must be a 36-character UUID.")
        if explicit.lower() not in {x.lower() for x in disks}:
            raise AuditError(
                "--disk-uuid cannot be verified as an attached hard disk; "
                "refusing a potentially stale base/snapshot image."
            )
        return explicit
    if len(disks) != 1:
        raise AuditError(
            f"Expected one confirmed attached hard-disk image UUID; found {len(disks)}. "
            "Check 'VBoxManage showvminfo <VM> --machinereadable' for storage entries. "
            "For multiple disks, specify the current attached disk UUID with --disk-uuid."
        )
    return disks[0]


def find_guest_root(mount: Path) -> Path:
    """Find one NTFS Windows volume exposed by VirtualBox's guest-FS support."""
    roots = [mount]
    try:
        roots.extend(p for p in mount.iterdir() if p.is_dir() and re.fullmatch(r"fs\d+", p.name, re.I))
    except OSError:
        pass
    matches = [p for p in roots if status_for(p.joinpath(*WINDOWS_SIGNATURE)) == "present"]
    if len(matches) != 1:
        raise AuditError(
            "Expected one readable Windows guest filesystem, found " + str(len(matches)) + ". "
            "Check vboximg-mount --guest-filesystem support, FUSE permissions, and NTFS availability."
        )
    return matches[0]


def foreground_mount_command(image_tool: str, disk_uuid: str, point: Path) -> list[str]:
    """Use the FUSE debug option to keep the mount in the foreground.

    macFUSE's foreground/debug mode avoids the unsafe fork of an already
    multithreaded Cocoa/Objective-C process observed on macOS Sequoia.
    VirtualBox 7.2 expects `--image UUID` with a *space*, not `--image=UUID`.
    """
    return [image_tool, "--image", disk_uuid, "--guest-filesystem", "-o", "debug", str(point)]


def fuse_environment(compat: Path) -> dict[str, str]:
    """Prepare a process-local compatibility alias; never modify host libraries.

    VirtualBox 7.2 on macOS requests legacy `libosxfuse.dylib`, while macFUSE
    5.5 supplies `libfuse.2.dylib`. This temporary symlink is removed after
    the audit, and no SIP, kernel-extension or global linker setting changes.
    """
    env = os.environ.copy()
    if sys.platform == "darwin":
        sources = [Path("/usr/local/lib/libfuse.2.dylib"), Path("/usr/local/lib/libfuse.dylib")]
        source = next((candidate for candidate in sources if candidate.is_file()), None)
        if source is None:
            raise AuditError(
                "macFUSE 2-compatible library not found under /usr/local/lib. "
                "Install/approve macFUSE or use --root on a separately mounted volume."
            )
        compat.mkdir()
        (compat / "libosxfuse.dylib").symlink_to(source)
        previous = env.get("DYLD_LIBRARY_PATH", "")
        env["DYLD_LIBRARY_PATH"] = os.pathsep.join(
            part for part in [str(compat), "/usr/local/lib", previous] if part
        )
    return env


def inspect_vm(vm: str, disk_uuid: str | None = None) -> dict:
    manage = find_utility("VBoxManage")
    image_tool = find_utility("vboximg-mount")
    selected = choose_disk_uuid(vm, disk_uuid, manage)
    base = Path(tempfile.mkdtemp(prefix="deskmate-vboximg-"))
    point = base / "mount"
    compat = base / "fuse-compat"
    log_path = base / "fuse-output.log"
    process: subprocess.Popen | None = None
    mounted = False
    safely_unmounted = True
    try:
        point.mkdir()
        env = fuse_environment(compat)
        # Never use --rw. Preserve all subprocess output only in a temporary
        # host-side file, not in the report (it may reveal host paths).
        with log_path.open("wb") as log:
            try:
                process = subprocess.Popen(
                    foreground_mount_command(image_tool, selected, point),
                    stdout=log, stderr=subprocess.STDOUT, env=env,
                )
            except OSError as exc:
                raise AuditError("Cannot start the VirtualBox FUSE mounter.") from exc

            deadline = time.monotonic() + 45
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise AuditError(
                        "Foreground vboximg-mount exited before the Windows filesystem became available "
                        f"(exit {process.returncode}); run the manual -o debug mount to inspect details."
                    )
                # We never traverse the guest recursively; at most a handful
                # of exact filesystem-signature paths are inspected.
                try:
                    root = find_guest_root(point)
                except AuditError:
                    time.sleep(0.5)
                else:
                    mounted = True
                    return inspect_root(root)
            raise AuditError(
                "The foreground mount did not expose a readable Windows filesystem within 45 seconds. "
                "Run the manual -o debug mount to inspect its diagnostics."
            )
    finally:
        # Attempt orderly unmount while the FUSE foreground process is alive.
        # Never force-unmount or recursively remove an active filesystem.
        if process is not None:
            is_mounted = False
            try:
                is_mounted = os.path.ismount(point)
            except OSError:
                pass
            if is_mounted or mounted or process.poll() is None:
                unmount = shutil.which("umount")
                if unmount:
                    try:
                        result = subprocess.run(
                            [unmount, str(point)], capture_output=True, timeout=20, check=False
                        )
                        safely_unmounted = result.returncode == 0 or not os.path.ismount(point)
                    except (OSError, subprocess.TimeoutExpired):
                        safely_unmounted = not os.path.ismount(point)
                else:
                    safely_unmounted = not os.path.ismount(point)
            if safely_unmounted:
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)
            else:
                print(
                    "WARNING: guest FUSE filesystem may still be mounted read-only. "
                    "Run: umount " + str(point), file=sys.stderr,
                )
        if safely_unmounted:
            # Remove only the exact host-side files and directories we created.
            for path in (log_path, compat / "libosxfuse.dylib"):
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass
            for path in (point, compat, base):
                try:
                    path.rmdir()
                except OSError:
                    pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Inspect a powered-off Windows lab VM (or a previously mounted NTFS root), without writes."
    )
    origin = parser.add_mutually_exclusive_group(required=True)
    origin.add_argument("--vm", help="Registered VirtualBox VM name/UUID; ALL VMs must be powered off.")
    origin.add_argument("--root", type=Path, help="Existing read-only mount of the Windows C: volume.")
    parser.add_argument("--disk-uuid", help="Explicit attached image UUID for multi-disk VMs (not a base VDI).")
    parser.add_argument("--json", type=Path, help="Save sanitized JSON report on host, never in guest volume.")
    args = parser.parse_args(argv)
    if args.root and args.disk_uuid:
        parser.error("--disk-uuid applies only to --vm.")
    try:
        if args.json and args.json.expanduser().absolute().exists():
            raise AuditError("Refusing to overwrite existing report JSON.")
        if args.root:
            root = args.root.expanduser().resolve()
            if args.json:
                dest = args.json.expanduser().absolute()
                if os.path.commonpath((str(root), str(dest))) == str(root):
                    raise AuditError("Report output must not be written into the mounted Windows volume.")
            report = inspect_root(root)
        else:
            report = inspect_vm(args.vm, args.disk_uuid)
        serialized = json.dumps(report, indent=2, sort_keys=False, ensure_ascii=True) + "\n"
        print(serialized, end="")
        if args.json:
            output = args.json.expanduser().absolute()
            if output.exists():
                raise AuditError("Refusing to overwrite existing report JSON.")
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("x", encoding="utf-8") as fh:
                fh.write(serialized)
        return 0
    except AuditError as exc:
        print("AUDIT UNAVAILABLE: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
