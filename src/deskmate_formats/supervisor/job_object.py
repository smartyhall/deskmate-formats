"""Experimental Windows Job Object containment.

A static ``ParentProcessId`` is a poor custody handle: it survives the parent but
also survives reuse of the parent's number, and it says nothing about whether a
process is still running. A Job Object is stronger in three ways that matter to
deterministic procedures:

* membership is held by the operating system, not by a parent-child field, so a
  descendant stays a member after its parent exits;
* termination is requested for the whole membership at once;
* ``ActiveProcesses`` is a positive count of members that are still running, so
  "the tree is empty" is reported by the object instead of inferred.

What this module does *not* provide is a sandbox: a member may still write to
the filesystem, and a process that is allowed to break away leaves the job.

This is an experiment, qualified only on the local Windows host. On other
platforms every entry point reports that it is unavailable rather than
pretending to contain anything.
"""

import os
import sys

AVAILABLE = sys.platform == "win32"
REASON = "not-windows" if not AVAILABLE else None

_JOB_OBJECT_BASIC_ACCOUNTING_INFORMATION = 1
_JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9
_JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
_PROCESS_SET_QUOTA = 0x0100
_PROCESS_TERMINATE = 0x0001

if AVAILABLE:
    import ctypes as ct
    from ctypes import wintypes as wt

    _kernel = ct.WinDLL("kernel32", use_last_error=True)

    class _BasicLimit(ct.Structure):
        _fields_ = (("PerProcessUserTimeLimit", ct.c_int64),
                    ("PerJobUserTimeLimit", ct.c_int64),
                    ("LimitFlags", wt.DWORD),
                    ("MinimumWorkingSetSize", ct.c_size_t),
                    ("MaximumWorkingSetSize", ct.c_size_t),
                    ("ActiveProcessLimit", wt.DWORD),
                    ("Affinity", ct.c_size_t),
                    ("PriorityClass", wt.DWORD),
                    ("SchedulingClass", wt.DWORD))

    class _IoCounters(ct.Structure):
        _fields_ = tuple((name, ct.c_uint64) for name in (
            "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
            "ReadTransferCount", "WriteTransferCount", "OtherTransferCount"))

    class _ExtendedLimit(ct.Structure):
        _fields_ = (("BasicLimitInformation", _BasicLimit), ("IoInfo", _IoCounters),
                    ("ProcessMemoryLimit", ct.c_size_t), ("JobMemoryLimit", ct.c_size_t),
                    ("PeakProcessMemoryUsed", ct.c_size_t),
                    ("PeakJobMemoryUsed", ct.c_size_t))

    class _Accounting(ct.Structure):
        _fields_ = (("TotalUserTime", ct.c_int64), ("TotalKernelTime", ct.c_int64),
                    ("ThisPeriodTotalUserTime", ct.c_int64),
                    ("ThisPeriodTotalKernelTime", ct.c_int64),
                    ("TotalPageFaultCount", wt.DWORD), ("TotalProcesses", wt.DWORD),
                    ("ActiveProcesses", wt.DWORD), ("TotalTerminatedProcesses", wt.DWORD))

    _kernel.CreateJobObjectW.argtypes = (ct.c_void_p, wt.LPCWSTR)
    _kernel.CreateJobObjectW.restype = wt.HANDLE
    _kernel.SetInformationJobObject.argtypes = (wt.HANDLE, ct.c_int, ct.c_void_p, wt.DWORD)
    _kernel.SetInformationJobObject.restype = wt.BOOL
    _kernel.QueryInformationJobObject.argtypes = (wt.HANDLE, ct.c_int, ct.c_void_p,
                                                  wt.DWORD, ct.c_void_p)
    _kernel.QueryInformationJobObject.restype = wt.BOOL
    _kernel.AssignProcessToJobObject.argtypes = (wt.HANDLE, wt.HANDLE)
    _kernel.AssignProcessToJobObject.restype = wt.BOOL
    _kernel.TerminateJobObject.argtypes = (wt.HANDLE, wt.UINT)
    _kernel.TerminateJobObject.restype = wt.BOOL
    _kernel.OpenProcess.argtypes = (wt.DWORD, wt.BOOL, wt.DWORD)
    _kernel.OpenProcess.restype = wt.HANDLE
    _kernel.CloseHandle.argtypes = (wt.HANDLE,)
    _kernel.CloseHandle.restype = wt.BOOL

    _ERROR_ACCESS_DENIED = 5
    _ERROR_INVALID_PARAMETER = 87


class JobError(RuntimeError):
    """A job operation failed; ``reason`` is a stable machine-readable value."""

    def __init__(self, reason, detail=None):
        super().__init__(reason if detail is None else f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


def _unavailable():
    raise JobError("job-objects-unavailable", REASON)


if AVAILABLE:
    class Job:
        """One owned job object. Closing it terminates every remaining member."""

        def __init__(self, *, kill_on_close=True):
            handle = _kernel.CreateJobObjectW(None, None)
            if not handle:
                raise JobError("create-failed", ct.get_last_error())
            self._handle = handle
            self._closed = False
            if kill_on_close:
                limit = _ExtendedLimit()
                limit.BasicLimitInformation.LimitFlags = _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
                if not _kernel.SetInformationJobObject(
                        handle, _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
                        ct.byref(limit), ct.sizeof(limit)):
                    error = ct.get_last_error()
                    _kernel.CloseHandle(handle)
                    self._closed = True
                    raise JobError("limit-failed", error)

        def __enter__(self):
            return self

        def __exit__(self, *_):
            self.close()
            return False

        def assign(self, pid):
            """Add one process to the job.

            The caller is responsible for assigning before the process can spawn
            a child; spawning it suspended is the only race-free form.
            """
            if self._closed:
                raise JobError("job-closed")
            handle = _kernel.OpenProcess(_PROCESS_SET_QUOTA | _PROCESS_TERMINATE, False, pid)
            if not handle:
                error = ct.get_last_error()
                raise JobError("process-unavailable" if error == _ERROR_INVALID_PARAMETER
                               else "process-denied", error)
            try:
                if not _kernel.AssignProcessToJobObject(self._handle, handle):
                    error = ct.get_last_error()
                    # A process that already belongs to a non-nestable job, or a
                    # protected process, cannot be adopted. Report it; never
                    # assume containment that was refused.
                    raise JobError("assign-denied" if error == _ERROR_ACCESS_DENIED
                                   else "assign-failed", error)
            finally:
                _kernel.CloseHandle(handle)
            return self

        def state(self):
            """Return the job's own accounting, or ``None`` if it is unavailable.

            ``active`` is a positive count of members the object still owns. That
            is the observation a static parent chain cannot provide.
            """
            if self._closed:
                return None
            info = _Accounting()
            if not _kernel.QueryInformationJobObject(
                    self._handle, _JOB_OBJECT_BASIC_ACCOUNTING_INFORMATION,
                    ct.byref(info), ct.sizeof(info), None):
                return None
            return {"total": int(info.TotalProcesses), "active": int(info.ActiveProcesses),
                    "terminated": int(info.TotalTerminatedProcesses)}

        def terminate(self):
            """Terminate every member, then report what the object still owns."""
            if self._closed:
                raise JobError("job-closed")
            if not _kernel.TerminateJobObject(self._handle, 1):
                raise JobError("terminate-failed", ct.get_last_error())
            return self.state()

        def close(self):
            """Close the handle. With ``kill_on_close`` this terminates members."""
            if self._closed:
                return
            self._closed = True
            _kernel.CloseHandle(self._handle)

        @property
        def closed(self):
            return self._closed
else:
    class Job:  # pragma: no cover - the whole class is unreachable off Windows
        def __init__(self, **_):
            _unavailable()

        def __enter__(self):
            _unavailable()

        def __exit__(self, *_):
            return False

        def assign(self, pid):
            _unavailable()

        def state(self):
            _unavailable()

        def terminate(self):
            _unavailable()

        def close(self):
            return None

        @property
        def closed(self):
            return True


def containment(claim, *, deadline_seconds=3.0):
    """Express a process-tree claim as the question a job object answers.

    Returns the shape the rest of the Supervisor already understands, with the
    honest difference that a job's gate is ``active == 0`` rather than an empty
    session scan. A claim that never obtained a job handle reports ``unknown``.
    """
    job = claim.get("job") if type(claim) is dict else None
    if not AVAILABLE or type(job) is not Job:
        return {"descendants": "unknown", "enumeration": "unavailable",
                "reason": "no-job-handle"}
    state = job.state()
    if state is None:
        return {"descendants": "unknown", "enumeration": "unavailable",
                "reason": "job-accounting-unavailable"}
    if state["active"]:
        return {"descendants": "alive", "enumeration": "complete",
                "reason": "job-members-active", "remaining": state["active"]}
    return {"descendants": "stopped", "enumeration": "complete",
            "reason": "job-membership-empty", "remaining": 0}


def supported():
    """Whether this host can provide job-object containment at all."""
    if not AVAILABLE:
        return False, REASON
    return True, None


def _selftest_pid():
    """Diagnostic helper: the current process id, for ad-hoc experiments."""
    return os.getpid()
