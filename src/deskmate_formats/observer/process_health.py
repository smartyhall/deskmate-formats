"""Read-only local process identity checks. No subprocesses or control handles."""

from functools import cache
import os
from pathlib import Path
import sys

if sys.platform == "win32":
    import ctypes as ct
    from ctypes import wintypes as wt

    _kernel = ct.WinDLL("kernel32", use_last_error=True)
    _kernel.OpenProcess.argtypes = (wt.DWORD, wt.BOOL, wt.DWORD)
    _kernel.OpenProcess.restype = wt.HANDLE
    _kernel.CloseHandle.argtypes = (wt.HANDLE,)
    _kernel.GetProcessTimes.argtypes = (wt.HANDLE, *(ct.POINTER(wt.FILETIME),) * 4)
    _kernel.WaitForSingleObject.argtypes = (wt.HANDLE, wt.DWORD)
    _kernel.WaitForSingleObject.restype = wt.DWORD

    def _sample(pid):
        handle = _kernel.OpenProcess(0x1000 | 0x100000, False, pid)  # QUERY_LIMITED_INFORMATION | SYNCHRONIZE
        if not handle:
            return None, "not-found" if ct.get_last_error() == 87 else "unknown"
        try:
            creation, exit_time, kernel, user = (wt.FILETIME() for _ in range(4))
            if not _kernel.GetProcessTimes(handle, *(ct.byref(item) for item in (creation, exit_time, kernel, user))):
                return None, "unknown"
            wait = _kernel.WaitForSingleObject(handle, 0)
            status = {0: "stopped", 258: "alive"}.get(wait, "unknown")
            stamp = creation.dwHighDateTime << 32 | creation.dwLowDateTime
            return f"win-{stamp:x}", status
        finally:
            _kernel.CloseHandle(handle)

elif sys.platform == "linux":
    @cache
    def _boot_id():
        return Path("/proc/sys/kernel/random/boot_id").read_text(encoding="ascii").strip().replace("-", "")

    def _sample(pid):
        try:
            boot = _boot_id()
        except (OSError, ValueError):
            return None, "unknown"
        try:
            with Path(f"/proc/{pid}/stat").open("rb") as stream:
                data = stream.read(8192)
        except FileNotFoundError:
            return None, "not-found"
        except OSError:
            return None, "unknown"
        # The parenthesized command may contain spaces and parentheses.
        fields = data.rpartition(b") ")[2].split()
        if len(fields) < 20 or not fields[19].isdigit():
            return None, "unknown"
        return f"linux-{boot}-{fields[19].decode('ascii')}", "stopped" if fields[0] in (b"Z", b"X", b"x") else "alive"

else:
    def _sample(pid):
        return None, "unknown"


def process_claim(pid=None):
    """Return a claim for a live local PID, or None if it cannot be sampled."""
    pid = os.getpid() if pid is None else pid
    if type(pid) is not int or not 1 <= pid < 2**31:
        raise ValueError("invalid PID")
    identity, status = _sample(pid)
    return {"pid": pid, "identity": identity} if status == "alive" else None


def verify_process(pid, expected_identity):
    identity, status = _sample(pid)
    if identity is not None and identity != expected_identity:
        return "identity-mismatch"
    return status
