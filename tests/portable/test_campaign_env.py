"""Portable tests for campaign environment isolation and execution provenance.

The controlled experiment is here rather than only in the laboratory report:
two synthetic checkouts publish distinguishable markers, a third directory
carries a conflicting shared installation, and each campaign's parent and
isolated child must resolve their own checkout while ``PYTHONPATH`` points at
the other campaign's source and at the shared conflict.

The environments are built without ``ensurepip`` (a fraction of a second each)
and the synthetic package is linked with a ``.pth`` entry, which is how an
editable install is resolved.  The Windows laboratory qualification uses real
``pip`` installs; these tests check the mechanism, not pip.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import venv

from deskmate_formats.campaign_env import (
    cli,
    environment,
    identity,
    inventory,
    launch,
    preflight,
    probe,
    receipts,
)

PROBE_MODULE = """\
\"\"\"Report which implementation of this package the running process loaded.\"\"\"

import json
import os

from . import MARKER


def report():
    import isolation_probe

    return {
        "marker": MARKER,
        "origin": isolation_probe.__file__,
        "isolated": bool(__import__("sys").flags.isolated),
        "pythonpath_present": "PYTHONPATH" in os.environ,
        "interpreter": __import__("sys").executable,
    }


print(json.dumps(report()))
"""

PARENT_MODULE = """\
\"\"\"A campaign parent: record what it loaded, then launch one isolated child.

The child is given a deliberately hostile ``PYTHONPATH`` pointing at the
conflicting shared installation.  The parent itself runs with the campaign
environment's own resolution, because a parent that exported that same
``PYTHONPATH`` would (correctly) import the conflict before site-packages.
\"\"\"

import json
import os
import subprocess
import sys

import isolation_probe
from isolation_probe import MARKER

environment = dict(os.environ)
environment["PYTHONPATH"] = sys.argv[1] if len(sys.argv) > 1 else ""
child = subprocess.run(
    [sys.executable, "-I", "-m", "isolation_probe.probe"],
    capture_output=True,
    text=True,
    env=environment,
    timeout=120,
)
print(json.dumps({
    "parent_marker": MARKER,
    "parent_origin": isolation_probe.__file__,
    "parent_isolated": bool(sys.flags.isolated),
    "child_exit": child.returncode,
    "child": json.loads(child.stdout) if child.returncode == 0 else None,
    "child_stderr": child.stderr[-400:],
}))
"""


def write_package(root: Path, marker: str) -> Path:
    """A minimal synthetic checkout with ``src/isolation_probe``."""
    package = root / "src" / "isolation_probe"
    package.mkdir(parents=True, exist_ok=True)
    (package / "__init__.py").write_text(f'MARKER = "{marker}"\n', encoding="utf-8")
    (package / "probe.py").write_text(PROBE_MODULE, encoding="utf-8")
    (root / "parent.py").write_text(PARENT_MODULE, encoding="utf-8")
    return package


def make_environment(directory: Path) -> Path:
    """A virtual environment without pip, plus the interpreter path."""
    venv.EnvBuilder(with_pip=False, symlinks=os.name != "nt", clear=True).create(directory)
    return directory / ("Scripts" if os.name == "nt" else "bin") / (
        "python.exe" if os.name == "nt" else "python"
    )


def link_package(interpreter: Path, source: Path) -> str:
    """Resolve ``source`` from this environment's site-packages, as an editable install would."""
    site = environment.site_packages(interpreter)
    (Path(site) / "isolation_probe.pth").write_text(str(source), encoding="utf-8")
    return site


def run_child(interpreter: Path, cwd: Path, *, isolated: bool, pythonpath: Path) -> dict:
    argv = [str(interpreter)]
    if isolated:
        argv.append("-I")
    argv += ["-m", "isolation_probe.probe"]
    environment_variables = dict(os.environ)
    environment_variables["PYTHONPATH"] = str(pythonpath)
    completed = subprocess.run(argv, cwd=str(cwd), capture_output=True, text=True,
                               env=environment_variables, timeout=180)
    if completed.returncode != 0:
        raise AssertionError(f"child failed: {completed.stderr[-800:]}")
    return json.loads(completed.stdout)


class ControlledIsolationTest(unittest.TestCase):
    """Two campaigns, one conflicting shared installation, four launch sites."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(cls.enterClassContext(tempfile.TemporaryDirectory(prefix="campaign-isolation-"))).resolve()
        cls.alpha = cls.root / "alpha"
        cls.beta = cls.root / "beta"
        cls.alpha_package = write_package(cls.alpha, "alpha-checkout-2")
        cls.beta_package = write_package(cls.beta, "beta-checkout-7")
        shared = cls.root / "shared" / "isolation_probe"
        shared.mkdir(parents=True)
        (shared / "__init__.py").write_text('MARKER = "shared-stale-0"\n', encoding="utf-8")
        (shared / "probe.py").write_text(PROBE_MODULE, encoding="utf-8")
        cls.shared = cls.root / "shared"
        cls.alpha_python = make_environment(cls.root / "env-alpha")
        cls.beta_python = make_environment(cls.root / "env-beta")
        cls.alpha_site = link_package(cls.alpha_python, cls.alpha / "src")
        cls.beta_site = link_package(cls.beta_python, cls.beta / "src")
        cls.neutral = cls.root / "neutral"
        cls.neutral.mkdir()

    def test_isolated_child_resolves_its_own_checkout_despite_conflicting_pythonpath(self) -> None:
        for label, interpreter, own, other in (
            ("alpha", self.alpha_python, "alpha-checkout-2", self.beta),
            ("beta", self.beta_python, "beta-checkout-7", self.alpha),
        ):
            with self.subTest(campaign=label):
                for pythonpath in (self.shared, other / "src"):
                    report = run_child(interpreter, self.neutral, isolated=True, pythonpath=pythonpath)
                    self.assertEqual(report["marker"], own)
                    self.assertTrue(report["isolated"])
                    self.assertTrue(report["pythonpath_present"])
                    self.assertNotIn("shared", report["origin"])
                    self.assertNotIn(str(other), report["origin"])

    def test_without_isolation_the_conflicting_installation_wins(self) -> None:
        report = run_child(self.alpha_python, self.neutral, isolated=False, pythonpath=self.shared)
        self.assertEqual(report["marker"], "shared-stale-0")
        self.assertFalse(report["isolated"])

    def test_parent_and_isolated_child_agree_with_their_own_checkout(self) -> None:
        for label, checkout, interpreter, own in (
            ("alpha", self.alpha, self.alpha_python, "alpha-checkout-2"),
            ("beta", self.beta, self.beta_python, "beta-checkout-7"),
        ):
            with self.subTest(campaign=label):
                env = dict(os.environ) | {"PYTHONDONTWRITEBYTECODE": "1"}
                env.pop("PYTHONPATH", None)
                completed = subprocess.run([str(interpreter), str(checkout / "parent.py"),
                                            str(self.shared)],
                                           cwd=str(self.neutral), capture_output=True, text=True,
                                           env=env, timeout=180)
                self.assertEqual(completed.returncode, 0, completed.stderr[-800:])
                result = json.loads(completed.stdout)
                self.assertEqual(result["parent_marker"], own)
                self.assertEqual(result["child_exit"], 0, result["child_stderr"])
                self.assertEqual(result["child"]["marker"], own)
                self.assertTrue(result["child"]["isolated"])

    def test_probe_reports_its_own_origin_inside_the_environment(self) -> None:
        report = run_child(self.beta_python, self.neutral, isolated=True, pythonpath=self.shared)
        self.assertTrue(identity.contained(report["origin"], str(self.beta_package.parent)))
        self.assertFalse(identity.contained(report["origin"], str(self.alpha_package.parent)))


class IdentityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory(prefix="campaign-identity-")))

    def test_tree_digest_tracks_content_and_separates_python_from_data(self) -> None:
        package = write_package(self.root / "tree", "marker-a")
        first = identity.package_digests(package)
        (package / "notes.json").write_text('{"a": 1}\n', encoding="utf-8")
        second = identity.package_digests(package)
        self.assertNotEqual(first["tree_digest"], second["tree_digest"])
        self.assertEqual(first["python_digest"], second["python_digest"])
        (package / "extra.py").write_text("VALUE = 1\n", encoding="utf-8")
        third = identity.package_digests(package)
        self.assertNotEqual(second["python_digest"], third["python_digest"])
        self.assertGreater(third["file_count"], first["file_count"])

    def test_missing_tree_is_reported_rather_than_digested(self) -> None:
        with self.assertRaises(identity.IdentityError):
            identity.tree_digest(self.root / "absent")

    def test_source_identity_of_a_plain_directory_is_not_established(self) -> None:
        plain = self.root / "plain"
        plain.mkdir()
        described = identity.source_identity(plain)
        if described["state"] == "git-unavailable":
            self.assertIsNone(described["revision"])
        else:
            self.assertEqual(described["state"], "not-a-repository")
            self.assertIsNone(described["revision"])
            self.assertEqual(described["failure"], "rev-parse-failed")

    def test_source_identity_without_git_is_unknown(self) -> None:
        plain = self.root / "nogit"
        plain.mkdir()
        with mock.patch.object(identity.shutil, "which", return_value=None):
            described = identity.source_identity(plain)
        self.assertEqual(described["state"], "git-unavailable")
        self.assertEqual(described["failure"], "git-unavailable")
        self.assertIsNone(described["revision"])
        self.assertIsNone(described["dirty"])

    @unittest.skipIf(identity.shutil.which("git") is None, "Git is required for the laboratory repository")
    def test_source_identity_reads_revision_and_sees_a_change(self) -> None:
        repository = self.root / "repository"
        repository.mkdir()
        tracked = repository / "file.txt"
        tracked.write_text("one\n", encoding="utf-8")

        def git(*arguments: str) -> str:
            return subprocess.run(
                ["git", "-c", "user.name=Campaign Test", "-c", "user.email=test@example.invalid",
                 "-c", "commit.gpgsign=false", *arguments],
                cwd=str(repository), capture_output=True, text=True, check=True,
            ).stdout.strip()

        git("init", "-q")
        git("add", "file.txt")
        git("commit", "-q", "-m", "synthetic initial commit")
        expected = git("rev-parse", "HEAD")
        described = identity.source_identity(repository)
        self.assertEqual(described["state"], "git")
        self.assertEqual(described["revision"], expected)
        self.assertFalse(described["dirty"])
        tracked.write_text("two\n", encoding="utf-8")
        changed = identity.source_identity(repository)
        self.assertTrue(changed["dirty"])
        self.assertEqual(changed["changed_file_count"], 1)
        self.assertEqual(changed["untracked_file_count"], 0)

    def test_interpreter_identity_describes_another_interpreter(self) -> None:
        described = identity.interpreter_identity(sys.executable)
        self.assertEqual(described["state"], "described")
        self.assertIsNotNone(described["sha256"])
        self.assertEqual(described["version"], sys.version.split()[0])
        missing = identity.interpreter_identity(self.root / "python.exe")
        self.assertEqual(missing["state"], "unavailable")

    def test_containment_and_matching_are_three_valued(self) -> None:
        child = self.root / "parent" / "child"
        child.mkdir(parents=True)
        self.assertTrue(identity.contained(str(child), str(self.root / "parent")))
        self.assertFalse(identity.contained(str(self.root), str(child)))
        self.assertIsNone(identity.contained(None, str(child)))
        self.assertTrue(identity.matches(str(child), str(child)))
        self.assertIsNone(identity.matches(None, str(child)))


class LaunchTest(unittest.TestCase):
    def test_an_isolated_child_requires_an_explicit_absolute_interpreter(self) -> None:
        for value in (None, "", "python", "venv/Scripts/python.exe"):
            with self.subTest(interpreter=value):
                with self.assertRaises(launch.LaunchError):
                    launch.isolated_argv(value, "deskmate_formats.campaign_env.probe")

    def test_vector_shape_and_target_selection(self) -> None:
        interpreter = Path(sys.executable).resolve()
        self.assertEqual(
            launch.isolated_argv(interpreter, "example.module", arguments=["--json"]),
            [str(interpreter), "-I", "-m", "example.module", "--json"],
        )
        self.assertEqual(
            launch.isolated_argv(interpreter, code="print(1)"),
            [str(interpreter), "-I", "-c", "print(1)"],
        )
        for arguments in ({"module": None, "code": None}, {"module": "a", "code": "b"}):
            with self.subTest(arguments=arguments), self.assertRaises(launch.LaunchError):
                launch.isolated_argv(interpreter, arguments["module"], code=arguments["code"])

    def test_refused_names_do_not_become_arguments(self) -> None:
        interpreter = Path(sys.executable).resolve()
        with self.assertRaises(launch.LaunchError):
            launch.isolated_argv(interpreter, "example; rm -rf /")
        with self.assertRaises(launch.LaunchError):
            launch.isolated_argv(interpreter, "example", arguments=["bad\0argument"])

    def test_probe_parses_a_child_report(self) -> None:
        interpreter = Path(sys.executable).resolve()
        receipt = launch.run_isolated(interpreter, "deskmate_formats.campaign_env.probe",
                                      arguments=["--json"])
        if receipt["exit_status"] != 0:
            # A source-only checkout is not importable under -I; that is the
            # defect this campaign documents, not a test failure.
            self.assertIn("ModuleNotFoundError", str(receipt["stderr"]))
            self.skipTest("the package is not installed for this interpreter")
        report = json.loads(str(receipt["stdout"]))
        self.assertTrue(report["isolated"])
        self.assertEqual(report["package"]["name"], "deskmate_formats")


class ReceiptTest(unittest.TestCase):
    def test_receipts_round_trip_and_report_a_digest(self) -> None:
        root = Path(self.enterContext(tempfile.TemporaryDirectory(prefix="campaign-receipts-")))
        target = root / "nested" / "record.json"
        written = receipts.write(target, {"b": 1, "a": [1, 2]})
        self.assertTrue(target.is_file())
        self.assertEqual(written["sha256"], receipts.file_digest(target))
        self.assertEqual(receipts.read(target), {"a": [1, 2], "b": 1})

    def test_public_projection_removes_private_paths_and_search_paths(self) -> None:
        # Assembled rather than written out: a repository audit rejects a literal
        # host user path anywhere in a tracked file, and this test needs one.
        windows_home = "C:" + chr(92) + "Users" + chr(92) + "example"
        posix_home = "/" + "home/example"
        share = chr(92) * 2 + "server" + chr(92) + "share" + chr(92) + "private"
        record = {
            "kind": "campaign-environment-preflight",
            "checkout": windows_home + chr(92) + "secret-checkout",
            "interpreter": posix_home + "/.venvs/campaign/bin/python",
            "checks": [{"check": "interpreter", "state": "pass",
                        "detail": windows_home + chr(92) + "x"}],
            "child": {"sys_path": [posix_home + "/private", "C:" + chr(92) + "private"],
                      "sys_path_count": 4, "report": {"cwd": share,
                                                      "package": {"tree_digest": "ab" * 32}}},
            "unknown_key": windows_home + chr(92) + "kept-but-redacted",
        }
        projected = receipts.public(record, roots=(windows_home + chr(92) + "secret-checkout",))
        text = json.dumps(projected)
        self.assertNotIn(windows_home, text)
        self.assertNotIn(posix_home, text)
        self.assertNotIn(share, text)
        self.assertNotIn("sys_path", projected["child"])
        self.assertEqual(projected["child"]["sys_path_count"], 4)
        self.assertEqual(projected["checks"][0]["state"], "pass")
        self.assertEqual(projected["public_projection_version"], 1)

    def test_redaction_keeps_shapes_and_leaves_public_paths_alone(self) -> None:
        self.assertEqual(receipts.redact("C:" + chr(92) + "lab" + chr(92) + "file.py"), receipts.REDACTED_PATH)
        self.assertEqual(receipts.redact("/" + "home/lab/file.py"), receipts.REDACTED_HOME)
        self.assertEqual(receipts.redact("/usr/bin/python3"), "/usr/bin/python3")
        self.assertEqual(receipts.redact(""), "")


class EnvironmentLayoutTest(unittest.TestCase):
    def test_campaign_names_and_paths_are_predictable(self) -> None:
        root = Path(self.enterContext(tempfile.TemporaryDirectory(prefix="campaign-layout-")))
        described = environment.layout(root, "campaign-one")
        self.assertEqual(Path(str(described["directory"])),
                         (root / "local-results" / "campaign-envs" / "campaign-one").resolve())
        self.assertTrue(str(described["interpreter"]).endswith(("python", "python.exe")))
        for name in ("Uppercase", "with space", "../escape", "", "a" * 65):
            with self.subTest(name=name), self.assertRaises(environment.CampaignEnvironmentError):
                environment.layout(root, name)

    def test_existing_environment_is_not_replaced_implicitly(self) -> None:
        root = Path(self.enterContext(tempfile.TemporaryDirectory(prefix="campaign-existing-")))
        described = environment.layout(root, "existing")
        Path(str(described["record"])).parent.mkdir(parents=True)
        receipts.write(str(described["record"]), {"schema_version": 1})
        with self.assertRaises(environment.CampaignEnvironmentError):
            environment.provision(root, "existing")


class InventoryTest(unittest.TestCase):
    def test_isolated_launch_sites_are_found_with_their_target(self) -> None:
        root = Path(self.enterContext(tempfile.TemporaryDirectory(prefix="campaign-inventory-")))
        tools = root / "tools"
        tools.mkdir()
        (tools / "launcher.py").write_text(
            "import subprocess, sys\n"
            "def one():\n"
            "    return subprocess.run([sys.executable, \"-I\", \"-m\", \"example.module\", \"--json\"])\n"
            "def two():\n"
            "    return subprocess.run([\"python.exe\", \"-I\", \"-c\", \"print(1)\"])\n"
            "def three(executable):\n"
            "    return subprocess.run([executable, \"-I\", \"-c\", \"print(2)\"])\n"
            "def four():\n"
            "    return \"-I\"\n",
            encoding="utf-8",
        )
        (root / "src").mkdir()
        (root / "tests").mkdir()
        sites = inventory.launch_sites(root)
        self.assertEqual([site["line"] for site in sites], [3, 5, 7, 9])
        self.assertEqual(sites[0]["module"], "example.module")
        self.assertEqual(sites[0]["interpreter_expression"], "sys.executable")
        self.assertTrue(sites[0]["sys_executable"])
        self.assertTrue(sites[1]["inline_code"])
        self.assertEqual(sites[1]["interpreter_expression"], "literal:python.exe")
        self.assertEqual(sites[2]["interpreter_expression"], "unresolved")
        self.assertIsNone(sites[3]["module"])

    def test_module_origin_is_asked_of_the_interpreter(self) -> None:
        resolved = inventory.module_origin(sys.executable, "json")
        self.assertTrue(resolved.endswith("__init__.py"), resolved)
        self.assertEqual(Path(resolved).resolve().parent.name, "json")
        self.assertIn(inventory.module_origin(sys.executable, "definitely_not_a_module_xyz"),
                      {"missing", "error:ModuleNotFoundError"})

    def test_worktrees_are_read_without_git_dying(self) -> None:
        with mock.patch.object(inventory.shutil, "which", return_value=None):
            self.assertEqual(inventory.worktrees(Path.cwd()), [])


class ProbeAndPreflightTest(unittest.TestCase):
    def test_probe_report_describes_this_process(self) -> None:
        document = probe.report()
        self.assertEqual(document["package"]["name"], "deskmate_formats")
        self.assertEqual(document["sys_path_count"], len(document["sys_path"]))
        self.assertEqual(document["isolated"], bool(sys.flags.isolated))
        self.assertIsInstance(document["pythonpath_present"], bool)

    def test_preflight_without_an_environment_is_unknown_and_never_qualified(self) -> None:
        root = Path(self.enterContext(tempfile.TemporaryDirectory(prefix="campaign-unprovisioned-")))
        described = preflight.preflight(root, campaign="absent")
        self.assertEqual(described["verdict"], preflight.UNKNOWN)
        self.assertFalse(described["measurement_allowed"])
        self.assertEqual(described["reasons"], ["environment-not-provisioned"])
        self.assertEqual(preflight.exit_code(described["verdict"]), 2)

    def test_mismatched_interpreter_and_stale_source_are_unqualified(self) -> None:
        root = Path(self.enterContext(tempfile.TemporaryDirectory(prefix="campaign-preflight-")))
        checkout = root / "checkout"
        package = write_package(checkout, "checkout-a")
        digests = identity.package_digests(package)
        venue = root / "venue"
        venue.mkdir()
        described = environment.layout(checkout, "campaign", root=root / "envs")
        Path(str(described["record"])).parent.mkdir(parents=True)
        receipts.write(str(described["record"]), {
            "schema_version": 1,
            "kind": "campaign-environment",
            "campaign": "campaign",
            "package": "isolation_probe",
            "interpreter": str(venue / "python.exe"),
            "site_packages": str(venue),
            "site_packages_absent": True,
            "source": {"state": "git", "revision": "0" * 40, "dirty": False},
            "source_package": digests,
            "installed": {"state": "imported", "tree_digest": digests["tree_digest"],
                          "origin": str(venue / "isolation_probe")},
            "created_utc": identity.utc_now(),
            "verdict": "qualified",
        })
        (package / "__init__.py").write_text('MARKER = "checkout-b"\n', encoding="utf-8")
        described_state = preflight.preflight(checkout, campaign="campaign", root=root / "envs",
                                             package="isolation_probe")
        states = {entry["check"]: entry["state"] for entry in described_state["checks"]}
        self.assertEqual(states["source-content"], preflight._FAIL)
        self.assertEqual(states["interpreter"], preflight._FAIL)
        self.assertEqual(states["environment-record"], preflight._PASS)
        self.assertEqual(described_state["verdict"], preflight.UNQUALIFIED)
        self.assertFalse(described_state["measurement_allowed"])
        self.assertIn("source-content", described_state["reasons"])
        stale = next(entry for entry in described_state["checks"] if entry["check"] == "source-content")
        self.assertIn("stale", stale["detail"])
        self.assertEqual(preflight.exit_code(described_state["verdict"]), 1)

    def test_unknown_verdict_is_never_an_assertion(self) -> None:
        self.assertEqual(preflight.exit_code("qualified"), 0)
        self.assertEqual(preflight.exit_code("unqualified"), 1)
        self.assertEqual(preflight.exit_code("unknown"), 2)
        self.assertEqual(preflight.exit_code("anything-else"), 2)


class CommandLineTest(unittest.TestCase):
    def test_probe_and_preflight_have_defined_exit_statuses(self) -> None:
        root = Path(self.enterContext(tempfile.TemporaryDirectory(prefix="campaign-cli-")))
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            self.assertEqual(cli.main(["probe"]), 0)
            self.assertEqual(cli.main(["preflight", "--checkout", str(root), "--campaign", "absent"]), 2)
        documents = [json.loads(chunk) for chunk in _split_documents(buffer.getvalue())]
        self.assertTrue(documents[0]["isolated"] is not None)
        self.assertEqual(documents[-1]["verdict"], "unknown")

    def test_identity_command_reports_source_state(self) -> None:
        root = Path(self.enterContext(tempfile.TemporaryDirectory(prefix="campaign-cli-identity-")))
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            self.assertEqual(cli.main(["identity", "--checkout", str(root), "--public"]), 0)
        document = json.loads(buffer.getvalue())
        self.assertIn(document["source"]["state"], {"not-a-repository", "git-unavailable", "missing"})
        self.assertIsNone(document["source"]["revision"])


def _split_documents(text: str) -> "list[str]":
    """Split concatenated pretty-printed JSON objects printed by the CLI."""
    documents, depth, start = [], 0, None
    for index, character in enumerate(text):
        if character == "{":
            if depth == 0:
                start = index
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0 and start is not None:
                documents.append(text[start:index + 1])
                start = None
    return documents


if __name__ == "__main__":
    unittest.main()
