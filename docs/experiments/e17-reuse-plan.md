# E17 preparation: one deleted-record reuse test

## Historical preparation status: prepared, not performed

E17 was subsequently performed after the keyboard prerequisite was repaired.
See [the E17 result](e17-reuse.md). The following records the earlier blocked
preparation checkpoint and is retained unchanged as historical evidence.

The research sprint authorized E17 subject to reliable GUI entry and visual
verification. That gate failed: the separate screen-research installation opened
Find Date but the intended date did not visibly replace its existing value through
the bounded paste/direct-key attempts. The dialog was cancelled without saving.
No E17 Add Event was opened, no application-produced E17 file exists and no reuse
outcome is claimed. The optional Address Book survey was omitted to prioritize the required sprint
deliverables.

The E16 final source was verified independently: all126 installed files matched
its manifest. PERSONAL.CLN is7,168bytes, SHA-256
818c44af2f351cc764dfd48a82b3d8ae1dd0b5f733c8549dbdd902f67eed05ea.
A complete private before copy and manifest, raw baseline observations, all17
index triples and seven page hashes are retained separately from screen research
under DOSLAB EXPERIMENTS/PREPARATIONS/E17_reuse. There is deliberately no after
snapshot or generated output. E15/E16 archives remain unchanged.

## Verified starting observations

| Structure | E16 baseline |
|---|---|
| File size |7,168bytes, seven1,024-byte pages|
| Count0x0435..0x0439 |ASCII00017, including internal row|
| Opaque token0x043B..0x043D |ASCII001; meaning unknown|
| Next-ID candidate0x043F..0x0443 |ASCII00034(decimal), not simply max live ID+1|
| Live index |17six-byte entries from0x1428; all target page4, none page6 or ID0x21|
| Last two entries |0x1482:(4,0x27,0x11);0x1488:(4,0x3F,0x12)|
| Sentinel and unused index |882zero bytes at0x148E..0x17FF|
| Retired page6 row |24bytes at0x1800, prefix44, historical ID0x21 and BOUND12 payload|
| Page6 list marker/padding |03at0x1818;999zeros thereafter|
| Allocation-associated header |0x0026..27=006F;0x002A..2B=8FFF; meanings unknown|

These are fixed-fixture observations checked against the exact source hash, not
a general seven-page parser. Existing production reader/writer rejection remains
intentional. Retired payload bytes and counter candidates must not be interpreted
as an allocator specification.

## Controlled application procedure after the gate is repaired

1. Reverify the complete E16 source and make a fresh disposable installation.
   Preserve both source and before manifests plus emulator configuration guards.
2. First demonstrate non-editing date navigation and visible field input on the
   independent research copy. Do not use the E17 baseline for input troubleshooting.
3. Launch Calendar using the working SDL1/software profile copy. Visually verify
   the November1,2026 survivors and absence of BOUND12.
4. Add exactly one event: November1,2026,11:00AM–12:00PM, description REUSE17.
   Record the visible alarm value and preserve it; no alarm value was specified
   for this sprint. Verify every field before one submission. If entry is
   unpredictable, cancel without saving and stop the live part.
5. Verify REUSE17 appears and all16 pre-existing appointments survive on their
   established dates/times. Exit Calendar cleanly to DOS.
6. Preserve the full after installation, database, screenshots, actions and SHA-256
   manifest. Compare every file and every database byte; list size changes and
   appended/removed ranges separately. Do not run a second insertion or correction.

## Discriminating comparisons, not predictions to enforce

* At0x1800 inspect prefix44, old ID21, complete old payload and marker1818. A new
  row might overwrite this slot, append elsewhere on page6 or allocate elsewhere.
  If appended directly at1818, that old list marker would move; this is only one
  candidate address, not a required result.
* Distinguish reuse of ID0x21 from an ID derived from00034(decimal0x22), or another
  observed result. Record all counter/token bytes, not just a presumed increment.
* Inspect all index entries and terminators. If the previously observed ordering
  continues, REUSE17's key precedes the two2027 events and may occupy1482; independently
  verify the actual order, resolved locations and IDs instead of assuming this.
* Compare each survivor and the internal row by its before index reference and raw
  bytes, accounting explicitly for any index shift, relocation or reassigned ID.
* Compare all seven before pages and all four allocation-associated header bytes.
  Record whether file length stays7168 or changes; do not assume page reuse means
  the opaque token must decrease or that all header bytes must stay unchanged.
* List every unexpected byte. A leading44 reversal, retained tombstone, changed001
  token or new page reference is evidence only for this one observed operation.

Possible outcomes distinguish slot reuse from retained-page append or fresh
allocation. None establishes a general free-list algorithm. Do not extend the
production allocator/parser/writer or recover deleted records from this plan.

If E17 eventually succeeds, a useful next discriminating experiment would vary
the new description length in a separately authorized copy, testing whether reuse
depends on fitting the retired24-byte slot. That experiment is not performed here.

## Preparation verification

The complete126-file E16 source/preparation manifests and database hash passed.
The three existing private E16 regression tests also passed. No production parser
or writer code changed, and no new experimental result is represented by these
baseline checks. Raw preflight bytes and the installed copy remain private.
