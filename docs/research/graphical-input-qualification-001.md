# Graphical input qualification 001 — native pointer automation

Campaign `graphical-input-qualification-001` establishes dependable guest-level
pointing-device automation for the DeskMate research laboratory, so that
graphical interfaces no longer require host keyboard, host mouse, desktop
coordinates or window focus.

Status: **pointer delivery, calibration, clicks, drags, menus, file lists and
Save As dialogs are production-qualified; the three blocked Application Library
workflows were re-driven with the pointer, two of them to completion.** All
human input in this campaign travelled through the emulator's authenticated
loopback socket; no host mouse or keyboard event was injected.

## Identities

| Item | Value |
| --- | --- |
| Emulator executable | `86Box.exe`, 86Box 7.0, automation protocol 1 |
| Executable SHA-256 | `e7e1244588ea721aa239564a43fa2636611ae965ea8431672fdc06d8c12c280d` |
| Emulator source | 86Box upstream at `855258da966f1594f568350be59e8e1eca082ed1` |
| Mouse support commits | `1b3985523` (relative mouse), `0a88fbcda` (absolute tablet) |
| Guest machine | Tandy 1000 RSX, 640×480, DOS 5.00, DeskMate 3.05 |
| Mouse device | PS/2 mouse; absolute tablet unsupported (`tablet_type = none`) |
| Mouse driver | Logitech Mouse 6.00 (`C:\DOS\MOUSE.COM`, `MOUSE.SYS`), loaded as a TSR |
| Guest diagnostic | `MDIAG.COM`, 424 bytes, SHA-256 `b79d1f1379cdde704c2b00c8ca51a837e836476313d0c9969794207c6bbf6066` |
| Diagnostic source | `tools/experimental/guest_mouse_diag/mdiag.S` (GNU as, `.code16`) |
| Campaign checkout | branch `freebuff/graphical-input-qualification-001` at `5045901177b735c7f5aaaa3512e4d4741a9d7bb2` |

No production emulator change was needed: the shipped build already exposes
relative motion with an absolute button mask over the authenticated socket.
Nothing in this campaign replaced or promoted the production executable.

## What the production build already supported

Traced from the source and confirmed natively:

| Capability | State | Evidence |
| --- | --- | --- |
| Relative motion | Supported | `mouse <dx> <dy> <buttons>` delivered and consumed |
| Button press/release | Supported | Guest counter recorded 1 press + 1 release per click |
| Combined click | Supported | Press and release in one command also works; two commands are used for receipts |
| Absolute positioning | Present but unusable | `tablet` exists; machine reports `tablet_type = none` |
| Held execution | Supported | `advance` runs the guest with a request outstanding |
| Framebuffer capture | Supported | PNG at 640×480 used for visual verification |
| Guest coordinate reporting | Not in the socket API | Added locally by the resident `INT 33h` diagnostic |
| Guest driver identity | Not in the socket API | Verified by the driver's own banner and the diagnostic |
| Capability negotiation | Not needed | Protocol 1 advertises no pointer profile; behaviour is measured |
| Event acknowledgement | Socket-level only | The reply proves acceptance, not application action |

The distinction that matters operationally:

1. **Socket acceptance** — the command parses. Says nothing about the guest.
2. **Hardware delivery** — the emulated PS/2 device receives counts. Requests of
   128 units or more are silently truncated to nothing.
3. **Driver processing** — the TSR consumes accumulated counts on its 18.2 Hz
   tick and applies acceleration. Only a tick makes motion visible.
4. **Application action** — the application decides what a press/release means.
   DeskMate menus act on release, and only for gestures that began on the menu
   title.

The Application Library blockage was at levels 3 and 4, not at level 1: the
socket accepted clicks that no application ever saw, because the host had
loaded no mouse driver at all.

## Root cause of the earlier blockage

The sealed DeskMate 3.05 host image ships `C:\DOS\MOUSE.COM` and `MOUSE.SYS`
but its `CONFIG.SYS` loads neither. Without a driver, `INT 33h` is a stub, the
pointer is never drawn, and every pointer event is discarded. Loading `MOUSE`
from the DOS prompt before `DESK` enables the pointer for the whole session.
That single step — not emulator capability, not coordinates — was the blocker
behind "socket key events are ignored" in the Application Library campaign.

## Calibration

Two independent observations are used together:

* **Oracle** — the resident diagnostic publishes `x, y, buttons, presses,
  releases, ticks` under the `MDIAG001` signature. It is authoritative for
  driver-level state and cheap to read.
* **Framebuffer** — consecutive PNG captures are differenced to confirm that
  the cursor sprite was actually drawn where the driver reports it.

Measured response of Logitech 6.00 under DeskMate at 640×480, one axis:

| Requested units | Observed pixels |
| --- | --- |
| 4 | 2 |
| 8 | 10 |
| 16 | 26 |
| 24 | 42 |
| 32 | 58 |
| 48 | 90 |
| 64 | 122 |
| 128 and above | 0 (silently dropped) |

Consequences encoded in the facility:

* Requests stay below 128; the client caps at 64 by default.
* The curve is strongly accelerated, so the inverse is interpolated rather than
  divided by a single ratio.
* A 4-unit request occasionally moves nothing (driver dead zone), so a
  calibration size that produces no motion is retried once and then skipped.
* The clamp corner is **(0, 5)**, not (0, 0); homing requires the reported
  position to reach the left edge, and two unchanged samples away from it are
  reported as a blocked pointer rather than a clamp.

Closed-loop `move_to` converged within one pixel at (320, 240), (100, 100),
(600, 460), (35, 42) and everywhere used by the native trials, typically in two
to five steps.

## Facilities

`src/deskmate_formats/automation/pointer.py`, all layered so that application
knowledge stays out of the transport:

* `PointerTransport` — relative motion and an absolute button mask over
  `Client.mouse()`; tracks held buttons and never sends a request at the
  truncation limit.
* `Frame`, `Box`, `FrameCursor` — PNG decode, component merge (`gap=2`) for the
  XOR-drawn 12×16 sprite, differencing between frames.
* `Calibration` — measured curve plus `units_for(pixels)`, the inverse used by
  every aiming operation; records skipped sizes.
* `Pointer` — `home`, `calibrate`, `move_to`, `move_by`, `click`, `click_at`,
  `double_click_at`, `drag`, `release_all`, `sample_settled`.
* `PointerReceipt` — structured evidence: target, actual position, guest
  position/buttons/press and release counts, steps, emulated milliseconds,
  failure class and detail.
* `Failure` — `OUT_OF_RANGE`, `BLOCKED`, `NOT_REACHED`, `TARGET_NOT_REACHED`,
  `REJECTED`, `UNCERTAIN`, `AMBIGUOUS`, `NOT_DELIVERED`.
* `ScreenState` — framebuffer digests and bounded `wait_change` for
  application-visible verification.
* `MemoryMouseOracle` — discovery by signature in conventional RAM, held reads,
  and `verify_live` which proves the tick counter advances.

`Client.mouse()` and `Client.tablet()` were added to the existing automation
client; no other production interface changed.

## Failure modes established natively

| Symptom | Cause | Handling |
| --- | --- | --- |
| Click accepted, nothing happens | No mouse driver loaded | Load `MOUSE` before the application |
| Movement reported, cursor not drawn | Reading before the driver tick | `sample_settled` waits for two ticks |
| Move appears dropped, then overshoots | Guest busy repainting; motion accumulates and lands at once | Wait for ticks before each observation |
| Menu item highlights one entry late | DeskMate highlights after the next processing tick | Hold at the destination and nudge 1 px before release |
| Release over an already-open menu selects but does not activate | Activation requires a gesture that began on the title | Close with Escape, then press title, drag to item, release |
| Clicking a page in Express Publisher shows a help dialog | Text mode expects a text frame | Drop the cursor inside the frame first |
| Typed text arrives late or duplicated | Runtime redraws per keystroke | Type at 140–260 ms per key, then wait 8–14 s |

Every uncertain completion is reported, never replayed: a failed aim returns a
receipt with a failure class and the observed position, and `release_all` is the
only recovery action taken.

## Native qualifications

### DeskMate Text — Save As (complete)

Desktop File menu, Text launch by double-click, File → Save as via
press-drag-release, field focus at (350, 203), name typed, SAVE at (283, 283).
The title bar changed to `Text - SYNTH001.TXT`. The document was then extracted
from the stopped image: `C:\SYNTH001.TXT`, 32 bytes, SHA-256
`8a43e5d4b11c1b2a847de66c71e95c47d909072d27564551ededf99be16186c9`,
containing the typed line. Application-visible saved output verified on disk.

### Lotus Spreadsheet — open the synthetic worksheet through the file list (complete)

`File → Open...` from the menu bar (press-drag-release), the file list scrolled
with its own control, `SYNTH001.WK1` selected by clicking its row (the field
updated to the selected name), `OK` at (381, 304). The reopened sheet shows
`A1 = 10`, `A2 = 20`, `A3 = 30`, and clicking A3 puts `+A1+A2` in the control
line: the saved values and the formula survived the reopen. No document was
written; the worksheet was opened read-only in effect.

### Express Publisher — create, Save As, exit, cold reopen (complete)

Page text placed by clicking inside the text frame and typing at 260 ms per
key; `File → Save as...` reached the Save As dialog
(`C:\EXPRESS\DOCS`, File Type `Document`); the name was typed by clicking the
File field, clearing it with Backspace and typing `EPPAGE1`; `OK` wrote
`SYNTH01.EPD` (3,265 bytes, SHA-256
`9ddb9368364b8b283d080bd95f9a0bac8c30fb3146a7ed9ab6335c5b5471bec0`) — the
first native `.EPD` document from this laboratory. After exiting with Escape
and restarting the emulator, `EPDM DOCS\SYNTH01.EPD` reopened the document cold:
the title reads `EP - DOCS\SYNTH01.EPD` and the page shows the synthetic text.

The document is synthetic and private; only its identity is published here.

## Blocked, partial and unverified

* **Express Publisher's in-app `Save as...` menu item could not be armed
  reliably.** In this runtime the menu highlight lags the pointer by more than
  the measured 500 ms hold, so the release sometimes activates the previously
  highlighted entry (`Close`, then a "Document has been modified" prompt). The
  Save As dialog was reached through that prompt and through a later session;
  the workflow completed, but the menu recipe needs a visual highlight check
  rather than a fixed hold before it can be called dependable.
* **A second Express session lost the typed page text.** Text typed while the
  document was unsaved disappeared from the view after `OK`, although the file
  written in the same session contained no text. The first session's document
  is the one verified here; the loss is recorded rather than explained.
* **DeskMate Install accessory was not exercised.** The pointer facility is
  ready for it, but this campaign did not run the accessory.
* **Draw graphical operations were not exercised.**
* **Absolute positioning remains unavailable** on this machine
  (`tablet_type = none`), so every operation is relative and closed-loop.
* **The framebuffer is evidence, not ground truth, for cursor position.** A
  software XOR cursor can be corrupted by application redraws; the oracle is
  authoritative and the frame diff only confirms drawing.

## Private evidence

Complete captures, guest images, the diagnostic media, receipts and the
synthetic documents remain outside Git under the campaign evidence directory:
the machine clones (`graphical-input-001`, `-lotus`, `-express`), the
`trials/` PNG sequences, the `outputs/` extracts and the helper scripts used to
boot, probe and inspect. Published evidence is limited to identities, hashes,
measurements and the recipes in the
[graphical automation runbook](graphical-automation-runbook.md).

## Reproduction

```bash
# from the campaign checkout, with a machine clone and the production build
python tools/86box_launch.py --machine <campaign-clone>
# in the guest, at the DOS prompt
MOUSE
MDIAG
CD \DESKMATE
DESK
```

Then, from the client:

```python
from deskmate_formats.automation.client import Client
from deskmate_formats.automation.pointer import MemoryMouseOracle, Pointer

with Client(token_path) as client:
    pointer = Pointer(client, oracle=MemoryMouseOracle.discover(client))
    pointer.home()
    pointer.calibrate()
    pointer.drag((35, 42), (50, 79), step_pixels=8)   # File -> Open
```
