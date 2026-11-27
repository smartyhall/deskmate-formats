"""Isolated child argument vectors built from an explicitly chosen interpreter.

The existing laboratory launch sites all use ``[sys.executable, "-I", "-m",
"deskmate_formats..."]``.  That is correct isolation of the environment and
incorrect attribution of the interpreter: ``sys.executable`` is whichever
Python ran the parent, so on this VM the child imports the shared wheel rather
than the campaign's source.

``isolated_argv`` makes the interpreter an argument rather than an ambient
fact.  It refuses to build a vector without one, and it records the exact
vector in the receipt so the child's resolution can be attributed afterwards.

Isolation itself is preserved: ``-I`` is not optional here, because a campaign
child that is not isolated can read ``PYTHONPATH`` and silently run another
campaign's code.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import re
import subprocess

ISOLATION_FLAG = "-I"
DEFAULT_TIMEOUT_SECONDS = 600
_MODULE = re.compile(r"[A-Za-z_][A-Za-z0-9_.]{0,200}")
_INTERPRETER_NAME = re.compile(r"python(?:\d+(?:\.\d+)*)?(?:\.exe)?", re.IGNORECASE)


class LaunchError(ValueError):
    """The requested child launch was not specific enough to be attributable."""


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def require_interpreter(interpreter: "str | os.PathLike[str]") -> str:
    """Return an absolute interpreter path, refusing a bare command name."""
    if interpreter is None or str(interpreter).strip() == "":
        raise LaunchError("an explicit interpreter is required for an isolated child")
    path = Path(str(interpreter))
    if not path.is_absolute():
        raise LaunchError("the interpreter must be an absolute path")
    if not _INTERPRETER_NAME.fullmatch(path.name):
        raise LaunchError("the interpreter does not look like a Python executable")
    return str(path)


def isolated_argv(interpreter: "str | os.PathLike[str]", module: str | None = None, *,
                  code: str | None = None, arguments: "tuple[str, ...] | list[str]" = ()) -> "list[str]":
    """``[interpreter, "-I", "-m", module, *arguments]`` (or ``-c`` for ``code``)."""
    executable = require_interpreter(interpreter)
    if (module is None) == (code is None):
        raise LaunchError("exactly one of module or code is required")
    argv = [executable, ISOLATION_FLAG]
    if module is not None:
        if not _MODULE.fullmatch(module):
            raise LaunchError("invalid module name")
        argv += ["-m", module]
    else:
        if not isinstance(code, str) or not code.strip():
            raise LaunchError("inline code must be a non-empty string")
        argv += ["-c", code]
    for argument in arguments:
        if not isinstance(argument, str) or "\0" in argument:
            raise LaunchError("invalid child argument")
        argv.append(argument)
    return argv


def run(argv: "list[str]", *, cwd: "str | os.PathLike[str] | None" = None,
        environment: "dict[str, str] | None" = None,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
        stdin_data: "bytes | None" = None) -> dict[str, object]:
    """Run one already-assembled vector and record what happened, not what was hoped."""
    started = utc_now()
    receipt: dict[str, object] = {
        "argv": list(argv),
        "cwd": str(Path(cwd).resolve()) if cwd else None,
        "started_utc": started,
        "exit_status": None,
        "failure": None,
        "timeout_seconds": timeout,
        "elapsed_seconds": 0.0,
        "stdout": "",
        "stderr": "",
        "stdout_sha256": None,
        "stderr_sha256": None,
    }
    import time

    start = time.monotonic()
    try:
        completed = subprocess.run(
            argv,
            cwd=str(cwd) if cwd else None,
            env=environment,
            input=stdin_data,
            capture_output=True,
            timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        stdout, stderr, status = completed.stdout, completed.stderr, completed.returncode
    except subprocess.TimeoutExpired as error:
        stdout = error.stdout or b""
        stderr = error.stderr or b""
        status = "timed-out"
        receipt["failure"] = "TimeoutExpired"
    except OSError as error:
        stdout, stderr, status = b"", b"", "unavailable"
        receipt["failure"] = type(error).__name__
    receipt["elapsed_seconds"] = round(time.monotonic() - start, 6)
    receipt["finish_utc"] = utc_now()
    receipt["exit_status"] = status
    receipt["stdout"] = stdout.decode("utf-8", "replace")
    receipt["stderr"] = stderr.decode("utf-8", "replace")
    receipt["stdout_sha256"] = hashlib.sha256(stdout).hexdigest()
    receipt["stderr_sha256"] = hashlib.sha256(stderr).hexdigest()
    return receipt


def run_isolated(interpreter: "str | os.PathLike[str]", module: str, *,
                 arguments: "tuple[str, ...] | list[str]" = (),
                 cwd: "str | os.PathLike[str] | None" = None,
                 environment: "dict[str, str] | None" = None,
                 timeout: int = DEFAULT_TIMEOUT_SECONDS) -> dict[str, object]:
    """Launch ``module`` under the given interpreter with ``-I`` and record it."""
    return run(isolated_argv(interpreter, module, arguments=arguments), cwd=cwd,
               environment=environment, timeout=timeout)


def probe(interpreter: "str | os.PathLike[str]", *, cwd: "str | os.PathLike[str] | None" = None,
          environment: "dict[str, str] | None" = None,
          package: "str | None" = None,
          timeout: int = DEFAULT_TIMEOUT_SECONDS) -> dict[str, object]:
    """Run the campaign probe as an isolated child and merge its parsed report."""
    arguments = ["--package", package] if package else []
    receipt = run_isolated(interpreter, "deskmate_formats.campaign_env.probe",
                           arguments=arguments, cwd=cwd, environment=environment, timeout=timeout)
    document = None
    if receipt["exit_status"] == 0 and receipt["stdout"]:
        import json

        try:
            document = json.loads(str(receipt["stdout"]))
        except ValueError:
            document = None
    receipt["report"] = document
    receipt["report_parsed"] = document is not None
    return receipt
