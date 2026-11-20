# Offline archive intelligence

Build a private SQLite library from a downloader inventory or transfer
database. Python 3.11 or newer with SQLite FTS5 handles the index, ZIP, TAR,
GZIP, FAT12/FAT16, and DOS text without network access. Install the project's
Python package or set `PYTHONPATH` to the checkout's `src` directory to use
the project readers for DeskMate Text and native corpus qualification.

Use a database and content store outside the mirror and the checkout.
Keep the database, the sibling `.blobs` directory, and the source mirror
together as private research evidence. Below, assign `$db`, `$mirror`,
`$supplement` and the optional executable paths for your laboratory.

```powershell
python tools/archive/archive_intelligence.py --database $db ingest $mirror --live --seven-zip $sevenZip --lhasa $lha --pdf-python $pdfPython
python tools/archive/archive_intelligence.py --database $db ingest $supplement --manifest "$supplement/inventory.jsonl" --seven-zip $sevenZip --lhasa $lha --pdf-python $pdfPython
python tools/archive/archive_intelligence.py --database $db stats
```

`--live` snapshots committed rows from the downloader's transfer SQLite
database through a short-lived read-only connection. It does not start or
control transfers. Each run can overlap acquisition. It hashes new verified
inputs and checks their receipt size and SHA-256 before extraction. Pending
or partial files remain searchable as source statuses. For a saved snapshot,
omit `--live` to read the default `manifests/inventory.jsonl`; for a separate
supplemental root pass `--manifest`. Both expect the same receipt fields
(`kind`, `url`, `rel`, `status`, and for verified files `local`, `bytes`,
`sha256`). Each manifest is the current listing for its own input root.
A pending receipt does not displace a verified copy imported from another root.

Run the same command as further files arrive. Unchanged indexed roots are
skipped. Equivalent analyses share extraction and full-text rows while all
source/member paths remain individually searchable. Source IDs derive from the
exact source URL. Member IDs derive from the parent ID and member name and
ordinal. Ordinals disambiguate repeated names within a container. Changed
container member order may change member IDs. Full-text page numbers start at
one for PDFs and use zero for a whole unpaginated file.

Use a single index writer per database. Searches use read-only connections
and can run while the index updates. The CLI emits sorted-key JSON lines.
Use `--max-files` to bound a pass, `--progress` to change the progress
interval, and `--select` with a case-insensitive shell glob to prioritize
original source paths. Create the sibling `.STOP` file, for example
`library.STOP`, or supply `--stop` for a different private path. The indexer
checks the sentinel during import, checksum reads and traversal. A bounded
helper call can delay the stop. The current root transaction rolls back and
completed roots stay indexed. Remove the sentinel explicitly before resuming.
The mirror has its own separate stop file.

## Find the evidence

```powershell
python tools/archive/archive_intelligence.py --database $db files --kind ff1
python tools/archive/archive_intelligence.py --database $db files --name dm_music
python tools/archive/archive_intelligence.py --database $db search 'Rockwell OR MoreType OR AllType'
python tools/archive/archive_intelligence.py --database $db search '"printer driver" AND DeskMate'
python tools/archive/archive_intelligence.py --database $db search '"3.05" AND "DeskMate"'
python tools/archive/archive_intelligence.py --database $db files --kind sng --limit 200
python tools/archive/archive_intelligence.py --database $db sources --state unavailable
python tools/archive/archive_intelligence.py --database $db document $occurrenceId --page 164
python tools/archive/archive_intelligence.py --database $db duplicates --limit 100
python tools/archive/desk_native_inventory.py $db --compare $audioHashes --compare $drawHashes --summary
```

`search` accepts FTS5 syntax and returns the original URL, location chain,
page, first-line title and a short snippet. `document` returns text for that
occurrence. Query results may include originals or personal information and
belong in the private lab. Dropping `--summary` from the native inventory
returns per-digest parser outcomes, source chains and evidence including Sound
slot/sample information and Music MIDI projection status. Supply prior hash
receipts to distinguish byte identities outside the selected comparison set.

## Extend extraction

7-Zip is optional for supported legacy archives and Shrink/Implode ZIP
members. Lhasa adds bounded level-zero LHA extraction including Express
Publisher EPB, with independent size/checksum checks. An optional
`--pdftotext` command or `--pdf-python` interpreter with pypdf extracts PDF
text locally. PDF extraction preserves physical pages and reports empty or
failed text coverage. Image-only scans need a separate OCR pass. Plain DOS
text uses UTF-8 when possible and a CP437 fallback. A first-line title and
source modification date are search aids. Neither supplies a historical
publication identity by itself.

No archive-controlled member name becomes a filesystem output path.
The content store uses SHA-256 filenames. Extraction bounds each input,
member, container, helper, depth and source tree. Unsafe, unsupported,
failed and partial members or containers carry explicit statuses.
Limitations include ARC compression profiles, legacy document codecs,
filesystem layouts other than the supported FAT profiles, and older
self-extracting archive variants. Catalog findings and filenames have
different evidence strengths. Executables stay inert during inventory.

To retest intact receipts, use `ingest --recheck`. To invalidate compatible
cached results after code changes, use `requeue` with a kind, an occurrence
status or a source glob. Shared analysis invalidation also queues its
other source occurrences. Then run ingest for each affected root. Adding or
changing an optional extractor path requires `ingest --update-tools` once.
That invalidates the kinds affected by the changed tool and retains the
other cached analyses. Changed extraction bounds require a new index.
`stats` reports active analyses reached by indexed occurrences.
