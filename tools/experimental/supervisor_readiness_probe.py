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
import shutil
import stat
import subprocess
import sys
from time import monotonic
from uuid import UUID

from deskmate_formats.observer._private_storage import private_file, storage_directory
from deskmate_formats.supervisor.driver import NATIVE_SHA256, digest, write_record
from deskmate_formats.supervisor.protocol import PROFILE_SHA256, VERSION


def policy_presence(path):
    # exists() can suppress inspection errors. Only a missing path means absent.
    try:
        if os.name == "nt":
            kernel = ct.WinDLL("kernel32", use_last_error=True)
            kernel.GetDriveTypeW.argtypes = (wt.LPCWSTR,)
            kernel.GetDriveTypeW.restype = wt.UINT
            if kernel.GetDriveTypeW(path.anchor) != 3:
                raise ValueError("nonlocal policy path; presence remains unknown")
            # Do not follow policy-path junctions to remote or unreviewed targets.
            for component in reversed((path, *path.parents)):
                if component.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                    raise ValueError("redirected policy path; presence remains unknown")
        path.stat()
    except FileNotFoundError:
        return False
    return True


def requirements_path(value, kind):
    # Do not expand an environment string using this process's ambient secrets.
    # The pinned source requires an absolute path; unsupported types are unknown.
    if kind not in (1, 2) or not isinstance(value, str) or not Path(value).is_absolute() or "\0" in value:
        raise ValueError("unsupported requirements registry path; policy remains unknown")
    return Path(value)


def check_schemas(inventories, expected):
    if inventories[0] != inventories[1] or inventories[0] != expected or expected["profile_sha256"] != PROFILE_SHA256:
        raise ValueError("offline schema drift; preserve exports and do not launch")


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
            value, kind = winreg.QueryValueEx(key, "RequirementsPath")
            requirements = requirements_path(value, kind)
            override = True
    except FileNotFoundError:
        pass
    return [system / "config.toml", requirements], override


def probe(root, executable, checkout):
    root, checkout = Path(root).absolute(), Path(checkout).resolve()
    executable = Path(executable)
    if sys.platform != "win32" or os.path.lexists(root):
        raise ValueError("requires Windows and a fresh private archive directory")
    if (not executable.is_absolute() or executable.suffix.lower() != ".exe"
            or executable.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT
            or digest(executable) != NATIVE_SHA256):
        raise ValueError("native executable pin mismatch; nothing executed")
    executable = str(executable.resolve())
    root = storage_directory(root, create=True)
    for name in ("home", "scratch"):
        storage_directory(root / name, create=True)
    env = {k: os.environ[k] for k in ("SystemRoot", "WINDIR") if k in os.environ}
    env.update(CODEX_HOME=str(root / "home"), HOME=str(root / "home"), USERPROFILE=str(root / "home"),
               TEMP=str(root / "scratch"), TMP=str(root / "scratch"))
    commands = []

    def command(argv, *, sanitized=False):
        start = monotonic()
        failure = None
        try:
            result = subprocess.run(argv, cwd=root / "scratch" if sanitized else checkout,
                                    env=env if sanitized else None, capture_output=True, timeout=60,
                                    creationflags=subprocess.CREATE_NO_WINDOW)
            stdout, stderr, returncode = result.stdout, result.stderr, result.returncode
        except (OSError, subprocess.TimeoutExpired) as error:
            failure = type(error).__name__
            stdout, stderr, returncode = getattr(error, "stdout", None) or b"", getattr(error, "stderr", None) or b"", None
        number = len(commands) + 1
        for label, data in (("stdout", stdout), ("stderr", stderr)):
            with private_file(root / f"{number:02d}-{label}.txt", write=True) as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
        receipt = {"argv": argv, "sanitized_environment": sanitized, "returncode": returncode, "failure": failure,
                   "elapsed_host_seconds": monotonic() - start,
                   "stdout_sha256": digest(root / f"{number:02d}-stdout.txt"),
                   "stderr_sha256": digest(root / f"{number:02d}-stderr.txt")}
        commands.append(receipt)
        write_record(root / f"command-{number:02d}.json", receipt)
        if returncode != 0:
            raise RuntimeError("offline command failed; preserve archive")
        return stdout

    git = shutil.which("git")
    if git is None:
        raise ValueError("Git unavailable; no PATH fallback")
    revision = command([git, "-C", str(checkout), "rev-parse", "HEAD"], sanitized=True).decode().strip()
    command([git, "-C", str(checkout), "status", "--short"], sanitized=True)
    version = command([executable, "--version"], sanitized=True).decode().strip()
    if version != f"codex-cli {VERSION}":
        raise ValueError("native version mismatch; preserve archive")
    inventories = []
    for number in (1, 2):
        export = root / f"schema-{number}"
        command([executable, "app-server", "generate-json-schema", "--out", str(export)], sanitized=True)
        profile, inventory = root / f"profile-{number}.json", root / f"inventory-{number}.json"
        command([sys.executable, "-I", str(checkout / "tools/pin_app_server_schema.py"),
                 str(export), str(profile), str(inventory)], sanitized=True)
        inventories.append(json.loads(inventory.read_bytes()))
    check_schemas(inventories, json.loads((checkout / "docs/research/codex-app-server-0.166.0.json").read_bytes()))
    policy_paths, registry_override = windows_policy_paths()
    ancestor_paths = [parent / ".codex" / "config.toml" for parent in (root / "scratch", *(root / "scratch").parents)]
    # No credential values or configuration contents are emitted/read here.
    paths = [{"path": str(path), "present": policy_presence(path)} for path in policy_paths + ancestor_paths]
    result = {"git_revision": revision, "native_version": version, "native_sha256": digest(executable),
              "native_path": executable, "platform": platform.platform(), "python": sys.version,
              "environment": env, "configuration_path_presence_only": paths,
              "requirements_registry_override": registry_override,
              "schema_exports_equal": inventories[0] == inventories[1],
              "schema_matches_committed": True,
              "probe_source_sha256": digest(Path(__file__)),
              "schema_generator_source_sha256": digest(checkout / "tools/pin_app_server_schema.py"),
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
