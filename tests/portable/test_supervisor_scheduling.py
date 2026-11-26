"""Allowance-aware selection: unknown is not zero, and units are never conflated."""

from datetime import UTC, datetime
import unittest

from deskmate_formats.supervisor import scheduling

NOW = datetime(2026, 11, 26, 0, 5, 0, tzinfo=UTC)
DISPATCH = frozenset(("prepare", "dispatch"))


def allowance(value=None, *, at="2026-11-26T00:00:00Z", source="ui-observation"):
    if value is None:
        return scheduling.Measurement.unknown(
            scheduling.ALLOWANCE, "hours", scope="account", semantics="remaining")
    return scheduling.Measurement.observed(
        scheduling.ALLOWANCE, value, "hours", scope="account", semantics="remaining",
        source=source, observed_at_utc=at)


def capacity(worker_id, kind, *, capabilities=DISPATCH, health="available",
             resources=("source-read",), measurements=()):
    return scheduling.WorkerCapacity(worker_id, kind, frozenset(capabilities), health,
                                     resources, tuple(measurements))


class MeasurementTests(unittest.TestCase):
    def test_unknown_is_explicit_and_never_zero(self):
        measurement = allowance()
        self.assertFalse(measurement.known)
        self.assertIsNone(measurement.value)
        self.assertEqual(measurement.source, "unavailable")
        self.assertIsNone(measurement.age_seconds(NOW))
        self.assertFalse(measurement.fresh(NOW, max_age_seconds=900))

    def test_freshness_uses_the_observed_timestamp(self):
        self.assertTrue(allowance(20.0).fresh(NOW, max_age_seconds=900))
        self.assertFalse(allowance(20.0, at="2026-11-25T00:00:00Z").fresh(NOW, max_age_seconds=900))

    def test_totals_refuse_unlike_units_and_semantics(self):
        tokens = scheduling.Measurement.observed(
            "thread_input_tokens", 4800000, "tokens", scope="thread",
            semantics="cumulative", source="ui-observation",
            observed_at_utc="2026-11-26T00:00:00Z")
        cached = scheduling.Measurement.observed(
            "thread_cached_input_tokens", 4400000, "tokens", scope="thread",
            semantics="cumulative", source="ui-observation",
            observed_at_utc="2026-11-26T00:00:00Z")
        hours = allowance(20.0)
        self.assertEqual(scheduling.total((tokens, cached), "tokens"), 9200000)
        with self.assertRaises(scheduling.SchedulingError):
            scheduling.total((tokens, hours), "hours")
        with self.assertRaises(scheduling.SchedulingError):
            scheduling.total((hours,), "tokens")
        consumed = scheduling.Measurement.observed(
            scheduling.ALLOWANCE, 4.0, "hours", scope="account", semantics="consumed",
            source="ui-observation", observed_at_utc="2026-11-26T00:00:00Z")
        with self.assertRaisesRegex(scheduling.SchedulingError, "unlike semantics"):
            scheduling.total((hours, consumed), "hours")
        with self.assertRaisesRegex(scheduling.SchedulingError, "unlike units"):
            scheduling.total((hours, tokens), "hours")
        self.assertEqual(set(scheduling.grouped((tokens, hours))), {"tokens", "hours"})


class SelectionTests(unittest.TestCase):
    def test_missing_allowance_is_unknown_not_unlimited(self):
        task = scheduling.TaskRequirement("research", True, DISPATCH)
        decision = scheduling.select(
            task, [capacity("codex-a", "codex", measurements=(allowance(),))], now=NOW)
        self.assertFalse(decision.chosen)
        self.assertIn("unknown", decision.rejected[0][1])

    def test_stale_and_exhausted_allowances_are_ineligible(self):
        task = scheduling.TaskRequirement("research", True, DISPATCH)
        stale = scheduling.select(
            task, [capacity("codex-a", "codex",
                            measurements=(allowance(20.0, at="2026-11-25T00:00:00Z"),))], now=NOW)
        self.assertFalse(stale.chosen)
        self.assertIn("stale", stale.rejected[0][1])
        exhausted = scheduling.select(
            task, [capacity("codex-a", "codex", measurements=(allowance(0.0),))], now=NOW)
        self.assertFalse(exhausted.chosen)
        self.assertIn("exhausted", exhausted.rejected[0][1])

    def test_fresh_allowance_selects_the_inference_worker(self):
        task = scheduling.TaskRequirement("research", True, DISPATCH)
        decision = scheduling.select(
            task, [capacity("codex-a", "codex", measurements=(allowance(12.5),))], now=NOW)
        self.assertEqual(decision.worker_id, "codex-a")
        self.assertIn("12.5 hours remaining", decision.rationale)

    def test_deterministic_worker_is_preferred_for_a_no_model_task(self):
        task = scheduling.TaskRequirement("hash-fixtures", False, DISPATCH)
        decision = scheduling.select(task, [
            capacity("codex-a", "codex", measurements=(allowance(12.5),)),
            capacity("deterministic-local", "deterministic"),
        ], now=NOW)
        self.assertEqual(decision.worker_id, "deterministic-local")
        self.assertIn("no model inference consumed", decision.rationale)
        self.assertTrue(any("allowance is not required" in item for item in decision.unknowns))

    def test_worker_class_must_match_the_inference_mode(self):
        inference = scheduling.TaskRequirement("research", True, DISPATCH)
        self.assertFalse(scheduling.select(
            inference, [capacity("det", "deterministic")], now=NOW).chosen)
        local = scheduling.TaskRequirement("hash-fixtures", False, DISPATCH)
        decision = scheduling.select(
            local, [capacity("codex-a", "codex", measurements=(allowance(12.5),))], now=NOW)
        self.assertFalse(decision.chosen)
        self.assertIn("does not match", decision.rejected[0][1])

    def test_health_capability_and_resource_filters(self):
        task = scheduling.TaskRequirement("research", True, DISPATCH, resources=("emulator",))
        degraded = capacity("codex-a", "codex", health="degraded",
                            measurements=(allowance(10.0),))
        missing = capacity("codex-b", "codex", capabilities=frozenset(("prepare",)),
                           measurements=(allowance(10.0),))
        no_resource = capacity("codex-c", "codex", measurements=(allowance(10.0),))
        decision = scheduling.select(task, [degraded, missing, no_resource], now=NOW)
        self.assertFalse(decision.chosen)
        reasons = dict(decision.rejected)
        self.assertIn("health", reasons["codex-a"])
        self.assertIn("missing capability", reasons["codex-b"])
        self.assertIn("resource", reasons["codex-c"])

    def test_decision_serializes_its_own_basis(self):
        task = scheduling.TaskRequirement("hash-fixtures", False, DISPATCH)
        view = scheduling.select(
            task, [capacity("det", "deterministic")], now=NOW).as_dict()
        self.assertEqual(set(view), {"worker_id", "chosen", "rationale", "rejected", "unknowns"})
        self.assertTrue(view["chosen"])


if __name__ == "__main__":
    unittest.main()
