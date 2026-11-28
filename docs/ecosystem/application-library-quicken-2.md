# Quicken 2.0 for DeskMate (blocked)

Quicken 2.0 Release 3 is preserved in the private archive but could not be
installed in this campaign. The failure is recorded here so a later agent does
not repeat it without new media. It is the only entry in the
[application library](application-library.md) with an installation attempt and
no installation.

## Identity

| Item | Value |
| --- | --- |
| Product | Quicken 2 for DeskMate |
| Release | 2.0, Release 3 media (1989 program files) |
| Private archive | `Quicken-2-for-DeskMate/quicken2.zip` |
| Archive SHA-256 | `551ac18c69ce9ae38fa6f7d89f779229867311138ffd63d1948234f7f488da67` |
| Manual | `qdmman.zip`, SHA-256 `cc306413e5b78e73cc33d00c9f25cf7761985e202b9a7fbf6bcecd5084d141ef` (not redistributed) |
| Architecture | Standalone `INSTALL.COM` with DeskMate runtime 03.02 |
| Destination | Not installed |
| Baseline | `applib-001-quicken2` (private; clean host clone, no installation) |
| Stopped disk SHA-256 | `40099ef1fdbb01935e78afe010169b10d907394420d35505c82cd97c151f02a0` |

## What the archive contains

`quicken2.zip` holds a program set rather than a disk image: `Q.PDM` (304,192
bytes), `QCHECKS.DAT`, `Q.HLP`, a runtime `INSTALL.COM`, and supporting files
dated 1989. The set has no second program disk.

## Attempts

1. **Standalone installer.** Running `INSTALL.COM` from a labelled 720 KiB
   image built from the file set starts the DeskMate 03.02 runtime banner and
   then hangs at the splash screen. The installer expects a "Program Disk 2"
   that the archive does not contain, and no prompt accepts input at that
   point.
2. **Desktop accessory path.** Starting the DeskMate 03.05 Desktop and pressing
   `F7` to open the Install accessory produces the accessory menu, but the menu
   does not respond to socket keyboard events. No installation could be
   started from the Desktop either.

The machine was stopped after the second attempt and archived without an
installation. Its disk is a clean host clone, so the baseline is useful only as
a starting point for a retry with complete media.

## Why this is not a copy-protection workaround

No protection mechanism was bypassed and no executable was modified. The
blocker is missing media plus an input path that cannot drive the installer;
both are recorded rather than worked around.

## Prerequisites for a retry

- A verified Program Disk 2 for the same release, or a complete Release 3 disk
  set with its original labels.
- Quicken 2.0 Release 4 media, which may contain the missing disk or install
  non-interactively; it is in the remaining queue.
- A pointer-capable input path for the DeskMate Desktop accessory menus, which
  would also unblock other accessory-based installers.

## Research opportunities

- Compare `Q.PDM` with the Release 4 module once acquired, and check whether the
  data files (`QCHECKS.DAT`) share a format with Personal Financial Assistant.
- Determine whether the standalone installer's Program Disk 2 carries data
  files or additional runtime resources; the manual may describe the layout.
