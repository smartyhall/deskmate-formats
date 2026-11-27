#!/usr/bin/env python3
"""Run the portable suite under the performance qualification harness.

The wrapper puts this checkout's ``src`` first on ``sys.path`` so measurements
describe the working tree rather than whatever wheel happens to be installed.
That matters on the shared laboratory VM, where several checkouts are active at
once and a stale install would silently change the numbers.
"""
# SPDX-FileCopyrightText: Copyright (c) 2026 Michael A. Hall
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "src"
# ``python tools/test_performance.py`` puts ``tools/`` on ``sys.path``, not the
# repository root, so a few portable tests that import ``tools.*`` helpers would
# fail to load. Mirror what ``python -m unittest`` does from the root: the root
# is importable, with this checkout's ``src`` ahead of any installed wheel.
for entry in (str(ROOT), str(SOURCE)):
    if entry not in sys.path:
        sys.path.insert(0, entry)
if str(SOURCE) in sys.path:
    sys.path.remove(str(SOURCE))
    sys.path.insert(0, str(SOURCE))

from deskmate_formats.perf.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
