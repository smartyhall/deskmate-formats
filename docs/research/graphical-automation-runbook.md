# Graphical automation runbook — DeskMate over the 86Box socket

Actionable recipes for driving DeskMate and its applications with a real guest
pointer. Everything here travels through the emulator's authenticated loopback
socket; nothing touches the host mouse, host keyboard, desktop coordinates or
window focus.

Read first: the [qualification report](graphical-input-qualification-001.md)
explains how each rule was measured.

## 1. Preflight

1. Start the machine clone with a visible window: `tools/86box_launch.py
   --machine <clone>`. The window is for humans; control is the socket.
2. At the DOS prompt, load the driver **before** the application:

   ```
   MOUSE
   MDIAG
   CD \DESKMATE
   DESK
   ```

   Without `MOUSE` the pointer is never drawn and every pointer event is
   discarded. This is the single most common "clicks do nothing" cause.
3. Discover the diagnostic and confirm it is live:

   ```python
   oracle = MemoryMouseOracle.discover(client)
   assert oracle.verify_live()['ticks_after'] > oracle.verify_live()['ticks_before']
   ```

## 2. Pointer setup

```python
from deskmate_formats.automation.pointer import MemoryMouseOracle, Pointer

pointer = Pointer(client, oracle=oracle, press_ms=200)
pointer.home()        # drives into the clamp corner (0, 5)
pointer.calibrate()   # measures the acceleration curve
```

Never hard-code a ratio. The curve is strongly accelerated (64 units → 122 px),
requests of 128 units or more are dropped, and a 4-unit request may do nothing.
`pointer.calibration.curve` and `pointer.calibration.skipped` are the receipt.

## 3. Basic operations

| Goal | Call | Notes |
| --- | --- | --- |
| Absolute aim | `pointer.move_to(x, y)` | Closed loop; default tolerance 2 px, 20 steps |
| Click | `pointer.click_at(x, y)` | Aims, then one press and one release |
| Double-click | `pointer.double_click_at(x, y)` | Default 90 ms between release and second press |
| Drag | `pointer.drag((x0, y0), (x1, y1), step_pixels=8)` | Press, incremental moves, hold, release |
| Release everything | `pointer.release_all()` | The only recovery after an uncertain action |
| Wait for the driver | `pointer.sample_settled()` | Two driver ticks; use after a move |

Check `receipt.ok` and `receipt.failure` every time. A failure carries the
observed position; **do not re-send the same click**. Read the screen, decide,
and act again from a known state.

## 4. Framebuffer verification

```python
state = ScreenState(client)
before = state.capture()[0]
# ... act ...
changed = state.wait_change(before, timeout_ms=3000)
```

A PNG digest proves the screen changed; it does not prove the intended control
was pressed. For that, compare the region that should have changed, or read the
application's own title/status line from a fresh capture.

## 5. Menus (DeskMate and Lotus style)

DeskMate menus activate on **release**, and only for a gesture that began on the
menu title. A click on an already-open menu only selects.

```python
# Open the menu and choose an item in one gesture.
pointer.drag((35, 42), (50, 79), step_pixels=8)      # File -> Open...
```

Rules:

* Start the gesture on the title (DeskMate desktop: `File` at about (35, 42)).
* Move in small increments (`step_pixels=8`); a single jump can leave the
  highlight behind.
* The highlight lags the pointer by up to one processing tick. `drag()` holds
  for 500 ms and nudges 1 px before releasing. When the application is slower
  (Express Publisher), verify the highlighted row in a capture before relying
  on the result.
* If the menu is already open, press **Escape** first; pressing the title again
  closes it, and the following release lands on nothing.

Measured item rows (DeskMate 640×480, menu opened at y=42):

| Menu | Items |
| --- | --- |
| Desktop File | Get Info 75, Run 93, Copy 111, Delete 129, Rename 148, Update screen 179, Exit 211, About 259 |
| Desktop menu bar | File x≈35, Edit, View, Options, Help |
| Text File | New 76, Open 94, Save 112, Save as 128, Merge 146, Page setup 164, Print 182, Exit 218, To ASCII 267, About 293 |
| Lotus File | New 62, Open 79, Close 96, Save 115, Save as 133, Page Setup 277, Print 313, Exit 330 |
| Express File | New 72, Open 89, Close 166, Save 182, Save as 196, Print 228, Exit 246, Run 259, About 281 |

Treat these as measurements of one build, not as protocol.

## 6. File lists (Open dialogs)

```python
pointer.drag((35, 42), (50, 79), step_pixels=8)   # File -> Open...
pointer.click_at(243, 223)                        # list scroll/step control
pointer.click_at(250, 322)                        # the row itself
pointer.click_at(381, 304)                        # OK
```

Rules:

* The list header carries its own arrow controls; clicking the left arrow steps
  the visible window.
* Rows are 19 px apart. Measure the first visible row in a capture — dialog
  position changes between calls, and a click one row low silently selects the
  wrong file.
* Selecting a row updates the `File:` field. Read it in a capture before
  pressing OK; that field is the cheap, unambiguous confirmation.
* Typing in a list performs incremental search and moves the selection; it does
  not fill the field. Do not mix the two.

Measured dialogs:

| Dialog | Field | OK | Cancel | List rows |
| --- | --- | --- | --- | --- |
| DeskMate Open File | (350, 203) | (373, 273) | (383, 340) | 246, 265, 284, 303 |
| DeskMate Save File | (350, 203) | (283, 283) | (383, 340) | — |
| Lotus Open File | (350, 157) | (381, 297) | (383, 340) | first row 246, pitch 19 |
| Express Save As | (330, 170) | (385, 348) | (385, 383) | `[..]`, `[A:]`, `[C:]` |

## 7. Save As dialogs

```python
pointer.click_at(field_x, field_y)          # focus the name field
for _ in range(40):
    client.tap(0x0E); client.advance(100)   # Backspace to clear the proposal
client.type_ascii('SYNTH01', pace_ms=220)   # slow: the runtime redraws per key
client.advance(8000)                        # let the queue drain
pointer.click_at(ok_x, ok_y)
client.advance(12000)
```

Rules:

* Click **inside** the field, at its right side, so the caret lands at the end;
  a click past the field defocuses it and Backspace stops working.
* `0x0E` is Backspace, `0x53` is `.` — not Delete. There is no reliable
  select-all, so clear with Backspace from the end.
* Type no faster than 140 ms per key. Express Publisher needs 220–260 ms; typed
  characters otherwise arrive late and interleave with the previous attempt.
* Confirm the title bar or the filename in a capture before believing the save.
  A saved file is not proof that it contains what you typed — extract and hash
  the file afterwards.

## 8. Failure handling

| Receipt | Meaning | Action |
| --- | --- | --- |
| `BLOCKED` | Two requests produced no change | Check the driver is resident; read the screen; do not replay |
| `AMBIGUOUS` | The driver did not run within the timeout | Capture, wait, then resume from a fresh observation |
| `TARGET_NOT_REACHED` | Closed loop did not converge | Use a larger tolerance or a smaller target region; do not click blind |
| `REJECTED` / `UNCERTAIN` | Socket refused, or the outcome is unknown | `pointer.release_all()`, then re-observe |
| `NOT_DELIVERED` | Guest did not report the press | Check driver and button mask before retrying |

## 9. Limits

* Absolute positioning is unavailable on this machine; every operation is
  relative and closed-loop.
* The cursor is XOR-drawn and can be corrupted by application redraws; trust the
  oracle over the pixels for position, and the pixels over the oracle for
  "was it drawn".
* Emulated time, not host time, drives the driver. Advance time explicitly;
  host sleeps do nothing.
* Express Publisher's menu highlight is slower than the default hold; verify the
  highlighted row in a capture before depending on it.
