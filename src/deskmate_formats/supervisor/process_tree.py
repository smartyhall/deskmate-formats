"""Bounded read-only process-tree inspection.

Killing an owner process does not kill what it started. On POSIX an orphan is
reparented to init, so the parent chain is useless after death; the runner puts
each attempt in its own session, so the session identifier is the durable
handle. On Windows ``ParentProcessId`` is a static field that survives the
parent, so the chain itself is the handle.

This module is read-only: it opens no process handle for control, sends no
signal and starts nothing. Every scan is bounded by a process-count cap and a
deadline, and an incomplete scan is reported as ``unknown`` rather than
``stopped``: not finding a descendant is not proof that none exists.
"""

import os
from pathlib import Path
import sys
from time import monotonic

from deskmate_formats.observer.process_health import process_status, verify_process

MAX_PROCESSES = 8192
SCAN_DEADLINE_SECONDS = 3.0

if sys.platform == "win32":
    import ctypes as ct
    from ctypes import wintypes as wt

    _TH32CS_SNAPPROCESS = 0x00000002
    _kernel = ct.WinDLL("kernel32", use_last_error=True)

    class _Entry(ct.Structure):
        _fields_ = (("dwSize", wt.DWORD), ("cntUsage", wt.DWORD),
                    ("th32ProcessID", wt.DWORD), ("th32DefaultHeapID", ct.c_void_p),
                    ("th32ModuleID", wt.DWORD), ("cntThreads", wt.DWORD),
                    ("th32ParentProcessID", wt.DWORD), ("pcPriClassBase", ct.c_long),
                    ("dwFlags", wt.DWORD), ("szExeFile", wt.WCHAR * 260))

    _kernel.CreateToolhelp32Snapshot.argtypes = (wt.DWORD, wt.DWORD)
    _kernel.CreateToolhelp32Snapshot.restype = wt.HANDLE
    _kernel.Process32FirstW.argtypes = (wt.HANDLE, ct.POINTER(_Entry))
    _kernel.Process32NextW.argtypes = (wt.HANDLE, ct.POINTER(_Entry))
    _kernel.Process32FirstW.restype = wt.BOOL
    _kernel.Process32NextW.restype = wt.BOOL
    _kernel.CloseHandle.argtypes = (wt.HANDLE,)

    def _parent_map():
        """Return ``{pid: parent}`` or ``None`` if the snapshot is unavailable."""
        snapshot = _kernel.CreateToolhelp32Snapshot(_TH32CS_SNAPPROCESS, 0)
        if snapshot == wt.HANDLE(-1).value or snapshot == 2**64 - 1:
            return None
        try:
            entry = _Entry()
            entry.dwSize = ct.sizeof(_Entry)
            if not _kernel.Process32FirstW(snapshot, ct.byref(entry)):
                return None
            parents = {}
            while len(parents) < MAX_PROCESSES:
                parents[int(entry.th32ProcessID)] = int(entry.th32ParentProcessID)
                if not _kernel.Process32NextW(snapshot, ct.byref(entry)):
                    break
            return parents
        finally:
            _kernel.CloseHandle(snapshot)

    def _absent_below(pid):
        return None

    def _descendants(claim, deadline):
        parents = _parent_map()
        if parents is None:
            return None, False
        root = claim["pid"]
        found, frontier = [], [root]
        while frontier and monotonic() < deadline and len(found) < MAX_PROCESSES:
            current = frontier.pop()
            for child, parent in parents.items():
                if parent == current and child != current and child not in found:
                    found.append(child)
                    frontier.append(child)
        return found, len(found) < MAX_PROCESSES

else:
    def _absent_below(pid):
        """The session id of a live process, used as the durable tree handle."""
        try:
            return os.getsid(pid)
        except (OSError, AttributeError):
            return None

    def _descendants(claim, deadline):
        """Match the recorded session, which survives reparenting."""
        session = claim.get("session")
        if session is None:
            return None, False
        found, complete, scanned = [], True, 0
        try:
            entries = os.listdir("/proc")
        except OSError:
            return None, False
        for name in entries:
            if not name.isdigit():
                continue
            scanned += 1
            if scanned > MAX_PROCESSES or monotonic() >= deadline:
                complete = False
                break
            try:
                with open(f"/proc/{name}/stat", "rb") as stream:
                    data = stream.read(8192)
            except OSError:
                continue
            fields = data.rpartition(b") ")[2].split()
            # state, ppid, pgrp, session, tty, tpgid, ...
            if len(fields) < 6:
                continue
            if fields[3].isdigit() and int(fields[3]) == session and fields[0] not in (b"Z", b"X", b"x"):
                found.append(int(name))
        return found, complete


def tree_claim(pid=None):
    """Claim an owner plus the durable handle for its future descendants."""
    pid = os.getpid() if pid is None else pid
    if type(pid) is not int or not 1 <= pid < 2**31:
        raise ValueError("invalid PID")
    identity, status = _owner_sample(pid)
    if identity is None or status != "alive":
        return None
    claim = {"pid": pid, "identity": identity}
    # A session id is only a usable tree handle when the process leads its own
    # session. Recording the shared session of an ordinary shell process would
    # make every sibling look like a descendant.
    session = None if sys.platform == "win32" else _absent_below(pid)
    if session is not None and session == pid:
        claim["session"] = session
        claim["scope"] = "session"
    else:
        claim["scope"] = "process"
    return claim


def live_pids(claim, *, deadline_seconds=SCAN_DEADLINE_SECONDS):
    """PIDs still alive in the recorded tree, for inspection and cleanup."""
    pid = claim.get("pid") if type(claim) is dict else None
    if type(pid) is not int or not 1 <= pid < 2**31:
        return []
    found, complete = _descendants(claim, monotonic() + deadline_seconds)
    if not complete:
        return []
    return [pid for pid in found if process_status(pid) == "alive"]


def _owner_sample(pid):
    from deskmate_formats.observer import process_health

    return process_health._sample(pid)


def tree_state(claim, *, deadline_seconds=SCAN_DEADLINE_SECONDS):
    """Report the owner separately from its descendants.

    ``descendants`` is ``stopped`` only when a complete scan found none.
    ``unknown`` means the scan could not be trusted, which must never be read
    as proof that nothing is still running.
    """
    pid = claim.get("pid") if type(claim) is dict else None
    if type(pid) is not int or not 1 <= pid < 2**31:
        return {"owner": "unknown", "descendants": "unknown", "live": None}
    owner = verify_process(pid, claim.get("identity"))
    deadline = monotonic() + deadline_seconds
    found, complete = _descendants(claim, deadline)
    if not complete:
        return {"owner": owner, "descendants": "unknown", "live": None}
    alive = [pid for pid in found if process_status(pid) == "alive"]
    if alive:
        return {"owner": owner, "descendants": "alive", "live": len(alive)}
    return {"owner": owner,
            "descendants": "not-found" if owner == "not-found" else "stopped",
            "live": 0}


def stopped(claim, *, deadline_seconds=SCAN_DEADLINE_SECONDS):
    """True only when the owner and every descendant are positively gone."""
    state = tree_state(claim, deadline_seconds=deadline_seconds)
    return (state["owner"] in ("stopped", "not-found")
            and state["descendants"] in ("stopped", "not-found"))


def session_of(pid):
    """Public helper for tests that need the durable handle of a live process."""
    return None if sys.platform == "win32" else _absent_below(pid)


def worktree_root():
    """Diagnostic helper: the canonical location of this checkout, if any."""
    return Path(__file__).resolve().parents[3]
