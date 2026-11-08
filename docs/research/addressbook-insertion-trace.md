# Address Book 3.05 insertion: static successor checkpoint

2026-11-07 America/New_York; fetched main
`a41bed1b7a4efa5d8763145de4c0dc42468dfa6b`
(validation in the [receipt](../evidence/addressbook-insertion-trace.json));
branch `codex/addressbook-insertion-trace`. PR #78 is merged at
`0cba552411d96376cce5db3c6d4907cc8e9b4ace`, also an ancestor of this base.
Calendar generation/publication was not revisited. Refs #70.

**New result:** the pinned 3.05 code consumes DATA's trailing `3,2` as sort
ordinals, builds a ten-byte routing prefix from those fields, then compares
complete LastName and FirstName values before inserting a six-byte location/ID
entry. Physical row append and index ordering are separate operations. This
supports the existing A01 trial predictions; it is not a native two-contact result.

## Inputs and method

All offsets below are hexadecimal **absolute file offsets**, not guest addresses.
The MZ headers are 0x200 bytes; add 0x200 to the near CS offsets/table words used
here. ADDRESS's conditional DS file base is 0xBDD0, as established in the
[cross-application call review](database-call-review.md). Near relative branches
wrap at 16 bits; a Capstone display such as `0xffff9a3e` resolves to file 0x9A3E.

Rehashed inputs in the preserved `references/oldskool` collection:

| Input | Bytes | SHA-256 |
| --- | ---: | --- |
| extracted/deskmate/dm305dk4/ADDRESS.PDM | 61025 | `ef685b20e259f0932378668d9b120882468dc0da157a015e2df95d4ce61a60fb` |
| Same directory, DMDB.R89 | 1109 | `799444bb8c04632d261f61498ba269f9352e5528718f2e0a89512bf6ef7b808f` |
| Same directory, DMDBRD.RES | 21955 | `c4bc9f5699bfaf1ac5adb57a011b04dcec00a2ae75edb2baf603c8001fa99cee` |
| Same directory, DMDBUPD.RES | 13740 | `9e77a2081ebb3a9549903f5d337580c65d6e0a3f603185064d4c82e16327cf4f` |
| extracted/sdk-3.03/Development-Disk-1/DMDB.H | 14093 | `47c2ff4638d8ab1bcc12aeab3e2dd5b51ccfeef9bbddb1a014912c831df4d5aa` |
| Same directory, DMDB.INC | 13275 | `2ea33422d68ab2402ca2b83a1c1f5d7fee80db9c36000a8609d42712ce299a29` |
| originals/sdk-3.03/DeskMate-Development-Guide.pdf | 16801017 | `8081d5cd34305982844ab3598ebfbdf8887e7e369d1174a88a7631cba08439e0` |

Windows 10 build 19045, Python 3.13.17, existing private crosswalk venv with
Capstone 5.0.7/x86-16. Reused the allocator listings and decoded selected windows
again from explicit targets; linear sweeps only located candidates. No new
disassembler, dependencies, app-server or emulator process. Commands, selected
listings, original-byte measurements and source snapshots are durably retained
under private-evidence `addressbook-insertion-20261107`, with hashes in the receipt.

## Add and save route: executable findings

| Image / offset | Instruction/data relationship |
| --- | --- |
| ADDRESS C1DD/C1E1; CC60; 0A58–0AA6 | Menu event F582 points to the Add label at DS:0E90. Dispatcher subtracts F582; table CCC selects 0AA0, which calls 3B5F. Unless event F584, 0A67 first calls pending-record handler 3A44. |
| ADDRESS 3B5F–3C7A; 3A44–3B5E | Add initializes inline entry and state DS:009E=0x64. Pending-record handler's 0x64 branch scans populated fields (excluding the two date-label fields), then 3B2A calls 43F5. The 0x66 branch is a separate existing-record update route. |
| ADDRESS 0793/0797, 07A0–07BC | Quit-prompt path supplies DS:0934 (save-changes text at C704). Response F703 leads through 07A5 to 3A44; subsequent exit calls 2ADB. This connects the observed Escape/Yes workflow to the pending-record handler statically; no response was submitted here. |
| ADDRESS 43F5–45C9 | Rejects blank LastName; assembles table handle, column count and column-name/value pairs. Column-name array at C338 resolves to Title, FirstName, LastName, etc. 45C6 calls 8C05. |
| ADDRESS 8C05–8C19 → 0F38 → 9A3E → A9B9 | 8C0F loads selector 7; 8C13 calls 0F38; 0F47 forwards to 9A3E. Stores at 9A72/9A78 supply selector/argument pointer in DS:29B4/29B6; 9A99 calls A9B9; A9C7 far-calls DS:29C4. A1E5 binds that slot using the DMDB name. |
| RD 189E–19EC; UPD 0200–03AC | RD selector table entry 18D0 (7) selects 1938; second table entry 1993 selects 19E4, then far-call 19EC uses the named update slot DS:0128. UPD selector 7 branches at 0235/0238 to 025E → 02B0; 0340 calls row insertion 1277. |

SDK DMDB.H names selector 7 `ADD_ROW`, selector 19 `UPDATE_ROW`, and describes
the table/count/value-array request layout. Those names are **SDK statements**;
the constants, stores and calls above are **executable findings**. Name binding
and the DMDB.R89→reader forwarding are reused from the call review. Actual loaded
targets across far-indirect slots remain unobserved; these are conditional static
paths, not a runtime trace or closure of the loader gap in #25.

## Index construction and ordering

RD **2221–22AB** reads descriptor fields 3/4/7/8 into data-page, column-count,
next-ID and index-page state. At **2261–22AB**, field **9 onward** is parsed as
decimal ordinals into table object +0x0C. The helpers are 4040 (field→integer)
and 43B6 (one-based field pointer). A01's descriptor at **0425** ends in
`5<01>3<01>2<01><02>`: index page 5, LastName ordinal 3, FirstName ordinal 2.
Both name fields have schema type **K**. This supplies code backing for the
previous trailing-token hypothesis and agrees with SDK Guide PDF p.477.

UPD **1F8E** uses table+0x0C for the ordinary persistent index (200C), rather
than the temporary-index branch. **11C8–1276**, called at 2044, builds a
**ten-byte routing prefix**: extract each sort field via callback 0x31 → RD
43B6, copy up to nine available bytes, append separator 01, stop at ten bytes
or five fields, and zero-pad any remainder. Derived A01/new prefixes are
`USER A<01>TE<01>` / `ALPHA<01>ZUL<01>`. These are calculated from the decoded
algorithm, not newly observed native keys. Index-page subdivision routing uses
these short keys at **16C5–178F**; untouched A01 has four FF×9/00 boundaries.

Full comparison is **1BFC–1C45 → 29E5–2A34 → 2942–29E4**: obtain pointers to
each row's full ordinal-selected fields, compare the first field, and advance
to the next only on equality. **26B7–2849** binary-searches six-byte entries,
loads their row payloads through 23C6, compares complete fields at 276B, shifts
triples and writes `(page, in-page offset, ID)`. Thus the six-byte entry is a
locator, not a stored name key, and equal routing prefixes do not truncate the
full name comparison.

For **K**, 2942 delegates to UPD 33CB, callback 0x2C → RD **4502–4523**:
translate both bytes through the collation pointer SS:0144 and subtract their
weights. RD **1CB6–1D43** requests DOS INT 21h/6506 under version/error branches
and stores the returned table address plus two. The separate C comparison at
RD 434A folds ASCII lowercase; **that is not DATA's K path**. The actual table,
fallback/error behavior, non-ASCII, case equivalence and punctuation ordering
are not qualified here. Ascending ALPHA before USER A is predicted under the
ordinary A-before-U collation; no runtime table was captured.

At **2773**, `<=` searches earlier positions, so equal full keys go before an
existing equal key within this unsplit subdivision; no ID tie-break is present
in that comparator/search. Duplicate checking is separately gated at 0310–032C.
This is a bounded static tie finding, not a tested global duplicate policy across
subdivisions, splits or application validations.

## A01 consequences and remaining gate

Re-read the existing **tool-generated reconstruction**, 10,240 bytes, SHA-256
`19215ea147c65b259eb963fd240e9931d96e77f92d1001f0f7edf89024076ac8`, identical
to the historical native A01 hash. Original A01 archive remains unrecovered.
Its row is 61 bytes, ID 0x10 at 1000, marker at 103D, with one index entry at
1428. This measurement is of the reconstruction; native observations remain
the historical A01–A04 reports. Existing fixtures and reports were not edited.

| Existing Phase II prediction | New code support / limit |
| --- | --- |
| Append ID 0x11 at 103D; old 61 bytes unchanged | 02B0 reads next-ID object+8; 1277 follows the existing data chain to its last page, checks tail space, finds marker 03 and appends ID/payload/new marker at 133D–137C. No packing/relocation on this sufficient-space path. Reuses the [allocator study](dmdb-page-allocator.md). |
| New row 56 bytes through 1074; marker 1075 | Fits the decoded guard: 1023−61=962 available versus payload-through-02+4=58 required. Sixteen-field defaults/serialization still use the observed A01 profile; this run does not prove every UI default branch. No new page/map update is needed. |
| New index entry before old: `(4,61,17),(4,0,16)` at 1428 | Complete LastName/FirstName comparison supports this under ordinary DOS collation; 26B7 shifts the old triple by six. Two entries fit the existing subdivision, so no split or routing-boundary rewrite is predicted. |
| Count 00001→00002 at 0431; next-ID 00017→00018 at 043B | 036D/0373 increments ordinary next-ID by one; 0394 calls 30A8 with operation 7. 30E9–3108 increments descriptor field 5; 3111–3126 formats field 7 to width five. Opaque 000 at 0437 is unchanged on this path. Special low-byte-FF/wrap branches are outside this trial. |
| Ten pages; unrelated tables/header unchanged | Row/index writes at 13B9/13F2 and descriptor page write 3156 explain the bounded footprint. Successful application save may perform additional work; full before/after comparison remains necessary. |

The original [second-contact runbook](database-phase-ii.md) remains unchanged.
First-name or insertion-order indexing is now contradicted by the decoded
ordinary DATA path. Sorting keys, append placement and counters have stronger
support; native execution and persistence of this combination remain missing.

Four new opt-in private source regressions pin menu/selector transport,
descriptor/full-field comparison, prefix-versus-full-key/equality branches, and
row/counter calls. They assert original instructions/tables without executing
them; they do not test native acceptance. Existing portable Address Book and
Phase II diagnostics remain the portable checks; no duplicate byte-report tool,
writer prototype or new database sample was created. Validation and preservation
results are in the receipt.

Smallest next step: separately authorize the existing **A01→ZULU ALPHA / 555-0100**
single native Add/save trial, returning complete before/after ADR bytes and
installation manifests. Its index order, original-row preservation, 56-byte row,
count and next-ID resolve whether this static path predicts the actual saved
file. Reuse the existing read-only Phase II diagnostic. A later same-last-name
pair with a long shared prefix would test secondary comparison beyond the routing
prefix; it is not necessary to authorize that larger trial now.

No emulator launch/connection/input/save/reset, media replacement, RAM capture
or app-server launch occurred. Requested emulated time **0 ms**; actual guest-clock
delta **not measured**. No native two-contact acceptance is claimed.
