"""Portable tests for the performance qualification harness itself."""

from __future__ import annotations

import io
import sys
import unittest

from deskmate_formats.perf import hostload, microbench, report
from deskmate_formats.perf.runner import run_suite

import perf_harness_cases as cases


def _run(cases_to_run, *, trace=False, trace_git_commands=False):
    loader = unittest.TestLoader()
    suite = unittest.TestSuite(loader.loadTestsFromTestCase(case) for case in cases_to_run)
    return run_suite(suite, label="harness", profile="test", trace_processes=trace,
                     trace_git_commands=trace_git_commands,
                     sample_interval=60.0, verbosity=0, stream=io.StringIO())


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
        result = _run([cases.GitCase], trace_git_commands=True)
        record = result.records[0]
        self.assertEqual(record.git_commands.get("init"), 1)
        self.assertEqual(record.git_commands.get("rev-parse"), 1)
        self.assertEqual(sum(record.git_commands.values()), record.git_calls)

    def test_git_subcommands_are_not_sampled_by_default(self):
        result = _run([cases.GitCase], trace=True)
        record = result.records[0]
        self.assertGreaterEqual(record.git_calls, 2)
        self.assertEqual(record.git_commands, {})

    def test_git_subcommand_parsing_skips_global_options(self):
        from deskmate_formats.perf.runner import _git_subcommand
        self.assertEqual(_git_subcommand(["git", "-c", "core.autocrlf=false", "rev-parse", "HEAD"]),
                         "rev-parse")
        self.assertEqual(_git_subcommand("git log -1 --oneline"), "log")
        self.assertEqual(_git_subcommand(["git"]), "unknown")


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.result = _run([cases.FastCase, cases.SlowCase, cases.FailureCase], trace=True)
        self.payload = self.result.as_dict()
        self.summary = report.summarize(self.payload)

    def test_ranking_puts_the_slowest_test_first(self):
        ranking = self.summary["ranking"]
        self.assertEqual(ranking[0]["test_id"],
                         "perf_harness_cases.SlowCase.test_deliberate_delay")
        durations = [entry["wall_seconds"] for entry in ranking]
        self.assertEqual(durations, sorted(durations, reverse=True))

    def test_pareto_and_totals_are_consistent(self):
        pareto = self.summary["pareto"]
        self.assertLessEqual(pareto["tests_for_target"], pareto["tests_total"])
        self.assertGreaterEqual(pareto["tests_for_target"], 1)
        totals = self.summary["totals"]
        self.assertEqual(totals["tests"], 3)
        self.assertEqual(totals["failures"], 1)
        self.assertLessEqual(totals["attributed_wall_seconds"], totals["suite_wall_seconds"] + 0.01)

    def test_modules_aggregate_tests(self):
        module = next(entry for entry in self.summary["modules"]
                      if entry["module"] == "perf_harness_cases")
        self.assertEqual(module["tests"], 3)
        self.assertEqual(module["failures"], 1)
        # A single module holds every test, so its share rounds to 100%.
        self.assertAlmostEqual(module["share_percent"], 100.0, delta=1.0)

    def test_markdown_mentions_each_test(self):
        markdown = report.to_markdown(self.summary)
        self.assertIn("test_deliberate_delay", markdown)
        self.assertIn("Host conditions", markdown)
        self.assertIn("Limitations", markdown)

    def test_compare_flags_unlike_host_conditions(self):
        other = self.result.as_dict()
        other["tests"] = [dict(test) for test in other["tests"]]
        for test in other["tests"]:
            test["wall_seconds"] = max(0.0, float(test["wall_seconds"]) / 2.0)
        other["host"]["summary"]["cpu_total_percent"]["mean"] = 5.0
        self.payload["host"]["summary"]["cpu_total_percent"]["mean"] = 95.0
        comparison = report.compare(self.payload, other)
        self.assertFalse(comparison["comparable"])
        self.assertTrue(any("CPU" in warning for warning in comparison["warnings"]))
        self.assertTrue(comparison["improved"])
        self.assertIn("Before/after", report.compare_markdown(comparison))

    def test_compare_detects_mismatched_test_counts(self):
        other = self.result.as_dict()
        other["tests"] = other["tests"][:1]
        comparison = report.compare(self.payload, other)
        self.assertTrue(any("test count" in warning for warning in comparison["warnings"]))


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

    def test_unknown_benchmark_selection_is_empty(self):
        result = microbench.run_microbenchmarks(iterations=1, names=["not-a-benchmark"],
                                                sample_interval=60.0)
        self.assertEqual(result["benchmarks"], [])


if __name__ == "__main__":
    unittest.main()
