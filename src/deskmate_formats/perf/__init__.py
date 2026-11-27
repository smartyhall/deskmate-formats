"""Reusable performance qualification for the portable test suite.

The modules here are deliberately dependency-free: they use ``ctypes`` for
Windows host metrics and standard-library fallbacks elsewhere.  Nothing in this
package changes test semantics; it only observes them.

Entry points:

- ``python -m deskmate_formats.perf run``       instrumented test run
- ``python -m deskmate_formats.perf microbench`` bounded host microbenchmarks
- ``python -m deskmate_formats.perf compare``   before/after report comparison
"""

from .hostload import HostSample, HostSampler, process_memory, summarize_samples

__all__ = ["HostSample", "HostSampler", "process_memory", "summarize_samples"]
