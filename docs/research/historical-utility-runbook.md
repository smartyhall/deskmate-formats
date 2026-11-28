# Historical utility lab runbook

This procedure reuses the [campaign environment](campaign-environment-procedure.md)
and the [initial utility protocol](../historical-utility-validation.md).
The [campaign evidence](../evidence/historical-utility-qualification-001.json)
pins the baseline, ROM, runtime resources, stage images where recorded, and
result identities. Reproduce on independently owned disposable media.

## Host and guest preparation

1. Check out `research-origin-001` at
   `a49e72b3b967e6ed0b6097cb040114072a4970e7` in an owned worktree.
   Provision an offline campaign environment and run the reviewed preflight.
   The measured CPython 3.13.17 parent and isolated child passed all eleven
   checks. Record local resource ownership with the private campaign registry.
2. For native testing, clone the stopped 03.05.00 Filer baseline identified in
   the evidence. Copy its configuration and NVRAM into the owned clone.
   Use RSX i386SX at 25 MHz, 4 MiB, internal graphics, PS/2 input and guest
   network links down. For standalone testing, use the separately preserved
   clean MS-DOS 5.00 RSX disk. Its older INI starts with orphaned general keys
   that the launcher refuses. Preserve that file and use the qualified RSX
   profile from the Filer baseline on the disposable DOS clone. The clean
   disk's file listing has no DeskMate installation.
3. Use the pinned visible 86Box build. Launch with
   `python tools/86box_launch.py --machine <clone> --mode visible --port <free-loopback-port> --seed 1`.
   Verify the launcher PID, the matching loopback listener and the visible
   window. If the readiness read times out, reconcile that same process
   through the existing authenticated socket and Win32 process/window
   inspection. Require it to be held and unpaused at 0 ms before advancing.
   The first native launch needed this recovery. No second process or
   injected host input was needed.
4. Decompress selected bytes from the already-held original archives, then
   compare them against the [registry](historical-utility-registry.json).
   Python's ZIP reader opens the embedded ZIP in `dmrepair.exe` as data.
   For older ZIP compression, verify the extracted bytes against the member's
   declared length and CRC as well as the registry hash. Stage in a fresh
   1.44 MB FAT12 data floppy using the same geometry as
   [the existing Draw staging recipe](../../tools/experimental/draw_floppy.py).
   The utility trial added ordinary DOS 8.3 names and set a fixed 27 November
   2026 FAT directory date on its private staging copy. Verify media by
   extracting its staged files before mounting. Use only a campaign-owned
   floppy and hard disk. Keep the source archives read-only.
5. Boot to the DOS prompt before mounting. Mount only via the authenticated
   native socket. Send one DOS command at a time and step until its expected
   prompt or copy result is present. Back-to-back input while floppy I/O was
   busy dropped characters in this campaign. Eject the data floppy before
   boots and resets. A DOS retry that stalled before the prompt recovered
   after socket eject and hard reset.
6. Use held socket observations with framebuffer capture to verify each
   menu, filename, prompt and result. Advance deliberately in bounded
   steps. At a command timeout, inspect the current guest state before any
   further action. Capture a final prompt or dialog, call native quit, verify
   the owned process exited, and only then extract stopped-disk bytes.
   Record content inventories before and after, and compare selected outputs
   with the 7-Zip and direct FAT16 reads. Scope the comparison to file content
   and separately pin disk, NVRAM and configuration identities.

## DBrepair on native DeskMate 03.05.00

1. Copy the verified `DBREPAIR.PDM` and `FIL2DBF.PDM` to
   `C:\DESKMATE`. From the unmodified native QRECORD fixture, stage separate
   copies `C:\UTILTEST\GOOD.FIL` and `C:\UTILTEST\EXPORT.FIL`. The
   campaign also staged `COLD.FIL` as an unchanged control. Photograph only
   the synthetic guest states via socket framebuffer capture.
2. At `C:\DESKMATE>`, type `DESK DBREPAIR`. When the utility is ready, press
   F2, R, Enter to open Repair Database. Press Tab to focus the filename
   field, enter `C:\UTILTEST\GOOD.FIL`, then Enter. Accept the results
   dialog with Enter and exit to DOS with Escape. In the measured run the
   results appeared at 44,382 emulated ms and shutdown followed at 56,108 ms.
   Extract and compare the new `GOOD.FIL` and `GOOD.OLD` against the input.
3. Cold boot a fresh clone of the stopped disk. From the DeskMate directory,
   run `DESK FILER C:\UTILTEST\GOOD.FIL`. Inspect the value and exit with
   Escape without editing. The measured Filer screen appeared at 18,484 ms
   of the follow-up session.
4. After recording the healthy control, copy the original native bytes to a
   new `DEFECT.FIL` and set its zero-based byte at `0x1C2A` from `00` to
   `01`. The [fixture manifest](../../tests/fixtures/application-generated/manifest.json)
   gives the generator command and source hash. Keep the healthy original and
   damaged original separate from the file given to DBrepair. Record the
   expected index failure and recovery alternatives before launch.
5. Repeat the same repair workflow on `C:\UTILTEST\DEFECT.FIL`. The result
   dialog was captured at 35,656 ms of the follow-up session. Return to DOS,
   eject the floppy, cold-reset, and run `DESK FILER C:\UTILTEST\DEFECT.FIL`.
   The read-only reopen was observed at 55,156 ms on the cumulative socket
   clock, including the hard reset. Extract the output and OLD backup.
   A future trial can add a stopped-disk extraction before this second
   cold reopen to bound what the reopen could have changed.

## Fil2dbf export

1. Pre-write the source schema and ordered rows using
   `python -m deskmate_formats.filer <original.fil>`. For QRECORD, predict
   the named C/22 field, one padded active `F7Q9` record, lengths and
   terminators before launching Fil2dbf.
2. Native mode used
   `DESK FIL2DBF C:\UTILTEST\EXPORT.FIL C:\UTILTEST\EXPORT.DBF`.
   Select DATA in the table list. In the keyboard dialog, Tab moves button or
   list focus and extended Down (`0x150` in the socket client's key API)
   moves the active selection when the list has focus. Verify DATA is
   highlighted before Enter. At the field-name prompt enter `FTXT_A` and
   confirm. The program returned to DOS at 68,184 ms in the follow-up session.
3. For an independent negative input, use `NOT A DATABASE\r\n` as the
   contents of `BAD.FIL`. Launch in the same way with a fresh `BAD.DBF`
   destination and observe the reported error and any side effects. The
   negative trial had an Open Failed dialog at 74,904 ms. After acknowledging
   it, the native guest was stopped at 76,276 ms. DOS return was not observed
   after this rejection.
4. Standalone mode uses only the clean DOS clone. Copy `f2ddos.zip` members and
   the two PDMs from `f2d01.zip` to `C:\F2D` in the guest. Put the same
   original control there as `DOSGOOD.FIL`. From that directory set
   `DMCONFIG=C:\F2D` and `PATH C:\DOS;C:\F2D`, then run `FIL2DBF` with no
   arguments. Cancel mouse setup for keyboard operation, select
   `C:\F2D\DOSGOOD.FIL`, accept proposed `DOSGOOD.DBF`, select DATA and
   type `FTXT_A`. The output-file prompt was observed at 55,872 ms and the
   stopped guest remained at 62,944 ms after the DOS directory check.
5. After each stop, compare every created and modified file by size and
   SHA-256. For offline DBF inspection, create a separate owned checkout at
   `c679d9666febfb28212c132be30df51be0c5ab59` and verify its HEAD. This
   [analysis revision](https://github.com/smartyhall/deskmate-formats/blob/c679d9666febfb28212c132be30df51be0c5ab59/tools/experimental/inspect_fil2dbf.py)
   contains the inspector. Create a dedicated CPython 3.13 environment
   with `py -3.13 -m venv --without-pip <analysis-venv>`. The inspector uses
   the standard library. Run the following from the analysis checkout.

   ```powershell
   & "<analysis-venv>/Scripts/python.exe" -I tools/experimental/inspect_fil2dbf.py "<absolute-path-to-export.dbf>"
   ```

   The measured guest runs remain tied to `research-origin-001` at
   `a49e72b3b967e6ed0b6097cb040114072a4970e7`. The inspector reports the measured dBASE III
   character framing, raw descriptor, record bytes, padding and EOF.
   Compare its JSON against the independently written expectation.

## SND2WAV secondary test

Reuse the stopped standalone DOS profile. Stage `SND2WAV.EXE` 1.2 and the
manifested `odd-5500-native.snd` control in `C:\SNDTEST` as `ODD.SND`.
From the observed DOS prompt, run `SND2WAV ODD.SND ODD.WAV`. The successful
conversion returned to DOS and the session stopped at 37,592 emulated ms
including the boot and recovery reset. Compare the original SND with the
expected PCM using the Sound reader, then inspect the extracted WAV using
Python's `wave` and `struct` modules. Record RIFF chunk size, number of frames,
sample width, rate, channel count, alignment and the PCM SHA-256.

Use the qualified original variants for further tests. The RSX OEM Home
Organizer, early BASIC/Filer, HomeWord II, standalone graphics and Windows 98
VB6 profiles have separate dependencies. This campaign prepared only the
03.05.00 Filer and isolated DOS profiles. All owned guests exited and the
private configurations, disks, and evidence are preserved for coordinated reuse.
