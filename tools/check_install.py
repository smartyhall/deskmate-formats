"""Run against the installed wheel, with no src path injection."""
import importlib.metadata
from importlib.resources import files
from hashlib import sha256
from pathlib import Path
import subprocess
import sys
import sysconfig

import deskmate_formats.calendar.personal as personal
from deskmate_formats.calendar.writer import Appointment, capacity
from deskmate_formats.observer.http import ObserverServer
from deskmate_formats.supervisor.protocol import PROFILE_SHA256

assert personal.FILE_SIZE == 6144 and Appointment and callable(capacity)
assert callable(ObserverServer)
assert "PIL" not in sys.modules
assets = files("deskmate_formats.observer")
for name in ("dashboard.css", "dashboard.js"):
    assert assets.joinpath(name).read_bytes()
    assert assets.joinpath(name + ".license").read_bytes()
supervisor = files("deskmate_formats.supervisor")
for name in ("codex-0.166.0.json", "CODEX-NOTICE.txt"):
    assert supervisor.joinpath(name + ".license").read_bytes()
assert sha256(supervisor.joinpath("codex-0.166.0.json").read_bytes()).hexdigest() == PROFILE_SHA256

dist = importlib.metadata.distribution("deskmate-formats")
assert dist.version == "0.1.0.dev0"
for command in (
    "deskmate-calendar",
    "deskmate-calendar-append",
    "deskmate-86box-mcp",
    "deskmate-86box-observer",
    "deskmate-observer-event",
    "deskmate-observer-codex",
):
    matches = [entry for entry in dist.entry_points if entry.name == command]
    assert len(matches) == 1 and callable(matches[0].load())
    executable = Path(sysconfig.get_path("scripts")) / (
        command + (".exe" if sys.platform == "win32" else "")
    )
    subprocess.run([str(executable), "--help"], check=True, stdout=subprocess.DEVNULL)
print("Installed package, observer assets, and all six CLI entry points passed", sys.version.split()[0])
