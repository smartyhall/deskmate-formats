"""Windows offline S0 inventory. Never starts an app-server session or model.

Only native --version and the pinned source's offline schema generator execute.
All outputs (including local configuration path metadata) stay outside Git.
"""

import argparse
import ctypes as ct
from ctypes import wintypes as wt
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from time import monotonic
from uuid import UUID

from deskmate_formats.observer._private_storage import storage_directory
from deskmate_formats.supervisor.driver import digest, verify_native, write_record


def windows_policy_paths():
    import winreg

    # Same known-folder resolution and 64-bit policy registry view as 0.166.0.
    shell = ct.WinDLL("shell32")
    ole = ct.WinDLL("ole32")
    shell.SHGetKnownFolderPath.argtypes = (ct.c_void_p, wt.DWORD, wt.HANDLE, ct.POINTER(wt.LPWSTR))
    shell.SHGetKnownFolderPath.restype = ct.c_long
    ole.CoTaskMemFree.argtypes = (ct.c_void_p,)
    guid = ct.create_string_buffer(UUID("62ab5d82-fdc1-4dc3-a9dd-070d1d495d97").bytes_le)
    output = wt.LPWSTR()
    if shell.SHGetKnownFolderPath(guid, 0, None, ct.byref(output)) != 0:
        raise OSError("ProgramData known-folder query failed; do not assume absence")
    try:
        system = Path(output.value) / "OpenAI" / "Codex"
    finally:
        ole.CoTaskMemFree(ct.cast(output, ct.c_void_p))
    requirements = system / "requirements.toml"
    override = False
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\OpenAI\Codex",
                            access=winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
            value, _ = winreg.QueryValueEx(key, "RequirementsPath")
            requirements = Path(value)
            override = True
    except FileNotFoundError:
        pass
    return [system / "config.toml", requirements], override


def probe(root, executable, checkout):
    if sys.platform != "win32" or root.exists():
        raise ValueError("requires Windows and a fresh private archive directory")
    executable = verify_native(executable)
    root = storage_directory(root, create=True)
    for name in ("home", "scratch"):
        storage_directory(root / name, create=True)
    env = {k: os.environ[k] for k in ("SystemRoot", "WINDIR") if k in os.environ}
    env.update(CODEX_HOME=str(root / "home"), HOME=str(root / "home"), USERPROFILE=str(root / "home"),
               TEMP=str(root / "scratch"), TMP=str(root / "scratch"))
    commands = []

    def command(argv, *, sanitized=False):
        start = monotonic()
        result = subprocess.run(argv, cwd=root / "scratch" if sanitized else checkout,
                                env=env if sanitized else None, capture_output=True, timeout=60,
                                creationflags=subprocess.CREATE_NO_WINDOW)
        number = len(commands) + 1
        for label, data in (("stdout", result.stdout), ("stderr", result.stderr)):
            (root / f"{number:02d}-{label}.txt").write_bytes(data)
        receipt = {"argv": argv, "sanitized_environment": sanitized, "returncode": result.returncode,
                   "elapsed_host_seconds": monotonic() - start,
                   "stdout_sha256": digest(root / f"{number:02d}-stdout.txt"),
                   "stderr_sha256": digest(root / f"{number:02d}-stderr.txt")}
        commands.append(receipt)
        write_record(root / f"command-{number:02d}.json", receipt)
        if result.returncode:
            raise RuntimeError("offline command failed; preserve archive")
        return result.stdout

    revision = command(["git", "rev-parse", "HEAD"]).decode().strip()
    command(["git", "status", "--short"])
    version = command([executable, "--version"], sanitized=True).decode().strip()
    inventories = []
    for number in (1, 2):
        export = root / f"schema-{number}"
        command([executable, "app-server", "generate-json-schema", "--out", str(export)], sanitized=True)
        profile, inventory = root / f"profile-{number}.json", root / f"inventory-{number}.json"
        command([sys.executable, str(checkout / "tools/pin_app_server_schema.py"),
                 str(export), str(profile), str(inventory)])
        inventories.append(json.loads(inventory.read_bytes()))
    policy_paths, registry_override = windows_policy_paths()
    ancestor_paths = [parent / ".codex" / "config.toml" for parent in (root / "scratch", *(root / "scratch").parents)]
    # No credential values or configuration contents are emitted/read here.
    paths = [{"path": str(path), "present": path.exists()} for path in policy_paths + ancestor_paths]
    result = {"git_revision": revision, "native_version": version, "native_sha256": digest(executable),
              "native_path": executable, "platform": platform.platform(), "python": sys.version,
              "environment": env, "configuration_path_presence_only": paths,
              "requirements_registry_override": registry_override,
              "schema_exports_equal": inventories[0] == inventories[1],
              "schema_file_count": len(inventories[0]["sha256_by_path"]),
              "profile_sha256": inventories[0]["profile_sha256"],
              "schema_inventory_sha256": digest(root / "inventory-1.json"),
              "commands": commands, "app_server_sessions": 0, "model_turns": 0,
              "effective_configuration": "unverified", "authentication": "not provisioned or inspected",
              "emulated_time": "0 ms attributable; guest counter not measured; no emulator connection"}
    write_record(root / "probe.json", result)
    return {"archive": str(root), "probe_sha256": digest(root / "probe.json"), "decision": "BLOCKED"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--executable", required=True, type=Path)
    parser.add_argument("--checkout", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(probe(args.archive.absolute(), args.executable, args.checkout.resolve()), indent=2))
