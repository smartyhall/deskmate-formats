"""Compatibility entry point for the installable offline synthetic peer."""

import sys

from deskmate_formats.supervisor.synthetic_peer import main


if __name__ == "__main__":
    main(*sys.argv[1:])
