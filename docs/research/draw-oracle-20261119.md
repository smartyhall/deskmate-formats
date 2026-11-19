# DeskMate Draw comparison oracle

The first comparison run used a disposable clone of the stopped
[glyphs session](graphics-native-20261117.md#reproduction-and-evidence-scope).
Draw 03.05.00 ran on a Tandy 1000 RSX with a 25 MHz 386SX, 4 MiB RAM,
internal VGA and a COM1 serial mouse. The original disk stayed private.
The first session ended at 329,485 emulated milliseconds and 20,417
emulator-reported frames. That interval includes DOS I/O, menus, candidate
trials and the comparison captures. It does not measure drawing speed.

## Reproduce the capture

1. Copy the stopped RSX image, configuration and NVRAM into a new
   private machine directory. Verify the parent disk against
   `5da3bd24009006ab41c21cabd78b974d982d01a27cac1aa35e38e94a1c98b460`.
   Launch once through [86box_launch.py](../../tools/86box_launch.py) in
   held mode. This capture used the background option. Use the existing
   automation build and ROM pins from the previous graphics run.
2. Author candidate files with
   [draw_suite_candidates.py](../../tools/experimental/draw_suite_candidates.py)
   and prepare a new data image with
   [draw_floppy.py](../../tools/experimental/draw_floppy.py). Mount it
   after DOS boot, issue `copy a:\*.fig c:\deskmate`, and wait to observe
   the DOS copy summary before ejecting. Staging uses the guest floppy
   controller and writes only the disposable clone.
3. Run `DESK DRAW <name>.FIG` from `C:\DESKMATE`. Observe the filename in the
   native Draw title before using a capture. For candidate Save As, open File
   with F2 (scan `0x3c`), select the fourth row with four extended Down
   presses (`0x150`), press Enter, and allow the dialog to settle. The filename
   field starts selected. Send the new DOS name with paced input and Enter.
   Observe the new filename in the title and return to DOS with Escape.
4. Reopen the intended file from DOS in a fresh Draw invocation. F5 offers
   Normal, Two times, Four times, Half and Quarter. The baseline used the
   fresh Normal viewport without any selection or drawing tool active.
   Park the pointer above the canvas through the serial mouse socket.
   Capture, advance the guest 450 ms, and capture again. Require identical
   drawing-area bytes and check the private frames for the title and clean canvas.
5. Return to DOS and quit the owned emulator via the socket. Copy the stopped
   disk. Compare 7-Zip extraction against
   [draw_disk.py](../../tools/experimental/draw_disk.py) on the same stopped
   FAT16 image. Match each diagnostic file to the planning manifest.

[draw_oracle.py](../../tools/experimental/draw_oracle.py) takes the machine
directory, private evidence directory, capture label and ordered action
arguments. It reads the launch receipt, uses the authenticated loopback socket,
and records action intent, transitions, framebuffer PNGs and hashes. It steps
an already held clone. A new label is required for each capture. A failed or
uncertain action needs inspection of the prior receipt before another mutation.
No host keystrokes or display clicks are involved.

## Normal and Two times coordinate controls

The framebuffer is 640 × 480, VGA BIOS mode `0x12`. The drawing crop is the
half-open rectangle `[0, 62, 640, 480]`, retaining the original 640 × 418
pixels. The cursor and title/menu regions are outside that rectangle. The
guide does not establish the world-to-pixel mapping below. These observations
come from reopening the original, tool-authored MAP.FIG control.

| World position or span | Normal framebuffer pixels | Two times framebuffer pixels |
| --- | --- | --- |
| `(800,985)–(1200,985)` | x 64–96, y 147 | x 128–192, y 232 |
| `(1250,730)–(1750,730)` | x 100–140, y 125 | x 200–280, y 188 |
| `(1263,780)–(1763,780)` | x 101–141, y 129 | x 202–282, y 196 |
| `(-200,300)–(925,300)` | x 0–74, y 87 | x 0–148, y 113 |
| `(400,-200)–(400,800)` | x 32, y 62–131 | x 64, y 62–200 |
| `x=2000.25`, vertical line from `y=1000.25` | x 160, y starts at 148 | x 320, y starts at 234 |

The sampled endpoints agree with truncation of positive transformed
coordinates, scales `640/8000` and `418/4840`, and a framebuffer offset
of `(0,62)`. The sample shows inclusive endpoints and clipping for the
tested one-pixel lines. It does not identify the exact internal scale
constant, rounding order at all fractional thresholds, negative-coordinate
rounding before clipping, or the relation between zoom and a scrolled viewport.
The baseline uses the same origin and continuous scale for all SVGs.

The captured background is RGB `(0,0,129)`; the stored palette specifies
`(0,0,128)`. The tested stored values 128 and 192 appear as 129 and 194 in
the native framebuffer. Metrics preserve that difference. Each foreground
mask uses its own background so a palette conversion difference across the
blank canvas cannot dominate foreground agreement.
