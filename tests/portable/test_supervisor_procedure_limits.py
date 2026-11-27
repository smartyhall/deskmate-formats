"""Reviewed procedure limits, execution classification and offline build flags."""

from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from deskmate_formats.supervisor import deterministic, procedures


class ProcedureContractTests(unittest.TestCase):
    def test_every_procedure_states_whether_it_executes_repository_code(self):
        for name in procedures.names():
            descriptor = procedures.descriptor(name)
            self.assertIn(descriptor["executes"],
                          (procedures.FIXED_SCRIPT, procedures.REPOSITORY_CODE,
                           procedures.THIRD_PARTY_TOOL), name)
            self.assertIsInstance(descriptor["inputs"], list, name)
            self.assertIn(descriptor["network"], ("none", "no-isolation"), name)

    def test_running_tests_and_building_packages_are_repository_execution(self):
        for name in ("portable-tests", "package-build"):
            self.assertEqual(procedures.descriptor(name)["executes"],
                             procedures.REPOSITORY_CODE)
        for name in ("hash-files", "fixture-compare"):
            self.assertEqual(procedures.descriptor(name)["executes"],
                             procedures.FIXED_SCRIPT)

    def test_package_build_refuses_isolation_and_offline_variables_are_set(self):
        argv = procedures.build("package-build", {}, artifacts="/tmp/out",
                                working_directory="/tmp")
        self.assertIn("--no-isolation", argv)
        self.assertEqual(procedures.descriptor("package-build")["network"], "no-isolation")
        env = deterministic.environment("/tmp/out", "/tmp")
        self.assertEqual(env["PIP_NO_INDEX"], "1")
        self.assertEqual(env["UV_OFFLINE"], "1")
        self.assertNotIn("HTTPS_PROXY", env)

    def test_hash_and_compare_scripts_receive_their_reviewed_limits(self):
        hash_argv = procedures.build("hash-files", {"paths": ["a.txt"]},
                                      artifacts="/tmp/out", working_directory="/tmp")
        compare_argv = procedures.build("fixture-compare", {"expected": "a", "actual": "b"},
                                        artifacts="/tmp/out", working_directory="/tmp")
        for argv in (hash_argv, compare_argv):
            self.assertIn(str(procedures.MAX_FILE_BYTES), argv)
            self.assertIn(str(procedures.MAX_TOTAL_BYTES), argv)
            # The scripts are bounded, not read-everything helpers.
            self.assertNotIn("read_bytes()", " ".join(argv))

    def test_hostile_paths_are_refused_by_validation(self):
        for value in ("../escape", "/absolute", "a:b", "con.txt", "trailing. ", "a//b", "lpt1"):
            with self.assertRaises(procedures.ProcedureError, msg=value):
                procedures.validate("hash-files", {"paths": [value]})

    def test_unknown_argument_keys_are_refused(self):
        with self.assertRaises(procedures.ProcedureError):
            procedures.validate("hash-files", {"paths": ["a"], "executable": "/bin/sh"})


class ProcedureLimitTests(unittest.TestCase):
    """The declared cap is the cap the procedure actually applies."""

    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))

    def run_procedure(self, state, procedure, arguments, timeout=60):
        attempt = deterministic.prepare(
            state, campaign="synthetic-campaign", procedure=procedure,
            arguments=arguments, working_directory=str(self.root), timeout_seconds=timeout)
        return deterministic.run(state, authorization=attempt.plan_sha256)

    def test_binding_refuses_an_input_over_the_declared_limit(self):
        (self.root / "large.bin").write_bytes(b"x" * 32)
        with patch.object(procedures, "MAX_FILE_BYTES", 16):
            with self.assertRaisesRegex(deterministic.DeterministicError, "size limit"):
                deterministic.prepare(
                    self.root / "attempt", campaign="synthetic-campaign",
                    procedure="hash-files", arguments={"paths": ["large.bin"]},
                    working_directory=str(self.root))

    def test_hash_script_enforces_its_own_limit_when_it_runs(self):
        (self.root / "large.bin").write_bytes(b"x" * 32)
        with patch.object(procedures, "MAX_FILE_BYTES", 16):
            argv = procedures.build("hash-files", {"paths": ["large.bin"]},
                                    artifacts=self.root / "artifacts",
                                    working_directory=str(self.root))
        result = subprocess.run(argv, cwd=self.root, capture_output=True, timeout=120)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b"size limit", result.stderr)

    def test_compare_procedure_reports_identical_and_different_inputs(self):
        (self.root / "a.bin").write_bytes(b"same")
        (self.root / "b.bin").write_bytes(b"same")
        (self.root / "c.bin").write_bytes(b"other")
        same = self.run_procedure(self.root / "first", "fixture-compare",
                                  {"expected": "a.bin", "actual": "b.bin"})
        self.assertEqual(same["state"], "completed")
        self.assertEqual(same["structured_result"]["same"], True)
        different = self.run_procedure(self.root / "second", "fixture-compare",
                                       {"expected": "a.bin", "actual": "c.bin"})
        self.assertEqual(different["state"], "completed")
        self.assertEqual(different["structured_result"]["same"], False)
        self.assertEqual(different["structured_result"]["expected"]["size"], 4)
