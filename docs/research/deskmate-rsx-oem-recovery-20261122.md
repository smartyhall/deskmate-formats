# DeskMate 03.04.04 RSX OEM installation and application trials

## Resume checkpoint

On November 22, 2026, the same 86Box process from the
[November 21 Atlas trial](deskmate-evolution-native-20261121.md#tandy-1000-rsx-oem-030404)
answered through the authenticated loopback socket. It remained held
at 536,460 emulated ms, frame 32,391, in BIOS video mode `0x12` at
640 × 480. Drive A: still held the second reconstructed floppy.
The native frame showed **Disk Needed** for **DESKMATE 3**. The
previously preserved partial hard-disk image hashes to
`9b4eaa045d826d6d68026ffcfe7d38820a48dfe34afd963a96c0a45c41b2ceba`.
The live image was locked by 86Box. The existing copy is the disk
checkpoint. The held process retains the running installer state.

Resume by mounting the previously verified Disk 3 in A: and
confirming the displayed prompt once. Preserve the locked original
and existing captures. The machine, firmware, media construction,
initial launch, and first two copy stages are documented in the
Atlas trial.

## Reproduction inputs

- `system/rsxdisks.zip` is 4,083,315 bytes and has SHA-256
  `e8289597e3d246727ff977f151ee986dd59d50ace72bdfdd2a65614b88588a5c`.
  Its six nested DeskMate sets are separate from the DOS baseline and
  `UTILS.ZIP`. The volume labels are `DESKMATE_1` through
  `DESKMATE_6`. [Archive and working floppy hashes](deskmate-evolution-native-20261121.md#tandy-1000-rsx-oem-030404)
- The visible 86Box 7.0 automation build emulates a Tandy 1000 RSX
  with a 25 MHz i386SX, 4 MiB RAM, internal VGA, a PS/2 mouse, one
  1.44 MB floppy drive, and an IDE disk with 1,024 cylinders, four
  heads, and 26 sectors per track. Its separate Tandy MS-DOS 5.00
  boot disk is a writable clone. [Pinned emulator, BIOS, and DOS baseline](deskmate-303-305-comparison.md#installation-and-controls)
- Start with Disk 1 in A:. Run `DESK INSTALL` from A: and confirm the
  DeskMate 1 disk prompt. From the floppy desktop, press F2, Down
  twice, and Enter for File → Run. Submit `INSTALL.PDM` and leave
  the Data file blank. Accept `C:\DESKMATE`, then follow the numbered
  disk prompts. The banner reported 03.04.04 and a separate 04.03
  runtime marker. [Install invocation and first two stages](deskmate-evolution-native-20261121.md#tandy-1000-rsx-oem-030404)

## Continuing the six-disk copy

On the held machine, mount each verified 1.44 MB working floppy in A:
through the [authenticated socket](86box-client.md). Press Enter once to
accept the displayed prompt. Keep the original archive and the previous
partial hard-disk checkpoint. Observe the installer while advancing the
guest in held mode, where host wall time differs from guest time.

| Media accepted | Next observed state | Cumulative emulated time |
| --- | --- | ---: |
| Disk 3 | Disk Needed for DESKMATE 4, with Searching files behind the prompt | 766,464 ms |
| Disk 4 | Disk Needed for DESKMATE 5, with Searching files behind the prompt | 1,006,468 ms |
| Disk 5 | Printer Settings, with IBM Graphic and LPT1 selected | 1,526,472 ms |
| Disk 5, after printer setup | Disk Needed for DESKMATE 6 | 1,644,984 ms |
| Disk 6 | Updating AUTOEXEC.BAT and an Install dialog asking to remove the diskette before reset | 1,944,988 ms |

The numbered prompts were sampled in BIOS mode `0x12` at 640 × 480,
within 10,000 emulated ms of each transition. The Disk 5 wait
looked for another numbered prompt for 520,000 emulated ms and
ended at Printer Settings. The exact time that dialog opened is
unknown. Enter accepted IBM Graphic on LPT1 with the line feed
filter off. Its separate Characters Per Inch dialog defaulted to
10 CPI at 1,539,976 ms. Enter accepted 10 CPI and brought up Install
Printer at 1,549,980 ms. It offered **All** printer drivers or **One**.
Enter accepted **All**. At 1,564,984 ms the copy resumed with
`DMPDIBMM.RES` and the Disk 5 artwork still visible. After a further
80,000 emulated ms the installer displayed its Disk 6 prompt.
At 240,000 ms into the Disk 6 copy it was still copying
`MAZE.KUB`. At 300,000 ms it displayed the reset prompt.
The journal and original PNGs stay in the private lab.
[Published capture provenance](../evidence/deskmate-rsx-oem-20261122.json)

## First hard-disk boot and installed inventory

Eject A: at the Install reset prompt and press Enter once. The
installer caused a soft reset at 1,945,718 ms. With A: empty, the
guest executed the hard disk's `AUTOEXEC.BAT` and returned to the
`C:\>` prompt at 1,979,992 ms. At that prompt, run `VER`, then
`CD \DESKMATE` and `DESK`. The hard-disk launcher displayed
**03.04.04** at 1,981,985 ms. The first desktop capture was at
1,997,985 ms in BIOS mode `0x12`, 640 × 480. Escape opened the
exit confirmation. Enter returned to `C:\DESKMATE>` by 2,008,001 ms.
[Booted desktop](../../website/src/assets/reference/evolution-atlas/rsx-oem-first-hard-disk-desktop.png)

The stopped 54,525,952-byte hard disk hashes to
`3085c68955b7fcad648995a40ff30f8f3a799e943710bd43cc0326c69a107fc1`.
The post-run emulator configuration and NVRAM hashes are
`ccdfb129802cdee9467c1316ca1cbedeb30a83192d0ffdec7a57fad64d55b8b9` and
`e3ad097bc778d2be320b6f9a01e662eda1ba4ed4bcb9f4e41071d236f84368ac`.
The lab preserved that disk, config, and NVRAM before application experiments.
The six floppies rehashed to their original working-image digests after ejection.

7-Zip 26.05 extracted 513 files from the installed FAT16 image, up
from 98 on the pristine DOS clone. Of 413 files under
`C:\DESKMATE`, 411 matched a same-path file on the six floppies.
The two others were `DEFAULT.CFG` and `DESKTOP.CFG`. Both names
also appeared at the C: root. This count includes the first Desktop
launch and exit. All DOS baseline files remain present. `CONFIG.SYS`
was byte-identical. The installer added `SET DMCONFIG=C:\DESKMATE`
at the top of `AUTOEXEC.BAT` and extended its path to
`C:\DESKMATE;C:\DOS`. The installed batch file has SHA-256
`81e3342527a29f11e043564a81af4a71709ced599d995f44632535ad295aa4b9`.

## Desktop and navigation

The hard-disk desktop retains the floppy desktop's five illustrated
tiles, teal background, and F8 **Applications** menu. F8 exposes
Display, Move, Remove, Create, Create quick load, Redefine, Delete,
and Set startup app. The lower row holds Text, Programs, and Kubes
panels between AOL and L Invaders shortcut buttons. The stock 3.00
and 3.02 desktops instead place five file panels across a patterned
background with a calculator and calendar along the bottom. Their
center panel shows Hangman in 3.00 and Draw in 3.02. The 3.03.01
desktop uses a blue field with a text-panel Teach Me. Generic 3.05
also uses teal and has an illustrated Teach Me, but uses small
Address, Quick Load, Calendar, and PC-Link buttons. The generic
comparison screens have F7 Desktop and no F8 Applications menu.
These comparisons use the existing native default desktop captures.
[3.00](deskmate-evolution-native-20261121.md#generic-030000-on-the-rsx) · [3.02](deskmate-303-305-comparison.md#deskmate-302-stretch-experiment) · [3.03.01 and 3.05](deskmate-303-305-comparison.md#desktop-menus-and-dialogs)

## Application media inventory

The independent FAT12 extraction locates Information Center on Disk 3
(`INFOCNTR.PDM`, `.HLP`, `.DB`, and `.TUT`). The tutorial references
Daily Events. Disk 5 contains Automatic House. Its
599-byte `HOMEAUTO.PDM` references `HOMGREET.PDM`.
Floor Plan, Routine Maker, and Scheduler each have a separate
program and Help file at the root, and a corresponding icon under
`HOMEAUTO`. The separate modules
provide a way to check what works from the OEM desktop and which
parts load through the greeting program. [Six verified working media](deskmate-evolution-native-20261121.md#tandy-1000-rsx-oem-030404)

| Disk | File | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| 3 | `INFOCNTR.PDM` | 80,181 | `204da3c6e7e8f55df95f62243e930d04bcb7faadde40b486760486987edd9e79` |
| 5 | `HOMEAUTO.PDM` | 599 | `3932629fde07ab9daad59f26f335fb5170776ec48f09554f1bbad5a62402944b` |
| 5 | `HOMEAUTO.DB` | 8,192 | `4096af981c7f977f49d00d2a09001002d6a04add2b61898fc84277bf36f0c523` |
| 5 | `HOMEAUTO.TUT` | 60,120 | `09f756298d1cf8ebc821baeac119f8754c03c7a03d025834f1bd4850aefdb637` |
| 5 | `FLORPLAN.PDM` | 110,591 | `61fb65023db51b3d87ade002716148a41d64fd550fc4efab0c0ef4a5c621b535` |
| 5 | `ROUTINE.PDM` | 24,251 | `4b8e0c5eacaaa02ee56cae9623f273a7d9222acd0dffab5e1742b7bbdf1dec7d` |
| 5 | `SCHEDULE.PDM` | 69,929 | `bb232ca4f7a7c79374a7a34dd7fd9f4bcffdde17a4d514f6e65538fbb490eae3` |
