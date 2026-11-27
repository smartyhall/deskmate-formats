"""Portable checks for the advisory research campaign inventory."""
from copy import deepcopy
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("research_campaigns", ROOT / "tools/research_campaigns.py")
planner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(planner)


class CampaignInventoryTests(unittest.TestCase):
    def setUp(self):
        # Synthetic planning states must not change when real milestones close.
        self.data = {
            "schema_version": 1, "as_of": "2026-11-27", "base_revision": "a" * 40,
            "purpose": "Synthetic planning controls",
            "campaigns": [],
        }
        for key, status, deps in (
            ("supervisor-integration", "review", []),
            ("environment-isolation", "proposed", []),
            ("deterministic-canary", "proposed", ["supervisor-integration", "environment-isolation"]),
            ("archive-format-followup", "standing", []),
        ):
            self.data["campaigns"].append({
                "id": key, "domain": "infrastructure", "priority": 1, "status": status,
                "effort": "small", "workers": ["offline-lab"], "resources": ["owned-worktree"],
                "depends_on": deps, "sources": ["AGENTS.md"], "issues": [], "pull_requests": [],
                "evidence": "Synthetic control", "acceptance": "Synthetic completion",
                "completion_refs": [],
            })
        planner.validate(self.data)

    def test_inventory_and_order(self):
        inventory = planner.load()
        result = planner.report(inventory)
        self.assertTrue(result["advisory_only"])
        entries = result["campaigns"]
        self.assertEqual(entries, sorted(entries, key=lambda x: (x["priority"], x["id"])))
        self.assertEqual(len(entries), len(inventory["campaigns"]))

    def test_filter_preserves_unresolved_dependencies(self):
        entries = planner.report(self.data, "offline-lab")["campaigns"]
        canary = next(row for row in entries if row["id"] == "deterministic-canary")
        self.assertIn("supervisor-integration", canary["unresolved_dependencies"])
        self.assertIn("environment-isolation", canary["unresolved_dependencies"])

    def test_invalid_inventory(self):
        cases = []
        for field, value in (("priority", True), ("workers", ["unknown"]), ("sources", ["../AGENTS.md"]),
                             ("sources", ["does-not-exist.md"]), ("depends_on", ["unknown"]),
                             ("depends_on", ["archive-format-followup"]), ("status", "completed")):
            data = deepcopy(self.data)
            data["campaigns"][0][field] = value
            cases.append(data)
        duplicate = deepcopy(self.data)
        duplicate["campaigns"].append(deepcopy(duplicate["campaigns"][0]))
        cases.append(duplicate)
        cycle = deepcopy(self.data)
        cycle["campaigns"][0]["depends_on"] = [cycle["campaigns"][0]["id"]]
        cases.append(cycle)
        for data in cases:
            with self.subTest(data=data["campaigns"][0]), self.assertRaises(planner.InventoryError):
                planner.validate(data)

    def test_multi_node_cycle(self):
        data = deepcopy(self.data)
        first, second = data["campaigns"][:2]
        first["depends_on"] = [second["id"]]
        second["depends_on"] = [first["id"]]
        with self.assertRaisesRegex(planner.InventoryError, "cycle"):
            planner.validate(data)

    def test_completed_milestone_cannot_skip_dependency(self):
        data = deepcopy(self.data)
        canary = next(row for row in data["campaigns"] if row["id"] == "deterministic-canary")
        canary.update(status="completed", completion_refs=["synthetic receipt"])
        with self.assertRaisesRegex(planner.InventoryError, "incomplete dependency"):
            planner.validate(data)

    def test_completed_milestone_with_completed_dependencies(self):
        data = deepcopy(self.data)
        for row in data["campaigns"][:3]:
            row.update(status="completed", completion_refs=["synthetic receipt"])
        planner.validate(data)
        canary = next(row for row in planner.report(data)["campaigns"]
                      if row["id"] == "deterministic-canary")
        self.assertEqual(canary["unresolved_dependencies"], [])

    def test_unsupported_schema(self):
        data = deepcopy(self.data)
        data["schema_version"] = 2
        with self.assertRaisesRegex(planner.InventoryError, "unsupported schema"):
            planner.validate(data)

    def test_duplicate_json_properties(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "bad.json"
            path.write_text('{"schema_version": 1, "schema_version": 1}', encoding="utf-8")
            with self.assertRaisesRegex(planner.InventoryError, "duplicate JSON"):
                planner.load(path)


if __name__ == "__main__":
    unittest.main()
