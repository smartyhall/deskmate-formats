"""Child-side resolution report, meant to run as ``python -I -m ...probe``.

The report is evidence rather than a claim: this module can only print it if
its own package resolved in the child, and every field describes that child.

``isolated`` records whether ``-I`` was actually in effect.  A caller that
believes it launched an isolated child but reads ``isolated: false`` has a
launch-site defect, not a measurement.  ``pythonpath_present`` records that
``PYTHONPATH`` was set in the environment, which an isolated child ignores;
recording both is what proves the isolation rather than assuming it.

``interpreter`` is the path this process was invoked as, **not** the real path
it resolves to: on POSIX every virtual environment's ``bin/python`` resolves to
the base interpreter, so only ``prefix`` says which environment this is.
``interpreter_sha256`` digests the invoked path, which is what the parent's
receipt records.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys

from . import identity

PROBE_SCHEMA_VERSION = 2


def report(package: str = identity.PACKAGE) -> dict[str, object]:
    """Describe this process's interpreter, search path and package resolution."""
    resolved = identity.import_identity(package)
    sys_path = [str(entry) for entry in sys.path]
    executable = os.path.abspath(sys.executable) if sys.executable else None
    try:
        executable_digest = identity.file_digest(executable) if executable else None
    except OSError:
        executable_digest = None
    return {
        "schema_version": PROBE_SCHEMA_VERSION,
        "probe": "deskmate_formats.campaign_env.probe",
        "probe_origin": str(Path(__file__).resolve()),
        "interpreter": executable,
        "interpreter_realpath": os.path.realpath(executable) if executable else None,
        "interpreter_is_symlink": os.path.islink(executable) if executable else None,
        "interpreter_sha256": executable_digest,
        "python_version": sys.version.split()[0],
        "implementation": sys.implementation.name,
        "prefix": sys.prefix,
        "prefix_resolved": os.path.realpath(sys.prefix),
        "environment_name": Path(sys.prefix).name,
        "base_prefix": sys.base_prefix,
        "in_virtual_environment": sys.prefix != sys.base_prefix,
        "isolated": bool(sys.flags.isolated),
        "ignore_environment": bool(sys.flags.ignore_environment),
        "no_user_site": bool(sys.flags.no_user_site),
        "dont_write_bytecode": bool(sys.flags.dont_write_bytecode),
        "utf8_mode": bool(sys.flags.utf8_mode),
        "pythonpath_present": "PYTHONPATH" in os.environ,
        "pythonhome_present": "PYTHONHOME" in os.environ,
        "sys_path": sys_path,
        "sys_path_count": len(sys_path),
        "prefix_on_path": any(
            os.path.normcase(entry) == os.path.normcase(sys.prefix) for entry in sys_path
        ),
        "base_prefix_on_path": any(
            os.path.normcase(entry) == os.path.normcase(sys.base_prefix) for entry in sys_path
        ),
        "package": resolved,
        "observed_package": package,
        "cwd": os.getcwd(),
        "argv": list(sys.argv),
    }


def main(argv: "list[str] | None" = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="python -I -m deskmate_formats.campaign_env.probe")
    parser.add_argument("--package", default=identity.PACKAGE,
                        help="distribution package whose resolution is reported")
    parser.add_argument("--json", action="store_true", help="accepted for symmetry with the CLI")
    arguments = parser.parse_args(sys.argv[1:] if argv is None else argv)
    print(json.dumps(report(arguments.package), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
