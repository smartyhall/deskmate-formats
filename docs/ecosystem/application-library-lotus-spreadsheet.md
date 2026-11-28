# Lotus Spreadsheet 1.0 for DeskMate

Lotus Spreadsheet for DeskMate installs a native `.PDM` module and its resources
from two disks, and also ships a standalone launcher that starts the same module
without going through the Desktop. It was the second application qualified in
the [application library](application-library.md).

## Identity

| Item | Value |
| --- | --- |
| Product | Lotus Spreadsheet for DeskMate |
| Release | 1.0 (program files dated 1989-09-28 and 1990-09-26) |
| Private archive | `Lotus-Spreadsheet-for-DeskMate/123disk1.zip`, `123disk2.zip` |
| Disk 1 SHA-256 | `7b927b4fd91a024d5a17420d3a1fc92a6429a422053c529ceb8c8518c2aae266` |
| Disk 2 SHA-256 | `4252861db9ad749701a2ac02ca4060af4e05fc32a3f01950c9aba2651e552c68` |
| Support archive | `lotusqk.zip` (quick reference), `lotusman.zip` and `lotusbk.zip` (manual scans); not redistributed |
| Architecture | Native module plus standalone launcher |
| Destination | `C:\LOTUS-DM` |
| Baseline | `applib-001-lotus` (private) |
| Stopped disk SHA-256 | `fa626de115c9701df774b16a9cfe294ca1b8671a77ed1d94538af52a50728c9a` |

## Media

Both disks are file sets rather than images. They were built as labelled
720 KiB FAT12 images with
[`tools/experimental/application_library_media.py`](../../tools/experimental/application_library_media.py):

| Image | SHA-256 |
| --- | --- |
| `123dk1.img` | `d0de611d62eda7c0ad3a1fdad1b479b20a7635b0e9aff125bda565156e3bcc9e` |
| `123dk2.img` | `d9c6a32b22f2199ca29f4cf62c90da1f3644e87dfc1de376c14c3e7fcd66ca40` |

## Procedure

1. Clone the sealed DeskMate 03.05 host.
2. Boot DOS 5.00, insert Disk 1, and run `A:INSTALL`.
3. The installer identifies itself and copies to `C:\LOTUS-DM`.
4. Supply Disk 2 when prompted; the installer reports that the installation
   procedure is now complete.
5. Return to DOS and either start the module from the DeskMate Desktop or run
   `lotus-dm` from `C:\LOTUS-DM`.

## Result

- Installation completed with the same two disks and no manual file copying.
- `C:\LOTUS-DM` holds 49 files, 1,326,144 bytes before the smoke test.
- `lotus-dm` starts standalone at 640×480 with the application's own menus
  (File, Edit, Worksheet, Range, Graph, Data) and the `MENU` indicator.
- Starting from the Desktop is possible in principle but was not exercised in
  this session because the Desktop's accessory menus did not accept socket
  keyboard events; the standalone launcher was the qualified path.

## Smoke test

Fictional values only:

1. Entered `10` in A1 and `20` in A2, using the arrow keys to move between
   cells; the Enter key commits a cell but does not advance the pointer.
2. Entered the formula `+A1+A2` in A3; the sheet displayed `30`.
3. Opened File → Save as and saved as `SYNTH001.WK1` in `C:\LOTUS-DM`.
4. The application wrote a 1,443-byte file, SHA-256
   `d05f8e1085b7995f27b8c23e2aaa02b60fc2eb28174cd34cb2ff789963ed372a`.

The screen after the formula entry is the published screenshot for this
application.

### Reopen limitation

The native reopen of `SYNTH001.WK1` was not completed. The application's Open
dialog keeps keyboard focus in its file list, so a typed filename was ignored
and the previously highlighted `HOMEBUY.WK1` sample opened instead. Passing a
filename on the command line also failed to open it. The saved file itself was
read out of the stopped disk image and preserved privately; its size and hash
above come from that extraction, not from the application re-reading it.

Treat the workflow as qualified through native save, and reopen as an open item
that needs a pointer device or a different input path.

## Native files

- `.WK1` — the application's worksheet format; the save dialog proposes
  `HOMEBUY.WK1` from its sample files when browsing the program directory.
- `LOTUS-DM.PDM` — the spreadsheet module.
- `LOTUS-DM.EXE` — the standalone launcher.
- `LOTUS-DM.CNF` and `LOTUS-DM.SET` — configuration and setup data.

## Limitations

- Reopen not verified natively, as described above.
- Desktop-integrated launch not exercised.
- The worksheet was saved over an earlier attempt from the same session; the
  qualified file is the final 1,443-byte version.

## Research opportunities

- Compare `.WK1` output against DeskMate Worksheet documents and against
  generic Lotus 1-2-3 release 2 files.
- Determine whether `LOTUS-DM.PDM` is the same module the Desktop loads, and
  whether the standalone launcher passes different configuration.
- Establish whether files written by the standalone mode reopen from the
  Desktop mode and vice versa.
