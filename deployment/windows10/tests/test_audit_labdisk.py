"""Portable, synthetic tests for the host-only deployment disk audit."""
import importlib.util
import io
import os
import json
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stderr
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "Audit-LabDisk.py"
spec = importlib.util.spec_from_file_location("labdisk_audit", SCRIPT)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "windows-volume"
        (self.root / "Windows/System32/config").mkdir(parents=True)
        (self.root / "Windows/System32/config/SYSTEM").write_bytes(b"synthetic")

    def put(self, path, data="synthetic"):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(data, encoding="utf-8")

    def test_clean_pre_first_logon_does_not_claim_failure(self):
        self.put("DeskMateLab/installation-mode.txt", "Lab\n")
        self.put("DeskMateLab/Provision-Lab.ps1")
        result = audit.inspect_root(self.root)
        self.assertEqual(result["lab_account_mode"], "Lab")
        self.assertEqual(result["provisioning_phase"], "no_execution_evidence")
        self.assertEqual(result["lab_payload_files"]["provision_script"], "present")
        self.assertEqual(result["application_location_hints"]["ghidra_12_1_4"], "absent")

    def test_classified_error_never_leaks_private_content(self):
        self.put("DeskMateLab/setup-logs/last-error.txt", "Secret Xsword987 confidential-party-somebody WinGet missing: private token\n")
        r = json.dumps(audit.inspect_root(self.root))
        self.assertIn("winget_unavailable", r)
        self.assertEqual(json.loads(r)["provisioning_phase"], "failure_marker_present")
        self.assertNotIn("Xsword987", r)
        self.assertNotIn("somebody", r)
        self.assertNotIn("private token", r)

    def test_completed_vs_started(self):
        self.put("DeskMateLab/setup-logs/provision-00001.log")
        r = audit.inspect_root(self.root)
        self.assertEqual(r["provisioning_phase"], "started_not_confirmed_complete")
        self.assertEqual(r["provision_transcript_count"], 1)
        self.put("DeskMateLab/provision-complete.txt")
        self.assertEqual(audit.inspect_root(self.root)["provisioning_phase"], "completion_marker_present")

    def test_reject_non_windows_root(self):
        (self.root / "Windows/System32/config/SYSTEM").unlink()
        with self.assertRaises(audit.AuditError):
            audit.inspect_root(self.root)

    def test_parse_vm_state_and_current_disk_not_dvd(self):
        vm_info = '''VMState="poweroff"
SATA-0-0="/some/Snapshots/{snap}.vdi"
SATA-ImageUUID-0-0="11111111-1111-1111-1111-111111111111"
IDE-1-0="/some/installer.iso"
IDE-ImageUUID-1-0="22222222-2222-2222-2222-222222222222"
'''
        state, disks = audit.parse_machine_info(vm_info)
        self.assertEqual(state, "poweroff")
        self.assertEqual(disks, ["11111111-1111-1111-1111-111111111111"])

    def test_parse_real_virtualbox_quoted_controller_keys(self):
        # Oracle's documented form: the attachment keys themselves are quoted.
        vm_info = '''VMState="poweroff"
storagecontrollername0="SATA Controller"
"SATA Controller-0-0"="/some/Windows 10/Snapshots/{current}.vdi"
"SATA Controller-ImageUUID-0-0"="33333333-3333-3333-3333-333333333333"
"IDE Controller-1-0"="/tmp/Win10.iso"
"IDE Controller-ImageUUID-1-0"="22222222-2222-2222-2222-222222222222"
'''
        state, disks = audit.parse_machine_info(vm_info)
        self.assertEqual(state, "poweroff")
        self.assertEqual(disks, ["33333333-3333-3333-3333-333333333333"])

    def test_refuses_unverified_explicit_uuid(self):
        vm_info = '''VMState="poweroff"
"SATA Controller-0-0"="/VM/Snapshots/current.vdi"
"SATA Controller-ImageUUID-0-0"="33333333-3333-3333-3333-333333333333"
'''
        with patch.object(audit, "call_tool", side_effect=["", vm_info]):
            with self.assertRaisesRegex(audit.AuditError, "cannot be verified"):
                audit.choose_disk_uuid("LabVM", "11111111-1111-1111-1111-111111111111", "VBoxManage")

    def test_refuses_explicit_uuid_when_no_disks_discovered(self):
        with patch.object(audit, "call_tool", side_effect=["", 'VMState="poweroff"\n']):
            with self.assertRaisesRegex(audit.AuditError, "cannot be verified"):
                audit.choose_disk_uuid("LabVM", "11111111-1111-1111-1111-111111111111", "VBoxManage")

    def test_find_guest_fs(self):
        mount = Path(self.tmp.name) / "fuse"
        fs = mount / "fs2"
        (fs / "Windows/System32/config").mkdir(parents=True)
        (fs / "Windows/System32/config/SYSTEM").write_bytes(b"synthetic")
        self.assertEqual(audit.find_guest_root(mount), fs)

    def test_reject_write_into_guest(self):
        output = io.StringIO()
        with redirect_stderr(output):
            rv = audit.main(["--root", str(self.root), "--json", str(self.root / "report.json")])
        self.assertEqual(rv, 2)
        self.assertFalse((self.root / "report.json").exists())

    def test_reject_write_inside_new_guest_subdirectory(self):
        output = io.StringIO()
        target = self.root / "new-reports" / "report.json"
        with redirect_stderr(output):
            rv = audit.main(["--root", str(self.root), "--json", str(target)])
        self.assertEqual(rv, 2)
        self.assertFalse(target.exists())
        self.assertFalse(target.parent.exists())

    def test_canonical_alias_containment(self):
        root = self.root.resolve()
        self.assertTrue(audit.is_within_guest_volume(root, root / "new" / "report.json"))
        self.assertFalse(audit.is_within_guest_volume(root, root.parent / "report.json"))
        self.assertFalse(audit.is_within_guest_volume(root, root.parent / (root.name + "-other") / "report.json"))
        if os.name == "nt":
            # On Windows, path-case differences must not permit a guest write.
            other_case = Path(str(root).swapcase()) / "new" / "report.json"
            self.assertTrue(audit.is_within_guest_volume(root, other_case))

    def test_reject_guest_symlink_alias_when_supported(self):
        alias = Path(self.tmp.name) / "guest-alias"
        try:
            alias.symlink_to(self.root, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("This host cannot create directory symlinks")
        self.assertTrue(audit.is_within_guest_volume(self.root, alias / "report.json"))

    def test_refuses_running_other_vm(self):
        with patch.object(audit, "call_tool", return_value='"AnotherVM" {11111111-1111-1111-1111-111111111111}\n'):
            with self.assertRaisesRegex(audit.AuditError, "ALL VMs"):
                audit.choose_disk_uuid("LabVM", None, "VBoxManage")

    def test_foreground_command_uses_space_separated_image_and_debug(self):
        args = audit.foreground_mount_command(
            "/some/VirtualBox/vboximg-mount",
            "33333333-3333-3333-3333-333333333333",
            Path("/tmp/test-mount"),
        )
        self.assertEqual(args[:3], [
            "/some/VirtualBox/vboximg-mount", "--image",
            "33333333-3333-3333-3333-333333333333",
        ])
        self.assertIn("--guest-filesystem", args)
        self.assertEqual(args[-3:-1], ["-o", "debug"])
        self.assertFalse(any(a.startswith("--image=") or a == "--rw" for a in args))

    def test_mac_legacy_fuse_alias_is_private_and_temporary(self):
        import os
        compat = Path(self.tmp.name) / "compat"
        try:
            with patch.object(audit.sys, "platform", "darwin"), \
                    patch.object(audit.Path, "is_file", return_value=True), \
                    patch.dict(os.environ, {"DYLD_LIBRARY_PATH": "/legacy/path"}):
                env = audit.fuse_environment(compat)
        except OSError as exc:
            if os.name == "nt" and getattr(exc, "winerror", None) == 1314:
                self.skipTest("Windows symlink privilege required for macOS FUSE simulation")
            raise
        link = compat / "libosxfuse.dylib"
        self.assertTrue(link.is_symlink())
        self.assertEqual(link.readlink().as_posix(), "/usr/local/lib/libfuse.2.dylib")
        self.assertEqual(env["DYLD_LIBRARY_PATH"].split(os.pathsep), [
            str(compat), "/usr/local/lib", "/legacy/path",
        ])
        self.assertEqual(str(link.parent), str(compat))

    def test_fuse_environment_does_not_change_host_environment(self):
        import os
        compat = Path(self.tmp.name) / "compat"
        old = dict(os.environ)
        with patch.object(audit.sys, "platform", "linux"):
            env = audit.fuse_environment(compat)
        self.assertEqual(old, dict(os.environ))
        self.assertFalse(compat.exists())
        self.assertEqual(env.get("DYLD_LIBRARY_PATH"), old.get("DYLD_LIBRARY_PATH"))

    def test_reads_only_expected_paths(self):
        self.put("Users/Unrelated/DeskMate-PRIVATE.txt", "CANARY-no-copy")
        r = json.dumps(audit.inspect_root(self.root))
        self.assertNotIn("CANARY-no-copy", r)


if __name__ == "__main__":
    unittest.main()
