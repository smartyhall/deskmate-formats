# TVDog archive intelligence campaign

The [original snapshot verification](../ecosystem/tvdog-mirror-verification.md)
established 62 verified directories and 9,973 discovered file URLs. All
958 verified downloads matched their recorded hashes and totaled
323,456,026 bytes. Of the other URLs, 9,014 were pending and one deferred.
All 10,035 transfer rows agreed with the saved inventory. There were
no orphan downloads, partial files or duplicate source bytes in that
snapshot. The saved listings cover the discovered subtree as enumerated
by that run. Later acquisition continued under the operator's process.

The last persisted error was a first-attempt connection reset while
fetching `26-1271.zip`. The legacy script saved a cooldown and treated it
as a stop. The reusable downloader now waits through a persisted,
interruptible cooldown and retries transient connection, HTTP and
short-response errors. It honors the later of exponential backoff and
Retry-After, stops after repeated failures or explicit access denial, and
retains the source's pacing. The existing operator downloader remained
under operator control. The unrelated Windows Python 3.13 main CI rerun
completed successfully on attempt 2. [Run 44673090847](https://github.com/smartyhall/deskmate-formats/actions/runs/44673090847)

## Private evidence and continuation

- `C:/DeskMateLab/references/oldskool/tvdog-mirror` contains the
  operator-managed originals and live transfer receipts.
- `C:/DeskMateLab/references/oldskool/tvdog-intelligence/mirror-verification-20261119.json`
  retains the immutable initial audit and exact residual URLs.
- `C:/DeskMateLab/private-evidence/tvdog-intelligence/library.sqlite` and
  `library.blobs` contain the reusable index, full text and content-addressed
  members. Ingestion logs and native qualification reports are beside them.
- `C:/DeskMateLab/private-evidence/tvdog-priority-20261119` contains
  separately acquired priority packages and their `inventory.jsonl`.
  These packages have independent local identities. A matching verified
  mirror copy can take over as the original source of the same URL.
- `C:/DeskMateLab/private-evidence/tvdog-express-native-20261119` contains
  the reconstructed installation disks, native socket receipts and captures.

On the lab machine, use the same paths so new downloads extend the current
library. This operation takes a committed transfer-state snapshot and performs
zero network requests.

```powershell
$base = 'C:/DeskMateLab/private-evidence'
$db = "$base/tvdog-intelligence/library.sqlite"
$mirror = 'C:/DeskMateLab/references/oldskool/tvdog-mirror'
$priority = "$base/tvdog-priority-20261119"
$env:PYTHONPATH = (Resolve-Path src).Path
$tools = @('--seven-zip', 'C:/Program Files/7-Zip/7z.exe',
           '--lhasa', "$priority/lhasa/lha.exe",
           '--pdf-python', 'C:/Users/DeskMateLab/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe')
python tools/archive/archive_intelligence.py --database $db ingest $mirror --live @tools
python tools/archive/archive_intelligence.py --database $db ingest $priority --manifest "$priority/inventory.jsonl" @tools
python tools/archive/archive_intelligence.py --database $db search 'Rockwell OR "MoreType" OR "FastFonts"'
python tools/archive/desk_native_inventory.py $db --allow-sector-padding --compare "$base/audio-native-20261118/comparisons.json" --compare docs/evidence/draw-ii-corpus-20261119.json --summary
```

The [index guide](../../tools/archive/intelligence.md) covers queries,
receipt formats, cancellation and reprocessing. Keep extracted content,
the searchable database and raw captures private.

## Research outcomes

At 23:57:40 Eastern on November 19, the research database held 1,114
indexed source URLs. The operator-managed mirror supplied 1,095 of
them (513,727,187 bytes). The remaining 19 came from the separate
priority acquisition (45,059,340 bytes). The transfer snapshot still
had 8,858 pending file URLs and one partial. This research checkpoint
is independent of any later transfers.

| Measure | Count |
| --- | ---: |
| Hashed file occurrences | 6,296 |
| Distinct SHA-256 identities | 5,526 |
| Duplicate occurrences beyond one per digest | 770 |
| Unique indexed text analyses | 2,585 |
| Indexed pages or whole unpaginated texts | 14,129 |
| ZIP container occurrences | 485 complete, 6 partial |
| LHA container occurrences | 14 complete |
| ARJ container occurrences | 2 complete |
| FAT image occurrences | 1 complete, 1 unsupported disk candidate |
| ARC resource containers | 23 partial |
| PDF analyses | 97 with text, 21 without extractable text, 1 timed out |

Embedded PDF text includes all 84 pages of the Express Order guide,
215 of 216 Express Publisher manual pages, and all 257 pages of the
Tandy 4000 technical reference. A private render confirms the omitted
Express Publisher page is blank. Image-only PDFs remain OCR candidates.
The [demonstrator facts](../ecosystem/demonstrator-purchase-facts.md)
record 57 purchase offers from 21 sources. The linked guide separately
documents conflicting SL/TL catalog IDs and availability dates.
The ecosystem catalog has 42 entries, up from 22.

The structural qualification of distinct native candidates accepted
95 Music files with opt-in sector padding, 49 Sound containers, 34
Draw figures, 15 DMDB containers, seven Worksheets, two Address Books
and seven FF1s. Four distinct signature-classified formatted Text
files passed. The permissive extension-based DOC category includes
45 syntax-compatible files and requires application-level corroboration.
Relative to the selected prior hash receipts, 33 accepted Music files
and 19 accepted figures have additional byte identities. Accepted Sound
files include four slot-6 identities. Violin and Sax broaden that
comparison. The previously known Baritone is the only parsed slot-5
identity in the indexed set. These are container and parser observations.

[Reference records and leads](../ecosystem/tvdog-reference.md) capture
release evidence, SDK and community sources, and questions for native
trials. Express Publisher 1.00 includes three stock FF1s and the additional
Dingbat2 and Springer faces. Both new faces round-trip in the independent
reader. Dixon and Marin from the RLX copy have identical outlines to the
stock baselines and different pair tables. Rockwell remains unacquired.
The Express Publisher manual identifies EPD publications, EPT templates
and external TIFF dependencies during printing. The corpus contains
four EPT controls and a large printer resource set.

The Text reader now retains documented paragraph-margin control envelopes.
Its recovered projection of the historical VIDEOMEM document contains
2,016 characters and six independently located margin records. The two
Print Magic controls share a page marker and remain private candidates
for an independent reader. The [demonstrator's purchase evidence](../ecosystem/demonstrator-purchase-facts.md)
pins original prices, catalog IDs and compatibility without inventing
a purchase chronology.

The later linked SND hardware word at offset 92 is used by the PSSJ
Digital Sound Toolkit as a recording-machine selector. In the toolkit,
`LIBSRC/MAGIC.ASM` reads the low byte and nominal rate around lines
261–275 and writes the machine code around lines 1368–1370.
`LIBSRC/PLAY.ASM` around lines 294–320 selects from a hardware table
using that field. The toolkit names code 4 for the newer double-buffered
PSSJ profile, and both bundled 11 kHz recordings store 4. Its 11 kHz row
selects fine-skew code A0 in that case. This demonstrates toolkit
behavior and provides a hypothesis for native DeskMate playback.
[Toolkit archive](http://ftp.oldskool.org/pub/tvdog/tandy1000/wares/DeskMate-Development-System-3.03/PSSJ-Toolkit.zip)

Three historical Music files contain complete four-stream scores and a
tail ending exactly at the next 128-byte boundary. FISHHE has 110 bytes
of 1A, ADDAMS has 82 bytes of 1A, and TROUB2 has 110 mixed bytes. The
default parser keeps its strict bounds. The new opt-in recovery accepts
this exact envelope, still requires all four stream terminators, and returns
the original tail. The evidence establishes a bounded archive recovery
profile. Its transport origin and the native UI's tolerance remain open.
[FISHHE](http://ftp.oldskool.org/pub/tvdog/tandy1000/deskmate/fishhe.zip) ·
[ADDAMS](http://ftp.oldskool.org/pub/tvdog/tandy1000/deskmate/addams.zip) ·
[TROUB2](http://ftp.oldskool.org/pub/tvdog/tandy1000/deskmate/troub2.zip)

DM_Music 1.04 matches the earlier privately preserved bytes and imports
the VB6 runtime. The package supplies a Windows GUI executable and readme.
The launch/differential requires a disposable Windows guest. The current lab
inventory exposed DOS RSX profiles and the principal Windows research VM.
No HDS capture or differential is claimed. The
[acquisition handoff](../ecosystem/acquisitions.md) pins leads for the
companion MidiMapper and Yahoo Groups archive from PR #129.
