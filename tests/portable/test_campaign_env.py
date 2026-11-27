"""Portable tests for campaign environment isolation and execution provenance.

Two groups of tests live here.

The controlled experiment is real: two synthetic checkouts publish
distinguishable markers, a third directory carries a conflicting installation,
and each campaign's parent and isolated child must resolve their own checkout
while ``PYTHONPATH`` points at the other campaign's source and at the conflict.
The environments are built without ``ensurepip`` (a fraction of a second each)
and the synthetic package is linked with a ``.pth`` entry, which is how an
editable install is resolved; the Windows laboratory experiment uses real
``pip`` installs.

The regression tests answer the independent review of PR #206, one finding at a
time: parent versus requested interpreter identity, symlinked POSIX
environments, positive package-content matching, receipt binding, exact Git
checkout root, ownership and replacement of the target directory, and the
installation boundary that keeps the network-capable build backend opt-in.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import shutil
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


def make_environment(directory: Path, *, symlinks: bool = False) -> Path:
    """A virtual environment without pip, plus its interpreter path."""
    venv.EnvBuilder(with_pip=False, symlinks=symlinks, clear=True).create(directory)
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


def git(cwd: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-c", "user.name=Campaign Test", "-c", "user.email=test@example.invalid",
         "-c", "commit.gpgsign=false", "-c", "core.hooksPath=" + os.devnull, *arguments],
        cwd=str(cwd), capture_output=True, text=True, timeout=120,
    )
    if completed.returncode != 0:
        raise AssertionError(completed.stderr[-600:])
    return completed.stdout.strip()


def make_repository(path: Path, *, files: "dict[str, str] | None" = None) -> str:
    """A real repository with one commit, so identity is established not assumed."""
    path.mkdir(parents=True, exist_ok=True)
    for name, text in (files or {"file.txt": "one\n"}).items():
        target = path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    git(path, "init", "-q")
    git(path, "add", "--", ".")
    git(path, "commit", "-q", "-m", "synthetic initial commit")
    return git(path, "rev-parse", "HEAD")


def make_record(checkout: Path, target: "dict[str, object]", *, campaign: str = "campaign",
                package: str = "isolation_probe", revision: str = "0" * 40,
                python_digest: str = "a" * 64, tree_digest: str = "b" * 64,
                prefix: "str | None" = None, executable_sha256: str = "c" * 64,
                verdict: str = "qualified") -> dict:
    """A record shaped exactly like a provisioning receipt, for preflight tests."""
    venue = str(target["venv"])
    return {
        "schema_version": environment.SCHEMA_VERSION,
        "kind": environment.KIND,
        "campaign": campaign,
        "package": package,
        "checkout": str(checkout),
        "root": str(target["root"]),
        "directory": str(target["directory"]),
        "venv": venue,
        "interpreter": str(target["interpreter"]),
        "site_packages": str(Path(venue) / "Lib" / "site-packages"),
        "record_path": str(target["record"]),
        "created_utc": identity.utc_now(),
        "ownership": {"mode": "fresh", "previous_record_present": False, "retired_path": None},
        "source_before": {"state": "git", "revision": revision, "dirty": False},
        "source_after": {"state": "git", "revision": revision, "dirty": False},
        "source_unchanged": True,
        "source_package": {"tree_digest": tree_digest, "python_digest": python_digest,
                           "file_count": 3},
        "environment_identity": {"prefix": prefix if prefix is not None else venue,
                                 "executable_sha256": executable_sha256,
                                 "virtual_environment": True},
        "installed": {"state": "imported", "python_digest": python_digest,
                      "tree_digest": tree_digest,
                      "origin": str(Path(venue) / "Lib" / "site-packages" / package)},
        "verdict": verdict,
        "reasons": [] if verdict == "qualified" else ["installed-code-differs-from-source"],
    }


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


class SymlinkedEnvironmentIdentityTest(unittest.TestCase):
    """POSIX virtual environments share one executable inode and differ by prefix."""

    def setUp(self) -> None:
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory(prefix="campaign-symlink-"))).resolve()

    def test_two_symlinked_environments_are_distinguished_by_prefix(self) -> None:
        try:
            first = make_environment(self.root / "env-one", symlinks=True)
            second = make_environment(self.root / "env-two", symlinks=True)
        except (OSError, subprocess.SubprocessError) as error:
            self.skipTest(f"symbolic-link environments are unavailable here: {type(error).__name__}")
        if not first.is_symlink() or not second.is_symlink():
            self.skipTest("this platform created real copies instead of symbolic links")
        # The trap the review identified: one executable identity, two environments.
        self.assertTrue(os.path.samefile(first, second))
        self.assertEqual(os.path.realpath(first), os.path.realpath(second))
        one = identity.interpreter_identity(first)
        two = identity.interpreter_identity(second)
        self.assertEqual(one["state"], "described")
        self.assertEqual(two["state"], "described")
        self.assertEqual(one["executable_realpath"], two["executable_realpath"])
        self.assertNotEqual(one["prefix"], two["prefix"])
        self.assertFalse(identity.same_environment(one["prefix"], two["prefix"]))
        self.assertTrue(identity.same_environment(one["prefix"], one["prefix"]))
        self.assertNotEqual(one["site_packages"], two["site_packages"])
        self.assertTrue(identity.contained(one["site_packages"], one["prefix"]))

    def test_two_real_environment_copies_are_not_identical_either(self) -> None:
        first = make_environment(self.root / "copy-one")
        second = make_environment(self.root / "copy-two")
        one = identity.interpreter_identity(first)
        two = identity.interpreter_identity(second)
        self.assertNotEqual(one["prefix"], two["prefix"])
        self.assertIsNone(identity.same_environment(None, one["prefix"]))


class InterpreterIdentityTest(unittest.TestCase):
    def test_running_parent_is_described_without_resolving_its_path(self) -> None:
        described = identity.describe_running_interpreter()
        self.assertEqual(described["state"], "running-interpreter")
        self.assertEqual(described["executable"], os.path.abspath(sys.executable))
        self.assertEqual(described["prefix"], sys.prefix)
        self.assertEqual(described["executable_realpath"], os.path.realpath(sys.executable))
        self.assertEqual(described["virtual_environment"], sys.prefix != sys.base_prefix)
        self.assertIsNotNone(described["executable_sha256"])
        self.assertIs(described["site_packages_inside_prefix"], True)

    def test_missing_and_unreadable_interpreters_are_reported_not_guessed(self) -> None:
        missing = identity.interpreter_identity(Path(tempfile.gettempdir()) / "absent-python")
        self.assertEqual(missing["state"], "unavailable")
        self.assertIsNone(missing["prefix"])
        self.assertIsNone(missing["site_packages"])

    def test_environment_match_is_three_valued(self) -> None:
        self.assertTrue(identity.same_environment("/campaigns/a", "/campaigns/a"))
        self.assertTrue(identity.same_environment("/campaigns/a/", "/campaigns/a" + os.sep))
        self.assertFalse(identity.same_environment("/campaigns/a", "/campaigns/b"))
        self.assertIsNone(identity.same_environment(None, "/campaigns/a"))

    def test_probe_reports_invocation_path_prefix_and_digest(self) -> None:
        document = probe.report()
        self.assertEqual(document["schema_version"], probe.PROBE_SCHEMA_VERSION)
        self.assertEqual(document["interpreter"], os.path.abspath(sys.executable))
        self.assertEqual(document["prefix"], sys.prefix)
        self.assertEqual(document["observed_package"], "deskmate_formats")
        self.assertIsNotNone(document["interpreter_sha256"])
        self.assertEqual(document["sys_path_count"], len(document["sys_path"]))


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
        expected = make_repository(repository)
        described = identity.source_identity(repository)
        self.assertEqual(described["state"], "git")
        self.assertEqual(described["revision"], expected)
        self.assertIs(described["exact_checkout_root"], True)
        self.assertFalse(described["dirty"])
        (repository / "file.txt").write_text("two\n", encoding="utf-8")
        changed = identity.source_identity(repository)
        self.assertTrue(changed["dirty"])
        self.assertEqual(changed["changed_file_count"], 1)
        self.assertEqual(changed["untracked_file_count"], 0)

    @unittest.skipIf(identity.shutil.which("git") is None, "Git is required for the laboratory repository")
    def test_a_subdirectory_of_a_repository_is_not_its_own_checkout(self) -> None:
        repository = self.root / "outer"
        make_repository(repository, files={"nested/file.txt": "inner\n"})
        nested = repository / "nested"
        refused = identity.source_identity(nested)
        self.assertEqual(refused["state"], "enclosing-repository")
        self.assertEqual(refused["failure"], "checkout-not-repository-root")
        self.assertIsNone(refused["revision"])
        self.assertIs(refused["exact_checkout_root"], False)
        self.assertEqual(Path(str(refused["top_level"])).name, "outer")
        accepted = identity.source_identity(nested, accept_enclosing=True)
        self.assertEqual(accepted["state"], "git")
        self.assertEqual(accepted["revision"], identity.source_identity(repository)["revision"])
        self.assertIs(accepted["accept_enclosing"], True)

    def test_containment_matching_and_environment_identity_are_separate(self) -> None:
        child = self.root / "parent" / "child"
        child.mkdir(parents=True)
        self.assertTrue(identity.contained(str(child), str(self.root / "parent")))
        self.assertFalse(identity.contained(str(self.root), str(child)))
        self.assertIsNone(identity.contained(None, str(child)))
        self.assertTrue(identity.same_path(str(child), str(child)))
        self.assertIsNone(identity.same_path(None, str(child)))


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
        self.assertEqual(receipts.redact("C:" + chr(92) + "lab" + chr(92) + "file.py"),
                         receipts.REDACTED_PATH)
        self.assertEqual(receipts.redact("/" + "home/lab/file.py"), receipts.REDACTED_HOME)
        self.assertEqual(receipts.redact("/usr/bin/python3"), "/usr/bin/python3")
        self.assertEqual(receipts.redact(""), "")


class LayoutTest(unittest.TestCase):
    def test_campaign_names_and_paths_are_predictable(self) -> None:
        root = Path(self.enterContext(tempfile.TemporaryDirectory(prefix="campaign-layout-")))
        described = environment.layout(root, "campaign-one")
        # Unresolved on purpose: a redirecting root has to remain visible.
        self.assertEqual(Path(str(described["directory"])),
                         root / "local-results" / "campaign-envs" / "campaign-one")
        self.assertTrue(str(described["interpreter"]).endswith(("python", "python.exe")))
        for name in ("Uppercase", "with space", "../escape", "", "a" * 65):
            with self.subTest(name=name), self.assertRaises(environment.CampaignEnvironmentError) as caught:
                environment.layout(root, name)
            self.assertEqual(caught.exception.code, "invalid-campaign-name")

    def test_existing_environment_is_not_replaced_implicitly(self) -> None:
        root = Path(self.enterContext(tempfile.TemporaryDirectory(prefix="campaign-existing-")))
        repository = root / "checkout"
        make_repository(repository)
        described = environment.layout(repository, "existing", root=root / "envs")
        Path(str(described["record"])).parent.mkdir(parents=True)
        # The script directory differs by platform (``Scripts`` or ``bin``); the
        # layout already knows which one this host uses.
        Path(str(described["interpreter"])).parent.mkdir(parents=True)
        Path(str(described["interpreter"])).write_text("", encoding="utf-8")
        receipts.write(str(described["record"]),
                       make_record(repository, described, campaign="existing"))
        with self.assertRaises(environment.CampaignEnvironmentError) as caught:
            environment.provision(repository, "existing", root=root / "envs",
                                  package="isolation_probe")
        self.assertEqual(caught.exception.code, "environment-exists")


class TargetOwnershipTest(unittest.TestCase):
    """A pre-existing path is never assumed to be this campaign's to overwrite."""

    def setUp(self) -> None:
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory(prefix="campaign-ownership-"))).resolve()
        self.repository = self.root / "checkout"
        make_repository(self.repository)
        self.target = environment.layout(self.repository, "campaign", root=self.root / "envs")

    def _declare_owned(self, *, campaign: str = "campaign") -> str:
        directory = Path(str(self.target["directory"]))
        directory.mkdir(parents=True, exist_ok=True)
        venue = Path(str(self.target["venv"]))
        Path(str(self.target["interpreter"])).parent.mkdir(parents=True, exist_ok=True)
        (venue / "pyvenv.cfg").write_text("home = synthetic\n", encoding="utf-8")
        Path(str(self.target["interpreter"])).write_text("", encoding="utf-8")
        receipts.write(str(self.target["record"]),
                       make_record(self.repository, self.target, campaign=campaign))
        return receipts.file_digest(str(self.target["record"]))

    def test_path_kind_sees_redirects_windows_does_not_call_links(self) -> None:
        plain = self.root / "plain"
        plain.mkdir()
        self.assertEqual(environment.path_kind(plain), "directory")
        self.assertEqual(environment.path_kind(self.root / "absent"), "absent")
        self.assertEqual(environment.path_kind(plain / "file.txt") if (plain / "file.txt").write_text("x") else "file", "file")

    def test_absent_target_is_fresh_and_owned_target_is_recognized(self) -> None:
        self.assertEqual(environment.classify_target(self.target, "campaign", self.repository,
                                                     "isolation_probe")["mode"], "fresh")
        self._declare_owned()
        owned = environment.classify_target(self.target, "campaign", self.repository, "isolation_probe")
        self.assertEqual(owned["mode"], "owned")
        self.assertIsNotNone(owned["record"])

    def test_a_directory_without_a_record_is_not_treated_as_unowned_scratch_space(self) -> None:
        Path(str(self.target["directory"])).mkdir(parents=True)
        (Path(str(self.target["directory"])) / "someone-elses-file.txt").write_text("keep\n")
        with self.assertRaises(environment.CampaignEnvironmentError) as caught:
            environment.classify_target(self.target, "campaign", self.repository, "isolation_probe")
        self.assertEqual(caught.exception.code, "existing-directory-without-valid-record")
        self.assertTrue((Path(str(self.target["directory"])) / "someone-elses-file.txt").is_file())

    def test_a_foreign_or_partial_record_is_refused(self) -> None:
        self._declare_owned(campaign="another-campaign")
        with self.assertRaises(environment.CampaignEnvironmentError) as caught:
            environment.classify_target(self.target, "campaign", self.repository, "isolation_probe")
        self.assertEqual(caught.exception.code, "existing-directory-with-foreign-record")
        self.assertIn("record-campaign", caught.exception.detail)

    def test_a_missing_interpreter_makes_the_record_inconsistent(self) -> None:
        self._declare_owned()
        Path(str(self.target["interpreter"])).unlink()
        with self.assertRaises(environment.CampaignEnvironmentError) as caught:
            environment.classify_target(self.target, "campaign", self.repository, "isolation_probe")
        self.assertEqual(caught.exception.code, "existing-record-without-interpreter")

    def test_a_symbolic_link_at_the_target_is_refused(self) -> None:
        elsewhere = self.root / "elsewhere"
        elsewhere.mkdir()
        try:
            os.symlink(elsewhere, Path(str(self.target["directory"])), target_is_directory=True)
        except (OSError, NotImplementedError) as error:
            self.skipTest(f"symbolic links are unavailable here: {type(error).__name__}")
        self.assertIn(environment.path_kind(self.target["directory"]), {"symlink", "junction"})
        with self.assertRaises(environment.CampaignEnvironmentError) as caught:
            environment.classify_target(self.target, "campaign", self.repository, "isolation_probe")
        self.assertEqual(caught.exception.code, "existing-redirect-at-target")

    @unittest.skipUnless(os.name == "nt", "junctions exist on Windows")
    def test_a_junction_at_the_target_is_refused(self) -> None:
        elsewhere = self.root / "elsewhere"
        elsewhere.mkdir()
        completed = subprocess.run(["cmd", "/c", "mklink", "/J", str(self.target["directory"]),
                                    str(elsewhere)], capture_output=True, text=True)
        if completed.returncode != 0:
            self.skipTest("junction creation was refused on this host")
        self.assertEqual(environment.path_kind(self.target["directory"]), "junction")
        with self.assertRaises(environment.CampaignEnvironmentError) as caught:
            environment.classify_target(self.target, "campaign", self.repository, "isolation_probe")
        self.assertEqual(caught.exception.code, "existing-redirect-at-target")

    def _staging(self, name: str = "fresh-install.txt") -> Path:
        staging = Path(str(self.target["root"])) / f".staging-synthetic-{name}"
        (staging / environment.VENV_NAME).mkdir(parents=True)
        (staging / environment.VENV_NAME / name).write_text("new\n", encoding="utf-8")
        return staging

    def _swap(self, staging: Path, *, replace: bool, digest: "str | None") -> "Path | None":
        return environment._swap_into_place(staging, self.target, replace=replace,
                                            campaign="campaign", checkout=self.repository,
                                            package="isolation_probe",
                                            expected_record_sha256=digest)

    def test_staging_swap_replaces_content_and_retires_the_old_environment(self) -> None:
        digest = self._declare_owned()
        venue = Path(str(self.target["venv"]))
        (venue / "stale-install.txt").write_text("old\n", encoding="utf-8")
        retired = self._swap(self._staging(), replace=True, digest=digest)
        self.assertIsNotNone(retired)
        resident = sorted(path.name for path in venue.iterdir())
        self.assertEqual(resident, ["fresh-install.txt"])
        self.assertTrue((Path(str(retired)) / "stale-install.txt").is_file())
        shutil.rmtree(retired, ignore_errors=True)

    def test_swap_refuses_to_replace_without_permission(self) -> None:
        digest = self._declare_owned()
        with self.assertRaises(environment.CampaignEnvironmentError) as caught:
            self._swap(self._staging(), replace=False, digest=digest)
        self.assertEqual(caught.exception.code, "existing-environment-not-replaceable")
        self.assertTrue(Path(str(self.target["interpreter"])).is_file())

    def test_a_record_changed_after_classification_blocks_the_swap(self) -> None:
        digest = self._declare_owned()
        receipts.write(str(self.target["record"]),
                       make_record(self.repository, self.target, campaign="campaign",
                                   python_digest="f" * 64))
        with self.assertRaises(environment.CampaignEnvironmentError) as caught:
            self._swap(self._staging(), replace=True, digest=digest)
        self.assertEqual(caught.exception.code, "target-changed-during-provisioning")
        self.assertIn("record-changed", caught.exception.detail)
        self.assertTrue(Path(str(self.target["interpreter"])).is_file())

    def test_a_disappeared_record_blocks_the_swap(self) -> None:
        digest = self._declare_owned()
        Path(str(self.target["record"])).unlink()
        with self.assertRaises(environment.CampaignEnvironmentError) as caught:
            self._swap(self._staging(), replace=True, digest=digest)
        self.assertEqual(caught.exception.code, "target-changed-during-provisioning")
        self.assertTrue(Path(str(self.target["interpreter"])).is_file())

    def test_an_intervening_first_provision_blocks_a_fresh_swap(self) -> None:
        self._declare_owned()
        with self.assertRaises(environment.CampaignEnvironmentError) as caught:
            self._swap(self._staging(), replace=True, digest=None)
        self.assertEqual(caught.exception.code, "target-changed-during-provisioning")
        self.assertIn("target-appeared", caught.exception.detail)


class ParentIdentityTest(unittest.TestCase):
    """A passing prefix is not a passing parent: path and digest must match too.

    The running parent is replaced by a crafted identity here so that each of the
    three conditions can be broken on its own; the real parent is exercised in
    ``QualifiedPreflightTest``.
    """

    def setUp(self) -> None:
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory(prefix="campaign-parent-"))).resolve()
        self.repository = self.root / "checkout"
        package = write_package(self.repository, "parent-checkout")
        self.revision = make_repository(self.repository)
        self.target = environment.layout(self.repository, "campaign", root=self.root / "envs")
        self.digests = identity.package_digests(package)
        Path(str(self.target["record"])).parent.mkdir(parents=True)
        self.record = make_record(self.repository, self.target,
                                  python_digest=self.digests["python_digest"],
                                  tree_digest=self.digests["tree_digest"], revision=self.revision,
                                  prefix=str(self.target["venv"]),
                                  executable_sha256="a" * 64)
        receipts.write(str(self.target["record"]), self.record)
        self.parent = {
            "state": "running-interpreter",
            "prefix": str(self.target["venv"]),
            "executable": str(self.target["interpreter"]),
            "executable_sha256": "a" * 64,
        }

    def _parent(self, **changes) -> dict:
        parent = dict(self.parent) | changes
        with mock.patch.object(preflight.identity, "describe_running_interpreter", return_value=parent):
            described = preflight.preflight(self.repository, campaign="campaign",
                                            root=self.root / "envs", package="isolation_probe")
        return {entry["check"]: entry for entry in described["checks"]}["parent-interpreter"]

    def test_prefix_path_and_digest_all_matching_passes(self) -> None:
        parent = self._parent()
        self.assertEqual(parent["state"], preflight._PASS, parent)
        self.assertIs(parent["prefix_matches"], True)
        self.assertIs(parent["invocation_path_matches"], True)
        self.assertIs(parent["executable_digest_matches"], True)

    def test_a_matching_prefix_alone_does_not_pass(self) -> None:
        parent = self._parent(executable=str(self.root / "elsewhere" / "bin" / "python"))
        self.assertEqual(parent["state"], preflight._FAIL)
        self.assertIs(parent["prefix_matches"], True)
        self.assertIs(parent["invocation_path_matches"], False)
        self.assertIn("invoked by a different", parent["detail"])

    def test_a_matching_prefix_and_path_with_a_different_digest_do_not_pass(self) -> None:
        parent = self._parent(executable_sha256="b" * 64)
        self.assertEqual(parent["state"], preflight._FAIL)
        self.assertIs(parent["invocation_path_matches"], True)
        self.assertIs(parent["executable_digest_matches"], False)
        self.assertIn("digest", parent["detail"])

    def test_a_record_without_a_digest_cannot_prove_the_parent(self) -> None:
        self.record["environment_identity"]["executable_sha256"] = None
        receipts.write(str(self.target["record"]), self.record)
        parent = self._parent(executable_sha256=None)
        self.assertEqual(parent["state"], preflight._FAIL)
        self.assertIn("no executable digest", parent["detail"])

    def test_a_different_environment_fails_on_the_prefix(self) -> None:
        parent = self._parent(prefix=str(self.root / "other-venv"))
        self.assertEqual(parent["state"], preflight._FAIL)
        self.assertIs(parent["prefix_matches"], False)


class RequestedInterpreterTest(unittest.TestCase):
    """Two real POSIX virtual environments that share one executable."""

    def setUp(self) -> None:
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory(prefix="campaign-requested-"))).resolve()
        self.repository = self.root / "checkout"
        package = write_package(self.repository, "requested-checkout")
        self.revision = make_repository(self.repository)
        self.target = environment.layout(self.repository, "campaign", root=self.root / "envs")
        Path(str(self.target["venv"])).parent.mkdir(parents=True)
        try:
            self.selected = make_environment(Path(str(self.target["venv"])), symlinks=True)
            self.other = make_environment(self.root / "other-venv", symlinks=True)
        except (OSError, subprocess.SubprocessError) as error:
            self.skipTest(f"virtual environments are unavailable here: {type(error).__name__}")
        if not os.path.islink(self.selected):
            self.skipTest("this platform created real copies instead of symbolic links")
        digests = identity.package_digests(package)
        self.record = make_record(self.repository, self.target,
                                  python_digest=digests["python_digest"],
                                  tree_digest=digests["tree_digest"], revision=self.revision,
                                  prefix=str(self.target["venv"]),
                                  executable_sha256=identity.file_digest(self.selected))
        self.record["site_packages"] = environment.site_packages(self.selected)
        receipts.write(str(self.target["record"]), self.record)

    def _states(self, requested: Path) -> "dict[str, dict]":
        parent = identity.interpreter_identity(self.selected)
        with mock.patch.object(preflight.identity, "describe_running_interpreter", return_value=parent):
            described = preflight.preflight(self.repository, campaign="campaign",
                                            root=self.root / "envs", package="isolation_probe",
                                            interpreter=requested)
        return {entry["check"]: entry for entry in described["checks"]}

    def test_the_two_environments_share_one_executable(self) -> None:
        self.assertTrue(os.path.samefile(self.selected, self.other))
        self.assertTrue(identity.same_path(self.selected, self.other))
        self.assertNotEqual(identity.interpreter_identity(self.selected)["prefix"],
                            identity.interpreter_identity(self.other)["prefix"])

    def test_requesting_the_recorded_interpreter_passes(self) -> None:
        states = self._states(self.selected)
        self.assertEqual(states["requested-interpreter"]["state"], preflight._PASS)
        self.assertIs(states["requested-interpreter"]["prefix_matches"], True)
        self.assertIs(states["requested-interpreter"]["invocation_path_matches"], True)

    def test_requesting_the_other_environment_fails_despite_the_shared_executable(self) -> None:
        states = self._states(self.other)
        check = states["requested-interpreter"]
        self.assertEqual(check["state"], preflight._FAIL)
        self.assertIs(check["prefix_matches"], False)
        self.assertEqual(check["requested_prefix"], str(self.root / "other-venv"))
        self.assertIn("different environment", check["detail"])
        self.assertEqual(states["parent-interpreter"]["state"], preflight._PASS)

    def test_a_requested_path_that_does_not_exist_is_not_a_selection(self) -> None:
        check = self._states(self.root / "absent" / "bin" / "python")["requested-interpreter"]
        self.assertEqual(check["state"], preflight._FAIL)
        self.assertEqual(check["requested_state"], "unavailable")


class EnvironmentRootTest(unittest.TestCase):
    """A redirecting root is refused rather than silently followed."""

    def setUp(self) -> None:
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory(prefix="campaign-root-"))).resolve()
        self.repository = self.root / "checkout"
        make_repository(self.repository)

    def _redirect(self, path: Path, destination: Path) -> bool:
        try:
            os.symlink(destination, path, target_is_directory=True)
            return True
        except (OSError, NotImplementedError):
            pass
        if os.name == "nt":
            completed = subprocess.run(["cmd", "/c", "mklink", "/J", str(path), str(destination)],
                                       capture_output=True, text=True)
            return completed.returncode == 0
        return False

    def test_a_redirected_root_is_refused(self) -> None:
        elsewhere = self.root / "elsewhere"
        elsewhere.mkdir()
        redirect = self.root / "redirected-envs"
        if not self._redirect(redirect, elsewhere):
            self.skipTest("this host cannot create a directory redirect")
        with self.assertRaises(environment.CampaignEnvironmentError) as caught:
            environment.provision(self.repository, "campaign", root=redirect)
        self.assertEqual(caught.exception.code, "redirected-environment-root")
        self.assertEqual(list(elsewhere.iterdir()), [])

    def test_a_redirect_inside_the_checkout_is_refused_for_the_default_root(self) -> None:
        elsewhere = self.root / "elsewhere"
        elsewhere.mkdir()
        if not self._redirect(self.repository / "local-results", elsewhere):
            self.skipTest("this host cannot create a directory redirect")
        with self.assertRaises(environment.CampaignEnvironmentError) as caught:
            environment.provision(self.repository, "campaign")
        self.assertEqual(caught.exception.code, "redirected-environment-root")
        self.assertEqual(list(elsewhere.iterdir()), [])

    def test_a_plain_root_is_accepted_before_the_provision_runs(self) -> None:
        with self.assertRaises(environment.CampaignEnvironmentError) as caught:
            # No Git checkout package, so the provision stops after the root check.
            environment.provision(self.root / "plain-checkout", "campaign",
                                  root=self.root / "envs")
        self.assertEqual(caught.exception.code, "source-identity-not-established")


class ProvisioningLockTest(unittest.TestCase):
    """One provision per campaign at a time."""

    def setUp(self) -> None:
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory(prefix="campaign-lock-"))).resolve()
        self.repository = self.root / "checkout"
        make_repository(self.repository)
        self.target = environment.layout(self.repository, "campaign", root=self.root / "envs")

    def test_a_held_lock_refuses_a_second_provision(self) -> None:
        Path(str(self.target["root"])).mkdir(parents=True)
        Path(str(self.target["lock"])).write_text("pid=0\n", encoding="utf-8")
        with self.assertRaises(environment.CampaignEnvironmentError) as caught:
            environment.provision(self.repository, "campaign", root=self.root / "envs")
        self.assertEqual(caught.exception.code, "provisioning-in-progress")

    def test_the_lock_is_held_while_the_target_is_examined_and_released_afterwards(self) -> None:
        observed: dict[str, str] = {}
        real = environment.classify_target

        def spy(target, campaign, checkout, package):
            observed["lock"] = environment.path_kind(target["lock"])
            return real(target, campaign, checkout, package)

        plain = self.root / "not-a-repository"
        plain.mkdir()
        with mock.patch.object(environment, "classify_target", side_effect=spy):
            with self.assertRaises(environment.CampaignEnvironmentError) as caught:
                environment.provision(plain, "campaign", root=self.root / "envs")
        self.assertEqual(caught.exception.code, "source-identity-not-established")
        self.assertEqual(observed["lock"], "file")
        self.assertEqual(environment.path_kind(self.target["lock"]), "absent")


class ReplacementRecoveryTest(unittest.TestCase):
    """The previous installation survives until the new receipt is durable."""

    def setUp(self) -> None:
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory(prefix="campaign-recovery-"))).resolve()
        self.repository = self.root / "checkout"
        package = write_package(self.repository, "recovery-checkout")
        self.revision = make_repository(self.repository)
        self.target = environment.layout(self.repository, "recovery", root=self.root / "envs")
        self.digests = identity.package_digests(package)
        self._declare_owned()

    def _declare_owned(self) -> None:
        directory = Path(str(self.target["directory"]))
        directory.mkdir(parents=True, exist_ok=True)
        venue = Path(str(self.target["venv"]))
        Path(str(self.target["interpreter"])).parent.mkdir(parents=True, exist_ok=True)
        Path(str(self.target["interpreter"])).write_text("", encoding="utf-8")
        (venue / "installed-marker.txt").write_text("previous\n", encoding="utf-8")
        (venue / "pyvenv.cfg").write_text("home = synthetic\n", encoding="utf-8")
        receipts.write(str(self.target["record"]),
                       make_record(self.repository, self.target, campaign="recovery",
                                   python_digest=self.digests["python_digest"],
                                   tree_digest=self.digests["tree_digest"], revision=self.revision,
                                   prefix=str(self.target["venv"]),
                                   executable_sha256="a" * 64))

    @contextlib.contextmanager
    def _patches(self, *, verify=None, write=None):
        def fake_create(_bootstrap, venue, **_kwargs):
            Path(venue).mkdir(parents=True)
            return {"argv": [], "exit_status": 0}

        def fake_site(interpreter):
            return str(Path(interpreter).parent.parent / "Lib" / "site-packages")

        stacked = [
            mock.patch.object(environment, "create_venv", side_effect=fake_create),
            mock.patch.object(environment, "site_packages", side_effect=fake_site),
            mock.patch.object(environment, "install_source",
                              return_value={"attempts": [], "install_mode": "offline",
                                            "installed": True, "index_access": False,
                                            "build_isolation_explicitly_enabled": False}),
            mock.patch.object(environment.launch, "probe",
                              return_value={"report_parsed": True, "exit_status": 0,
                                            "report": {"package": {
                                                "state": "imported",
                                                "python_digest": self.digests["python_digest"]},
                                                "isolated": True}}),
            mock.patch.object(environment, "_verify",
                              side_effect=verify or (lambda *a, **k: ({}, {"state": "imported"}, [],
                                                                     str(self.target["venv"])))),
            mock.patch.object(environment.receipts, "write",
                              side_effect=write if write is not None else receipts.write),
        ]
        with contextlib.ExitStack() as stack:
            for patcher in stacked:
                stack.enter_context(patcher)
            yield

    def test_a_successful_replacement_removes_the_retired_environment(self) -> None:
        with self._patches() as _:
            record = environment.provision(self.repository, "recovery", root=self.root / "envs",
                                           package="isolation_probe", replace=True)
        venue = Path(str(self.target["venv"]))
        self.assertEqual(record["verdict"], "qualified")
        self.assertFalse((venue / "installed-marker.txt").is_file())
        self.assertEqual(record["ownership"]["mode"], "replaced-owned")
        self.assertIs(record["ownership"]["retired_removed"], True)
        self.assertFalse(Path(str(record["ownership"]["retired_path"])).exists())

    def test_a_failed_receipt_write_restores_the_previous_environment(self) -> None:
        before = receipts.file_digest(str(self.target["record"]))
        with self._patches(write=OSError("synthetic write failure")):
            with self.assertRaises(environment.CampaignEnvironmentError) as caught:
                environment.provision(self.repository, "recovery", root=self.root / "envs",
                                      package="isolation_probe", replace=True)
        self.assertEqual(caught.exception.code, "receipt-write-failed")
        venue = Path(str(self.target["venv"]))
        self.assertTrue((venue / "installed-marker.txt").is_file())
        self.assertEqual(receipts.file_digest(str(self.target["record"])), before)
        self.assertEqual([path.name for path in Path(str(self.target["root"])).iterdir()
                          if path.name.startswith(".failed-")], [])

    def test_a_failed_final_verification_restores_the_previous_environment(self) -> None:
        before = receipts.file_digest(str(self.target["record"]))
        failure = environment.CampaignEnvironmentError("verification-failed", "synthetic")

        def verify(*_args, **_kwargs):
            raise failure

        with self._patches(verify=verify):
            with self.assertRaises(environment.CampaignEnvironmentError) as caught:
                environment.provision(self.repository, "recovery", root=self.root / "envs",
                                      package="isolation_probe", replace=True)
        self.assertEqual(caught.exception.code, "verification-failed")
        self.assertTrue((Path(str(self.target["venv"])) / "installed-marker.txt").is_file())
        self.assertEqual(receipts.file_digest(str(self.target["record"])), before)

    def test_an_uncertain_recovery_is_reported_and_keeps_the_retired_data(self) -> None:
        with self._patches(write=OSError("synthetic write failure")):
            with mock.patch.object(environment, "_restore_previous",
                                   return_value={"state": "uncertain", "reason": "synthetic",
                                                 "retired_path": str(self.root / ".retired-synthetic")}):
                with self.assertRaises(environment.CampaignEnvironmentError) as caught:
                    environment.provision(self.repository, "recovery", root=self.root / "envs",
                                          package="isolation_probe", replace=True)
        self.assertEqual(caught.exception.code, "replacement-recovery-uncertain")
        detail = json.loads(caught.exception.detail)
        self.assertIn("retired_path", detail)
        self.assertEqual(detail["error"], "receipt-write-failed")
        retired = [path for path in Path(str(self.target["root"])).iterdir()
                   if path.name.startswith(".retired-")]
        self.assertEqual(len(retired), 1)
        self.assertTrue((retired[0] / "installed-marker.txt").is_file())

    def test_a_failed_fresh_provision_leaves_no_environment_behind(self) -> None:
        with self._patches(write=OSError("synthetic write failure")):
            with self.assertRaises(environment.CampaignEnvironmentError) as caught:
                environment.provision(self.repository, "recovery", root=self.root / "fresh-envs",
                                      package="isolation_probe")
        self.assertEqual(caught.exception.code, "receipt-write-failed")
        self.assertEqual(environment.path_kind(
            environment.layout(self.repository, "recovery", root=self.root / "fresh-envs")["directory"]),
            "absent")


class BootstrapInvocationTest(unittest.TestCase):
    """A bootstrap virtual environment is named, not resolved."""

    def setUp(self) -> None:
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory(prefix="campaign-bootstrap-"))).resolve()
        self.repository = self.root / "checkout"
        package = write_package(self.repository, "bootstrap-checkout")
        self.revision = make_repository(self.repository)
        self.digests = identity.package_digests(package)
        self.bootstrap_venv = self.root / "bootstrap-venv"
        self.bootstrap = make_environment(self.bootstrap_venv, symlinks=True)

    def test_the_recorded_bootstrap_keeps_its_invocation_path_and_prefix(self) -> None:
        target = environment.layout(self.repository, "campaign", root=self.root / "envs")

        def fake_create(_bootstrap, venue, **_kwargs):
            Path(venue).mkdir(parents=True)
            return {"argv": [], "exit_status": 0}

        def fake_site(interpreter):
            return str(Path(interpreter).parent.parent / "Lib" / "site-packages")

        with mock.patch.object(environment, "create_venv", side_effect=fake_create), \
                mock.patch.object(environment, "site_packages", side_effect=fake_site), \
                mock.patch.object(environment, "install_source",
                                  return_value={"attempts": [], "install_mode": "offline",
                                                "installed": True, "index_access": False,
                                                "build_isolation_explicitly_enabled": False}), \
                mock.patch.object(environment.launch, "probe",
                                  return_value={"report_parsed": True, "exit_status": 0,
                                                "report": {"package": {
                                                    "state": "imported",
                                                    "python_digest": self.digests["python_digest"]},
                                                    "isolated": True}}), \
                mock.patch.object(environment, "_verify",
                                  return_value=({}, {"state": "imported"}, [],
                                                str(target["venv"]))):
            record = environment.provision(self.repository, "campaign",
                                           root=self.root / "envs", python=self.bootstrap,
                                           package="isolation_probe")
        self.assertEqual(record["bootstrap_interpreter"], os.path.abspath(str(self.bootstrap)))
        self.assertEqual(record["bootstrap_identity"]["prefix"], str(self.bootstrap_venv))
        self.assertIs(record["bootstrap_identity"]["virtual_environment"], True)
        if os.name != "nt":
            # On POSIX the venv interpreter is a link to the base interpreter; the
            # record keeps the link, not the base path it would resolve to.
            self.assertEqual(os.path.realpath(record["bootstrap_interpreter"]),
                             os.path.realpath(sys.executable))
            self.assertNotEqual(record["bootstrap_interpreter"],
                                os.path.realpath(record["bootstrap_interpreter"]))


class RecordBindingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory(prefix="campaign-binding-"))).resolve()
        self.repository = self.root / "checkout"
        make_repository(self.repository)
        self.target = environment.layout(self.repository, "campaign", root=self.root / "envs")
        self.record = make_record(self.repository, self.target)

    def _problems(self) -> "list[str]":
        return environment.record_problems(self.record, campaign="campaign",
                                           checkout=self.repository, package="isolation_probe",
                                           target=self.target)

    def test_a_matching_record_has_no_problems(self) -> None:
        self.assertEqual(self._problems(), [])

    def test_schema_kind_campaign_checkout_package_and_layout_are_all_bound(self) -> None:
        cases = {
            "record-schema": {"schema_version": 2},
            "record-kind": {"kind": "something-else"},
            "record-campaign": {"campaign": "another-campaign"},
            "record-checkout": {"checkout": str(self.root / "other-checkout")},
            "record-package": {"package": "other_package"},
            "record-venv": {"venv": str(self.root / "elsewhere")},
            "record-interpreter": {"interpreter": str(self.root / "elsewhere" / "python.exe")},
            "record-site-packages": {"site_packages": str(self.root / "elsewhere" / "site-packages")},
        }
        for expected, change in cases.items():
            with self.subTest(problem=expected):
                record = dict(self.record) | change
                problems = environment.record_problems(record, campaign="campaign",
                                                       checkout=self.repository,
                                                       package="isolation_probe", target=self.target)
                self.assertIn(expected, problems)

    def test_a_non_object_record_is_refused(self) -> None:
        self.assertEqual(environment.record_problems([], campaign="campaign", checkout=self.repository,
                                                     package="isolation_probe", target=self.target),
                         ["record-not-an-object"])


class InstallationBoundaryTest(unittest.TestCase):
    """Build isolation is network-capable and therefore opt-in."""

    def setUp(self) -> None:
        self.calls: "list[list[str]]" = []

    def _fake_run(self, argv, **kwargs):
        self.calls.append(list(argv))
        failing = "--no-index" in argv
        return {"argv": list(argv), "exit_status": 2 if failing else 0, "stdout": "",
                "stderr": "synthetic failure" if failing else "", "failure": None,
                "timeout_seconds": kwargs.get("timeout"), "elapsed_seconds": 0.0,
                "started_utc": "", "finish_utc": "", "stdout_sha256": "", "stderr_sha256": ""}

    def test_offline_is_the_default_and_failure_is_final(self) -> None:
        with mock.patch.object(environment.launch, "run", side_effect=self._fake_run):
            result = environment.install_source("python.exe", "checkout", "target")
        self.assertFalse(result["installed"])
        self.assertEqual(len(self.calls), 1)
        self.assertIn("--no-build-isolation", self.calls[0])
        self.assertNotIn("build-isolation", [attempt["install_mode"] for attempt in result["attempts"]])
        self.assertFalse(result["build_isolation_explicitly_enabled"])

    def test_offline_mode_cannot_reach_a_package_index(self) -> None:
        with mock.patch.object(environment.launch, "run", side_effect=self._fake_run):
            result = environment.install_source("python.exe", "checkout", "target")
        argv = self.calls[0]
        self.assertIn("--no-index", argv)
        self.assertEqual(result["attempts"][0]["install_mode"], "offline")
        self.assertIs(result["attempts"][0]["index_access"], False)
        self.assertIs(result["index_access"], False)
        self.assertIsNone(result["install_mode"])

    def test_only_the_explicit_opt_in_may_use_an_index(self) -> None:
        with mock.patch.object(environment.launch, "run", side_effect=self._fake_run):
            result = environment.install_source("python.exe", "checkout", "target",
                                               allow_build_isolation=True)
        self.assertNotIn("--no-index", self.calls[1])
        self.assertIs(result["index_access"], True)
        self.assertEqual([entry["install_mode"] for entry in result["attempts"]],
                         ["offline", "build-isolation"])

    def test_build_isolation_is_used_only_when_explicitly_enabled(self) -> None:
        with mock.patch.object(environment.launch, "run", side_effect=self._fake_run):
            result = environment.install_source("python.exe", "checkout", "target",
                                                allow_build_isolation=True)
        self.assertTrue(result["installed"])
        self.assertEqual([attempt["install_mode"] for attempt in result["attempts"]],
                         ["offline", "build-isolation"])
        self.assertNotIn("--no-build-isolation", self.calls[1])
        self.assertTrue(result["build_isolation_explicitly_enabled"])

    def test_installation_arguments_are_fixed_and_never_a_shell(self) -> None:
        with mock.patch.object(environment.launch, "run", side_effect=self._fake_run):
            environment.install_source("python.exe", "checkout", "target",
                                       allow_build_isolation=True)
        argv = self.calls[0]
        self.assertEqual(argv[:4], ["python.exe", "-m", "pip", "install"])
        self.assertIn("--no-deps", argv)
        self.assertEqual(argv[-1], "checkout")


class SourceDriftTest(unittest.TestCase):
    @unittest.skipIf(identity.shutil.which("git") is None, "Git is required for the laboratory repository")
    def test_provisioning_evidence_distinguishes_drift_from_unavailable(self) -> None:
        root = Path(self.enterContext(tempfile.TemporaryDirectory(prefix="campaign-drift-")))
        repository = root / "checkout"
        revision = make_repository(repository)
        before = identity.source_identity(repository)
        digests_before = identity.package_digests(write_package(repository, "one"))
        same = identity.source_identity(repository)
        digests_same = identity.package_digests(repository / "src" / "isolation_probe")
        self.assertIs(environment.source_drift(before, same, digests_before, digests_same), False)
        (repository / "src" / "isolation_probe" / "__init__.py").write_text('MARKER = "two"\n',
                                                                           encoding="utf-8")
        edited = identity.source_identity(repository)
        digests_edited = identity.package_digests(repository / "src" / "isolation_probe")
        self.assertIs(environment.source_drift(before, edited, digests_before, digests_edited), True)
        git(repository, "add", "--", ".")
        git(repository, "commit", "-q", "-m", "synthetic drift commit")
        committed = identity.source_identity(repository)
        self.assertNotEqual(committed["revision"], revision)
        self.assertIs(environment.source_drift(before, committed, digests_before,
                                              identity.package_digests(repository / "src" / "isolation_probe")),
                      True)
        unreadable = dict(before) | {"state": "not-a-repository", "revision": None}
        self.assertIsNone(environment.source_drift(before, unreadable, digests_before, digests_edited))
        self.assertIsNone(environment.source_drift(before, same, {}, digests_same))


class PreflightTest(unittest.TestCase):
    """The parent in these tests is the test process, so its package is importable."""

    def setUp(self) -> None:
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory(prefix="campaign-preflight-"))).resolve()
        self.repository = self.root / "checkout"
        package = write_package(self.repository, "checkout-a")
        make_repository(self.repository)
        self.digests = identity.package_digests(package)
        # Resolve the synthetic package from outside its would-be installation
        # directory: that location difference is what the digest must survive.
        sys.path.insert(0, str(package.parent))
        self.addCleanup(sys.path.remove, str(package.parent))
        self.addCleanup(_forget_package, "isolation_probe")
        self.parent_package = identity.import_identity("isolation_probe")
        self.target = environment.layout(self.repository, "campaign", root=self.root / "envs")
        Path(str(self.target["record"])).parent.mkdir(parents=True)
        self.record = make_record(self.repository, self.target,
                                  python_digest=self.parent_package["python_digest"],
                                  tree_digest=self.digests["tree_digest"],
                                  revision=identity.source_identity(self.repository)["revision"])
        receipts.write(str(self.target["record"]), self.record)

    def _preflight(self, **kwargs):
        return preflight.preflight(self.repository, campaign="campaign", root=self.root / "envs",
                                   package="isolation_probe", **kwargs)

    def _states(self, receipt) -> "dict[str, dict]":
        return {entry["check"]: entry for entry in receipt["checks"]}

    def test_without_an_environment_the_verdict_is_unknown(self) -> None:
        other = self.root / "unprovisioned"
        other.mkdir()
        described = preflight.preflight(other, campaign="absent")
        self.assertEqual(described["verdict"], preflight.UNKNOWN)
        self.assertFalse(described["measurement_allowed"])
        self.assertEqual(described["reasons"], ["environment-not-provisioned"])
        self.assertEqual(preflight.exit_code(described["verdict"]), 2)

    def test_a_request_cannot_rescue_a_shared_parent(self) -> None:
        described = self._preflight(interpreter=self.target["interpreter"])
        states = self._states(described)
        # The request is recorded, and it is not evidence about the parent.
        self.assertTrue(described["requested_interpreter"]["supplied"])
        self.assertEqual(states["parent-interpreter"]["state"], preflight._FAIL)
        self.assertEqual(states["parent-interpreter"]["parent_prefix"], sys.prefix)
        self.assertNotEqual(states["parent-interpreter"]["expected_prefix"], sys.prefix)
        # A requested interpreter that cannot be described is not a selection
        # either: the check proves the interpreter, it does not accept the name.
        self.assertEqual(states["requested-interpreter"]["state"], preflight._FAIL)
        self.assertEqual(states["requested-interpreter"]["requested_state"], "unavailable")
        self.assertFalse(described["measurement_allowed"])
        self.assertIn("parent-interpreter", described["reasons"])

    def test_a_requested_interpreter_that_differs_from_the_record_is_refused(self) -> None:
        described = self._preflight(interpreter=self.root / "elsewhere" / "python.exe")
        states = self._states(described)
        self.assertEqual(states["requested-interpreter"]["state"], preflight._FAIL)
        self.assertEqual(states["parent-interpreter"]["state"], preflight._FAIL)
        self.assertIn("requested-interpreter", described["reasons"])

    def test_package_content_matches_even_outside_the_installation_directory(self) -> None:
        described = self._preflight()
        parent = self._states(described)["parent-package"]
        # The parent resolves the package from the checkout, not from the recorded
        # site-packages: the positive content match is what makes it evidence.
        self.assertIs(parent["inside_campaign_environment"], False)
        self.assertIs(parent["same_code"], True)
        self.assertEqual(parent["state"], preflight._PASS)

    def test_being_inside_the_installation_directory_is_not_enough(self) -> None:
        mismatched = make_record(self.repository, self.target, python_digest="f" * 64,
                                 tree_digest=self.digests["tree_digest"],
                                 revision=self.record["source_before"]["revision"])
        receipts.write(str(self.target["record"]), mismatched)
        described = self._preflight()
        parent = self._states(described)["parent-package"]
        self.assertEqual(parent["state"], preflight._FAIL)
        self.assertIs(parent["same_code"], False)
        self.assertIn("content", parent["detail"])
        self.assertIn("parent-package", described["reasons"])

    def test_stale_source_content_and_revision_are_reported(self) -> None:
        (self.repository / "src" / "isolation_probe" / "__init__.py").write_text(
            'MARKER = "checkout-b"\n', encoding="utf-8")
        states = self._states(self._preflight())
        self.assertEqual(states["source-content"]["state"], preflight._FAIL)
        self.assertIn("stale", states["source-content"]["detail"])
        self.assertEqual(states["source-revision"]["state"], preflight._PASS)
        git(self.repository, "add", "--", ".")
        git(self.repository, "commit", "-q", "-m", "synthetic drift commit")
        described = self._preflight()
        self.assertEqual(described["verdict"], preflight.UNQUALIFIED)
        self.assertIn("source-revision", described["reasons"])
        self.assertIn("source-content", described["reasons"])

    def test_an_enclosing_repository_is_refused_as_a_checkout(self) -> None:
        nested = self.repository / "nested"
        nested.mkdir()
        (nested / "src" / "isolation_probe").mkdir(parents=True)
        (nested / "src" / "isolation_probe" / "__init__.py").write_text("", encoding="utf-8")
        target = environment.layout(nested, "nested-campaign", root=self.root / "envs")
        Path(str(target["record"])).parent.mkdir(parents=True)
        digests = identity.package_digests(nested / "src" / "isolation_probe")
        receipts.write(str(target["record"]),
                       make_record(nested, target, campaign="nested-campaign",
                                   python_digest=digests["python_digest"],
                                   tree_digest=digests["tree_digest"]))
        described = preflight.preflight(nested, campaign="nested-campaign", root=self.root / "envs",
                                        package="isolation_probe")
        states = self._states(described)
        self.assertEqual(states["checkout-root"]["state"], preflight._FAIL)
        self.assertEqual(states["checkout-root"]["source_state"], "enclosing-repository")
        self.assertNotEqual(described["verdict"], preflight.QUALIFIED)

    def test_an_unbound_record_is_refused_before_any_other_check(self) -> None:
        receipts.write(str(self.target["record"]), self.record | {"campaign": "another-campaign"})
        described = self._preflight()
        self.assertEqual(described["verdict"], preflight.UNQUALIFIED)
        self.assertEqual(described["reasons"], ["environment-record"])
        self.assertEqual([entry["check"] for entry in described["checks"]], ["environment-record"])
        self.assertIn("record-campaign", described["checks"][0]["problems"])

    def test_exit_codes_map_to_verdicts(self) -> None:
        self.assertEqual(preflight.exit_code("qualified"), 0)
        self.assertEqual(preflight.exit_code("unqualified"), 1)
        self.assertEqual(preflight.exit_code("unknown"), 2)
        self.assertEqual(preflight.exit_code("anything-else"), 2)


PREFLIGHT_SCRIPT = """
import json
import sys

from deskmate_formats.campaign_env import preflight

receipt = preflight.preflight(sys.argv[1], campaign=sys.argv[2], root=sys.argv[3],
                              package="isolation_probe")
print(json.dumps(receipt))
"""


class QualifiedPreflightTest(unittest.TestCase):
    """A real parent, a real isolated child and a bound record, end to end.

    The parent here is the campaign interpreter itself, launched as a
    subprocess: that is the only way to exercise the parent-identity check
    honestly, because the test runner is always in some other environment.
    """

    def setUp(self) -> None:
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory(prefix="campaign-qualified-"))).resolve()
        self.repository = self.root / "checkout"
        package = write_package(self.repository, "checkout-qualified")
        self.revision = make_repository(self.repository)
        self.target = environment.layout(self.repository, "campaign", root=self.root / "envs")
        self.interpreter = make_environment(Path(str(self.target["venv"])))
        self.site = environment.site_packages(self.interpreter)
        (Path(self.site) / "isolation_probe.pth").write_text(
            str(package.parent), encoding="utf-8")
        project_source = Path(__file__).resolve().parents[2] / "src"
        (Path(self.site) / "deskmate_formats.pth").write_text(
            str(project_source), encoding="utf-8")
        digests = identity.package_digests(package)
        self.record = make_record(self.repository, self.target, package="isolation_probe",
                                  python_digest=digests["python_digest"],
                                  tree_digest=digests["tree_digest"], revision=self.revision,
                                  executable_sha256=identity.file_digest(self.interpreter))
        self.record["site_packages"] = self.site
        receipts.write(str(self.target["record"]), self.record)

    def _run(self) -> dict:
        variables = dict(os.environ) | {"PYTHONDONTWRITEBYTECODE": "1"}
        variables.pop("PYTHONPATH", None)
        completed = subprocess.run(
            [str(self.interpreter), "-c", PREFLIGHT_SCRIPT, str(self.repository), "campaign",
             str(self.target["root"])],
            cwd=str(self.root), capture_output=True, text=True, env=variables, timeout=300)
        self.assertEqual(completed.returncode, 0, completed.stderr[-1200:])
        return json.loads(completed.stdout)

    def test_a_bound_record_with_a_real_parent_and_child_qualifies(self) -> None:
        described = self._run()
        states = {entry["check"]: entry for entry in described["checks"]}
        self.assertEqual(sorted(states), sorted(preflight.CHECKS))
        for name, entry in states.items():
            with self.subTest(check=name):
                self.assertEqual(entry["state"], preflight._PASS, entry)
        self.assertEqual(described["verdict"], preflight.QUALIFIED)
        self.assertTrue(described["measurement_allowed"])
        self.assertEqual(described["reasons"], [])
        self.assertEqual(described["reasons"], [])
        self.assertEqual(states["parent-interpreter"]["parent_prefix"], str(self.target["venv"]))
        self.assertEqual(states["observed-origin"]["inside_campaign_environment"], False)
        self.assertIs(states["observed-origin"]["same_code"], True)
        self.assertTrue(described["child"]["report"]["isolated"])

    def test_unavailable_git_metadata_is_unknown_not_qualified(self) -> None:
        hidden = self.repository / ".git-hidden"
        (self.repository / ".git").rename(hidden)
        try:
            described = self._run()
            states = {entry["check"]: entry for entry in described["checks"]}
            self.assertEqual(states["checkout-root"]["state"], preflight._UNKNOWN)
            self.assertEqual(states["source-revision"]["state"], preflight._UNKNOWN)
            self.assertEqual(states["child-isolation"]["state"], preflight._PASS)
            self.assertEqual(described["verdict"], preflight.UNKNOWN)
            self.assertFalse(described["measurement_allowed"])
            self.assertEqual(preflight.exit_code(described["verdict"]), 2)
        finally:
            hidden.rename(self.repository / ".git")

    def test_drifted_package_content_and_a_moved_head_unqualify_the_measurement(self) -> None:
        source = self.repository / "src" / "isolation_probe" / "__init__.py"
        source.write_text('MARKER = "moved-after-provisioning"\n', encoding="utf-8")
        described = self._run()
        states = {entry["check"]: entry for entry in described["checks"]}
        self.assertEqual(states["source-revision"]["state"], preflight._PASS)
        self.assertEqual(states["source-content"]["state"], preflight._FAIL)
        self.assertEqual(states["observed-content"]["state"], preflight._FAIL)
        self.assertEqual(described["verdict"], preflight.UNQUALIFIED)
        # Editing the source changes what the editable link resolves to, so the
        # mismatch is caught in the parent and the child as well as on disk.
        self.assertEqual(described["reasons"],
                         ["parent-package", "source-content", "observed-origin", "observed-content"])
        git(self.repository, "add", "--", ".")
        git(self.repository, "commit", "-q", "-m", "synthetic post-provisioning commit")
        described = self._run()
        states = {entry["check"]: entry for entry in described["checks"]}
        self.assertEqual(states["source-revision"]["state"], preflight._FAIL)
        self.assertIn("source-revision", described["reasons"])
        self.assertEqual(described["verdict"], preflight.UNQUALIFIED)


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

    def test_identity_command_reports_source_state_and_both_interpreters(self) -> None:
        root = Path(self.enterContext(tempfile.TemporaryDirectory(prefix="campaign-cli-identity-")))
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            self.assertEqual(cli.main(["identity", "--checkout", str(root)]), 0)
        document = json.loads(buffer.getvalue())
        self.assertIn(document["source"]["state"], {"not-a-repository", "git-unavailable", "missing"})
        self.assertIsNone(document["source"]["revision"])
        self.assertEqual(document["parent_interpreter"]["prefix"], sys.prefix)
        self.assertIsNone(document["requested_interpreter"])

    def test_provision_failure_reports_a_publishable_code(self) -> None:
        root = Path(self.enterContext(tempfile.TemporaryDirectory(prefix="campaign-cli-provision-")))
        checkout = root / "checkout"
        make_repository(checkout)
        (Path(str(environment.layout(checkout, "campaign", root=root / "envs")["directory"]))).mkdir(parents=True)
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            status = cli.main(["provision", "--checkout", str(checkout), "--campaign", "campaign",
                               "--root", str(root / "envs")])
        self.assertEqual(status, 1)
        document = json.loads(buffer.getvalue())
        self.assertEqual(document["reason"], "existing-directory-without-valid-record")
        self.assertEqual(document["verdict"], "failed")


def _forget_package(name: str) -> None:
    for module in [key for key in sys.modules if key == name or key.startswith(name + ".")]:
        del sys.modules[module]


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
