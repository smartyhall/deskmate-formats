# HomeWord II 1.20 for DeskMate

HomeWord II is Sierra's word processor for DeskMate and the first application
qualified in the [application library](application-library.md). It installs a
native module and runtime resources into its own directory, then runs with the
DeskMate runtime already present on the host.

## Identity

| Item | Value |
| --- | --- |
| Product | Sierra HomeWord II for DeskMate |
| Release | 1.20 (1990 media) |
| Private archive | `Homeword-II-for-DeskMate/HomeWord II 1.20 (1990) (5.25-360k).7z` |
| Archive SHA-256 | `8de88e3d08f355b7b0e09e77452b714e0132afba56c6b70f40582c01f2a8c2cf` |
| Manual | `Homeword-II-for-DeskMate/hwman.zip`, SHA-256 `44afab116329fe48872d8ed7f7fd70cd004fb737a7073346c6dd98db8b738f33` (not redistributed) |
| Installation set | `Homeword-II-for-DeskMate/install.zip`, SHA-256 `d863afb2eec08a230a5e66c7ea129aa8ec23d47a82fc7d8041c31ed546a326dd` |
| Thesaurus set | `Homeword-II-for-DeskMate/thesaurs.zip`, SHA-256 `4ec039350765df162f259ba4f3bbd17d4b42535875bb538bc944aae875bfb30c` |
| Architecture | Native application with bundled runtime resources |
| Destination | `C:\HOMEWORD` |
| Baseline | `applib-001-homeword2` (private) |
| Stopped disk SHA-256 | `1f551f42353bff17b7c1da35ca3e12e650cd35f0d9c6f3c7a124eaa1154802cf` |

Program files in the archive are dated 1990; the original media set is
described as 5.25-inch 360 KiB disks.

## Media reconstruction

The archive contains four extracted 360 KiB disk trees rather than mountable
images. Copying them to 360 KiB images and switching the drive to `525_2dd`
failed in this machine profile: the BIOS reported invalid configuration
information for the changed floppy type, and the machine looped on floppy boot
without reading the disks.

The original four 360 KiB images are therefore preserved as the media identity
of record, and the working media were rebuilt as four 720 KiB images from the
same file contents using 7-Zip extraction and
[`tools/experimental/application_library_media.py`](../../tools/experimental/application_library_media.py).
The rebuild changes only geometry and directory metadata, not file contents.
Working image hashes:

| Image | SHA-256 |
| --- | --- |
| `hw2dk1.img` | `4886d76932381aa4d89ab6807fe4d1e080cae10172194e9f6559a3dd20f42c64` |
| `hw2dk2.img` | `424440c0dc68218b8bf773122120b37f9d5a127609b15216b5ae4a365cc70924` |
| `hw2dk3.img` | `f597f3ab7ae5b34b3dfcfd89ffbdbfdcb027c826590e564ab73dc79882685d40` |
| `hw2dk4.img` | `767645bdcee105008f6405e10b3a284be493a39cd09aafd22139ca939ca02885` |

Two alternate images (`hw2dk2b.img`, `hw2dk3b.img`) were built while resolving
the thesaurus disk label; the qualified installation used the four images in
the table.

## Procedure

1. Clone the sealed DeskMate 03.05 host; keep its own configuration unchanged.
2. Boot DOS 5.00, insert Disk 1, and run `INSTALL.EXE` from `A:`.
3. Select VGA video, an IBM graphics printer, and a PS/2 mouse. The installer
   reported no serial-mouse option usable with this profile.
4. Accept the destination `C:\HOMEWORD` and supply Disks 2, 3, and 4 when
   prompted, including the thesaurus disk.
5. The installer completes and returns to DOS.
6. Start the application; on first launch it requested `DMMDSERI.RES` from
   Disk 2 before the editor opened.

## Smoke test

Qualification states: verified media, inspected installer, installed, native launch,
partial functional testing, native document creation, cold reopen, candidate
baseline preserved. Independent canonical qualification: not achieved.

Fictional content only:

1. At the editor, typed two lines: "Synthetic memo for the DeskMate application
   library." and "Fictional content only. No personal data."
2. Opened the File menu, chose Save As, and entered `SYNTH001`.
3. The application saved `C:\HOMEWORD\SYNTH001.HMW`, 770 bytes, SHA-256
   `204f2ab3fb932efd3757eda9599b3422638a98bdc2420eb5d66e0a2a32e3cdb3`.
4. Exited to DOS normally, relaunched the application cold, and reopened
   `SYNTH001.HMW`; both lines reappeared and the title bar showed
   `C:\HOMEWORD\SYNTH001.HMW`.

Save As and Open both required the file list to receive focus before typed
filenames reached the name field; the same keyboard path is recorded in the
session transcript that produced the receipt.

## Native files

- `.HMW` — HomeWord II document, the application's native save type. The default
  name before saving is `UNTITLED`.
- `HOMEWORD.PDM` — the application module loaded by the runtime.
- `DMMDSERI.RES` — a runtime resource the application requests at first launch.
- Thesaurus data from the thesaurus disk supports the Word check and thesaurus
  menus.

## Limitations

- The qualified installation used rebuilt 720 KiB media; the original 360 KiB
  images were never successfully mounted on this profile.
- The thesaurus disk label mismatch cost one retry; the alternate images show
  the intermediate attempt.
- Screenshots and the synthetic document are privately preserved; the document
  is a candidate fixture for later format research.

## Research opportunities

- Compare HomeWord II `.HMW` against DeskMate Text and Q&A Write documents, and
  test text import and export paths in both directions.
- Identify which runtime resources HomeWord II shares with the DeskMate host and
  which it installs itself.
- Determine whether the thesaurus data can be read independently, and whether
  the document container carries embedded style or printer information.
