"""A disposable executable stand-in that emits bytes and never runs fixture commands."""

import argparse
import os
from pathlib import Path
import signal
import subprocess
import sys
from time import monotonic, sleep


def child_command(fixture, *options):
    # A Windows venv redirector would hold the pipe independently of the child.
    return [sys._base_executable, __file__, "emit", str(fixture), *options]


def wrapper_command(journal, fixture, *options, visible=True):
    return [sys.executable, __file__, "capture", str(journal),
            "observer" if visible else "private", str(fixture), *options]


def emit(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("fixture", type=Path)
    parser.add_argument("--exit", type=int, default=0)
    parser.add_argument("--interrupt", action="store_true")
    parser.add_argument("--tail", action="store_true")
    parser.add_argument("--close-stdout", action="store_true")
    parser.add_argument("--gate", type=Path)
    parser.add_argument("--hold-inherited-stdout", action="store_true")
    args = parser.parse_args(argv)
    sys.stdout.buffer.write(args.fixture.read_bytes())
    if args.tail:
        sys.stdout.buffer.write(b'{"type":"error","message":"missing final LF"}')
    sys.stdout.buffer.flush()
    print("synthetic child stderr", file=sys.stderr, flush=True)
    if args.hold_inherited_stdout:
        subprocess.Popen([sys.executable, "-c", "import time; time.sleep(3)"], stdin=subprocess.DEVNULL)
    if args.close_stdout:
        fd = sys.stdout.fileno()
        if os.name == "nt":
            # Close the inherited Win32 standard handle when it is distinct
            # from the C runtime descriptor used by Python.
            from ctypes import WinDLL, wintypes
            import msvcrt

            kernel = WinDLL("kernel32", use_last_error=True)
            kernel.GetStdHandle.argtypes = (wintypes.DWORD,)
            kernel.GetStdHandle.restype = wintypes.HANDLE
            kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
            inherited = kernel.GetStdHandle(-11)
            if inherited and inherited != msvcrt.get_osfhandle(fd):
                kernel.CloseHandle(inherited)
        os.close(fd)
    if args.gate is not None:
        until = monotonic() + 15
        while not args.gate.exists() and monotonic() < until:
            sleep(0.02)
    if args.interrupt:
        if os.name == "nt":
            from ctypes import WinDLL, wintypes
            exit_process = WinDLL("kernel32").ExitProcess
            exit_process.argtypes = (wintypes.DWORD,)
            exit_process(0xC000013A)
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        os.kill(os.getpid(), signal.SIGINT)
    os._exit(args.exit)


if __name__ == "__main__":
    mode, *arguments = sys.argv[1:]
    if mode == "emit":
        emit(arguments)
    else:
        from deskmate_formats.observer.codex_cli import _raw_stdout, capture_codex
        from deskmate_formats.observer.codex_exec import SUPPORTED_VERSION

        journal, visibility, fixture, *options = arguments
        forward = "--raw-stdout" in options
        if forward:
            options.remove("--raw-stdout")
        result = capture_codex(child_command(fixture, *options), journal,
                               version=SUPPORTED_VERSION, visibility=visibility,
                               raw_output=_raw_stdout() if forward else None)
        raise SystemExit(result)
