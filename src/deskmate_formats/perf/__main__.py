"""Enable ``python -m deskmate_formats.perf``.

The package docstring has always advertised module invocation; this module is
what makes that true instead of a documented entry point that did not exist.
"""

from __future__ import annotations

from .cli import main


if __name__ == "__main__":
    raise SystemExit(main())
