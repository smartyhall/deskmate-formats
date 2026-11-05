# Visible and unattended 86Box operation

2026-11-04, America/Los_Angeles. Follow-up to the completed
[RSX DOS baseline](rsx-dos5-baseline.md). That baseline was published first at
`95dabbfddea86740558e4dbca9bb074c43e7abf7` on
[the dedicated experiment branch](https://github.com/smartyhall/deskmate-formats/tree/experiment/86box-dos5-baseline).
No merge, history rewrite or change to PR 29 was performed.

This report describes the earlier visibility session, not new emulator activity
during repository synchronization. PRs 29 and 30 are now merged into main at
`194b8b95c624be59dfcfbb76988481e029be9d38`. The previously unpublished launcher,
five portable tests and observer design were selectively transferred from local
commit `04c2c859d656d9d6eaea623d6427065ef8a89085` onto a fresh follow-up branch.
The merged visible manual launch and strict RDP/Computer Use restrictions were
retained. No baseline commits or deployment corrections were replayed or removed.

## Diagnosis

The earlier PowerShell launch explicitly used `Start-Process -WindowStyle Hidden`.
There was no Python subprocess launcher in the completed client: it only attached
to an existing socket. The pinned 86Box source's `qt_main.cpp` creates MainWindow
and calls `show()`/`showMaximized()` independently of automation. The process and
agent were both in the active interactive RDP session, ID 1. No inherited Qt
offscreen environment override was present.

Controlled launches of the **unchanged executable** confirmed:

| Mode | Child settings | Programmatic observation |
|---|---|---|
| Visible | Qt `windows`, startup show 4 (`SW_SHOWNOACTIVATE`) | One visible titled emulator window, nonzero HWND, session 1 |
| Background | Qt `windows`, startup show 0 (`SW_HIDE`) | Hidden emulator window exists; MainWindowHandle 0 and empty MainWindowTitle |
| Headless | Qt `offscreen`, startup show 0 | No enumerated visible/top-level emulator window; native framebuffer still available |

Thus the old launch suppressed the normal window; automation itself does not
require it hidden. A newly returned process object also initially reported zero
before Qt finished creating the visible window. A single MainWindowHandle sample
is therefore insufficient. The launcher waits for authenticated held startup and
uses `EnumWindows`, owner PID and `IsWindowVisible` to verify visible readiness.
Win32 diagnostics also record process session, capture handles and cursor clipping.
The launcher performs no window activation, display clicking or host keystroke injection.
A brief host capture attempt at initial 0-ms startup timed out; GUI screenshots
were not needed for the programmatic diagnosis and are not claimed as evidence.

## Preferred launch procedure

Use a **writable clone** of the private sealed baseline, never the baseline itself.
The [launcher](../../tools/86box_launch.py) defaults to visible operation:

```powershell
python tools/86box_launch.py --machine C:\DeskMateLab\machines\rsx-dos5-visible
python tools/86box_client.py --machine C:\DeskMateLab\machines\rsx-dos5-visible status
python tools/86box_client.py --machine C:\DeskMateLab\machines\rsx-dos5-visible step 1000
```

The executable/runtime defaults match the laboratory. `--exe`, `--runtime`,
`--port` and `--seed` are explicit overrides. Arguments are passed as a list,
supporting paths containing spaces without shell interpolation. The child gets
its own runtime PATH and Qt platform; the caller's environment is unchanged.

Every launch includes authenticated loopback TCP, default token-file handling,
`--automation-hold`, a seed (default 1) and `--nohook`. Readiness requires
`held=true`, `paused=false`, `ms=0`, and the expected process session. The visible
mode requires a matching visible window and refuses service session 0.
The launcher never advances guest time during startup.

Per-launch private receipts/logs reside in a new `launch-<id>` directory inside
the selected machine. They record PID, command/creation flags, source-independent
executable/config hashes, status, window state and diagnostic errors; never tokens.
They contain private paths and guest metadata and must stay out of Git. A private
global config disables automatic focus/dialog pausing without changing the user's
global 86Box preferences. Working-profile input settings are backed up byte for
byte before an explicit UTF-8 rewrite. Guest CPU, RAM, disk and input hardware
settings are retained. Existing tokens or busy endpoints cause refusal rather
than disruption of an existing emulator. Startup failure does not automatically
kill a process or replay guest mutations; inspect its receipt and status.

## Input behavior and the important capture limitation

`--nohook` disables 86Box's global low-level keyboard hook. The visible launch
requests no keyboard-focus activation; in the final controlled launch the
foreground HWND stayed unchanged. This is a request to Windows, not a universal
guarantee against focus changes initiated by users or window managers.

**Do not click the emulated display.** The normal 86Box window intentionally
retains its manual click-to-capture behavior. This small launcher does not disable
all host input or install an input firewall. Keep it windowed, and use the socket
for every guest operation. There is no forced mouse capture or GUI input in the
harness. Capture HWNDs remained zero and cursor clipping stayed at the complete
1366 x 768 RDP desktop during all three mode checks.

An attempted `kbd_req_capture=1` safeguard **failed validation**: socket key
requests returned success but DOS received no characters. At the pinned revision,
`automation.c` calls `keyboard_input()`, and `src/device/keyboard.c` applies the
same capture gate to those calls. No capture was enabled to bypass it. The working
profile now explicitly uses `kbd_req_capture=0`, preserving uncaptured socket
input, with relative mouse input mode 0 and the PS/2 devices unchanged. No emulator
source/binary patch was made. A future true passive-display option should block
host input in the frontend while allowing authenticated socket input separately;
that work is deferred.

## Unattended modes and measured checks

```powershell
# Actual Qt offscreen backend, with native screenshot/text/socket operation:
python tools/86box_launch.py --machine C:\DeskMateLab\machines\rsx-dos5-visible --mode headless

# Preserve the earlier hidden Windows-window workflow:
python tools/86box_launch.py --machine C:\DeskMateLab\machines\rsx-dos5-visible --mode background
```

Quit the current test through the socket and wait for process exit before
switching modes on the same machine/port. These commands do not launch additional
clients against an already running instance.

Each mode passed: stable 0-ms hold across host waiting; twelve exact 1,000-ms
steps; hard-disk boot with no floppy; socket typing of `VER`; observed DOS 5.00;
ordinary BDA memory read; native PNG capture; held status at 12,516 ms after key
events and a further 500-ms step; and socket quit. Visible operation did not
change deterministic step behavior. Background reproduced the old zero-handle
symptom while remaining fully controllable.

Offscreen mode was verified in the current logged-in Windows/RDP session. Running
as a service, after RDP disconnect, under a locked desktop, or with different Qt
builds was **not** tested. No Windows restart, RDP disconnection, security change,
cross-session launch or emulator rebuild was attempted. The existing background
mode remains available if an offscreen backend is unavailable elsewhere.

Five new ROM-free tests cover secure command construction, argument boundaries,
invalid port/seed, child-only display environment, preservation of guest hardware
and config backups, and refusal to modify a sealed baseline. Private live evidence
is under `C:\DeskMateLab\private-evidence\visible-session-20261104`.
The complete portable suite passes 110 tests on Python 3.13.17 and UCRT64 Python
3.14 with source imports; REUSE, focused Ruff and content checks pass as well.

The original baseline, acquisition and first-session evidence remain intact.
The first-session Windows audit warning remains part of that historical report.
PR 29 subsequently merged canonical-path containment corrections and portable
regressions; those corrections are retained here. Passing synthetic guards does
not establish that the complete guest-volume audit works on Windows: no live
guest-volume audit was performed during this synchronization task. Host-dependent
symlink skips are reported explicitly, without changing privilege or security
settings. The optional browser observer is a [design only](86box-observer-design.md).
