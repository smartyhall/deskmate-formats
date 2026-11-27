"""Portable tests for the performance qualification harness itself.

The comparison tests build reports directly instead of timing real runs: a
comparison rule must be pinned by its inputs, not by whatever the host happened
to measure while the test ran.
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from deskmate_formats.perf import cli, hostload, microbench, report, sanitize
from deskmate_formats.perf.runner import SubprocessTracer, _source_revision, run_suite

import perf_harness_cases as cases


def _run(case_types, *, trace=None, trace_git=False, interval=60.0):
    trace = bool(trace if trace is not None else trace_git)
    loader = unittest.TestLoader()
    suite = unittest.TestSuite(loader.loadTestsFromTestCase(case) for case in case_types)
    return run_suite(suite, label="harness", profile="test", trace_processes=trace,
                     trace_git_commands=trace_git, sample_interval=interval,
                     verbosity=0, stream=io.StringIO())


def _record(identifier, seconds, *, outcome="success", iteration=0, message=""):
    return {
        "test_id": identifier,
        "module": identifier.rsplit(".", 2)[0] if identifier.count(".") > 2 else identifier,
        "case": "Case",
        "name": identifier.rsplit(".", 1)[-1],
        "outcome": outcome,
        "message": message,
        "wall_seconds": seconds,
        "cpu_seconds": 0.1,
        "setup_seconds": 0.0,
        "teardown_seconds": 0.0,
        "spawn_count": 0,
        "spawn_seconds": 0.0,
        "git_calls": 0,
        "git_spawn_seconds": 0.0,
        "git_run_seconds": 0.0,
        "python_spawns": 0,
        "git_commands": {},
        "iteration": iteration,
    }


def _report(tests, *, revision="a" * 40, digest="digest-1", dirty=False,
            python=("CPython", "3.13.17"), platform_name="Windows-10-10.0.19045-SP0",
            cpu=10.0, memory=3_000_000_000, interval=5.0, iterations=1, schema=2,
            wall=100.0, matches_source=True, trace=True, discovered=None,
            suite_errors=None):
    suite_errors = list(suite_errors or ())
    cpu_max = None if cpu is None else cpu + 5
    cpu_min = None if cpu is None else cpu - 5
    return {
        "schema_version": schema,
        "meta": {
            "profile": "portable",
            "label": "synthetic",
            "started_utc": "2026-01-01T00:00:00Z",
            "finished_utc": "2026-01-01T00:01:40Z",
            "wall_seconds": wall,
            "tests": len(tests),
            "outcomes": {},
            "trace_processes": trace,
            "trace_git_commands": False,
            "sample_tests": False,
            "sample_interval": interval,
            "iteration": 0,
            "iterations": iterations,
            "discovered_tests": len(tests) + len(suite_errors) if discovered is None else discovered,
            "source": {
                "revision": revision,
                "branch": "synthetic",
                "dirty": dirty,
                "worktree_digest": digest,
                "complete": revision is not None,
                "state": "stable" if revision is not None else "unknown",
            },
            "source_changed": revision is None,
            "package": {
                "name": "deskmate_formats",
                "version": "0.1.0.dev0",
                "distribution_version": "0.1.0.dev0",
                "origin": "<path>/src/deskmate_formats",
                "expected_origin": "<path>/src/deskmate_formats",
                "matches_source": matches_source,
                "source_on_path": True,
                "source_first": True,
                "modules": {"runner": "<path>/runner.py"},
            },
        },
        "environment": {
            "python_version": python[1],
            "python_implementation": python[0],
            "platform": platform_name,
            "cpu_count": 6,
        },
        "host": {
            "summary": {
                "samples": 20,
                "cpu_total_percent": {"mean": cpu, "median": cpu,
                                      "max": cpu_max, "min": cpu_min},
                "memory_available_bytes": {"mean": memory, "min": memory},
            },
            "sampling": {
                "interval": interval,
                "samples": 20,
                "expected_at_least": 20,
                "complete": True,
                "error": None,
            },
            "samples": [],
        },
        "tests": tests,
        "suite_errors": suite_errors,
    }


def _warnings(comparison):
    return " | ".join(comparison["warnings"])


class HostLoadTests(unittest.TestCase):
    def test_sampler_reports_identity_and_pressure(self):
        sampler = hostload.HostSampler()
        first = sampler.sample()
        self.assertRegex(first.at_utc, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
        self.assertGreater(first.process_count or 0, 0)
        if first.memory_total_bytes is not None:
            self.assertGreater(first.memory_total_bytes, 0)
            self.assertIsNotNone(first.memory_available_bytes)
            self.assertLessEqual(first.memory_available_bytes, first.memory_total_bytes)
        # A second sample may still have no CPU figure if the counters did not move.
        second = sampler.sample()
        if second.cpu_total_percent is not None:
            self.assertGreaterEqual(second.cpu_total_percent, 0.0)
            self.assertLessEqual(second.cpu_total_percent, 100.0)

    def test_windows_kernel_time_excludes_idle(self):
        # GetSystemTimes reports kernel time including idle. 80 idle, 90 kernel
        # (10 of it busy) and 10 user is 20% busy; summed naively it reads 55.6%.
        times = hostload._windows_times(80, 90, 10)
        sampler = hostload.HostSampler()
        sampler._previous = (0, 0, 0)
        self.assertEqual(sampler._deltas(times), (20.0, 10.0, 10.0))

    def test_a_backward_counter_makes_the_interval_unknown(self):
        sampler = hostload.HostSampler()
        sampler._previous = (100, 100, 100)
        self.assertEqual(sampler._deltas((50, 120, 120)), (None, None, None))
        # The new counters stay the baseline, so the next interval can be read.
        self.assertEqual(sampler._previous, (50, 120, 120))

    def test_each_timeline_owns_its_cpu_baseline(self):
        first = hostload.HostTimeline(interval=60.0)
        second = hostload.HostTimeline(interval=60.0)
        self.assertIsNot(first.sampler, second.sampler)

    def test_timeline_rejects_an_unusable_interval(self):
        for bad in (0, -1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                hostload.HostTimeline(interval=bad)

    def test_missing_process_memory_fields_stay_unknown(self):
        memory = hostload.ProcessMemory(working_set_bytes=None,
                                        peak_working_set_bytes=1024,
                                        private_bytes=None)
        self.assertEqual(memory.as_dict()["working_set_bytes"], None)
        self.assertEqual(memory.as_dict()["peak_working_set_bytes"], 1024)

    def test_summary_handles_missing_cpu(self):
        summary = hostload.summarize_samples([hostload.HostSample(at_utc="2026-01-01T00:00:00Z")])
        self.assertEqual(summary["samples"], 1)
        self.assertIsNone(summary["cpu_total_percent"]["mean"])
        self.assertIsNone(summary["memory_available_bytes"]["min"])

    def test_environment_describes_interpreter(self):
        environment = hostload.describe_environment()
        expected = ".".join(str(part) for part in sys.version_info[:3])
        self.assertEqual(environment["python_version"], expected)
        self.assertEqual(environment["python_executable"], sys.executable)
        self.assertGreater(environment["cpu_count"], 0)


class SourceIdentityTests(unittest.TestCase):
    def setUp(self):
        self.directory = Path(tempfile.mkdtemp(prefix="deskmate-source-identity-"))
        self.addCleanup(shutil.rmtree, self.directory, True)

    def _environment(self):
        env = {key: value for key, value in os.environ.items()
               if not key.upper().startswith("GIT_")}
        env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                   GIT_AUTHOR_NAME="Synthetic", GIT_AUTHOR_EMAIL="source@example.invalid",
                   GIT_COMMITTER_NAME="Synthetic", GIT_COMMITTER_EMAIL="source@example.invalid")
        return env

    def _git(self, *arguments):
        return subprocess.run(["git", *arguments], cwd=self.directory, check=True,
                              env=self._environment(), capture_output=True)

    def test_absent_repository_is_unknown_not_clean(self):
        info = _source_revision(self.directory)
        self.assertFalse(info["complete"])
        self.assertIsNone(info["revision"])
        # "clean" and "not a repository" must not look the same.
        self.assertIsNone(info["dirty"])
        self.assertIsNone(info["worktree_digest"])
        self.assertTrue(info["failed_commands"])
        for failure in info["failed_commands"]:
            self.assertNotIn("stderr", failure)

    def test_digest_pins_the_uncommitted_change(self):
        if shutil.which("git") is None:
            self.skipTest("git is not available")
        self._git("init", "-q", "-b", "main")
        (self.directory / "file.txt").write_text("one\n", encoding="utf-8")
        self._git("add", "file.txt")
        self._git("commit", "-q", "-m", "one")
        clean = _source_revision(self.directory)
        self.assertTrue(clean["complete"])
        self.assertFalse(clean["dirty"])
        self.assertRegex(clean["worktree_digest"], r"^[0-9a-f]{64}$")
        (self.directory / "file.txt").write_text("two\n", encoding="utf-8")
        dirty = _source_revision(self.directory)
        self.assertTrue(dirty["dirty"])
        self.assertTrue(dirty["complete"])
        self.assertNotEqual(clean["worktree_digest"], dirty["worktree_digest"])


class RunnerTests(unittest.TestCase):
    def test_records_identity_outcome_and_fixture_time(self):
        result = _run([cases.FastCase, cases.SlowCase])
        self.assertTrue(result.successful)
        records = {record.name: record for record in result.records}
        self.assertEqual(records["test_immediate"].outcome, "success")
        slow = records["test_deliberate_delay"]
        self.assertGreaterEqual(slow.wall_seconds, 0.2)
        self.assertGreaterEqual(slow.setup_seconds, 0.04)
        self.assertGreaterEqual(slow.teardown_seconds, 0.04)
        self.assertEqual(slow.module, "perf_harness_cases")
        self.assertEqual(slow.case, "SlowCase")
        self.assertGreaterEqual(result.wall_seconds, slow.wall_seconds)

    def test_failure_is_recorded_without_changing_semantics(self):
        result = _run([cases.FailureCase])
        self.assertFalse(result.successful)
        record = result.records[0]
        self.assertEqual(record.outcome, "failure")
        self.assertIn("synthetic failure", record.message)

    def test_failure_message_is_redacted_when_recorded(self):
        result = _run([cases.PathMessageCase])
        record = result.records[0]
        self.assertEqual(record.outcome, "failure")
        self.assertIn("<path>", record.message)
        self.assertNotIn("Users", record.message)
        self.assertNotIn("evidence.json", record.message)

    def test_subtest_outcomes_use_the_failure_exception(self):
        result = _run([cases.SubtestFailureCase, cases.SubtestErrorCase])
        outcomes = {record.case: record.outcome for record in result.records}
        self.assertEqual(outcomes["SubtestFailureCase"], "failure")
        self.assertEqual(outcomes["SubtestErrorCase"], "error")

    def test_class_level_error_is_kept_as_a_suite_issue(self):
        result = _run([cases.BrokenSetupCase])
        self.assertFalse(result.successful)
        self.assertEqual(result.records, [])
        self.assertEqual(len(result.suite_errors), 1)
        self.assertEqual(result.suite_errors[0]["outcome"], "error")
        self.assertIn("synthetic class fixture failure", result.suite_errors[0]["message"])
        self.assertEqual(result.meta["discovered_tests"], 2)

        summary = report.summarize(result.as_dict())
        self.assertEqual(summary["totals"]["suite_errors"], 1)
        self.assertEqual(summary["totals"]["failures"], 1)
        self.assertEqual(summary["failures"][0]["scope"], "suite")
        kinds = {issue["kind"] for issue in summary["integrity"]}
        self.assertIn("not-executed", kinds)

    def test_subprocess_tracing_counts_spawns(self):
        result = _run([cases.SpawnCase], trace=True)
        record = result.records[0]
        self.assertEqual(record.subprocess_calls, 1)
        self.assertGreaterEqual(record.spawn_count, 1)
        self.assertGreaterEqual(record.python_spawns, 1)
        self.assertGreater(record.spawn_max_seconds, 0.0)
        self.assertGreater(record.subprocess_seconds, 0.0)

    def test_untraced_runs_report_zero_spawns(self):
        result = _run([cases.SpawnCase], trace=False)
        self.assertEqual(result.records[0].spawn_count, 0)

    def test_git_subcommands_are_counted_when_sampled(self):
        result = _run([cases.GitCase], trace_git=True)
        record = result.records[0]
        self.assertEqual(record.git_commands.get("init"), 1)
        self.assertEqual(record.git_commands.get("rev-parse"), 1)
        self.assertEqual(sum(record.git_commands.values()), record.git_calls)

    def test_git_subcommands_are_not_sampled_by_default(self):
        result = _run([cases.GitCase], trace=True)
        record = result.records[0]
        self.assertGreaterEqual(record.git_calls, 2)
        self.assertEqual(record.git_commands, {})

    def test_git_creation_latency_is_separate_from_call_duration(self):
        result = _run([cases.GitCase], trace=True)
        record = result.records[0]
        self.assertGreater(record.git_spawn_seconds, 0.0)
        self.assertGreater(record.git_run_seconds, 0.0)
        # A call contains its own process creation, so the call sum cannot be
        # smaller than the creation sum.
        self.assertGreaterEqual(record.git_run_seconds + 1e-6, record.git_spawn_seconds)

    def test_git_subcommand_parsing_skips_global_options(self):
        from deskmate_formats.perf.runner import _git_subcommand
        self.assertEqual(_git_subcommand(["git", "-c", "core.autocrlf=false", "rev-parse", "HEAD"]),
                         "rev-parse")
        self.assertEqual(_git_subcommand("git log -1 --oneline"), "log")
        self.assertEqual(_git_subcommand([Path("git.exe"), "status"]), "status")
        self.assertEqual(_git_subcommand([Path("git"), "rev-parse"]).lower(), "rev-parse")
        self.assertEqual(_git_subcommand(["git"]), "unknown")

    def test_peak_working_set_delta_starts_from_the_peak(self):
        result = _run([cases.SlowCase])
        record = result.records[0]
        if record.working_set_peak_before is None or record.working_set_peak_after is None:
            self.skipTest("the host does not report process peak working set")
        self.assertEqual(
            record.peak_working_set_delta,
            max(0, record.working_set_peak_after - record.working_set_peak_before),
        )

    def test_run_records_before_and_after_identity(self):
        result = _run([cases.FastCase])
        self.assertIn("source_before", result.meta)
        self.assertIn("source_after", result.meta)
        self.assertEqual(result.meta["iterations"], 1)
        self.assertIn("matches_source", result.meta["package"])
        self.assertNotIn("working_directory", result.meta)
        self.assertNotIn("command", result.meta)

    def test_invalid_measurement_configuration_is_rejected(self):
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromTestCase(cases.FastCase)
        for bad in (0, -1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                run_suite(suite, sample_interval=bad, stream=io.StringIO())
        with self.assertRaises(ValueError):
            run_suite(suite, iteration=-1, stream=io.StringIO())

    def test_instrumented_runs_cannot_overlap(self):
        tracer = SubprocessTracer()
        tracer.install()
        try:
            suite = unittest.TestLoader().loadTestsFromTestCase(cases.FastCase)
            with self.assertRaises(RuntimeError):
                run_suite(suite, trace_processes=True, sample_interval=60.0,
                          stream=io.StringIO())
        finally:
            tracer.uninstall()
        # The hooks are restored, so a later run still works.
        self.assertTrue(_run([cases.FastCase]).successful)


class ReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = _run([cases.FastCase, cases.SlowCase, cases.FailureCase], trace=True)
        cls.payload = cls.result.as_dict()

    def test_ranking_puts_the_slowest_test_first(self):
        summary = report.summarize(self.payload)
        ranking = summary["ranking"]
        self.assertEqual(ranking[0]["test_id"],
                         "perf_harness_cases.SlowCase.test_deliberate_delay")
        durations = [entry["wall_seconds"] for entry in ranking]
        self.assertEqual(durations, sorted(durations, reverse=True))

    def test_pareto_and_totals_are_consistent(self):
        summary = report.summarize(self.payload)
        pareto = summary["pareto"]
        self.assertLessEqual(pareto["tests_for_target"], pareto["tests_total"])
        self.assertGreaterEqual(pareto["tests_for_target"], 1)
        totals = summary["totals"]
        self.assertEqual(totals["tests"], 3)
        self.assertEqual(totals["failures"], 1)
        self.assertLessEqual(totals["attributed_wall_seconds"], totals["suite_wall_seconds"] + 0.01)

    def test_modules_aggregate_tests(self):
        summary = report.summarize(self.payload)
        module = next(entry for entry in summary["modules"]
                      if entry["module"] == "perf_harness_cases")
        self.assertEqual(module["tests"], 3)
        self.assertEqual(module["failures"], 1)
        # A single module holds every test, so its share rounds to 100%.
        self.assertAlmostEqual(module["share_percent"], 100.0, delta=1.0)

    def test_markdown_mentions_each_test(self):
        markdown = report.to_markdown(report.summarize(self.payload))
        self.assertIn("test_deliberate_delay", markdown)
        self.assertIn("Host conditions", markdown)
        self.assertIn("Limitations", markdown)
        self.assertIn("Parent-process CPU", markdown)

    def test_duplicate_identity_is_flagged(self):
        payload = _report([_record("m.C.test_one", 1.0), _record("m.C.test_one", 2.0)])
        summary = report.summarize(payload)
        kinds = {issue["kind"] for issue in summary["integrity"]}
        self.assertIn("duplicate-identity", kinds)
        self.assertEqual(summary["totals"]["distinct_tests"], 1)

    def test_discovered_versus_executed_is_reported(self):
        payload = _report([_record("m.C.test_one", 1.0)], discovered=4)
        summary = report.summarize(payload)
        self.assertEqual(summary["totals"]["not_executed"], 3)
        kinds = {issue["kind"] for issue in summary["integrity"]}
        self.assertIn("not-executed", kinds)

    def test_empty_run_is_an_integrity_issue(self):
        summary = report.summarize(_report([]))
        kinds = {issue["kind"] for issue in summary["integrity"]}
        self.assertIn("empty-run", kinds)


class ComparisonTests(unittest.TestCase):
    def test_repeated_iterations_are_matched_by_identity(self):
        before = _report([_record("m.C.test_a", 1.0, iteration=0),
                          _record("m.C.test_a", 2.0, iteration=1)], iterations=2)
        after = _report([_record("m.C.test_a", 0.5, iteration=0),
                         _record("m.C.test_a", 1.0, iteration=1)], iterations=2)
        comparison = report.compare(before, after)
        self.assertTrue(comparison["comparable"])
        self.assertEqual(comparison["workload"]["common"], 2)
        self.assertEqual(sorted(item["iteration"] for item in comparison["per_test"]), [0, 1])
        self.assertEqual(comparison["workload"]["repeats_before"], {"m.C.test_a": 2})

    def test_repeated_identities_are_not_collapsed_to_the_last_one(self):
        before = _report([_record("m.C.test_a", 1.0, iteration=0),
                          _record("m.C.test_a", 9.0, iteration=1)], iterations=2)
        after = _report([_record("m.C.test_a", 0.5, iteration=0),
                         _record("m.C.test_a", 3.0, iteration=1)], iterations=2)
        comparison = report.compare(before, after)
        first = next(item for item in comparison["per_test"] if item["iteration"] == 0)
        self.assertEqual(first["before_seconds"], 1.0)
        self.assertEqual(first["after_seconds"], 0.5)

    def test_missing_iteration_is_not_comparable(self):
        before = _report([_record("m.C.test_a", 1.0, iteration=0),
                          _record("m.C.test_a", 2.0, iteration=1)], iterations=2)
        after = _report([_record("m.C.test_a", 1.0, iteration=0)], iterations=2)
        comparison = report.compare(before, after)
        self.assertFalse(comparison["comparable"])
        self.assertEqual(comparison["workload"]["only_before"], ["m.C.test_a#1"])
        self.assertIn("workload", _warnings(comparison))

    def test_extra_test_is_not_comparable(self):
        before = _report([_record("m.C.test_a", 1.0)])
        after = _report([_record("m.C.test_a", 1.0), _record("m.C.test_b", 1.0)])
        comparison = report.compare(before, after)
        self.assertFalse(comparison["comparable"])
        self.assertEqual(comparison["workload"]["only_after"], ["m.C.test_b#0"])

    def test_repetition_count_change_is_not_comparable(self):
        before = _report([_record("m.C.test_a", 1.0, iteration=0)])
        after = _report([_record("m.C.test_a", 1.0, iteration=0),
                         _record("m.C.test_a", 1.0, iteration=1)], iterations=2)
        comparison = report.compare(before, after)
        self.assertFalse(comparison["comparable"])
        self.assertIn("repetitions", _warnings(comparison))

    def test_outcome_change_is_not_comparable(self):
        before = _report([_record("m.C.test_a", 1.0)])
        after = _report([_record("m.C.test_a", 1.0, outcome="failure")])
        comparison = report.compare(before, after)
        self.assertFalse(comparison["comparable"])
        self.assertIn("outcomes", _warnings(comparison))
        self.assertEqual(len(comparison["outcome_changes"]["new_failures"]), 1)
        self.assertEqual(comparison["outcome_changes"]["resolved"], [])

    def test_newly_resolved_failure_is_also_reported(self):
        before = _report([_record("m.C.test_a", 1.0, outcome="error")])
        after = _report([_record("m.C.test_a", 1.0)])
        comparison = report.compare(before, after)
        self.assertFalse(comparison["comparable"])
        self.assertEqual(len(comparison["outcome_changes"]["resolved"]), 1)

    def test_skip_change_is_not_comparable(self):
        before = _report([_record("m.C.test_a", 1.0, outcome="skipped")])
        after = _report([_record("m.C.test_a", 1.0)])
        self.assertFalse(report.compare(before, after)["comparable"])

    def test_suite_error_difference_is_not_comparable(self):
        before = _report([_record("m.C.test_a", 1.0)])
        after = _report([_record("m.C.test_a", 1.0)],
                        suite_errors=[{"test_id": "setUpClass (m.C)",
                                       "outcome": "error", "message": "synthetic"}])
        comparison = report.compare(before, after)
        self.assertFalse(comparison["comparable"])
        self.assertIn("outcomes", _warnings(comparison))

    def test_interpreter_mismatch_is_not_comparable(self):
        before = _report([_record("m.C.test_a", 1.0)], python=("CPython", "3.13.17"))
        after = _report([_record("m.C.test_a", 1.0)], python=("CPython", "3.14.0"))
        comparison = report.compare(before, after)
        self.assertFalse(comparison["comparable"])
        self.assertIn("interpreter", _warnings(comparison))

    def test_platform_mismatch_is_not_comparable(self):
        before = _report([_record("m.C.test_a", 1.0)], platform_name="Windows-10")
        after = _report([_record("m.C.test_a", 1.0)], platform_name="Linux-6.8")
        comparison = report.compare(before, after)
        self.assertFalse(comparison["comparable"])
        self.assertIn("platform", _warnings(comparison))

    def test_unknown_source_identity_is_not_comparable(self):
        before = _report([_record("m.C.test_a", 1.0)])
        after = _report([_record("m.C.test_a", 1.0)], revision=None)
        comparison = report.compare(before, after)
        self.assertFalse(comparison["comparable"])
        self.assertIn("source", _warnings(comparison))

    def test_imported_package_outside_the_source_is_not_comparable(self):
        before = _report([_record("m.C.test_a", 1.0)])
        after = _report([_record("m.C.test_a", 1.0)], matches_source=False)
        comparison = report.compare(before, after)
        self.assertFalse(comparison["comparable"])
        self.assertIn("package", _warnings(comparison))

    def test_different_trace_settings_are_not_comparable(self):
        before = _report([_record("m.C.test_a", 1.0)], trace=True)
        after = _report([_record("m.C.test_a", 1.0)], trace=False)
        comparison = report.compare(before, after)
        self.assertFalse(comparison["comparable"])
        self.assertIn("instrumentation", _warnings(comparison))

    def test_different_sample_interval_is_not_comparable(self):
        before = _report([_record("m.C.test_a", 1.0)], interval=5.0)
        after = _report([_record("m.C.test_a", 1.0)], interval=60.0)
        comparison = report.compare(before, after)
        self.assertFalse(comparison["comparable"])
        self.assertIn("sample interval", _warnings(comparison))

    def test_schema_mismatch_is_not_comparable(self):
        before = _report([_record("m.C.test_a", 1.0)], schema=1)
        after = _report([_record("m.C.test_a", 1.0)], schema=2)
        comparison = report.compare(before, after)
        self.assertFalse(comparison["comparable"])
        self.assertIn("schema", _warnings(comparison))

    def test_missing_host_cpu_is_not_comparable(self):
        before = _report([_record("m.C.test_a", 1.0)], cpu=None)
        after = _report([_record("m.C.test_a", 1.0)], cpu=None)
        comparison = report.compare(before, after)
        self.assertFalse(comparison["comparable"])
        self.assertIn("not observed", _warnings(comparison))

    def test_missing_memory_is_not_comparable(self):
        before = _report([_record("m.C.test_a", 1.0)])
        after = _report([_record("m.C.test_a", 1.0)], memory=None)
        comparison = report.compare(before, after)
        self.assertFalse(comparison["comparable"])
        self.assertIn("memory was not observed", _warnings(comparison))

    def test_zero_memory_is_not_turned_into_a_ratio(self):
        before = _report([_record("m.C.test_a", 1.0)], memory=0)
        after = _report([_record("m.C.test_a", 1.0)], memory=0)
        comparison = report.compare(before, after)
        self.assertFalse(comparison["comparable"])
        self.assertIn("zero", _warnings(comparison))

    def test_unlike_host_load_is_not_comparable(self):
        before = _report([_record("m.C.test_a", 1.0)], cpu=10.0)
        after = _report([_record("m.C.test_a", 1.0)], cpu=40.0)
        comparison = report.compare(before, after)
        self.assertFalse(comparison["comparable"])
        self.assertIn("CPU", _warnings(comparison))
        self.assertEqual(comparison["delta_label"], "observation")
        self.assertIn("not a speedup claim", report.compare_markdown(comparison))

    def test_qualified_comparison_is_labelled_improvement(self):
        before = _report([_record("m.C.test_a", 4.0)], wall=10.0)
        after = _report([_record("m.C.test_a", 2.0)], wall=6.0)
        comparison = report.compare(before, after)
        self.assertTrue(comparison["comparable"], comparison["warnings"])
        self.assertEqual(comparison["delta_label"], "improvement")
        self.assertEqual(comparison["totals"]["delta_seconds"], -4.0)
        self.assertTrue(comparison["improved"])
        markdown = report.compare_markdown(comparison)
        self.assertIn("Most improved tests", markdown)
        self.assertNotIn("not a speedup claim", markdown)

    def test_qualified_slowdown_is_labelled_regression(self):
        before = _report([_record("m.C.test_a", 2.0)], wall=6.0)
        after = _report([_record("m.C.test_a", 4.0)], wall=10.0)
        comparison = report.compare(before, after)
        self.assertTrue(comparison["comparable"])
        self.assertEqual(comparison["delta_label"], "regression")
        self.assertIn("Most regressed tests", report.compare_markdown(comparison))

    def test_qualification_names_every_dimension(self):
        comparison = report.compare(_report([_record("m.C.test_a", 1.0)]),
                                    _report([_record("m.C.test_a", 1.0)]))
        dimensions = [entry["dimension"] for entry in comparison["qualification"]]
        self.assertEqual(dimensions, list(report._DIMENSIONS))
        self.assertTrue(all(entry["status"] == "matched"
                            for entry in comparison["qualification"]))

    def test_markdown_lists_workload_differences(self):
        before = _report([_record("m.C.test_a", 1.0), _record("m.C.test_b", 1.0)])
        after = _report([_record("m.C.test_a", 1.0)])
        markdown = report.compare_markdown(report.compare(before, after))
        self.assertIn("Workload differences", markdown)
        self.assertIn("m.C.test_b#0", markdown)

    def test_real_runs_within_one_process_compare_as_observations(self):
        # The same dirty checkout within one process is characterized, but the
        # two runs' wall times are still not a controlled experiment.
        before = _run([cases.SlowCase]).as_dict()
        after = _run([cases.SlowCase]).as_dict()
        comparison = report.compare(before, after)
        self.assertEqual(comparison["workload"]["common"], 1)
        self.assertEqual(comparison["workload"]["only_before"], [])
        self.assertIn("Before/after", report.compare_markdown(comparison))


class SanitizeTests(unittest.TestCase):
    def test_redact_text_scrubs_windows_unc_and_home_paths(self):
        # Built at run time: the repository audit (correctly) rejects a literal
        # host path in tracked source.
        drive = "C:" + os.sep
        unc = os.sep * 2 + "server" + os.sep + "share"
        posix_home = "/" + "home/" + "someone/private/notes.md"
        text = (f"failed at {drive}Users{os.sep}someone{os.sep}AppData{os.sep}Local"
                f"{os.sep}Temp{os.sep}tmp123{os.sep}f.json"
                f" and {unc}{os.sep}private{os.sep}evidence.json"
                f" and {posix_home}")
        redacted = sanitize.redact_text(text)
        self.assertNotIn("someone", redacted)
        self.assertNotIn("evidence.json", redacted)
        self.assertNotIn("server", redacted)
        self.assertIn("<path>", redacted)
        self.assertIn("<home>", redacted)

    def test_redact_text_replaces_known_roots(self):
        redacted = sanitize.redact_text("under /srv/deskmate/worktree/report.json now",
                                        roots=("/srv/deskmate/worktree",))
        self.assertNotIn("worktree", redacted)
        self.assertIn("<path>", redacted)

    def test_public_projection_drops_private_fields(self):
        payload = _run([cases.FastCase]).as_dict()
        payload["meta"]["working_directory"] = str(Path.cwd())
        payload["meta"]["command"] = "python " + str(Path.cwd() / "runner.py")
        payload["tests"][0]["message"] = str(Path.cwd() / "private.json")
        projected = sanitize.public_projection(payload)
        serialized = json.dumps(projected)
        self.assertNotIn("working_directory", projected["meta"])
        self.assertNotIn("command", projected["meta"])
        self.assertNotIn(str(Path.cwd()), serialized)
        self.assertNotIn("private.json", serialized)
        self.assertNotIn("python_executable", projected["environment"])
        self.assertIn("python_executable_name", projected["environment"])

    def test_public_projection_keeps_measurements(self):
        payload = _run([cases.SlowCase]).as_dict()
        projected = sanitize.public_projection(payload)
        self.assertEqual(projected["tests"][0]["wall_seconds"],
                         payload["tests"][0]["wall_seconds"])
        self.assertEqual(projected["schema_version"], payload["schema_version"])
        self.assertIn("summary", projected["host"])
        self.assertTrue(projected["meta"]["package"]["origin_recorded"])


class MicrobenchTests(unittest.TestCase):
    def test_bounded_benchmark_reports_statistics(self):
        result = microbench.run_microbenchmarks(iterations=1, names=["thread_start_join"],
                                                sample_interval=60.0)
        self.assertEqual(result["schema_version"], microbench.SCHEMA_VERSION)
        entry = result["benchmarks"][0]
        self.assertEqual(entry["name"], "thread_start_join")
        self.assertEqual(entry["iterations"], 1)
        self.assertGreaterEqual(entry["median_seconds"], 0.0)
        self.assertIn("thread_start_join", microbench.to_markdown(result))

    def test_unknown_benchmark_name_is_rejected(self):
        with self.assertRaises(ValueError):
            microbench.run_microbenchmarks(iterations=1, names=["not-a-benchmark"],
                                           sample_interval=60.0)

    def test_nonpositive_iterations_are_rejected(self):
        for bad in (0, -1):
            with self.assertRaises(ValueError):
                microbench.run_microbenchmarks(iterations=bad, names=["thread_start_join"],
                                               sample_interval=60.0)


class CommandLineTests(unittest.TestCase):
    def setUp(self):
        self.directory = Path(tempfile.mkdtemp(prefix="deskmate-perf-cli-"))
        self.addCleanup(shutil.rmtree, self.directory, True)

    def test_module_entry_point_exists(self):
        self.assertIsNotNone(importlib.util.find_spec("deskmate_formats.perf.__main__"))

    def test_nonpositive_repeat_is_rejected(self):
        with self.assertRaises(SystemExit):
            cli.main(["run", "--profile", "focused", "--test",
                      "perf_harness_cases.FastCase.test_immediate", "--repeat", "0"])

    def test_empty_discovery_is_rejected(self):
        with self.assertRaises(SystemExit) as raised:
            cli.main(["run", "--profile", "portable", "--start", str(self.directory)])
        self.assertIn("no tests were discovered", str(raised.exception))

    def test_nonpositive_sample_interval_is_rejected(self):
        with self.assertRaises(SystemExit) as raised:
            cli.main(["run", "--profile", "focused", "--test",
                      "perf_harness_cases.FastCase.test_immediate",
                      "--sample-interval", "0"])
        self.assertIn("sample_interval", str(raised.exception))

    def test_unknown_microbench_name_is_rejected(self):
        with self.assertRaises(SystemExit) as raised:
            cli.main(["microbench", "--name", "not-a-benchmark"])
        self.assertIn("unknown benchmark", str(raised.exception))

    def test_nonpositive_microbench_iterations_are_rejected(self):
        with self.assertRaises(SystemExit):
            cli.main(["microbench", "--iterations", "0"])

    def test_merge_keeps_iterations_intact(self):
        first = _run([cases.FastCase])
        second = _run([cases.FastCase])
        self.assertEqual(first.meta["iterations"], 1)
        first_records = list(first.records)
        merged = cli._merge([first, second])
        # The inputs are untouched, so their own iteration data is still true.
        self.assertEqual(first.meta["iterations"], 1)
        self.assertEqual(first.records, first_records)
        self.assertEqual(len(merged.records), 2)
        self.assertEqual([record.iteration for record in merged.records], [0, 1])
        self.assertEqual(merged.meta["iterations"], 2)
        self.assertEqual(len(merged.meta["iteration_outcomes"]), 2)

    def test_merge_of_nothing_is_rejected(self):
        with self.assertRaises(ValueError):
            cli._merge([])


if __name__ == "__main__":
    unittest.main()
