# Immediate acquisition handoff — next Codex campaign

The operator supplied two archives in ChatGPT on 2026-11-19. Their
exact uploaded bytes were hashed here; no transfer to the Windows VM
is claimed. Acquire the same files by an accessible operator-provided
path or the documented distribution source, verify SHA-256, and record
any version differences rather than silently substituting.

| Filename | Bytes | SHA-256 |
| --- | ---: | --- |
| dm305dk9.zip | 86916 | 52befdd828e7065fc2e1fde60c010693d946ca5e4c477703f9c43564086cd883 |
| PFS First Publisher 2.01 for DeskMate.7z | 671052 | b080193f1d05d3db7e6097e1dd08992c73bc3af8d72155a111c27757c94c50a7 |

- First Publisher distribution lead:
  https://winworldpc.com/product/first-publisher/201-for-deskmate
  (also lists a separately available book).
- DeskMate disk 9 distribution lead:
  https://www.dosdays.co.uk/computers/Tandy%201000/download.php
  (verify the exact archive; no direct download link verified here).

Use a private archive directory under C:/DeskMateLab and preserve
the original archives before extraction. Do not put their bytes in Git.
The ChatGPT attachment paths are not Windows VM paths.

DeskMate disk 9 ZIP directory was directly checked: COBB.FF1,
MARIN.FF1, and eight DMVE display RES files for Hercules, MCGA,
Tandy, Tandy 1000, CGA, EGA, VGA and TC16. Compare exact font hashes
against the existing pinned resources and inventory display resources.
Do not assume this disk provides a new face.

First Publisher: prior inspection reported three FAT12 disk images,
MASTER.FNT, EXTRA.FNT, APLASER.FNT, HPLASER.FNT, DESKJET.FNT and
FONTMOVE.EXE. Reproduce and verify that extraction in the VM; record
exact hash/size identities, font record descriptors and the HP-soft-font
conversion path. WinWorld identifies the bundled runtime as 3.02.
Do not overwrite the current 3.05 lab runtime; test in a separate clone
and compare dependencies. Native-format acceptance and any shared
clipboard/font behavior are untested. Record `.PUB` and other candidate
extensions only as measured or explicitly unverified.

For the next Draw/font campaign, stage these archives and make a
bounded inventory. Prioritize FF1 serialization, original synthetic
font creation, modern OpenType/TrueType conversion and native
load/print/round-trip verification over an extensive First Publisher
reverse-engineering diversion. Search for additional FF1 resources,
especially the historical Rockwell reference, and for Express Publisher
and the Q&A Write font-import documentation. Record blocked acquisition
honestly; no paid acquisition or contacts without separate authorization.
