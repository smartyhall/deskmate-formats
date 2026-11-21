"""Tests for conservative site-only CI classification."""
# SPDX-FileCopyrightText: Copyright (c) 2026 Michael A. Hall
# SPDX-License-Identifier: GPL-3.0-or-later

import sys
from pathlib import Path
import unittest
from unittest.mock import patch
import subprocess

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from ci_scope import changed_paths, needs_portable  # noqa: E402


class CiScopeTests(unittest.TestCase):
    def test_site_assets_and_site_docs_skip_portable_matrix(self):
        self.assertFalse(needs_portable({
            "website/src/assets/reference/desk-calendar.png",
            "website/src/_includes/base.njk",
            "docs/site/page-map.json",
            ".github/workflows/reference-publish.yml",
            ".github/workflows/reference-preview.yml",
        }))

    def test_unrelated_code_or_policy_runs_portable(self):
        for path in (
            "src/deskmate_formats/calendar.py",
            "tests/portable/test_ci_scope.py",
            "docs/reference/tandy-filer-format.md",
            "tools/ci_scope.py",
            "tools/check_reference_pages.py",
            ".github/workflows/ci.yml",
            "AGENTS.md",
            ".github/SECURITY.md",
        ):
            with self.subTest(path=path):
                self.assertTrue(needs_portable({"website/README.md", path}))

    def test_unknown_or_empty_diff_never_skips(self):
        self.assertTrue(needs_portable(set()))

    @patch("ci_scope.subprocess.run")
    def test_pr_uses_base_and_merge_sha_without_rename_folding(self, run):
        base, head = "a" * 40, "b" * 40
        run.return_value.stdout = b"docs/site/page-map.json\0website/src/assets/ui.png\0"
        self.assertEqual(
            changed_paths("pull_request", "", base, head),
            {"docs/site/page-map.json", "website/src/assets/ui.png"},
        )
        run.assert_called_once_with(
            ["git", "diff", "--no-renames", "--name-only", "-z", base, head],
            check=True, capture_output=True,
        )

    def test_unknown_event_or_zero_baseline_refuses_to_classify(self):
        with self.assertRaises(ValueError):
            changed_paths("workflow_dispatch", "", "", "f" * 40)
        with self.assertRaises(ValueError):
            changed_paths("push", "0" * 40, "", "f" * 40)
        with self.assertRaises(ValueError):
            changed_paths("pull_request", "", "bad", "f" * 40)

    @patch("ci_scope.subprocess.run", side_effect=subprocess.CalledProcessError(1, "git"))
    def test_git_diff_failure_propagates_for_conservative_fallback(self, run):
        with self.assertRaises(subprocess.CalledProcessError):
            changed_paths("push", "a" * 40, "", "b" * 40)


if __name__ == "__main__":
    unittest.main()
