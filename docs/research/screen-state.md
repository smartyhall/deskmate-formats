# DeskMate 3.05 screen-state extraction research

## Result and scope

Read-only native debugger RAM dumps recovered a formatted Calendar schedule row
on two independently screenshot-verified screens in one running session. No OCR,
pixel recognition, guest memory writes or database edits were used for that readback.
This is a **partial schedule readback**, not a complete screen-state API. It does
not recover the screen header, all menus, fields, coordinates, selection or focus.
Two different Calendar day views were tested; two different applications were not.
No stable address across restarts, other dialogs or applications is established.

Research starts from main f5a044ebbb688b8d0907af014ac9712ae80db1d4 after a
clean-tree inspection, fetch and fast-forward-only synchronization. E16 was not
repeated; Dependabot PR 2 and the existing E15/E16 history were left untouched.

## Actual installed build and video mode

The installed DOSBox-X SDL1 2026.10.01 Release exposes native menu commands for
the video debug overlay, Copy all text on DOS screen (Ctrl+F5), and its debugger.
The unchanged working profile uses svga_s3 and software surface output.
Observed overlay results:

| Screen | Reported mode | Resolution / parameters |
|---|---|---|
| DOS command prompt | M_TEXT | 80 columns, 25 rows, 720 by 400 pixels |
| DeskMate main screen | M_EGA | 640 by 480 (overlay G640x480>480) |
| Calendar | M_EGA | 640 by 480 (same overlay) |

The BIOS data area in the paused Calendar capture reports mode 0x12 at physical
0x449, 80 columns, 29 for rows-minus-one and character height 16. These BIOS
bookkeeping values do not establish DeskMate's own text-cell geometry. The
overlay was restored off. Font appearance alone was not used to classify mode.

## Built-in copying: positive control and graphics failure

Each trial installed a unique clipboard sentinel and read back a fresh result.
DOS Ctrl+F5 copied the visible command prompt (58 characters, 23 CRLFs).
DeskMate main returned 2,218 characters and 29 CRLFs, zero ASCII letters and
1,821 solid-block characters. Calendar, with the overlay off, returned 2,218
characters and 29 CRLFs, zero ASCII letters and 365 solid blocks. Output changed
with the display but contained none of the expected screen text. Line boundaries
alone are not usable positions; field values, menu labels and focus were not
recovered. The debugger log also reports failed INT10 character recognition.

Release-tag source documents why text-mode success does not generalize:
[clipboard.cpp](https://github.com/joncampbell123/dosbox-x/blob/dosbox-x-v2026.10.01/src/misc/clipboard.cpp)
delegates selection to
[mouse.cpp](https://github.com/joncampbell123/dosbox-x/blob/dosbox-x-v2026.10.01/src/ints/mouse.cpp).
[int10_char.cpp](https://github.com/joncampbell123/dosbox-x/blob/dosbox-x-v2026.10.01/src/ints/int10_char.cpp)
reads character memory in text mode but attempts font/pixel matching in graphics
modes. The latter would also fail the strict no-image-recognition criterion.
The release source is documentary support, not a claim of binary identity with
the installed executable. Installed menus, HELP and observed behavior were checked.

## Bounded RAM observation

The pre-existing emulator connector reported disconnected. A later bounded
read-only process/port inspection found the external MCP server running, tools
available in this chat, and the native debugger present. The profile specifies
mcp_server=58991, while the connector reports 56681 and its existing server
listens on loopback ports 56681/56682. A connection/port mismatch is the likely
cause; the exact handshake was not traced. This is not evidence that MCP is
unsupported. The future remedy is to align the existing connection settings in
a separately authorized maintenance task, then check ping and live HELP. No
server was installed, started, repaired or reconfigured during this diagnostic. The installed native debugger's own HELP confirms MEMDUMPBIN
and F5 resume. Only read-only dump commands, HELP and resume were used. Host
console commands were typed with verified foreground ownership and read back
before Enter. No debugger guest-key injection, stepping, patches, breakpoints,
memory writes or network service was used.

Pause Calendar, and use the documented hexadecimal command syntax:

```text
MEMDUMPBIN 0000:0 10000 <private-output-for-chunk-0>
MEMDUMPBIN 1000:0 10000 <private-output-for-chunk-1>
...
MEMDUMPBIN 9000:0 10000 <private-output-for-chunk-9>
```

Each dump must be exactly 65,536 bytes; join in segment order to cover physical
0..0x9FFFF while paused. Resume with F5. The initial attempted 0:0 A0000 dump
wrapped its 16-bit offset, repeating the first 64 KiB ten times. It is retained
privately and explicitly invalidated as a full-range capture. Corrected captures
use ten segment-local dumps. This behavior agrees with the real-mode address
calculation in [debug.cpp](https://github.com/joncampbell123/dosbox-x/blob/dosbox-x-v2026.10.01/src/debug/debug.cpp).

| Verified Calendar display | Physical ASCII span | Exact extracted row |
|---|---|---|
| Saturday October 31, 2026 | 0x1266E, 44 bytes | `Holiday               Halloween             ` |
| Friday October 23, 2026 | 0x12676, 36 bytes | ` 9:00 AM - 10:00 AM   EARLY26       ` |

Both spans end immediately before 0x1269A, whose byte is 0x01, followed by NUL.
The preceding bytes and marker semantics are not decoded. The starting position
changes; this is not evidence of a fixed row structure. A bounded comparison of
the surrounding region establishes that the formatted text changed with the
display. EARLY26 also occurs at 0x98BAC in **both** captures, including when not
displayed. A static-looking resource at 0xA296 also retains Halloween followed by NUL in both captures. That negative control rules out treating arbitrary string hits as a
screen readback. The row is a display-related buffer candidate. A third, screenshot-verified
state at the DOS prompt after Calendar exit used a targeted read of exactly
physical 0x12660..0x126DF (128 bytes). It contained unrelated filename/prompt
material and binary values, with neither formatted row present. Identical raw
regions from A and B and the raw C dump are retained before any decoding, with
every changed offset/value in a private comparison report. Thus the candidate
updates within Calendar and does not persist there after exit in this session.
That does not establish its lifetime in other Calendar dialogs or rule out stale
contents elsewhere. No character-attribute stride, grid, pointer structure or
meaning for the adjacent binary values has been established. The shared 0x01/NUL
suffix is an observation, not a proven logical-screen delimiter.

The independent screenshots show the matching holiday and appointment schedule.
They are ground truth, not the text-extraction mechanism. Navigation used Find
Date only; no event dialog was modified or saved. Calendar exited normally to DOS.

## Minimal reproducible readback helper

`tools/read_ram_text.py` reads a caller-selected span from a previously captured
private dump, preserves spaces and emits JSON. It deliberately does not scan for
an appointment, infer a date, determine the active screen, or automate the debugger.

```text
python tools/read_ram_text.py <private-A-capture> 0x1266e 44
python tools/read_ram_text.py <private-B-capture> 0x12676 36
```

Those offsets are evidence for this session only. Explicit bounds, printable
ASCII validation and a 256-byte limit reject malformed spans. JSON labels the
result unclassified RAM text with no focus/coordinates and live_screen_verified
false: external screenshot comparison supplied the association for this research.
Synthetic unit tests exercise the helper without distributing guest RAM.

## Limits and next controlled step

There is no measured UI-overhead reduction. Ten command dumps per state took
substantially more interaction than a screenshot; offline ASCII decoding is not
an end-to-end performance measurement. A future bounded experiment should test
the candidate's lifetime and location across one Calendar restart, preferably
using a targeted segment-local read and screenshot verification. No such restart
test was performed here. Additional applications, dialogs and focus cannot yet
use this method reliably. Conventional text-video RAM is appropriate to the DOS
control, not DeskMate's observed EGA screen.

Rendering-interface interception was not investigated further because a useful
partial direct-memory observation succeeded. No common DeskMate rendering routine
or driver interface has been identified by this task. If buffer stability fails,
a future narrowly scoped rendering-interface study is preferable to assuming a
full memory map. No emulator instrumentation or background service was added.

## Private reproducible evidence

DOSLAB retains EXPERIMENTS/RESEARCH/screen_state: complete before/after installed
trees and manifests, screenshots, native menu/HELP/console transcripts, clipboard
results, ten chunks per state, corrected joined captures, the invalid wrapped
capture with correction record, command scripts, preservation guards and hashes.
These contain proprietary memory/application material and are not redistributed.
The Phase III-A five-appointment fixture was verified before use; E16 and emulator
profile/executable preservation are checked independently. See its private
verification.json and manifest.json for exact final integrity and file-difference
results. No original software, dump or screenshot belongs in this repository.
