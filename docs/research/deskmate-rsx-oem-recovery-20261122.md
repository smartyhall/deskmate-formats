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

## Continuing the six-disk copy

On the held machine, mount each verified 1.44 MB working floppy in A:
through the [authenticated socket](86box-client.md). Press Enter once to
accept the displayed prompt. Keep the original archive and the previous
partial hard-disk checkpoint. Observe the installer while advancing the
guest in held mode, where host wall time differs from guest time.

| Media accepted | Next observed state | Cumulative emulated time |
| --- | --- | ---: |
| Disk 3 | Disk Needed for DESKMATE 4, with Searching files behind the prompt | 766,464 ms |

The Disk 4 prompt was sampled in BIOS mode `0x12` at 640 × 480.
The time is the observation boundary, within 10,000 emulated ms of the
transition. The journal and original PNG stay in the private lab.

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
