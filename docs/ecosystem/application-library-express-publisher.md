# Express Publisher 1.00 for DeskMate

Express Publisher is Power Up!'s desktop publisher for DeskMate and the one
distribution in this campaign that installs its own complete DeskMate runtime.
It is the clearest case of the
[bundled-runtime architecture](application-library.md#installation-architectures-observed):
the application runs whether or not DeskMate is present, and its runtime must
be preserved separately from the host environment.

## Identity

| Item | Value |
| --- | --- |
| Product | Express Publisher for DeskMate |
| Release | 1.00 (1991 media); bundled runtime reports 03.05.00 |
| Private archive | `Express-Publisher-for-DeskMate/EPDisk1.zip`, `EPDisk2.zip`, `EPDisk3.zip` |
| Disk 1 SHA-256 | `9427a2f71d12c2bbb8a6c7b7fc2dfe8655d4bc14241fd1362d78992334c4bed2` |
| Disk 2 SHA-256 | `741a1e9b68df704562ef8df2780acf7776be97736da8fb680765e9e370ed9556` |
| Disk 3 SHA-256 | `9138249ce155c82507c9fa17a9db503f3f34ae18bae136a99bcaa3f9088e79b6` |
| Manual | `EPMan.zip`, SHA-256 `b612fae43988e5be0223689beab240396510281bb0f477c13e24cea8a4831f4e` (not redistributed) |
| Architecture | Standalone distribution with bundled DeskMate runtime |
| Destination | `C:\EXPRESS` |
| Launcher | `EPDM` (`EPDM.EXE`) |
| Baseline | `applib-001-express` (private) |
| Stopped disk SHA-256 | `b9147b1d987a5ba43195610589c9d3cc22a049f1f4cd3dd6b52aebca67f26444` |

The installer banner and runtime both identify the vendor: "(c) 1991, Power Up!
Software Corporation" and "DeskMate Runtime / Version: 03.05.00", with
"Copyright 1984,1990 Tandy Corporation" for the runtime.

## Media

Three file sets were built as labelled 720 KiB images:

| Image | SHA-256 |
| --- | --- |
| `epdk1.img` | `8e4c7a75d27bbab9136a651bd336b8817981ba113dc8c3b75535979fb1e9c0ad` |
| `epdk2.img` | `5452fbdd6871372b7511779c0dbd7495c56593b0fa243a6cd63ab8dc6dd92f20` |
| `epdk3.img` | `108025dbb11f18eb80d171230dc2c06f8089b5fcd38044098904d03692ed2c0b` |

Disk 3 carries the runtime installer; Disks 1 and 2 carry the application,
fonts, art, and documentation sets.

## Procedure

1. Clone the sealed DeskMate 03.05 host.
2. Boot DOS 5.00, insert Disk 1, and run `INSTALL` (`EINSTALL.EXE`).
3. Accept the licence screen, confirm the runtime installation, and insert
   Disk 3 when requested. The installer extracts `DMPDIBMM.RES` and the rest of
   the runtime resources, then starts the DeskMate-style installer.
4. In "Express Publisher Installation", keep the proposed program directory
   `C:\EXPRESS` and the default options: install Express Publisher, install
   printer drivers, install Atech FastFont, and do not copy the art images to
   the hard disk.
5. Supply Disk 1 (fonts and resources) and Disk 2 (program files) at the
   prompts. Installation takes several minutes of emulated time.
6. At completion, note the "To use DeskMate Express Publisher Runtime, enter
   EPDM at the prompt." message and return to DOS.
7. From `C:\EXPRESS`, run `EPDM`. On first launch the font installer lists
   available and installed fonts; choose Install to finish the font
   registration, then acknowledge the completion dialog.

## Result

- Installation completed; `C:\EXPRESS` holds 162 files, 2,798,696 bytes.
- The distribution's own runtime (`DM*.RES`, `.R89`, `.ACC`, `.PDM` files) is
  installed inside `C:\EXPRESS` and is independent of `C:\DESKMATE`.
- `EPDM` starts the Express Publisher page workspace at 640×480 with the
  application's own menus (File, Edit, Text, Page, Object, Options) and
  tool palette.

## The `FILES=20` requirement

On the first launch attempts the runtime displayed:

> Express Publisher requires a FILES=20 statement in your CONFIG.SYS.

The host's `CONFIG.SYS` then contained `FILES=10`. Raising it to `FILES=20` and
then `FILES=30` did not satisfy the check while the statement followed device
driver lines; the runtime started only after `CONFIG.SYS` contained `FILES=20`
as an ordinary statement, along with the existing driver lines. The check is
therefore stricter than a simple minimum count, and the working configuration
is recorded here as observed behavior rather than documented intent.

The resource files also carry useful operational messages, including the
runtime's 570K conventional-memory requirement and its expectation of
`COBB.FF1`, `DIXON.FF1`, and `MARIN.FF1` in the font directory.

## Smoke test

1. Typed "SYNTHETIC PAGE" into the page area; the text appeared as a placed text
   object in Text Mode.
2. Opened File → Save As, which proposed `UNTITLED.EPD` in `C:\EXPRESS\DOCS`
   with File Type "Document".
3. The dialog did not accept socket key events, so the filename could not be
   entered and no document was written.

The workflow is therefore qualified through page editing and the Save As
dialog, but not through a native save. This is a guest-input limitation, not an
application defect: the same dialog path accepted a pointer device in the
original environment.

## Native files

- `.EPD` — Express Publisher document, the Save As default type.
- `.EPB` — the distribution's packaged resource archives on the install media.
- `.FF1` — bitmap font files (`COBB`, `DIXON`, `MARIN`, `DINGBAT2`,
  `SPRINGER`), installed by the font installer.
- `.PDM` — application modules (`EPDM.PDM`, `EPMDM.PDM`, `EPDMACLN.PDM`).
- `.PCX` and `.TIF` — art images supplied on Disk 1 for import.
- `EPDM.INI` — runtime paths for fonts, documents, art, and text.

## Limitations

- No native document was saved, so no `.EPD` sample exists yet.
- The installer's options were accepted at their defaults; the art-copy option
  and the alternate printer drivers were not exercised.
- The distribution bundles a 03.05.00 runtime, so this baseline must not be used
  to test behavior that depends on the host's own runtime files.

## Research opportunities

- Compare Express Publisher's `.FF1` fonts and printer resources with First
  Publisher and Print Magic to see which are shared and which are vendor
  specific.
- Capture an `.EPD` document with a pointer-capable input path and compare its
  container with the `.EPB` package format.
- Determine whether the bundled runtime differs from the generic 03.05.00
  installation, and whether the application's `.PDM` loads in the host runtime.
