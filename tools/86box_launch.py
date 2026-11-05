"""Launch a private Windows research machine, visibly by default, held at 0 ms.

All guest control remains in 86box_client. No GUI clicks, host key injection,
cross-session launch, token printing or emulator modifications are performed.
"""
import argparse
import configparser
import ctypes
from ctypes import wintypes
import hashlib
import importlib
import json
import os
from pathlib import Path
import socket
import stat
import subprocess
import sys
import time
import uuid

Client = importlib.import_module('86box_client').Client
ROOT = Path(__file__).resolve().parents[1]
MODES = ('visible', 'headless', 'background')


def command(executable, machine, global_config, port, seed):
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError('invalid loopback port')
    if type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError('seed must be an unsigned 32-bit integer')
    return [str(executable), '--vmpath', str(machine), '--global', str(global_config),
            '--automation', f'tcp:127.0.0.1:{port}', '--automation-hold',
            '--automation-seed', str(seed), '--nohook']


def child_environment(runtime, mode, environment=None):
    if mode not in MODES:
        raise ValueError('unknown display mode')
    env = dict(os.environ if environment is None else environment)
    env['PATH'] = str(runtime) + os.pathsep + env.get('PATH', '')
    env['QT_QPA_PLATFORM'] = 'offscreen' if mode == 'headless' else 'windows'
    return env


def observer_preferences(machine, run):
    """Back up before changing only host input preferences on a working profile."""
    cfg = machine / '86box.cfg'
    if (machine / 'baseline-manifest.json').exists() or not cfg.stat().st_mode & stat.S_IWRITE:
        raise ValueError('clone the sealed/read-only baseline into a writable working directory')
    original = cfg.read_bytes()
    parser = configparser.ConfigParser(interpolation=None)
    parser.read_string(original.decode('utf-8-sig'))
    # This revision's keyboard_input() applies the capture gate to socket keys too.
    # Keep the proven uncaptured socket path; --nohook and SW_SHOWNOACTIVATE
    # reduce host interference without claiming a host-input firewall.
    wanted = {'General': {'kbd_req_capture': '0'},
              'Input devices': {'mouse_input_mode_initial': '0'}}
    changed = any(not parser.has_option(s, k) or parser[s][k] != v
                  for s, fields in wanted.items() for k, v in fields.items())
    if changed:
        with (run / '86box.cfg.before').open('xb') as out:
            out.write(original)
        for section, fields in wanted.items():
            if not parser.has_section(section):
                parser.add_section(section)
            parser[section].update(fields)
        with cfg.open('w', encoding='utf-8', newline='\n') as out:
            parser.write(out)
    return hashlib.sha256(cfg.read_bytes()).hexdigest()


def windows_state(pid):
    """Read-only Win32 diagnostics, independent of .NET MainWindowHandle caching."""
    if os.name != 'nt':
        raise OSError('window diagnostics require Windows')
    user = ctypes.WinDLL('user32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.ProcessIdToSessionId.argtypes = [wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    kernel.ProcessIdToSessionId.restype = wintypes.BOOL
    session = wintypes.DWORD()
    if not kernel.ProcessIdToSessionId(pid, ctypes.byref(session)):
        raise ctypes.WinError(ctypes.get_last_error())
    user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user.GetWindowThreadProcessId.restype = wintypes.DWORD
    user.IsWindowVisible.argtypes = [wintypes.HWND]
    user.IsWindowVisible.restype = wintypes.BOOL
    user.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user.GetWindowTextW.restype = ctypes.c_int
    user.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user.GetWindowRect.restype = wintypes.BOOL
    user.GetClipCursor.argtypes = [ctypes.POINTER(wintypes.RECT)]
    user.GetClipCursor.restype = wintypes.BOOL
    user.GetForegroundWindow.restype = wintypes.HWND

    class GuiInfo(ctypes.Structure):
        _fields_ = [('cbSize', wintypes.DWORD), ('flags', wintypes.DWORD),
                    ('active', wintypes.HWND), ('focus', wintypes.HWND),
                    ('capture', wintypes.HWND), ('menu_owner', wintypes.HWND),
                    ('move_size', wintypes.HWND), ('caret', wintypes.HWND),
                    ('caret_rect', wintypes.RECT)]

    user.GetGUIThreadInfo.argtypes = [wintypes.DWORD, ctypes.POINTER(GuiInfo)]
    user.GetGUIThreadInfo.restype = wintypes.BOOL
    windows = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    @callback_type
    def collect(hwnd, unused):
        owner = wintypes.DWORD()
        thread = user.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid:
            title = ctypes.create_unicode_buffer(1024)
            user.GetWindowTextW(hwnd, title, len(title))
            rect = wintypes.RECT()
            bounds = None
            if user.GetWindowRect(hwnd, ctypes.byref(rect)):
                bounds = [rect.left, rect.top, rect.right, rect.bottom]
            info = GuiInfo()
            info.cbSize = ctypes.sizeof(info)
            capture = int(info.capture or 0) if user.GetGUIThreadInfo(thread, ctypes.byref(info)) else None
            windows.append({'hwnd': int(hwnd), 'title': title.value,
                            'visible': bool(user.IsWindowVisible(hwnd)),
                            'bounds': bounds, 'capture_hwnd': capture})
        return True

    user.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    user.EnumWindows.restype = wintypes.BOOL
    if not user.EnumWindows(collect, 0):
        raise ctypes.WinError(ctypes.get_last_error())
    rect = wintypes.RECT()
    clip = None
    if user.GetClipCursor(ctypes.byref(rect)):
        clip = [rect.left, rect.top, rect.right, rect.bottom]
    return {'session_id': session.value, 'windows': windows, 'cursor_clip': clip,
            'foreground_hwnd': int(user.GetForegroundWindow() or 0)}


def launch(executable, machine, runtime, mode='visible', port=8765, seed=1, timeout=20):
    if os.name != 'nt':
        raise OSError('this launcher currently targets Windows')
    if mode not in MODES or timeout <= 0:
        raise ValueError('invalid display mode or startup timeout')
    executable, machine, runtime = (Path(p).resolve(strict=True) for p in (executable, machine, runtime))
    command(executable, machine, 'validation-only', port, seed)
    if machine.is_relative_to(ROOT) or not executable.is_file() or not runtime.is_dir():
        raise ValueError('use an executable/runtime and a private machine outside the repository')
    cfg = machine / '86box.cfg'
    if (machine / 'baseline-manifest.json').exists() or not cfg.stat().st_mode & stat.S_IWRITE:
        raise ValueError('clone the sealed/read-only baseline into a writable working directory')
    if (machine / 'automation.token').exists():
        raise ValueError('token already exists; inspect process state/stale token before launching')
    initial = windows_state(os.getpid())
    if mode == 'visible' and initial['session_id'] == 0:
        raise ValueError('visible launch requires the interactive user session, not service session 0')
    # Check without contacting or disturbing any existing automation service.
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', port))
    run = machine / ('launch-' + uuid.uuid4().hex)
    run.mkdir()
    config_hash = observer_preferences(machine, run)
    global_config = run / '86box-global.cfg'
    global_config.write_text('[Emulator]\ndo_auto_pause = 0\ndo_auto_dialog_pause = 0\n', encoding='ascii')
    args = command(executable, machine, global_config, port, seed)
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    # Request display without taking keyboard focus; background preserves legacy SW_HIDE.
    startup.wShowWindow = 4 if mode == 'visible' else 0
    receipt = {'mode': mode, 'command': args, 'creationflags': 0,
               'show_window': startup.wShowWindow, 'config_sha256': config_hash,
               'executable_sha256': hashlib.sha256(executable.read_bytes()).hexdigest(),
               'caller_session_id': initial['session_id'],
               'foreground_before': initial['foreground_hwnd'], 'state': 'starting'}
    receipt_file = run / 'launch.json'
    with (run / 'startup.log').open('xb') as log:
        process = subprocess.Popen(args, cwd=machine, env=child_environment(runtime, mode),
            startupinfo=startup, creationflags=0, stdin=subprocess.DEVNULL,
            stdout=log, stderr=subprocess.STDOUT)
    receipt['pid'] = process.pid
    receipt_file.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    try:
        deadline = time.monotonic() + timeout
        ready = False
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f'emulator exited ({process.returncode}); inspect {run / "startup.log"}')
            token_file = machine / 'automation.token'
            if token_file.exists() and token_file.stat().st_size >= 64:
                try:
                    with Client(token_file, port=port, timeout=min(timeout, 3)) as client:
                        status, identity = client.status(), client.info()
                    window = windows_state(process.pid)
                    if mode != 'visible' or any(w['visible'] and '86Box' in w['title'] for w in window['windows']):
                        ready = True
                        break
                except (ConnectionRefusedError, FileNotFoundError):
                    pass  # Startup readiness only; no guest mutation is retried.
            time.sleep(0.1)
        if not ready:
            raise TimeoutError('startup/window readiness timed out; inspect launch receipt; no automatic kill')
        if status.get('held') is not True or status.get('paused') is not False or status.get('ms') != 0:
            raise RuntimeError('machine did not start held and unpaused at 0 ms')
        if window['session_id'] != initial['session_id']:
            raise RuntimeError('unexpected process session')
        receipt.update(state='ready', status=status, info=identity, window_state=window)
    except Exception as exc:
        receipt.update(state='startup_failed', error=str(exc))
        raise
    finally:
        receipt_file.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    return receipt_file, receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--machine', required=True, type=Path)
    parser.add_argument('--exe', type=Path, default=Path('C:/DeskMateLab/builds/86box-automation/src/86Box.exe'))
    parser.add_argument('--runtime', type=Path, default=Path('C:/msys64/ucrt64/bin'))
    parser.add_argument('--mode', choices=MODES, default='visible')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--seed', type=int, default=1)
    args = parser.parse_args()
    path, receipt = launch(args.exe, args.machine, args.runtime, args.mode, args.port, args.seed)
    print(json.dumps({'pid': receipt['pid'], 'mode': receipt['mode'],
                      'state': receipt['state'], 'private_receipt': str(path)}, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError) as exc:
        print(f'86Box launch: {exc}', file=sys.stderr)
        raise SystemExit(2)
