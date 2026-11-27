"""Cheap, dependency-free host load sampling for qualification reports.

A shared research VM runs several campaigns at once, so a duration alone is not
evidence.  Every measurement in this package is stored next to the host
conditions observed while it was taken, and reports must not compare runs taken
under materially different load without saying so.

The Windows path uses ``ctypes`` only.  WMI and PowerShell are deliberately
avoided: both cost hundreds of milliseconds to seconds on a contended host and
would dominate the very measurement they describe.
"""

from __future__ import annotations

import ctypes
from dataclasses import dataclass
from datetime import datetime, timezone
import math
import os
import platform
import sys
import threading
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True)
class HostSample:
    """One observation of host-wide conditions.

    CPU percentages describe the interval since the previous sample of the same
    sampler, because Windows and Linux both expose cumulative counters.  The
    first sample of a session therefore has ``None`` CPU values.
    """

    at_utc: str
    cpu_total_percent: float | None = None
    cpu_user_percent: float | None = None
    cpu_system_percent: float | None = None
    memory_total_bytes: int | None = None
    memory_available_bytes: int | None = None
    commit_total_bytes: int | None = None
    commit_available_bytes: int | None = None
    process_count: int | None = None
    thread_count: int | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "at_utc": self.at_utc,
            "cpu_total_percent": self.cpu_total_percent,
            "cpu_user_percent": self.cpu_user_percent,
            "cpu_system_percent": self.cpu_system_percent,
            "memory_total_bytes": self.memory_total_bytes,
            "memory_available_bytes": self.memory_available_bytes,
            "commit_total_bytes": self.commit_total_bytes,
            "commit_available_bytes": self.commit_available_bytes,
            "process_count": self.process_count,
            "thread_count": self.thread_count,
        }


@dataclass(frozen=True)
class ProcessMemory:
    """Process-wide memory counters; peaks are high-water marks for the process.

    A field the platform cannot observe is ``None``.  Reporting a peak as if it
    were the current value, or zero as if it were a measurement, would be worse
    than reporting nothing.
    """

    working_set_bytes: int | None
    peak_working_set_bytes: int | None
    private_bytes: int | None

    def as_dict(self) -> dict[str, int | None]:
        return {
            "working_set_bytes": self.working_set_bytes,
            "peak_working_set_bytes": self.peak_working_set_bytes,
            "private_bytes": self.private_bytes,
        }


class _FILETIME(ctypes.Structure):
    _fields_ = [("dwLowDateTime", ctypes.c_uint32), ("dwHighDateTime", ctypes.c_uint32)]


class _MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_uint32),
        ("dwMemoryLoad", ctypes.c_uint32),
        ("ullTotalPhys", ctypes.c_uint64),
        ("ullAvailPhys", ctypes.c_uint64),
        ("ullTotalPageFile", ctypes.c_uint64),
        ("ullAvailPageFile", ctypes.c_uint64),
        ("ullTotalVirtual", ctypes.c_uint64),
        ("ullAvailVirtual", ctypes.c_uint64),
        ("ullAvailExtendedVirtual", ctypes.c_uint64),
    ]


class _PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", ctypes.c_uint32),
        ("cntUsage", ctypes.c_uint32),
        ("th32ProcessID", ctypes.c_uint32),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", ctypes.c_uint32),
        ("cntThreads", ctypes.c_uint32),
        ("th32ParentProcessID", ctypes.c_uint32),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", ctypes.c_uint32),
        ("szExeFile", ctypes.c_wchar * 260),
    ]


class _PROCESS_MEMORY_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("cb", ctypes.c_uint32),
        ("PageFaultCount", ctypes.c_uint32),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
    ]


class _PERFORMANCE_INFORMATION(ctypes.Structure):
    """``PERFORMANCE_INFORMATION``: host-wide totals, in pages."""

    _fields_ = [
        ("cb", ctypes.c_uint32),
        ("CommitTotal", ctypes.c_size_t),
        ("CommitLimit", ctypes.c_size_t),
        ("CommitPeak", ctypes.c_size_t),
        ("PhysicalTotal", ctypes.c_size_t),
        ("PhysicalAvailable", ctypes.c_size_t),
        ("SystemCache", ctypes.c_size_t),
        ("KernelTotal", ctypes.c_size_t),
        ("KernelPaged", ctypes.c_size_t),
        ("KernelNonpaged", ctypes.c_size_t),
        ("PageSize", ctypes.c_size_t),
        ("HandleCount", ctypes.c_uint32),
        ("ProcessCount", ctypes.c_uint32),
        ("ThreadCount", ctypes.c_uint32),
    ]


_TH32CS_SNAPPROCESS = 0x00000002
_INVALID_HANDLE = ctypes.c_void_p(-1).value
# ``Process32NextW`` reports normal exhaustion this way; any other error means
# the enumeration was cut short.
_ERROR_NO_MORE_FILES = 18


def _windows_times(idle_ticks: int, kernel_ticks: int, user_ticks: int) -> tuple[int, int, int]:
    """Turn ``GetSystemTimes`` output into non-overlapping ``(idle, user, system)``.

    The API's kernel time *includes* idle time. Summing the three raw counters
    therefore counts idle twice and overstates the busy share; subtracting it
    here keeps the result consistent with the POSIX counters.
    """
    return (idle_ticks, user_ticks, max(0, kernel_ticks - idle_ticks))


class _WindowsCounters:
    """Lazily bound Win32 calls.  Import-time failure is reported, never fatal."""

    def __init__(self) -> None:
        self.error: str | None = None
        try:
            self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            self.psapi = ctypes.WinDLL("psapi", use_last_error=True)
            self.kernel32.GlobalMemoryStatusEx.argtypes = [ctypes.POINTER(_MEMORYSTATUSEX)]
            self.kernel32.GlobalMemoryStatusEx.restype = ctypes.c_int
            self.kernel32.GetSystemTimes.argtypes = [
                ctypes.POINTER(_FILETIME), ctypes.POINTER(_FILETIME), ctypes.POINTER(_FILETIME),
            ]
            self.kernel32.GetSystemTimes.restype = ctypes.c_int
            self.kernel32.CreateToolhelp32Snapshot.argtypes = [ctypes.c_uint32, ctypes.c_uint32]
            self.kernel32.CreateToolhelp32Snapshot.restype = ctypes.c_void_p
            self.kernel32.Process32FirstW.argtypes = [
                ctypes.c_void_p, ctypes.POINTER(_PROCESSENTRY32W),
            ]
            self.kernel32.Process32FirstW.restype = ctypes.c_int
            self.kernel32.Process32NextW.argtypes = [
                ctypes.c_void_p, ctypes.POINTER(_PROCESSENTRY32W),
            ]
            self.kernel32.Process32NextW.restype = ctypes.c_int
            self.kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
            self.kernel32.CloseHandle.restype = ctypes.c_int
            self.kernel32.GetCurrentProcess.restype = ctypes.c_void_p
            self.psapi.GetProcessMemoryInfo.argtypes = [
                ctypes.c_void_p, ctypes.POINTER(_PROCESS_MEMORY_COUNTERS), ctypes.c_uint32,
            ]
            self.psapi.GetProcessMemoryInfo.restype = ctypes.c_int
            self.psapi.GetPerformanceInfo.argtypes = [
                ctypes.POINTER(_PERFORMANCE_INFORMATION), ctypes.c_uint32,
            ]
            self.psapi.GetPerformanceInfo.restype = ctypes.c_int
        except (OSError, AttributeError) as error:  # pragma: no cover - non-Windows
            self.error = f"{type(error).__name__}: {error}"

    def memory(self) -> tuple[int, int] | None:
        """Total and available physical memory.

        The page-file fields of ``MEMORYSTATUSEX`` describe this process's
        commit allowance, not the host's, so they are deliberately not returned
        as commit headroom.  ``performance()`` supplies the system-wide values.
        """
        status = _MEMORYSTATUSEX()
        status.dwLength = ctypes.sizeof(_MEMORYSTATUSEX)
        if not self.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return None
        return status.ullTotalPhys, status.ullAvailPhys

    def performance(self) -> dict[str, int] | None:
        """Host-wide commit headroom and process/thread counts.

        ``GetPerformanceInfo`` reports system-wide totals in pages.  It also
        gives the counts in the same call, so the toolhelp enumeration below is
        only a fallback.
        """
        info = _PERFORMANCE_INFORMATION()
        info.cb = ctypes.sizeof(_PERFORMANCE_INFORMATION)
        if not self.psapi.GetPerformanceInfo(ctypes.byref(info), info.cb):
            return None
        page = int(info.PageSize) or 4096
        return {
            "commit_total_bytes": int(info.CommitLimit) * page,
            "commit_available_bytes": max(0, int(info.CommitLimit) - int(info.CommitTotal)) * page,
            "process_count": int(info.ProcessCount),
            "thread_count": int(info.ThreadCount),
        }

    def system_times(self) -> tuple[int, int, int] | None:
        """Return non-overlapping ``(idle, user, busy_system)`` counters.

        ``GetSystemTimes`` reports kernel time *including* idle time, so the two
        must be separated here; summed as returned by the API they would count
        idle twice and overstate the busy share. The subtraction keeps this
        function's result consistent with the POSIX counters, which are already
        non-overlapping.
        """
        idle, kernel, user = _FILETIME(), _FILETIME(), _FILETIME()
        if not self.kernel32.GetSystemTimes(
            ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)
        ):
            return None
        return _windows_times(
            (idle.dwHighDateTime << 32) | idle.dwLowDateTime,
            (kernel.dwHighDateTime << 32) | kernel.dwLowDateTime,
            (user.dwHighDateTime << 32) | user.dwLowDateTime,
        )

    def process_totals(self) -> tuple[int, int] | None:
        """Count processes and threads, or report that the count is unknown.

        A failed enumeration must not read as an exhausted host: only
        ``ERROR_NO_MORE_FILES`` means the walk finished normally, and anything
        else returns ``None`` instead of a partial total.
        """
        snapshot = self.kernel32.CreateToolhelp32Snapshot(_TH32CS_SNAPPROCESS, 0)
        if snapshot in (None, _INVALID_HANDLE):
            return None
        entry = _PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(_PROCESSENTRY32W)
        processes = threads = 0
        try:
            if not self.kernel32.Process32FirstW(snapshot, ctypes.byref(entry)):
                return (0, 0) if ctypes.get_last_error() == _ERROR_NO_MORE_FILES else None
            while True:
                processes += 1
                threads += entry.cntThreads
                if not self.kernel32.Process32NextW(snapshot, ctypes.byref(entry)):
                    break
            if ctypes.get_last_error() != _ERROR_NO_MORE_FILES:
                return None
            return processes, threads
        finally:
            self.kernel32.CloseHandle(snapshot)

    def own_memory(self) -> ProcessMemory | None:
        counters = _PROCESS_MEMORY_COUNTERS()
        counters.cb = ctypes.sizeof(_PROCESS_MEMORY_COUNTERS)
        if not self.psapi.GetProcessMemoryInfo(
            self.kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb
        ):
            return None
        return ProcessMemory(
            working_set_bytes=int(counters.WorkingSetSize),
            peak_working_set_bytes=int(counters.PeakWorkingSetSize),
            private_bytes=int(counters.PagefileUsage),
        )


class _PosixCounters:
    """Minimal /proc reader; absent files simply yield ``None``."""

    error: str | None = None

    def _stat(self) -> tuple[int, int, int] | None:
        try:
            with open("/proc/stat", "r", encoding="ascii") as stream:
                fields = stream.readline().split()
        except OSError:
            return None
        if not fields or fields[0] != "cpu":
            return None
        values = [int(value) for value in fields[1:8]]
        while len(values) < 7:
            values.append(0)
        user, nice, system, idle, iowait, irq, softirq = values
        return (
            idle + iowait,
            user + nice + irq + softirq,
            system,
        )

    def _meminfo(self) -> dict[str, int]:
        values: dict[str, int] = {}
        try:
            with open("/proc/meminfo", "r", encoding="ascii") as stream:
                for line in stream:
                    key, _, rest = line.partition(":")
                    parts = rest.split()
                    if parts:
                        values[key] = int(parts[0]) * 1024
        except OSError:
            return {}
        return values

    def sample(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        times = self._stat()
        if times is not None:
            result["times"] = times
        memory = self._meminfo()
        if memory:
            result["memory_total_bytes"] = memory.get("MemTotal")
            available = memory.get("MemAvailable")
            result["memory_available_bytes"] = (
                available if available is not None else memory.get("MemFree")
            )
            result["commit_total_bytes"] = memory.get("CommitLimit")
            committed = memory.get("Committed_AS")
            limit = memory.get("CommitLimit")
            if committed is not None and limit is not None:
                result["commit_available_bytes"] = max(0, limit - committed)
        try:
            result["process_count"] = sum(
                1 for name in os.listdir("/proc") if name.isdigit()
            )
        except OSError:
            pass
        return result

    def own_memory(self) -> ProcessMemory | None:
        try:
            import resource
        except ImportError:  # pragma: no cover - exotic platform
            return None
        usage = resource.getrusage(resource.RUSAGE_SELF)
        peak = int(usage.ru_maxrss)
        # ``ru_maxrss`` is bytes on Darwin and kibibytes everywhere else; only
        # the peak is available here, so the current values stay unknown.
        if sys.platform != "darwin":
            peak *= 1024
        return ProcessMemory(working_set_bytes=None, peak_working_set_bytes=peak,
                              private_bytes=None)


class HostSampler:
    """Thread-safe host sampler; CPU percentages are deltas between calls."""

    def __init__(self) -> None:
        self.platform = sys.platform
        self.windows = self.platform == "win32"
        self._lock = threading.Lock()
        self._previous: tuple[int, int, int] | None = None
        self._windows: _WindowsCounters | None = None
        self._posix: _PosixCounters | None = None
        self.backend_error: str | None = None
        if self.windows:
            self._windows = _WindowsCounters()
            self.backend_error = self._windows.error
        else:
            self._posix = _PosixCounters()

    def sample(self) -> HostSample:
        with self._lock:
            if self._windows is not None and self._windows.error is None:
                return self._sample_windows(self._windows)
            if self._posix is not None:
                return self._sample_posix(self._posix)
            return HostSample(at_utc=_utc_now())

    def _sample_windows(self, counters: _WindowsCounters) -> HostSample:
        times = counters.system_times()
        total = user = system = None
        if times is not None:
            total, user, system = self._deltas(times)
        memory = counters.memory()
        performance = counters.performance()
        totals = counters.process_totals() if performance is None else None
        return HostSample(
            at_utc=_utc_now(),
            cpu_total_percent=total,
            cpu_user_percent=user,
            cpu_system_percent=system,
            memory_total_bytes=memory[0] if memory else None,
            memory_available_bytes=memory[1] if memory else None,
            commit_total_bytes=performance["commit_total_bytes"] if performance else None,
            commit_available_bytes=(performance["commit_available_bytes"]
                                    if performance else None),
            process_count=(performance["process_count"] if performance
                           else (totals[0] if totals else None)),
            thread_count=(performance["thread_count"] if performance
                          else (totals[1] if totals else None)),
        )

    def _sample_posix(self, counters: _PosixCounters) -> HostSample:
        raw = counters.sample()
        total = user = system = None
        times = raw.get("times")
        if times is not None:
            total, user, system = self._deltas(times)
        return HostSample(
            at_utc=_utc_now(),
            cpu_total_percent=total,
            cpu_user_percent=user,
            cpu_system_percent=system,
            memory_total_bytes=raw.get("memory_total_bytes"),
            memory_available_bytes=raw.get("memory_available_bytes"),
            commit_total_bytes=raw.get("commit_total_bytes"),
            commit_available_bytes=raw.get("commit_available_bytes"),
            process_count=raw.get("process_count"),
        )

    def _deltas(self, times: tuple[int, int, int]) -> tuple[float | None, float | None, float | None]:
        """Convert cumulative (idle, user, system) counters into percentages.

        The three counters must not overlap, so the total is their sum and the
        busy share is the total minus idle. Callers are responsible for
        separating idle from kernel time where the platform conflates them.
        """
        previous, self._previous = self._previous, times
        if previous is None:
            return None, None, None
        idle_delta = times[0] - previous[0]
        user_delta = times[1] - previous[1]
        system_delta = times[2] - previous[2]
        if idle_delta < 0 or user_delta < 0 or system_delta < 0:
            # One component moved backwards, so the interval cannot be turned
            # into percentages even if the overall delta stayed positive.  The
            # new values remain the baseline, so the next interval is
            # measurable rather than lost for the rest of the run.
            return None, None, None
        total_delta = idle_delta + user_delta + system_delta
        if total_delta <= 0:
            return None, None, None
        busy = total_delta - idle_delta
        return (
            round(100.0 * busy / total_delta, 2),
            round(100.0 * user_delta / total_delta, 2),
            round(100.0 * system_delta / total_delta, 2),
        )

    def process_memory(self) -> ProcessMemory | None:
        with self._lock:
            if self._windows is not None and self._windows.error is None:
                return self._windows.own_memory()
            if self._posix is not None:
                return self._posix.own_memory()
        return None


_DEFAULT_SAMPLER: HostSampler | None = None


def default_sampler() -> HostSampler:
    """One process-wide sampler, so CPU deltas are not double-counted."""
    global _DEFAULT_SAMPLER
    if _DEFAULT_SAMPLER is None:
        _DEFAULT_SAMPLER = HostSampler()
    return _DEFAULT_SAMPLER


def process_memory() -> ProcessMemory | None:
    return default_sampler().process_memory()


class HostTimeline:
    """Background sampler recording host conditions for the duration of a run.

    Sampling off the test thread keeps the per-test cost at zero, which matters
    because many portable tests complete in a few milliseconds.
    """

    def __init__(self, interval: float = 5.0, sampler: HostSampler | None = None) -> None:
        interval = float(interval)
        if not math.isfinite(interval) or interval <= 0:
            # Clamping would silently measure at a different interval than the
            # one the report records.
            raise ValueError(f"host sampling interval must be positive and finite, not {interval!r}")
        self.interval = interval
        # A timeline owns its baseline: sharing the process-wide sampler lets an
        # unrelated sample (a per-test one, or a previous run) consume the
        # interval this timeline meant to measure.
        self.sampler = sampler or HostSampler()
        self.samples: list[HostSample] = []
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._error: str | None = None
        self._failures = 0

    @property
    def error(self) -> str | None:
        """Why sampling stopped or degraded, if it did."""
        return self._error

    @property
    def failures(self) -> int:
        """Number of samples that raised, so partial coverage is visible."""
        return self._failures

    def __enter__(self) -> "HostTimeline":
        self.samples.append(self.sampler.sample())
        self._thread = threading.Thread(target=self._run, name="host-timeline", daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *_exc: object) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=max(2.0, self.interval))
        self.samples.append(self.sampler.sample())

    def _run(self) -> None:
        while not self._stop.wait(self.interval):
            try:
                self.samples.append(self.sampler.sample())
            except Exception as error:  # pragma: no cover - defensive
                # Keep sampling: one bad interval should not end the timeline,
                # but the report must say coverage was imperfect.  Only the
                # exception class is kept, never its message.
                self._failures += 1
                self._error = type(error).__name__


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return round(ordered[middle], 3)
    return round((ordered[middle - 1] + ordered[middle]) / 2.0, 3)


def summarize_samples(samples: list[HostSample]) -> dict[str, Any]:
    """Reduce a host timeline to comparable, explicitly-labelled statistics."""
    def column(name: str) -> list[float]:
        return [
            float(value) for value in (getattr(sample, name) for sample in samples)
            if value is not None
        ]

    cpu = column("cpu_total_percent")
    available = column("memory_available_bytes")
    processes = column("process_count")
    threads = column("thread_count")
    total_memory = [value for value in column("memory_total_bytes") if value > 0]
    return {
        "samples": len(samples),
        "first_utc": samples[0].at_utc if samples else None,
        "last_utc": samples[-1].at_utc if samples else None,
        "cpu_total_percent": {
            "mean": round(sum(cpu) / len(cpu), 2) if cpu else None,
            "median": _median(cpu),
            "max": round(max(cpu), 2) if cpu else None,
            "min": round(min(cpu), 2) if cpu else None,
        },
        "memory_available_bytes": {
            "mean": round(sum(available) / len(available)) if available else None,
            "min": int(min(available)) if available else None,
        },
        "memory_total_bytes": int(max(total_memory)) if total_memory else None,
        "process_count": {
            "mean": round(sum(processes) / len(processes), 1) if processes else None,
            "max": int(max(processes)) if processes else None,
        },
        "thread_count": {
            "mean": round(sum(threads) / len(threads), 1) if threads else None,
            "max": int(max(threads)) if threads else None,
        },
    }


def describe_environment() -> dict[str, Any]:
    """Identity of the interpreter and machine a report was produced on."""
    import locale
    import multiprocessing

    return {
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "cpu_count": multiprocessing.cpu_count(),
        "preferred_encoding": locale.getpreferredencoding(False),
        "python_utf8_mode": bool(sys.flags.utf8_mode),
        "python_dont_write_bytecode": bool(sys.dont_write_bytecode),
    }
