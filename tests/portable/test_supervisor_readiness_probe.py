"""Offline probe guards; synthetic subprocesses only, never native Codex."""

from copy import deepcopy
from pathlib import Path
import runpy
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch


PROBE = runpy.run_path(str(Path(__file__).resolve().parents[2] / "tools/experimental/supervisor_readiness_probe.py"))


class ProbeTests(unittest.TestCase):
    def test_schema_drift_fails_instead_of_reporting_success(self):
        expected = {"profile_sha256": PROBE["PROFILE_SHA256"], "sha256_by_path": {"one.json": "a"}}
        PROBE["check_schemas"]([expected, deepcopy(expected)], expected)
        different = expected | {"sha256_by_path": {"one.json": "b"}}
        for inventories, committed in (([expected, different], expected), ([different, different], expected),
                                        ([expected, expected], expected | {"profile_sha256": "wrong"})):
            with self.subTest(inventories=inventories), self.assertRaises(ValueError):
                PROBE["check_schemas"](inventories, committed)

    def test_policy_inspection_error_is_not_absence(self):
        with patch.object(Path, "stat", side_effect=PermissionError("synthetic denied")):
            with self.assertRaises(PermissionError):
                PROBE["policy_presence"](Path.cwd())
        with patch.object(Path, "stat", side_effect=FileNotFoundError):
            self.assertFalse(PROBE["policy_presence"](Path.cwd()))

    def test_registry_path_is_absolute_typed_and_not_environment_expanded(self):
        for value, kind in (("relative.toml", 1), ("%SYNTHETIC%/requirements.toml", 2), (123, 4),
                            (str(Path.cwd()), 7), (str(Path.cwd()) + "\0", 1)):
            with self.subTest(value=value), self.assertRaises(ValueError):
                PROBE["requirements_path"](value, kind)
        self.assertEqual(PROBE["requirements_path"](str(Path.cwd()), 1), Path.cwd())

    @unittest.skipUnless(sys.platform == "win32", "Windows native private-storage APIs")
    def test_timeout_preserves_partial_streams_and_only_sanitized_native_calls(self):
        with TemporaryDirectory() as directory:
            root = Path(directory) / "probe"
            namespace = PROBE["probe"].__globals__
            replies = [subprocess.CompletedProcess([], 0, b"synthetic-revision", b""),
                       subprocess.CompletedProcess([], 0, b"", b""),
                       subprocess.CompletedProcess([], 0, f'codex-cli {PROBE["VERSION"]}\n'.encode(), b""),
                       subprocess.TimeoutExpired("synthetic-schema", 60, output=b"partial-output", stderr=b"partial-error")]
            with patch.dict(namespace, digest=lambda _: PROBE["NATIVE_SHA256"]), \
                    patch("subprocess.run", side_effect=replies) as launch, \
                    patch.dict("os.environ", {"OPENAI_API_KEY": "synthetic-secret", "GIT_DIR": "synthetic-override"}):
                with self.assertRaisesRegex(RuntimeError, "preserve archive"):
                    PROBE["probe"](root, Path(sys.executable), Path.cwd())
            self.assertEqual((root / "04-stdout.txt").read_bytes(), b"partial-output")
            self.assertEqual((root / "04-stderr.txt").read_bytes(), b"partial-error")
            self.assertIn(b'TimeoutExpired', (root / "command-04.json").read_bytes())
            self.assertFalse((root / "probe.json").exists())
            for call in launch.call_args_list:
                self.assertNotIn("OPENAI_API_KEY", call.kwargs["env"])
                self.assertNotIn("GIT_DIR", call.kwargs["env"])
            self.assertEqual(launch.call_args_list[-1].args[0][1:3], ["app-server", "generate-json-schema"])
