# TVDog mirror verification, November 19, 2026

The saved [TVDog directory tree](http://ftp.oldskool.org/pub/tvdog/) was
enumerated through 62 directory listings. The transfer run stopped after
acquiring **958 of 9,973 discovered files (9.61%)**. The exported observation
window ran from November 20 at 03:12:36 through 04:17:29 UTC, or November 19
from 10:12:36 to 11:17:29 p.m. EST. The tree scope is the direct-child links
reachable through the saved indexes, including material outside `tandy1000/`.
The lab did not query the live server during verification.

| Check | Result |
| --- | ---: |
| Discovered directories / successfully enumerated | 62 / 62 |
| Saved listing bytes rehashed | 2,037,592 |
| Discovered files / verified local originals | 9,973 / 958 |
| Verified original bytes | 323,456,026 |
| Unique original SHA-256 digests / duplicate copies | 958 / 0 |
| Pending, never acquired | 9,014 |
| Deferred after a connection reset | 1 |
| Partial / unavailable / blocked / invalid file rows | 0 / 0 / 0 / 0 |
| Missing verified files, orphan originals, partial downloads | 0 |
| Inventory rows compared with SQLite | 10,035 |
| Discrepancies across SQLite, inventories, current listings and disk | 0 |

The 958 verified originals comprise 554 `.txt`, 386 `.zip`, 14 `.exe`,
two `.apm`, one `.pdf` and one extensionless file by source name. These are
pathname counts. Container signatures and nested duplicates belong to the
content inventory. The 957 files under `originals/` and one under `mapped/`
match the recorded local paths. The mapper gave a Tandy external floppy-drive
archive a SHA-256-based local filename because the source name contains a
double quote. Its URL and exact source name remain in the manifest.

The state records a single deferred file, the [26-1271 archive](http://ftp.oldskool.org/pub/tvdog/tandy1000/documents/26-1271.zip).
The server reset the connection on its first attempt and the downloader
recorded a host-wide cooldown. The snapshot records 9,013 pending files
under `tandy1000/` and one pending top-level note. Rechecking file hashes
establishes that the lab copies agree with their transfer receipts. The
saved directory indexes establish discovery coverage as of the observation
window. The checks do not establish that the server exposed every file or
that its content has stayed unchanged.

## Selected discovery and acquisition leads

| Evidence in the snapshot | Observation |
| --- | --- |
| [Express Publisher directory](http://ftp.oldskool.org/pub/tvdog/tandy1000/wares/Express-Publisher-for-DeskMate/) | Four ZIPs verified locally, `EPDisk1.zip` through `EPDisk3.zip` and `EPMan.zip`. Media identities require member inspection. |
| [AOL DeskMate collection](http://ftp.oldskool.org/pub/tvdog/tandy1000/documents/aoldesk.zip) | Local ZIP verified at 146,733 bytes, SHA-256 `5b93438fead67d22ddae4801329e72055b838b7f27820441bc04a3e548abf188`. |
| [DM_Music](http://ftp.oldskool.org/pub/tvdog/tandy1000/sound/dm_music.zip) | Exact path discovered. Its row has zero transfer attempts and no local bytes. |
| [Q&A Write candidate](http://ftp.oldskool.org/pub/tvdog/tandy1000/wares/DeskMate-Q%26A-Write/QWD.zip) | Listing verified. Distribution pending and edition unverified. |
| [Video memory document](http://ftp.oldskool.org/pub/tvdog/tandy1000/documents/videomem.zip) and [Print Magic candidate](http://ftp.oldskool.org/pub/tvdog/tandy1000/documents/cblmgc.zip) | Both paths discovered. Their content awaits acquisition. |

## Reproduce the check

The [verifier](../../tools/archive/verify_mirror.py) opens the settled
transfer database read-only, checks SQLite integrity, compares every export
row, recomputes SHA-256 for all verified originals and listings, and compares
canonical direct-child links to receipt rows. It traces `.part` files back
to their intended URLs and reports missing and unexpected artifacts. Run from
the repository root with the mirror downloader stopped. Exit `0` indicates
on-disk verification of a completed discovered tree, `3` a consistent but
incomplete mirror, `4` discrepancies, and `2` an input or report-write error.
Choose a new output path in an established private directory outside the mirror.

```powershell
python tools/archive/verify_mirror.py C:/DeskMateLab/references/oldskool/tvdog-mirror --output C:/DeskMateLab/references/oldskool/tvdog-intelligence/mirror-verification-20261119.json
```

The private report contains all 9,015 outstanding receipt rows, including
the exact source URLs and local mappings, as well as duplicate groups and
reconciliation details. Running the verifier twice against this snapshot
produced identical reports with SHA-256
`d1bf59437fed7d1317e48010c35e7e2a483e85f5d56def1dd02c38f26b85b6f3`.
The original inputs at verification had the following SHA-256 digests.

| Input relative to mirror root | SHA-256 |
| --- | --- |
| `manifests/inventory.jsonl` | `95bf3d4ae0f93d54f9aa844c143db84bf643b245be6fbcb082f3b5bc87b9e285` |
| `manifests/summary.json` | `c16cd4adfd84bc63d07bd0d7a2a6397ea57d91921af67f45adea0476c82f9c76` |
| `transfer-state/mirror.sqlite3` | `8cd662951c7fc07b40f6149f94ed2da1b07b26fc1d28ee304a1c59b37fe9dc40` |

The transfer queue remains resumable with the
[configuration-driven downloader](../../tools/archive/README.md) under the
[existing server and preservation rules](archive-mirror.md). Preserve this
dated report before any acquisition run updates the mirror state.
