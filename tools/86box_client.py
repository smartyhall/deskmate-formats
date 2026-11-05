"""Backward-compatible checkout CLI; the reusable client is now packaged."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from deskmate_formats.automation.client import *  # noqa: F403

if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, ProtocolError, CommandError) as exc:
        print(f'86Box client: {exc}', file=sys.stderr)
        raise SystemExit(2)
