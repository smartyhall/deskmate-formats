# Quicken 2.0 Release 4 for DeskMate (blocked)

Quicken 2.0 is preserved in the private archive in two releases, and neither
was installed in this campaign. This page records which package the campaign
actually used, how that identity was established, and what is observed
behavior as distinct from a requirement established from the program's own
text. It is the only entry in the [application library](application-library.md)
with an installation attempt and no installation.

## Corrected identity

The [acquisition gaps](acquisition-gaps.md) record identifies `QDM.zip` as
Release 3 and `Quicken-2-for-DeskMate/quicken2.zip` as Release 4, by the
distinct `Q.PDM` members. The campaign used `quicken2.zip`, so every
observation below belongs to **Release 4**. Earlier campaign drafts called it
Release 3; that label was wrong and is corrected here.

| Item | Release 3 (`QDM.zip`) | Release 4 (`quicken2.zip`) |
| --- | --- | --- |
| Archive SHA-256 | `131d0e110827991a47e0eb49d45705fa238fece64ae92deb6972bb025ce73d2c` | `551ac18c69ce9ae38fa6f7d89f779229867311138ffd63d1948234f7f488da67` |
| Archive bytes | 209 KiB class | 380,185 |
| Members | 27 | 27 |
| `Q.PDM` bytes | 304,096 | 304,192 |
| `Q.PDM` SHA-256 | `affeb2c28f6f8a163291ac7c6f90b68075a0a4b26438065fd313b5c1977b4e45` | `80386dfe77ee2d3e4ab65ecd5ed29daf94b13c236000457ae93a8932b987470e` |
| `Q.PDM` member date | 1989-04-11 | 1989-10-19 |
| Version string inside `Q.PDM` | `Version 2.0  Release 3` | `Version 2.0  Release 4` |

Both archives carry the same `Q.EXE` (15,992 bytes, CRC `6eaab508`), the same
runtime resource set, and the same 992-byte `INSTALL.COM`; they differ in
`Q.PDM`, `QCHECKS.DAT`, and `Q.HLP`. The version strings above were read
directly from the preserved members, not inferred from the directory names.

| Item | Value |
| --- | --- |
| Product | Quicken 2 for DeskMate |
| Publisher | Intuit |
| Release used | 2.0 Release 4 (media dated 1989-10-19) |
| Architecture | Standalone `INSTALL.COM` with DeskMate runtime 03.02 |
| Destination | Not installed |
| Baseline | `applib-001-quicken2` (private; clean host clone, no installation) |

## Observed installer behavior

`INSTALL.COM` (992 bytes) was run from a labelled 720 KiB image built from the
Release 4 member set. It printed the DeskMate 03.02 runtime banner and then
stopped at the runtime splash screen. No prompt appeared, and the process
accepted no further input. That is the observation: **the installer stopped at
the splash screen**.

The second attempt used the DeskMate 03.05 Desktop `F7` Install accessory. The
accessory menu opened but did not respond to socket keyboard events; it never
reached an installer.

## Independently established media requirement

Separately from the splash stop, the preserved program text states the
requirement. `Q.PDM` contains the prompts "Please insert Quicken Disk 2 in
drive X." and "Quicken Disk 2 or another diskette which", along with the disk
labels `QUICKEN DISK 1`, `QUICKEN DISK 2`, `WORKING QUICKEN DISK 1`, and
`WORKING QUICKEN DISK 2`.

The archived member set is a single program-disk file set: it contains
`Q.PDM`, `Q.HLP`, `QCHECKS.DAT`, `Q.EXE`, `INSTALL.*`, and the shared runtime
resources, and no second-disk member set. So a second disk is required by the
program text and absent from the archived set, which is established from the
members themselves.

This does not explain the splash stop, and the campaign does not claim it does.
The stop is an observed runtime behavior; the missing second disk is a
separate, independently evidenced gap. Whether the splash would have advanced
to a disk prompt with different input timing was not established.

## Releases are not interchangeable

Release 3's `Q.PDM` is a different build (304,096 versus 304,192 bytes) with a
different `QCHECKS.DAT` and `Q.HLP`. A Release 3 disk 2 was **not** tried with
the Release 4 program, and the campaign does not assume the two releases share
media. A future attempt should use a complete disk set from the same release,
or establish member compatibility first.

## Prerequisites for a retry

- A verified Release 4 second program disk, or a complete Release 4 set with
  its original labels.
- A pointer-capable input path for the DeskMate Desktop accessory menus, which
  would also unblock other accessory-based installers.
- Read the manual (`qdmman.zip`, SHA-256 `cc306413e5b78e73cc33d00c9f25cf7761985e202b9a7fbf6bcecd5084d141ef`)
  for the documented disk layout before substituting media.

## Research opportunities

- Compare the two `Q.PDM` builds to see what changed between Releases 3 and 4,
  and whether the data files (`QCHECKS.DAT`) remain readable across them.
- Determine whether the Release 4 second disk carries data files or runtime
  resources.
- Compare both releases with Personal Financial Assistant and Quicken 2.1 when
  acquired.
