# Print Companion and native printing on the Tandy 1000 RSX

November 23, 2026. Print Companion on the installed RSX OEM DeskMate
03.04.04 opened five applications. Four editors performed Save As and Open with synthetic entries. A cold
control found that Name Tags retained the description but lost typed text. Graphics Manager created an illustration in Draw and
reopened it through the same manager. Two printer selections produced
different byte streams for the same saved card. The IBM Graphic stream
reconstructs both panels on a single Letter sheet, including the rotated
inside panel. [Earlier RSX installation](deskmate-rsx-oem-recovery-20261122.md)

## Native application survey

The Desktop's Print Companion shortcut enters a five-icon navigator. Select
an icon and press Enter. The navigator has Color and Black and white options.
An editor's Escape returns to the navigator, except that Graphics Manager
first returns from Draw to its own thumbnail browser. The lower navigation
bar also links to Graphics Manager, Print Companion, or the Desktop as
appropriate to the current editor.

| Branch | Measured interface and procedure | Synthetic control |
| --- | --- | --- |
| Greeting Cards | Two ruled panes labeled Front and Inside. Enter text in Front, click the first line in Inside, wait for focus, and enter the inside text. F2 → Save as stores a description. F2 → Open lists descriptions and dates. Page setup and Print are separate. | **LAB MOON**, front `HELLO MOON`, inside `FROM THE LAB`. |
| Notices | Single scrolling ruled canvas. F3 offers standard editing and Plain, Bold, and Underline for selected text. F4 offers Illustration and Stationery and removal commands. F5 offers Text settings and Preview. F2 → Save as, then F2 → Open. | **MOON LAB NOTICE**, two lines `MOON LAB` and `OPEN TODAY`. |
| Personal Letters | Dated letter form with separate salutation, body, and closing areas. F2 offers Print letter and Print envelope. F5 offers Text settings, Proof, Thesaurus, Dictionary, Translate, and Run Diary. Type at the salutation insertion point, click the first body line, enter the body, then use F2 → Save as and Open. | **MOON LAB LETTER**, salutation `Dear Moon Lab,`, body `Welcome to the moon lab.` |
| Name Tags | Single bordered, ruled tag. F4 offers Select list, Field association, and Run Address Book. Print all tags was disabled without a list. F2 offers Print name tag, plus Name tags format and setup. F5 offers Text settings and Stationery. Type two lines, then use F2 → Save as and Open. | **MOON LAB TAG**, two lines `MOON LAB` and `GUEST 01`. |
| Graphics Manager | F3 switches between Illustrations and Stationery. The thumbnail browser names the selected .FIG and offers Edit and Delete. F2 → Create adds .FIG to a typed basename and launches Draw. Drag a diagonal using the Line tool on the small upper-left canvas, use F2 → Save, and press Escape. Select Edit and press Enter to reopen in Draw. | **LABLINE.FIG**, one diagonal line using the default Draw style. |

Notices Text Settings listed Cobb, Dixon, Marin, and System, with point
size, width, bold, italic, and hollow controls. Its default was Cobb at
24 points and 100% width. The notice preview placed the two text lines
near the upper-left of a portrait page.

Name Tags offered Paper sheets, Roll tags, and Single tags. Paper Sheets
Setup showed a 5.5 × 4.5-inch tag, 1.5-inch spacing, four one-inch margins,
and an unchecked pause option. The warm Open showed both typed lines.
On a fresh visible boot from a stopped disk copy, the description was
present in the Open picker, but the opened tag body was blank. Notices
recovered both lines on the same cold boot.

The card Page Setup showed 8.5 × 11 inches,
one-inch top and bottom margins, zero left and right margins, and an
unchecked pause option. The campaign used the card defaults. The editor
formats and margins were read from the dialogs. No physical paper was fed.

### Document storage

See the [format notes](../reference/deskmate-print-companion-formats.md)
and [binary fixture manifest](../../tests/fixtures/application-generated/manifest.json)
for exact identities and evidence limits.

## Printer setup and isolated capture

F10 → Setup → F2 Options → Printer opens system-wide Printer Settings.
The visible list at the selected IBM Graphic entry contained HP LaserJet,
HP LaserJet Compatible, IBM Daisywheel Compatible, and IBM Graphic. The
dialog offers LPT1, LPT2, LPT3, No printer, a Line feed filter, and a
floppy-based Update button. This is the observed list viewport. The
earlier native install selected **All** printer drivers. The lab's stock
setting was IBM Graphic at 10 CPI, LPT1, with the filter off. The HP
LaserJet test selected Courier at 10 CPI and 150 DPI. The same dialog
offers Letter Gothic Condensed, Prestige Elite 12 CPI, 300 DPI, and
Advanced Settings. [OEM install and IBM setting](deskmate-rsx-oem-recovery-20261122.md#resume-checkpoint)

1. Clone the sealed RSX OEM hard disk, config, and NVRAM into a disposable
   machine directory. The disk SHA-256 is
   `3085c68955b7fcad648995a40ff30f8f3a799e943710bd43cc0326c69a107fc1`.
   The profile uses a 25 MHz 386SX, 4 MiB, internal VGA, PS/2 mouse,
   and a 1,024-cylinder, four-head, 26-sector IDE disk. Leave network
   links down and A: empty. [Pinned ROMs and hardware](deskmate-303-305-comparison.md#installation-and-controls)
2. With 86Box stopped, configure the clone as shown below. Use a new regular
   file in the private evidence directory. 86Box opens it in binary write
   mode and truncates it at startup. The strobe option uses the emulated
   LPT handshake. The immediate flush makes it possible to inspect the
   settled byte count before stopping. This attachment performs file I/O
   and has no host printer or print queue connection.
3. Launch with `python tools/86box_launch.py --machine <clone>`. The
   authorized visible run used seed 1 and 86Box 7.0 automation build
   `e7e1244588ea721aa239564a43fa2636611ae965ea8431672fdc06d8c12c280d`
   from source `855258da966f1594f568350be59e8e1eca082ed1`.
   Advance approximately 35,000 emulated ms from power-on, then run
   `CD \DESKMATE` and `DESK` over the [authenticated socket](86box-client.md).
4. Create and save **LAB MOON** as described above. In F2 → Print, choose
   the active printer and one copy. Confirm once. The lab file was empty
   before the first job and stabilized at 1,347 bytes after a 40,000 ms
   observation. The File radio button is a separate guest destination
   and was unused for this LPT test.
5. Reopen **LAB MOON**, choose HP LaserJet through Setup, keep the same
   LPT1 port and disabled filter, and reopen and print the saved card
   at 150 DPI. Another 4,391 bytes were present after the 35,000 ms
   observation. The session file retained its IBM job prefix unchanged.
   Split at byte 1,347, the verified end of the first job, and hash both
   slices. A fresh capture file per job is also suitable if using separate
   emulator runs.

```ini
[Ports (COM & LPT)]
lpt1_enabled = 1
lpt1_device = file

[File (LPT) #1]
path = <absolute path to new private capture file>
strobe = 1
append = 0
flush = 1
```

The BIOS video mode was 0x12 at 640 × 480. Timing is cumulative emulated
time from the held launch. See the [evidence manifest](../evidence/print-companion-20261123.json)
for frame timestamps, machine and application identities, and stream hashes.
Native framebuffer PNGs, socket journals, and the verified stopped disk
copy were preserved privately. The survey run stopped at 610,524 emulated
ms after a clean exit to DOS.

## Two print streams from one card

| Driver | Bytes | Observed output |
| --- | ---: | --- |
| IBM Graphic | 1,347 | IBM-style dot-matrix commands. Five `ESC L` bands with 243, 241, 243, 202, and 200 columns, followed by one form feed. |
| HP LaserJet | 4,391 | HP PCL commands. Two `ESC * t 150 R` settings. 68 positioned raster transfers with 2,206 binary payload bytes and one form feed. |

IBM Graphic uses `ESC J n` for advance in 1/216-inch units, CR to
return horizontally, and spaces at 10 CPI before each band. `ESC L`
takes a little-endian column count and one eight-pin byte per column,
with the high bit at the top. The dots occupy a 120 × 72 dpi grid.
The output shares commands with ESC/P. The native selection and the
IBM print mode semantics support identifying it as IBM Graphic-style
output. The setup bytes include 66 lines per sheet and CR-only
behavior under this profile. [Epson FX-86e/286e command summary, Appendix A](https://files.support.epson.com/pdf/fx86e_/fx86e_u1.pdf)

The HP stream starts with pitch and page controls. It positions the
cursor with `ESC & a # H` and `ESC & a # V`, starts raster graphics
at the current position with `ESC * r 1 A`, transfers the counted row
with `ESC * b # W`, and ends graphics with `ESC * r B`. Following the
explicit lengths consumes both payloads through their respective final
form feeds. The PCL 5 reference documents these command meanings. The
capture does not establish which PCL generation the DeskMate driver
originally targeted. [HP PCL Printer Language Technical Reference, raster graphics](https://www.hp.com/ctg/Manual/bpl13210.pdf)

## PDF reconstructed from the IBM stream

Run the extended [IBM Graphic inspector](../../tools/experimental/typography_ibm_print.py)
from the checkout with ReportLab installed.

```powershell
python tools/experimental/typography_ibm_print.py tests/fixtures/application-generated/print-companion/card-ibm-graphic.prn --pdf lab-moon-card.pdf
```

The program accepts the measured initializer and rejects unknown or
truncated commands. It renders the captured dots directly on a 612 ×
792-point page. Its JSON reports five bands and 1,090 distinct dots.
Their inclusive bounds are (237, 372) to (681, 430) in 120 × 72 dpi
coordinates relative to the model's top left. No modern font was used
to recreate the lettering. The raster shows `FROM THE LAB` upside
down on the left and `HELLO MOON` upright on the right. Both editor
panes had been displayed upright. The print placement is consistent
with a fold layout. No fold or physical-print measurement was made.

The PDF preserves modeled dot centers and panel orientation. Dot radius
(0.32 points), mechanical printer origin, ribbon impression, and paper
feed tolerances are outside the measurement. A modern printer can use the
generated PDF through an ordinary PDF print dialog at actual size once an
operator authorizes a physical trial. PCL rendering and physical calibration
remain separate follow-ups.

## Shared printing and next experiments

The native Setup path and driver swap show that Greeting Cards uses the
shared printer selection state. After the swap, reopening the same card
changed the destination label and the LPT byte language. Static string
inspection separately found `DMPD.CFG` in Cards, Notices, Personal Letters,
and Name Tags, and `DMPRTSEL` in Setup. A before/after comparison found a 20-byte IBMM record in the baseline
configuration and an appended 20-byte LASR record after the change. The
installation contains parallel
.ACC, .RES, and .RFD sets with the basenames `DMPDIBMM`, `DMPDLASR`,
`DMPDASCI`, and `DMPDS`. `DMDRWPRT.ACC` is present, but this experiment
did not trace its calls. No conclusion about DOS INT 17h versus direct
adapter writes follows from capture at the emulated LPT device.

The earlier Draw trial used IBM Graphic and Print to File, yielding a
shorter initializer and the same `ESC L` band framing. The inspector
retains that parser entry point. A future matched Draw LPT and File
control can test whether their differences arise from application
initialization or the destination. Text, Filer, and Worksheet are good
targets for the same capture transport, starting with synthetic one-page
jobs and recording whether the drivers emit resident text, bitmap graphics,
or both. Output similarity can guide a runtime call trace. It cannot
establish shared code by itself. [Earlier Draw and font printing trial](typography-lab-20261119.md#native-printing)

The application survey recorded stationery controls, default layouts,
and menu affordances. It leaves populated Address Book merges,
envelope printing, alternate tag media, 300 DPI, the full driver list,
and equivalence to native Print to File for later qualification.
