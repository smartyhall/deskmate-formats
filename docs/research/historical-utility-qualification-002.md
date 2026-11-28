# Historical Utility Qualification 002

This campaign extends [qualification 001](historical-utility-qualification-20261127.md)
from merge commit `5045901177b735c7f5aaaa3512e4d4741a9d7bb2`.
It addresses the native differential work in
[issue #178](https://github.com/smartyhall/deskmate-formats/issues/178).

## Environment and Filer corpus

The campaign used CPython 3.13.17 in a dedicated worktree and environment.
All eleven preflight checks passed, including an isolated `-I` child.
Both parent and child resolved the checkout's package tree SHA-256
`27a4e0012e9b26ca5310e8a7e24da914f982ef555c2b2dd42eee358e41b39c8a`.
The visible RSX guests used seed 1, an authenticated held loopback socket,
and the emulator, ROM and runtime identities pinned by
[qualification 001](../evidence/historical-utility-qualification-001.json).
The native and DOS disks started as copies of 001's stopped
`native-305` and `standalone-dos` disks. The DOS clone used 001's
qualified RSX configuration. Every guest action went through the socket.
7-Zip and direct FAT16 extraction agreed on the four first specimens.

| Native specimen | DATA records | Native operations |
| --- | ---: | --- |
| [Empty form](../../tests/fixtures/application-generated/filer/hu002-form.fil) | 0 | Draw three text fields and one numeric field in Form Setup, then close. |
| [Unsorted](../../tests/fixtures/application-generated/filer/hu002-unsorted.fil) | 8 | Add ZULU, ALPHA, MIKE, BRAVO, CHARLIE, DELTA, ECHO, FOXTROT. |
| [Sorted](../../tests/fixtures/application-generated/filer/hu002-sorted.fil) | 8 | Set ITEM_CODE as the sole sort key. |
| [Delete then insert](../../tests/fixtures/application-generated/filer/hu002-churn.fil) | 8 | Delete ALPHA, then add GOLF with memo REPLACEMENT. |

The shared reader and Filer inspector accepted all four specimens. DATA
declares ITEM_CODE (K/40), MEMO TEXT (K/336), AMT (N/18) and DATE/TEXT
(K/15). Form Setup offered Text and Number. The specimen stores dates as
ordinary character data, including the synthetic leap day 02/29/2024.
AMT stores a blank distinctly from zero. The default numeric editor
ignored the point in the typed `-12.50` and saved `-1250`. It accepted all
16 digits of `9999999999999999`. The longest measured memo contains 271
characters. The DATA chain grows from page 6 to pages 6 → 8, with the
index on page 7.

Sorting preserves all eight physical row locations and identifiers.
Deleting ALPHA and then inserting GOLF on a separate copy compacts DATA.
MIKE moves from `0x183C`/ID 18 to `0x1825`/ID 17, reusing ALPHA's ID.
GOLF takes ID 23, formerly FOXTROT's. The resulting DATA index contains
eight active entries and the independent reader finds no retained DATA row.

## Reproduction

Start from the qualified 03.05.00 and standalone DOS snapshots, on
separately owned disposable media, using the
[historical utility runbook](historical-utility-runbook.md). In
`C:\DESKMATE`, launch `DESK FORMSET` and accept new file MIXED. Use
Field → Add, select each field's rectangle, and choose Text or Number in
Data Field Definition. The DATA schema and exact field placement can
be inspected in the empty form's DBCOLS and LAYOUTS tables. Copy the
saved file before entering records. In Filer use Ctrl+A to add and Tab
between fields. Pace text input through the socket to avoid losing keys
in long multiline values. Close to DOS, copy the unsorted file, then
reopen the working copy. Choose Records → Sort, select ITEM_CODE, press
Add to Sort and confirm. Copy the sorted file before the delete/insert
trial. Use Ctrl+D and confirm once, then Ctrl+A for GOLF and close.

The [pre-run predictions](../evidence/historical-utility-qualification-002-predictions.json)
pin the exact independent DBrepair input mutations and alternatives.
Regenerate those inputs into an empty private output location with:

```powershell
python -I tools/experimental/historical_utility_002_defects.py tests/fixtures/application-generated/filer/hu002-sorted.fil <new-directory>
```
