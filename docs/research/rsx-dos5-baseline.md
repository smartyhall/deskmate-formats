# Tandy 1000 RSX / Tandy MS-DOS 5.00 baseline

Research session: **2026-11-04**, America/Los_Angeles. Acquisition and some
private log timestamps fall on November 5 in UTC. This is a live emulator
experiment, separate from the earlier static automation preflight. No DeskMate
installation or Calendar database experiment was performed.

## Verified result

The designated RSX profile's BIOS error was reproduced and corrected in an
isolated copy. Original Tandy DOS media were verified, DOS Setup completed on a
new 52 MiB IDE image, and DOS booted without floppy media. A full emulator
process restart and a fresh writable clone of the sealed baseline both booted
successfully. `VER`, `MEM`, and a completed read-only `CHKDSK C:` were observed
through the native socket. The disk hash remained unchanged across verification
and the restore test.

The reusable [Python client](86box-client.md), synthetic tests, and
[media derivation tool](../../tools/experimental/tandy_dos5_media.py) are public
source. Original media, documentation, NVRAM, installed binaries, images,
framebuffers, register/memory captures and socket journals remain outside Git.
Public [baseline metadata](../evidence/rsx-dos5-baseline.json) contain hardware,
geometry and an inventory of 98 installed files with sizes and SHA-256 hashes.

## Repository and laboratory identity

The existing repository was clean on `main` at `99eae60` when inspected. Remote
information was fetched without reset or local-work removal. The experimental
branch `experiment/86box-dos5-baseline` was created from
`origin/feature/windows10-lab-deployment` at
**6d388ff8068022514cbdbe5e22394637de5f9bb7**, the branch associated with draft
[PR 29](https://github.com/smartyhall/deskmate-formats/pull/29). Deployment scripts,
ROM provisioning, prior protocol review and research history were reviewed.
No `AGENTS.md` existed; concise standing research instructions were added with
the repository's approved documentation license. No push, merge or PR edit was
performed. Local commit identities are in Git history and the private session
completion receipt, avoiding a self-referential commit hash in this document.
Reusable client/media tooling and standing instructions are committed at
**fafc31168eb45a63e5dd69c0a1880097eb34a422**. Git identity was absent on this
workstation; these local commits use the same public noreply identity as the
existing deployment commits through command-scoped Git options, without changing
global identity settings.

| Component | Observed identity |
|---|---|
| 86Box source | `855258da966f1594f568350be59e8e1eca082ed1`, clean checkout |
| ROM checkout | `908394b690f7da28f47727d9876774fd672c4ed3`, clean checkout |
| Executable | `C:\DeskMateLab\builds\86box-automation\src\86Box.exe` |
| Executable SHA-256 | `e7e1244588ea721aa239564a43fa2636611ae965ea8431672fdc06d8c12c280d` |
| Build configuration | CMake Release, `AUTOMATION:BOOL=ON`; existing build reused |
| Runtime | `C:\msys64\ucrt64\bin`; private CMake cache and loaded-module inventory retained |
| Protocol / reported version | 1 / 7.0 |
| Transport | authenticated `127.0.0.1:8765`, one client, default per-launch token file |
| Launch policy | `--automation-hold --automation-seed 1`; no explicit token-file argument |

No emulator was running initially. The existing profile was preserved, including
configuration and NVRAM backups before changes. Its configuration SHA-256
`78877439cbdeef3503ae96c8009b6f2f70fa63ce88aac9c7affe9c03eb6013c5`
and NVRAM SHA-256
`982835352216e2390a2e1f354ab59fd382889d1064d86c7cd5e3b2770964a03e`
still matched their originals at session end.

## Media acquisition and original documentation

The explicitly authorized [Nextcloud download](https://nextcloud.retroconnect.org/raw/arNSj24G52zEbcy)
returned HTTP 200, 947,189 bytes, content type `application/x-7z-compressed`.
**It is a 7-Zip archive, not a ZIP.** Its SHA-256 is
`826029a352455e016efe6c1dfe4c4c7243a30526cb604be92a227a7d6643438b`.
No filename was supplied in a Content-Disposition header; the initially assigned
local name `tandy-dos5-original.zip` was retained and the actual format recorded.
No alternative download source was used.

The archive's complete entry list was inspected before extraction. It contained
one named distribution directory and precisely two images plus two text files.
The extraction helper required that exact allowlist, extracted each file through
7-Zip stdout, and wrote only fixed, exclusively created staging filenames. No
archive-supplied filesystem destination or link was followed. Thus traversal,
absolute paths, alternate streams, links and unexpected members were excluded
by the allowlist rather than delegated to general recursive extraction.

Original archive and response headers are under
`C:\DeskMateLab\private-evidence\dos5-session-20261104`. The images and both
accompanying text files are staged under `C:\DeskMateLab\media\TandyDOS5` with
read-only file attributes. Exact entry sizes/hashes are in the independent
[acquisition inventory](../evidence/tandy-dos5-acquisition.json).

| Original image | Bytes | Verified SHA-256 |
|---|---:|---|
| MSDOS1.img | 1,474,560 | `ad566ffef55afab65e73b7bfd4edd94ff22c062bfdfab92bd70bb0c2884594fe` |
| MSDOS2.img | 1,474,560 | `c187413ce6d40c715e49b94001f976d1bb35f7fd6a96aa06745dd620aad2f393` |

Both original hashes were rechecked after installation. They matched exactly.
The accompanying archive README identifies RLX/RLX-HD B distribution models;
it does not establish general RSX compatibility. This experiment demonstrates
the installed DOS baseline on this emulated RSX, not every supplied utility.

Disk 1's `README.1ST` directs the reader to Disk 2's `README.TXT`, Section 2.
That section addresses machine-specific HIMEM switches, lists other systems,
and supplies no RSX-specific switch. Section 4.3 discusses fallback switches
for Phoenix BIOS problems. The default installed HIMEM worked here with A20
handler 1, so no fallback was applied.

`SETUPRLX.EXE` contains an explicit Tandy 1000 RLX setup identity and is a
hardware-configuration utility, distinct from DOS `SETUP.EXE`. It was inspected
offline but never executed on the RSX. The supplied `CONFIG.DSK`/`AUTOEXEC.DSK`
templates include RLX ROM-drive and DeskMate assumptions. They were not copied
over the installer-generated startup files. The actual installer produced
ordinary C:\DOS startup settings without those ROM-drive references.

### Necessary Disk 2 working-copy derivation

The verified original Disk 2 has no FAT root volume-label entry. `SETUP.INI`
expects `DISK      2`. Setup repeatedly rejected the original working image at
61%, despite successful mounting and subsequent execution time. Inspection of
the original FAT root and installer metadata identified the mismatch.

A derived image adds a root label entry at decimal offset **11,328** (`0x2c40`).
Exactly offsets **11,328 through 11,339** changed from zero to the eleven ASCII
label bytes and attribute `08`. No file content, FAT chain or boot-sector byte
changed. The 32-byte directory entry after derivation is:

```text
4449534b20202020202032080000000000000000000000000000000000000000
```

`MSDOS2-labeled.img` SHA-256:
**2fa123a23b28ac1148caa95410ff43ec96f5e06ff74894777abec87cf859165e**.
Setup accepted it and resumed copying Disk 2. The public helper independently
reproduced the same hash from the preserved original:

```powershell
python tools/experimental/tandy_dos5_media.py C:\DeskMateLab\media\TandyDOS5 C:\DeskMateLab\machines\new-dos5-working-media
```

The destination must be new. Both original hashes are checked before publication.
Four synthetic tests cover precise changes, invalid geometry/existing labels,
hash failure and no-overwrite staging. The original Disk 2 remains unchanged;
the labeled derivative is explicitly identified as installation working media.

## BIOS diagnosis and corrective procedure

The inherited profile omitted the `Floppy and CD-ROM drives` section. The pinned
86Box `src/config.c:load_floppy_and_cdrom_drives` defaults drives A and B to
`525_2dd`, i.e. 360 KB drives. The saved Phoenix Setup instead described A as
1.44 MB and B as absent. This mismatch was the reproduced cause of the POST
configuration error.

Controlled sequence, using copied configuration and copied 128-byte NVRAM:

1. Start held; advance 10,000 emulated ms in validated 1,000-ms steps. Capture
   CP437 text, native framebuffer, registers, BDA equipment/base-memory words,
   status and machine identity. The configuration error appears.
2. Enter F2, dismiss its warning, inspect Setup and save with F2 without changes.
   After the reboot and another 10,000 ms, the same error appears. Preserve that
   configuration/NVRAM checkpoint and quit the emulator.
3. Set `fdd_01_type = 35_2hd` and `fdd_02_type = none` in the copied profile.
   Preserve NVRAM; do not delete or reseed it. Restart. POST now reaches the
   expected no-boot-device prompt without the configuration error.
4. Mount a verified working Disk 1 and reset. Allow approximately 30,000 ms for
   the floppy boot, checking actual screens. DOS reaches A> and reports 5.00.
5. Later full process restarts and the restored pristine clone retain a clean
   POST with those explicit drive settings.

This rules out nonpersistent NVRAM as the explanation of the reproduced error:
saved NVRAM was retained, and matching emulated drive hardware cleared it.
It does not rule out unrelated RTC/NVRAM bugs on other machines or revisions.
No CMOS byte patch, ROM patch, emulator-source change or original-profile reset
was needed. The RSX IDE controller is added by
`machine_at_common_ide_init`; `hdc_1 = none` means no additional controller here.

Early ad-hoc staging used Python's Windows default text decoding on a UTF-8
configuration, producing a malformed leading section while the valid hardware
sections still loaded. That intermediate file was preserved. Before final cold
boot, the same hardware settings were written as an explicit ASCII config;
86Box's subsequent saved config has a valid General section. Host RTC syncing
was then explicitly disabled. Preliminary drive-picker navigation also selected
unintended entries; screen readback caught these and drive C was verified as
AUTO before partitioning. Final settings are supported by captures, not by
provisional screenshot filenames.

## Final hardware and storage

| Setting | Verified value |
|---|---|
| Machine | `tandy1000rsx`, Headland HT18 |
| CPU | 386SX, 25 MHz, dynamic recompilation disabled |
| Configured RAM | 4,096 KiB |
| POST memory | 640 KiB base + 3,072 KiB extended; shadow remapping disabled |
| Video | internal Cirrus GD5402, observed 720 x 400 text framebuffer |
| Input | PS/2 keyboard and mouse; no tablet; socket input only |
| Sound | internal; audio behavior not tested |
| Networking | all four configured links off; no networking changes |
| Floppy | A 1.44 MB 3.5-inch; B absent; no media in final state |
| BIOS disk setup | C AUTO, D absent; startup A with hard-disk fallback |
| IDE disk | primary master, raw image, 54,525,952 bytes (52 MiB) |
| Disk geometry | 1024 cylinders x 4 heads x 26 sectors x 512 bytes |
| Timing profile | saved 86Box default `1997_5400rpm`; not claimed historically accurate |
| Clock | `time_sync = disabled`; restore saved NVRAM with disk/config |

The size approximates the requested historical nominal 52 MB class. The selected
geometry and timing are laboratory choices, not a claim about a particular
original RSX drive model. IDE AUTO was used instead of a mismatched fixed type.

Offline MBR/BPB inspection independently agrees with the emulator geometry:
one active type-06 FAT16 primary partition, start LBA 26, 106,366 sectors,
54,459,392 bytes, end CHS 1022/3/26. The FAT16 BPB has 512-byte sectors,
4 sectors/cluster, two FATs of 104 sectors each, and 512 root entries. Setup
left its chosen trailing geometry margin rather than consuming every disk byte.
Volume label is `MS-DOS_5`, serial `5D64-A800`.

## Installation procedure

Only the exclusively created emulated image
`C:\DeskMateLab\machines\rsx-dos5-experiment\rsx-dos5-working.img` was
partitioned/formatted. No Windows disk initialization API or host-volume command
was used. The raw file was created with Python exclusive mode and truncated to
`1024 * 4 * 26 * 512` bytes. Existing research images were not targets.

The isolated profile uses these essential disk settings:

```ini
[Floppy and CD-ROM drives]
fdd_01_type = 35_2hd
fdd_02_type = none

[Hard disks]
hdd_01_fn = rsx-dos5-working.img
hdd_01_ide_channel = 0:0
hdd_01_parameters = 26, 4, 1024, 0, ide
```

1. Back up config/NVRAM, create the new raw disk, attach it to primary IDE
   master, and set BIOS drive C to AUTO. Verify that Setup's main screen
   actually displays AUTO; disk-picker cursor position matters. Save with F2.
2. Mount the verified working Disk 1, reset, and wait for A>. Run `SETUP`.
   Accept United States/US keyboard and hard-disk installation, use C:\DOS,
   and select **not** to run DOS Shell at startup.
3. Allow Setup to allocate all free disk space on the sole new disk. It
   partitions and reboots. On this distribution the floppy AUTOEXEC does not
   automatically resume Setup: run `SETUP` again from A>.
4. Continue Setup. It formats C and copies files. Observe progress with bounded
   emulated-time steps; do not use fixed host sleeps as completion evidence.
5. At the Disk 2 request, eject Disk 1, mount the separately labeled Disk 2
   derivative, allow the media change to settle, and press Enter. Wait until
   Setup explicitly reports completion.
6. Eject all floppy media, then press Enter to reboot. Verify a C:\> prompt,
   `VER`, `MEM`, startup settings and a fully completed `CHKDSK C:`.
7. Quit and wait for the **process to exit**, not just the socket reply, before
   copying/hashing images. Preserve the as-installed checkpoint. Normalize text
   encoding and disable host time sync in the experiment profile; cold-boot it
   again and repeat validation before sealing.

All emulator interaction used the authenticated socket, never display clicks or
RDP keyboard/mouse injection. Private installation scripts and the complete
request journal record actual steps and readbacks. The reusable client remains
separate from those installation-specific scripts. The archive's HDNEW helper
and SETUPRLX were not used.

## Installed baseline observations

The installed root contains IBMBIO.COM, IBMDOS.COM, COMMAND.COM, WINA20.386,
CONFIG.SYS, AUTOEXEC.BAT and the DOS directory. There are **98 installed files**:
six at the root and 92 in DOS. Full filenames, byte lengths and content hashes
are in the public metadata; no original file bytes are included there.

Setup generated C:\DOS paths for SETVER and HIMEM, DOS=HIGH, FILES=10, a normal
prompt, C:\DOS in PATH and C:\DOS as TEMP. No EMM386, mouse TSR, Shell startup,
RLX ROM-drive startup or DeskMate application startup was enabled. Distribution
utilities copied by Setup, including SETUPRLX and INSTALL.PDM, were not executed
as separate experiments.

Observed `MEM` results after the final cold boot:

- 655,360 total conventional bytes; 654,336 available to DOS.
- 636,800-byte largest executable program.
- 3,145,728 total contiguous extended bytes; 3,080,192 available XMS bytes.
- DOS resident in the HMA; HIMEM A20 handler 1; no EMS configured.

Completed `CHKDSK C:` reported 54,335,488 data bytes, 51,924,992 free bytes,
2,048-byte allocation units, 26,531 total units and 25,354 free units, with no
error report. Its 96 user files plus two hidden system files agree with the
independent 98-file inventory. A first short capture stopped during CHKDSK's
output; the final cold-boot check waited for the complete output and prompt.

## Preservation, hashes and restore

All emulators are stopped at session end. The original machine remains unchanged.
Research locations:

- Original acquisition/backups/private logs:
  `C:\DeskMateLab\private-evidence\dos5-session-20261104`.
- Verified original media/docs: `C:\DeskMateLab\media\TandyDOS5`.
- Working machine: `C:\DeskMateLab\machines\rsx-dos5-experiment`.
- As-installed checkpoint: `C:\DeskMateLab\baselines\rsx-dos5-as-installed-20261104`.
- **Pristine baseline:** `C:\DeskMateLab\baselines\rsx-dos5-pristine-20261104`.
- Verified writable restore clone: `C:\DeskMateLab\machines\rsx-dos5-validation`.

| Pristine artifact | Bytes | SHA-256 |
|---|---:|---|
| rsx-dos5-working.img | 54,525,952 | `6c146364c24000dbf46898eec1abd4940c3f8a3a666670bdda3aa30a01e681ec` |
| 86box.cfg | 789 | `12bb7f7699f85c1eb094bd17da5994f5fc2a0c7bc74de27117b904ce5e5d1773` |
| nvr/tandy1000rsx.nvr | 128 | `a883930c6a8ed73bfbe238b7cdad519e63acea18b68f9ff1f367d6f02fd4aba2` |
| baseline-manifest.json | recorded privately | `27847256c686c6c944ba9ea9def8ed7143c76d8a8d8e753d1c14c7f8e8eea11b` |

Baseline files carry Windows read-only attributes. Always verify the manifest
and copy its config/disk/NVRAM into a **new** machine directory, making only the
copies writable. The disk filename is relative in the config, so the restored
clone uses its own image. Never launch the sealed baseline directly. Tokens and
mounted floppy images are absent from the capsule. A validation clone was made
with exclusive new-directory creation, booted for 12,000 emulated ms, and
reported DOS 5.00 with no floppy mounted. Its disk hash and every sealed baseline
hash were checked afterward; all matched. Disk identity is also unchanged from
the earlier as-installed checkpoint.

RTC state naturally changes while running, so clone NVRAM is disposable. Copy
the saved NVRAM again for another clean start. No claim of general bit-identical
emulator replay is made: timed execution deltas, cold boot, restore behavior and
disk preservation were the tested properties.

## Validation and remaining work

The portable suite passes **105 tests** on Python 3.13.17 and UCRT64 Python 3.14
(the latter with `PYTHONPATH=src`, since the package was not installed into that
interpreter). This includes 13 new transport/client tests and four media tests.
The 11 deployment-customization tests also pass. REUSE licensing, focused Ruff
checks, repository-content audit and package build are checked before commit.
The content boundary now also excludes NVRAM, ROM, VHD/VHDX/HDI/raw images and
token files.

The wider existing deployment audit suite has two Windows-host failures:
`test_mac_legacy_fuse_alias_is_private_and_temporary` needs symlink privilege,
and `test_reject_write_into_guest` exposes differing Windows path
canonicalization between the resolved root and absolute output path (including
short/long path spellings). The containment guard fails its synthetic test;
the deployment audit should not be used on Windows before that guard is fixed.
These are outside the emulator change and were
recorded without changing security policy or silently skipping them. No private
DeskMate fixture tests or hardware utility compatibility tests were run.

Runtime capabilities demonstrated: token authentication, status/info, native
register inspection, ordinary BDA RAM reads, coherent held read groups, CP437
text, validated native PNG framebuffer capture, set-1 keyboard input, exact
timed steps, media mount/eject, reset and clean quit. Native captures were visually
inspected. Source-pinned protocol review remains useful context; its proposed
MCP lease/epoch interface has not been implemented or registered.

Remaining limits: hardware utilities and broad RLX/RSX compatibility, exact
historical drive timing, precise debugger execution breakpoints, and semantic
DeskMate UI decoding remain unverified. The current socket supplies observation
data but no field/dialog semantics or Ghidra load-map correspondence.

Recommended next task: on a fresh writable clone, run independently authored
guest canary code with known RAM/register values and a known rendered pattern;
test reset/reconnect identity and debugger stop behavior against it. Then plan a
separately authorized DeskMate installation and memory/Ghidra correlation task.
Do not use this DOS baseline as evidence that Calendar runtime bindings or UI
structures have been resolved.
