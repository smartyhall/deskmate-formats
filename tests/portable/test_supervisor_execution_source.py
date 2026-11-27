"""Source-bound execution: the accepted checkout runs, nothing else.

Every test here uses the production command-construction path.  The conflicting
installation is real, in a disposable virtual environment: this file never
modifies the laboratory's shared interpreter.
"""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import py_compile
import subprocess
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from deskmate_formats.campaign_env import receipts
from deskmate_formats.observer._private_storage import storage_directory
from deskmate_formats.supervisor import deterministic, execution_source, procedures, workspace
from execution_fixture import (git, install_conflict, make_checkout, make_environment,
                               write_package)

PYTHON = str(Path(sys.executable).resolve())


class InventoryTests(unittest.TestCase):
    def test_every_production_procedure_declares_its_execution_source(self):
        for name in procedures.names():
            with self.subTest(procedure=name):
                entry = procedures.descriptor(name)
                self.assertIn(entry["execution_source"], execution_source.SOURCES)
        self.assertEqual(procedures.descriptor("repository-audit")["execution_source"],
                         execution_source.WORKSPACE)
        self.assertEqual(procedures.descriptor("hash-files")["execution_source"],
                         execution_source.CONTROLLER)
        self.assertEqual(procedures.descriptor("reuse-lint")["execution_source"],
                         execution_source.EXTERNAL)

    def test_inventory_classifies_launches_and_names_the_corrected_site(self):
        inventory = execution_source.inventory()
        self.assertEqual(inventory["schema_version"], 1)
        self.assertEqual(inventory["bootstrap_sha256"], execution_source.bootstrap_digest())
        sites = {entry["identifier"]: entry for entry in inventory["sites"]}
        self.assertTrue(set(sites) >= {
            "procedures.hash-files", "procedures.repository-audit",
            "workspace.test-step", "workspace.publication-audit",
            "driver.synthetic-peer", "driver.codex-app-server",
        })
        for identifier, entry in sites.items():
            with self.subTest(site=identifier):
                self.assertIn(entry["intended"], execution_source.SOURCES)
                for key in ("caller", "construction", "resolution", "receipt", "failure"):
                    self.assertTrue(entry[key], key)
        # The audited defect is recorded where a reviewer will look for it.
        self.assertIn("shared wheel", sites["workspace.publication-audit"]["correction"])
        self.assertIn("-I ignored the path",
                      sites["procedures.repository-audit"]["correction"])
        # An unbound class-D launch is admitted rather than hidden.
        self.assertIn(execution_source.UNRESOLVED,
                      {entry["intended"] for entry in inventory["sites"]})
        self.assertTrue(inventory["non_production"])


class SourceBindingTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))
        self.state = self.root / "attempt"
        self.checkout, self.revision = make_checkout(self.root / "alpha", marker="alpha")
        self.selection, target, _ = make_environment(
            root=self.root / "envs", checkout=self.checkout,
            campaign="alpha-campaign", revision=self.revision)
        self.target = target
        self.conflict = install_conflict(target["interpreter"], marker="shared-preinstalled")

    def prepare(self, *, procedure="repository-audit", arguments=None, timeout=30,
                environment=None, state=None, **extra):
        return deterministic.prepare(
            state or self.state, campaign="alpha-campaign", procedure=procedure,
            arguments={} if arguments is None else arguments,
            working_directory=str(self.checkout), timeout_seconds=timeout,
            environment=self.selection if environment is None else environment, **extra)

    def run_attempt(self, attempt, **extra):
        return deterministic.run(attempt.directory if hasattr(attempt, "directory") else self.state,
                                 authorization=attempt.plan_sha256, **extra)

    def audit_marker(self, outcome):
        self.assertEqual(outcome["state"], "completed", outcome["stderr"]["excerpt"])
        return outcome["stdout"]["excerpt"].strip()

    def test_two_workspaces_run_their_own_publication_audit(self):
        second_root = self.root / "beta"
        second_checkout, second_revision = make_checkout(second_root, marker="beta")
        second_selection, second_target, _ = make_environment(
            root=self.root / "envs", checkout=second_checkout,
            campaign="beta-campaign", revision=second_revision)
        install_conflict(second_target["interpreter"], marker="shared-preinstalled")

        first = self.audit_marker(self.run_attempt(self.prepare()))
        state = self.root / "second-attempt"
        second_attempt = deterministic.prepare(
            state, campaign="beta-campaign", procedure="repository-audit", arguments={},
            working_directory=str(second_checkout), environment=second_selection)
        second = self.audit_marker(self.run_attempt(second_attempt))

        self.assertEqual(first, "audit:alpha")
        self.assertEqual(second, "audit:beta")
        outcome = self.run_attempt  # readability only; receipts are read below
        self.assertTrue(callable(outcome))
        recorded = json.loads((self.state / "outcome.json").read_text(encoding="utf-8"))
        self.assertEqual(recorded["execution"]["binding"]["source"], execution_source.WORKSPACE)
        self.assertEqual(recorded["execution"]["binding"]["workspace"]["revision"], self.revision)
        self.assertTrue(recorded["execution"]["child"]["checks"]["python_digest_matches"])

    def test_the_legacy_vector_reproduces_the_publication_audit_defect(self):
        """The pre-correction launch imports the installed wheel, not the checkout."""
        legacy_environment = dict(os.environ)
        legacy_environment["PYTHONPATH"] = str(self.checkout / "src")
        legacy = subprocess.run(
            [self.target["interpreter"], "-I", "-c", workspace.AUDIT],
            cwd=str(self.checkout), env=legacy_environment, capture_output=True,
            text=True, timeout=120)
        self.assertEqual(legacy.returncode, 0, legacy.stderr)
        self.assertEqual(legacy.stdout.strip(), "audit:shared-preinstalled")
        self.assertIn("shared-preinstalled", (Path(self.conflict) / "__init__.py").read_text())

        # The same contention through the production path reports the checkout.
        outcome = self.run_attempt(self.prepare())
        self.assertEqual(self.audit_marker(outcome), "audit:alpha")

    def test_a_conflicting_pythonpath_does_not_bypass_the_binding(self):
        attempt = self.prepare()
        plan = json.loads((self.state / "plan.json").read_text(encoding="utf-8"))
        argv = execution_source.bound_argv(plan["execution"], mode="code", target=workspace.AUDIT)
        hostile = dict(os.environ)
        hostile["PYTHONPATH"] = str(self.conflict.parent)
        report = self.state / "manual-report.json"
        argv[6] = str(report)
        completed = subprocess.run(argv, cwd=str(self.checkout), env=hostile,
                                   capture_output=True, text=True, timeout=120)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout.strip(), "audit:alpha")
        child = json.loads(report.read_text(encoding="utf-8"))
        self.assertTrue(child["isolated"])
        self.assertTrue(child["pythonpath_present"])
        self.assertEqual(child["interpreter"], self.target["interpreter"])
        self.assertTrue(child["origin_inside_root"])

    def test_a_stale_environment_is_refused_before_any_launch(self):
        make_environment(root=self.root / "stale", checkout=self.checkout,
                         campaign="alpha-campaign", revision="f" * 40)
        with self.assertRaisesRegex(deterministic.DeterministicError,
                                    "environment-source-mismatch"):
            deterministic.prepare(
                self.state, campaign="alpha-campaign", procedure="repository-audit",
                arguments={}, working_directory=str(self.checkout),
                environment={"campaign": "alpha-campaign", "checkout": str(self.checkout),
                             "root": str(self.root / "stale")})
        self.assertFalse(self.state.exists())

    def test_missing_or_unreadable_identity_evidence_fails_closed(self):
        missing = self.root / "missing"
        with self.assertRaisesRegex(deterministic.DeterministicError,
                                    "environment-record-missing"):
            deterministic.prepare(
                missing, campaign="alpha-campaign", procedure="repository-audit",
                arguments={}, working_directory=str(self.checkout),
                environment={"campaign": "alpha-campaign", "checkout": str(self.checkout),
                             "root": str(self.root / "absent")})
        record = json.loads(Path(self.target["record"]).read_text(encoding="utf-8"))
        record["environment_identity"]["executable_sha256"] = "0" * 64
        receipts.write(self.target["record"], record)
        with self.assertRaisesRegex(deterministic.DeterministicError,
                                    "environment-interpreter-mismatch"):
            self.prepare(state=self.root / "tampered")

    def test_source_change_after_preparation_invalidates_the_plan(self):
        attempt = self.prepare()
        target = self.checkout / "src" / "deskmate_formats" / "extra.py"
        target.write_text("MARKER = 'changed'\n", encoding="utf-8")
        with patch.object(deterministic, "_execute",
                          side_effect=AssertionError("must not execute")):
            with self.assertRaises(deterministic.DeterministicError):
                self.run_attempt(attempt)
        self.assertFalse(self.state.joinpath("attempt.json").exists())

    def test_failed_environment_verification_does_not_dispatch(self):
        attempt = self.prepare()
        record = json.loads(Path(self.target["record"]).read_text(encoding="utf-8"))
        record["verdict"] = "unqualified"
        receipts.write(self.target["record"], record)
        with patch.object(deterministic, "_execute",
                          side_effect=AssertionError("must not execute")):
            with self.assertRaisesRegex(deterministic.DeterministicError,
                                        "environment-not-qualified"):
                self.run_attempt(attempt)
        self.assertFalse((self.state / "attempt.json").exists())

    def test_child_failure_and_timeout_are_honest_outcomes(self):
        failing, revision = make_checkout(
            self.root / "failing", marker="failing",
            tests={"tests/portable/test_failure.py":
                   "import unittest\n\n\nclass Failing(unittest.TestCase):\n"
                   "    def test_always_fails(self):\n        self.fail('synthetic')\n"})
        selection, _, _ = make_environment(root=self.root / "failing-envs", checkout=failing,
                                           campaign="failing-campaign", revision=revision)
        attempt = deterministic.prepare(
            self.root / "failing-attempt", campaign="failing-campaign",
            procedure="portable-tests", arguments={"scope": "all"},
            working_directory=str(failing), timeout_seconds=60, environment=selection)
        outcome = self.run_attempt(attempt)
        self.assertEqual(outcome["state"], "failed")
        self.assertNotEqual(outcome["exit_status"], 0)
        self.assertTrue(outcome["execution"]["verified"])

        slow, slow_revision = make_checkout(
            self.root / "slow", marker="slow",
            tests={"tests/portable/test_slow.py":
                   "import time, unittest\n\n\nclass Slow(unittest.TestCase):\n"
                   "    def test_sleeps(self):\n        time.sleep(30)\n"})
        slow_selection, _, _ = make_environment(root=self.root / "slow-envs", checkout=slow,
                                                campaign="slow-campaign", revision=slow_revision)
        slow_attempt = deterministic.prepare(
            self.root / "slow-attempt", campaign="slow-campaign", procedure="portable-tests",
            arguments={"scope": "all"}, working_directory=str(slow), timeout_seconds=1,
            environment=slow_selection)
        timed = self.run_attempt(slow_attempt)
        self.assertEqual(timed["state"], "timed-out")
        self.assertEqual(timed["exit_status"], "timeout")

    def test_controller_launch_is_not_attributed_to_the_workspace(self):
        attempt = self.prepare(
            procedure="hash-files",
            arguments={"paths": ["src/deskmate_formats/supervisor/repository_audit.py"]})
        outcome = self.run_attempt(attempt)
        self.assertEqual(outcome["state"], "completed", outcome["stderr"]["excerpt"])
        binding = outcome["execution"]["binding"]
        self.assertEqual(binding["source"], execution_source.CONTROLLER)
        self.assertNotIn("workspace", binding)
        self.assertEqual(outcome["working_directory"], str(self.checkout.resolve()))
        self.assertEqual(outcome["execution"]["verified"], True)

    def test_an_unverified_child_is_not_a_completed_measurement(self):
        attempt = self.prepare()
        with patch.object(execution_source, "read_child_report",
                          return_value={"verified": False, "state": "report-missing"}):
            outcome = self.run_attempt(attempt)
        self.assertEqual(outcome["state"], "failed")
        self.assertEqual(outcome["reason"], "bound-source-not-verified")
        self.assertTrue(any("not a measurement" in item for item in outcome["limitations"]))

    def test_public_projection_removes_private_paths(self):
        attempt = self.prepare()
        plan = json.loads((self.state / "plan.json").read_text(encoding="utf-8"))
        published = json.dumps(execution_source.public_execution(plan["execution"]))
        for private in (str(self.checkout), str(self.root), str(self.target["interpreter"])):
            self.assertNotIn(private, published)
            self.assertNotIn(private.replace("\\", "\\\\"), published)
        self.assertIn("python_digest", published)
        self.assertIn("record_sha256", published)


class BootstrapRefusalTests(unittest.TestCase):
    def test_a_checkout_whose_content_differs_from_the_binding_is_refused(self):
        root = Path(self.enterContext(TemporaryDirectory()))
        checkout, revision = make_checkout(root / "checkout", marker="alpha")
        selection, target, _ = make_environment(root=root / "envs", checkout=checkout,
                                                campaign="alpha-campaign", revision=revision)
        attempt = deterministic.prepare(
            root / "attempt", campaign="alpha-campaign", procedure="repository-audit",
            arguments={}, working_directory=str(checkout), environment=selection)
        plan = json.loads((root / "attempt" / "plan.json").read_text(encoding="utf-8"))
        binding = plan["execution"]
        # A child told to expect other content must refuse rather than run.
        argv = execution_source.bound_argv(binding, mode="code", target=workspace.AUDIT)
        argv[5] = "0" * 64
        report = root / "refused-report.json"
        argv[6] = str(report)
        completed = subprocess.run(argv, cwd=str(checkout), capture_output=True, text=True,
                                   timeout=120)
        self.assertEqual(completed.returncode, execution_source.REFUSED_EXIT)
        self.assertEqual(completed.stdout, "")
        self.assertEqual(json.loads(report.read_text(encoding="utf-8"))["state"],
                         "content-mismatch")


class StaleBytecodeTests(unittest.TestCase):
    """A cached .pyc is not source, and must not be able to stand in for it."""

    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))
        self.checkout, self.revision = make_checkout(self.root / "checkout", marker="alpha")
        self.selection, self.target, _ = make_environment(
            root=self.root / "envs", checkout=self.checkout,
            campaign="alpha-campaign", revision=self.revision)
        install_conflict(self.target["interpreter"], marker="shared-preinstalled")
        self.module = (self.checkout / "src" / "deskmate_formats" / "supervisor"
                       / "repository_audit.py")
        self.bound = self.module.read_bytes()

    def plant_stale_cache(self):
        """A cache compiled from other code whose stored size and mtime still match.

        This is the condition the content digest cannot see: the source files
        are the bound ones, but a cache that Python would accept describes
        different code.
        """
        stale = self.bound.replace(b'return "audit:" + MARKER', b'return "audit:" + "stal"')
        self.assertEqual(len(stale), len(self.bound))
        self.assertNotEqual(stale, self.bound)
        stamp = 1700000000
        self.module.write_bytes(stale)
        os.utime(self.module, (stamp, stamp))
        cache = Path(importlib.util.cache_from_source(str(self.module)))
        py_compile.compile(str(self.module), cfile=str(cache), doraise=True,
                           invalidation_mode=py_compile.PycInvalidationMode.TIMESTAMP)
        self.module.write_bytes(self.bound)
        os.utime(self.module, (stamp, stamp))
        return cache

    def run_audit(self):
        attempt = deterministic.prepare(
            self.root / "attempt", campaign="alpha-campaign", procedure="repository-audit",
            arguments={}, working_directory=str(self.checkout), environment=self.selection)
        return deterministic.run(attempt.directory, authorization=attempt.plan_sha256)

    def test_a_stale_cache_cannot_stand_in_for_the_bound_source(self):
        cache = self.plant_stale_cache()
        outcome = self.run_audit()
        self.assertEqual(outcome["state"], "completed", outcome["stderr"]["excerpt"])
        self.assertEqual(outcome["stdout"]["excerpt"].strip(), "audit:alpha")
        child = outcome["execution"]["child"]
        self.assertTrue(child["verified"], child)
        self.assertTrue(child["checks"]["bytecode_caches_bypassed"], child)
        self.assertTrue(child["checks"]["bytecode_prefix_outside_source"], child)
        self.assertTrue(child["checks"]["sourceless_bytecode_absent"], child)
        self.assertGreaterEqual(child["bytecode_caches"], 1)
        # The checkout was not cleaned up to pass: the cache is intact, and a
        # launch without the redirect still executes the code it describes.
        self.assertTrue(cache.is_file())
        legacy = subprocess.run(
            [self.target["interpreter"], "-I", "-c",
             "import sys; sys.path.insert(0, sys.argv[1]); "
             "from deskmate_formats.supervisor import repository_audit as a; print(a.audit())",
             str(self.checkout / "src")],
            cwd=str(self.checkout), capture_output=True, text=True, timeout=120)
        self.assertEqual(legacy.returncode, 0, legacy.stderr)
        self.assertEqual(legacy.stdout.strip(), "audit:stal")

    def test_sourceless_bytecode_in_the_bound_source_is_refused(self):
        loose = self.checkout / "src" / "deskmate_formats" / "supervisor" / "planted.pyc"
        source = loose.with_suffix(".py")
        source.write_bytes(b"VALUE = 1\n")
        py_compile.compile(str(source), cfile=str(loose), doraise=True)
        source.unlink()
        outcome = self.run_audit()
        self.assertEqual(outcome["state"], "failed")
        self.assertEqual(outcome["exit_status"], execution_source.REFUSED_EXIT)
        self.assertEqual(outcome["reason"], "bound-source-refused")
        self.assertEqual(outcome["stdout"]["excerpt"], "")
        self.assertFalse(outcome["execution"]["verified"])
        report = json.loads((self.root / "attempt" / "execution-child.json")
                           .read_text(encoding="utf-8"))
        self.assertEqual(report["state"], "sourceless-bytecode")
        self.assertIn("planted.pyc",
                      [Path(item).name for item in report["sourceless_bytecode"]])


class FreshChildReportTests(unittest.TestCase):
    """Each checkpoint step's evidence must come from that step's child."""

    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))
        self.checkout, revision = make_checkout(self.root / "checkout", marker="alpha")
        self.run_root = storage_directory(self.root / "run", create=True)
        self.execution = execution_source.workspace_execution(
            self.checkout, environment={"interpreter": PYTHON},
            revision=revision, report_path=self.run_root / "plan-child.json")

    def test_a_step_without_its_own_child_report_cannot_pass(self):
        first = workspace.command(self.run_root, self.checkout, "publication-audit",
                                  ("code", workspace.AUDIT), execution=self.execution)
        self.assertEqual(first["exit_status"], 0, first["child"])
        self.assertTrue(first["execution_verified"], first["child"])
        verified = Path(first["child_report_path"])
        self.assertTrue(verified.is_file())
        # A verified report still sitting at the binding's own path — the one
        # path the pre-correction command read for every step — is not inherited.
        shared = Path(self.execution["bootstrap"]["report_path"])
        shared.write_bytes(verified.read_bytes())
        silent = SimpleNamespace(returncode=0)
        with patch.object(workspace.subprocess, "run", return_value=silent):
            second = workspace.command(self.run_root, self.checkout, "test-portable-full",
                                       ("module", *workspace.TEST_PROFILES["portable-full"]),
                                       execution=self.execution)
        self.assertNotEqual(second["child_report_path"], first["child_report_path"])
        self.assertEqual(second["exit_status"], 0)
        self.assertFalse(second["execution_verified"])
        self.assertEqual(second["child"]["state"], "report-missing")
        self.assertEqual(second["child"]["path"], second["child_report_path"])
        self.assertFalse(Path(second["child_report_path"]).exists())
        self.assertTrue(shared.is_file())


if __name__ == "__main__":
    unittest.main()
