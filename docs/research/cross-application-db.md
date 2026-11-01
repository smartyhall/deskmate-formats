# DeskMate 3.05 cross-application database investigation

2026-11-01. Offline research; no application launch, GUI, keyboard, DOSBox,
OCR, native mutation or service recovery was attempted.

## Assessment

**Shared low-level storage structures are strongly supported.** Calendar,
Address Book and both shipped Filer candidates share complete metadata rows,
table-directory grammar, index headers, six-byte index entries and row framing.
These correspondences extend through actual targets and application-specific
tables. They exceed the earlier isolated-string evidence.

A [follow-up call/reference review](database-call-review.md) recovered named
DMDB binding sequences and far-indirect call thunks in all three applications.
This supports a common callable service interface. **Runtime binding and the
storage-operation meanings of those calls remain unresolved.**
No general Filer allocator, writer, codec or universal parser follows.

| Hypothesis | Evidence and limitations | Assessment |
|---|---|---|
| H1: common underlying engine | Shared structures and code-backed named service calls; record-operation dispatch remains incomplete | Strong static interface evidence; shared storage implementation still a hypothesis |
| H2: shared low-level structures, application-specific storage | Common directories/indexing/framing with different schemas and payloads directly demonstrated | Strongest supported architectural description, high confidence for inspected files; separate implementations not established |
| H3: conventions without substantial shared implementation | Separately compiled/copied format implementations remain possible | Not excluded as implementation claim; isolated naming coincidence cannot explain the complete indexed structures |

H1 and H2 overlap unless “application-specific storage” means distinct low-level
implementations. A shared engine can store application-specific schemas and
payloads. Evidence discriminates strongly about structures, less strongly about
implementation identity. Confidence is qualitative, not a probability or a
published format specification.

## Existing evidence reconstructed

Local worktrees inspected: Calendar `experiment/e19-space-pressure` at `7384053`,
Address Book `research/addressbook-phase2` at `b4a83ee`, OCR at `da484ff`, and
Filer `research/filer-f00-f02` at `b4a83ee`. Filer's report and sidecar were
untracked in their original worktree; they were copied unchanged into this branch
to retain that authored checkpoint. Other worktrees were preserved.
This branch, `research/cross-application-db`, starts at `b4a83ee`, incorporating
the latest relevant Calendar and Address Book results. No fetch, merge, push or
publication was performed. OCR was inventoried, not rerun or incorporated.

| Evidence | Native operations actually established | Boundary |
|---|---|---|
| [Calendar E00–E14](../formats/calendar/CALENDAR_FORMAT.md) | No-edit content control; isolated field mutations; variable records, index movement, compaction, shrink/growth and ID reuse in original six-block profile | Full codecs/general ID rules and control payload unknown |
| [E15](../experiments/e15-page-boundary.md) | Writer-prepared near-capacity fixture accepted unchanged; native insertion allocates block6 and preserves old rows | Preparation was not all native; one allocation is not a general allocator |
| [E16](../experiments/e16-page-reclamation.md) | Native deletion retains block6, changes prefix80→44, removes index entry, decrements count, increments opaque000→001; next ID not decremented | General deletion/free-space accounting unknown |
| [E17](../experiments/e17-reuse.md), [E18](../experiments/e18-reuse-variants.md), [E19](../experiments/e19-space-pressure.md) | Equal/smaller/larger records append after retired row; under pressure thirteenth77-byte insertion allocates block7 instead of compacting retired24 bytes; 29 prior indexed rows remain stable | Header map, index growth and universal hole reuse unknown |
| [Address Book I](addressbook-phase1.md) | A00 no-edit keeps126 contents unchanged despite ADR timestamp change; A01/A02 each create one contact; First Name+4 bytes shifts ending+4 | One contact per fixture cannot establish ordering/deletion |
| [Address Book II](addressbook-phase2.md) | A03 phone−4 bytes; A04 City+5 in field4; remaining aligned fields, counters/index stable versus A01 | Other fields/non-ASCII untested |
| [Filer F00](filer-f00-f02.md) | No native operation; full126-file before/run copies and static candidates retained | F00 launch/exit, F01 schema and F02 insertion unperformed |

Existing private `lab.py` supplies dumps, strings, numeric candidates, snapshots
and heuristic pairwise differences. Calendar validates its explicit six-block
profile and rejects expanded layouts. Neither provides independently offset
region comparison plus candidate index probes without Calendar acceptance.
The new [inspection helper](structural-inspection.md) fills that narrow gap,
reusing Calendar block-size/index-header constants. Production parsers/writers,
dependencies, CI and licensing policy are unchanged.

## Corpus and reproducibility

Raw outputs remain private in DOSLAB
`EXPERIMENTS/RESEARCH/cross_application_db`. The four primary files come from
`EXPERIMENTS/FILER/F00_baseline/before/files/DESKMATE`: a preserved known-good
research installation, **not** pristine empty Calendar media. Calendar has five
appointments plus its pre-existing control row. Address Book is empty of contacts,
with NAMES/CONFIG rows. Shipped Filer samples' native roles were not observed.

| Name / file | Bytes | SHA-256 |
|---|---:|---|
| C / PERSONAL.CLN |6144| `e48066b2b78fb73ec414271ae4404468529628c840dfac3f7c374621544bc243` |
| A / PERSONAL.ADR |10240| `cb890e6d7ba96fafb5a5d3991e208f4de862bee485f6ce32696e989c97d3394c` |
| F-C / CARMAINT.FIL |14336| `ca5ea9d77dc7545e761457ddc9d40c0b5aca427d7f787a19038d61495f4c67e7` |
| F-I / INVNTORY.FIL |12288| `62316203c555e42cddc47b118f4a34ef1c60362e684d2b90a978fb3675d9c6fe` |

Offsets are absolute zero-based hexadecimal. Prose/table ranges are inclusive;
utility/machine ranges have exclusive ends. Confidence applies to the stated
observation, never automatically to the associated hypothesis.
[cross-application-evidence.json](cross-application-evidence.json) records table
summaries and component identities. Private `research.py` records exact probes,
assumptions and paths: run `probe`, `structures`, `components`, `deepen`,
`relations` in order to regenerate raw findings. Its fixed-fixture structural
probe is an experiment, not a supported decoder. External-fixture regression
tests independently check the principal correspondences.

## Evidence-backed structural matrix

| Feature / reference | C | A | F-C / F-I | Confidence / significance |
|---|---|---|---|---|
| Header0000–0003 |03 46 49 4C|03 00 00 00|Both03 46 49 4C|High bytes; magic alone cannot recognize whole family |
| Header0020 onward |Repeated FF/8F/F8 patterns; E15/E19 allocation changes measured |Related pattern|Related, with differences|High bytes; page-map/free-list/checksum meanings unknown |
| Directory0400; label0402 |T/01/DBCOLS…01/02|Same grammar|Same grammar|High static structure, beyond label match |
| Complete six self-schema rows0800–0897 |Identical152 bytes|Identical|Both identical|High: all six pairwise comparisons; SHA-256 `090cfee8845b005925fd79a7dfce21362976239a08d02dc7061b84928316c353` |
| Row starts0800,081B,0836,084E,0866,087F |IDs10–15; six fields; ownerDBCOLS|Same|Same|High: literals0802,081D,0838,0850,0868,0881 belong to complete matching records |
| First application descriptor0898 |Date/PERSONAL|Title/DATA|ITEM#/LAYOUTS|High divergence immediately after common region |
| Every table's index block+0000–0027 |(FF×9,00)×4|Same|Same|High:14 indexes, including empty ones |
| Index entries at block+0028, six bytes |19 entries/2tables|43/4|54/4 and52/4|High: all168 LE16 triples resolve block×1024+offset to matching80/low-ID prefixes; unique targets per table; zero tuple follows |
| Schema index0C28 onward |13; self-schema first|27; CONFIG first|28/26; DATA first|High: all four indexes sort owner then padded position, independently of physical order |
| Directory count versus index count |13/6|27/0/15/1|28/22/4/0;26/20/3/3|High equality; native C/A mutations corroborate count role; Filer is static |
| Row framing at targets |Seven fields,01 02 ending|Native DATA sixteen fields, same ending|LAYOUTS13, GRAPHICS2, F-I DATA5|High measured spans; escaping and general ID encoding unknown |
| Empty DATA |E00 still has internal row1000|03 at1000, zero entry1428|F-C03 at2000, zero entry2428|High bytes; empty must identify table |
| Populated DATA |Native mutations measured|A01–A04 target1000/ID10; variable spans|F-I targets2800,291E,29D2; IDs10,11,12; slots2C28,2C2E,2C34|High static Filer framing/arithmetic; native acceptance untested |
| Extra data blocks |E15/E19 direct targets6/7|Untested allocation|F-C LAYOUTS4/10; GRAPHICS6/11/12/13; F-I GRAPHICS6/8/9|Strong common block/index structure; allocation policy measured only in C |
| Retired framing |E16 native44 at1800, unindexedID21|Untested|F-I unindexed44/16 at10F0–1119,44/1A at1196–11BF, thirteen fields each|High bytes; probable shared retired-row representation, history unverified |
| Opaque token |E16 000→001 at043B–043D|000 in DATA controls|F-I LAYOUTS002 at043A–043C with two unindexed44 rows|Medium deleted-row accounting hypothesis; no Filer mutation |
| Next-ID-like token |Native behavior depends on layout/operation|00016→00017 first insertion|F-I DBCOLS00022 at0418–041C, max indexedID29hex (=41)|High counterexample to universal max-ID+1 or greater-than-all-IDs rules |
| Encoding |ASCII plus binary dates/times|Literal ASCII native test values|ASCII schema/layout/data plus opaque graphics|High for observed bytes; CP437, escaping and C/K/N type semantics unknown |

The directory's data-block token is a starting-block candidate, not a restriction
that all rows reside there. F-C LAYOUTS includes an indexed row at2800 in block10.
Graphics rows each have their own indexed target; this does not establish a
single record spanning multiple blocks. Full target lists remain private in
`structures.json`; machine summaries record target block sets.

An alternative block-size check held all 168 entry slots/counts fixed and tested
64, 128, 256, 512, 1024, 2048 and 4096 as address multipliers. Matching in-bounds
80/ID targets numbered respectively **0, 0, 1, 3, 168, 3 and 1**. Thus 1024 is
supported by target arithmetic across all four files, beyond size divisibility
or coincidental string alignment. This does not measure Filer allocation policy.
Raw scores and per-file results are in private `alternative_block_sizes.json`.

## Why matching offsets matter

The common rows encode names, owner, positions001–006, lengths80/80/4/4/1/1,
typesC/C/N/N/C/N and final0. Their full lengths explain matching literal offsets.
They also have matching-ID index references **at different slots**: cname is
referenced at C:0C28, A:0C9A, F-C:0C52, F-I:0C46. This supports a shared
self-schema representation whose index orders different application schemas,
rather than unrelated layouts sharing labels.

All four schema indexes sort by (owner,position); directory tails2,3 are those
fields' one-based ordinals. Calendar PERSONAL tail1,2,4,5,7 fits chronological
ordering. ADR DATA tail3,2 names LastName then FirstName; CARMAINT tail3,1 names
Car then Date. A sort-key ordinal list is a **medium-confidence** interpretation.
This does not establish comparator semantics, collation, uniqueness or enforcement.
A native two-record experiment inserted against sort order would discriminate it.

## Differences, negative results and limits

F-I's six self-schema rows contain six fields, but its next twenty schema rows
contain five, omitting a final uniq value. F-C stores six fields in all28 rows.
F-I also uses C where F-C uses K for some text-bearing fields. The sixth schema
descriptor does not guarantee six physically present values in every row.
Implicit defaults, historical versions or conversion are possibilities; no
particular explanation is established and absent values must not be fabricated.

Both Filer samples have labels LAYOUTS0427, GRAPHICS044D, DATA0470, yet DATA
block/index tokens differ8/9 versus10/11. They differ in DATA fields7 versus5,
records0 versus3, schema rows28 versus26, layouts22 versus20 and graphics4 versus3.
Equal metadata offsets do not imply equal data offsets or a fixed six-block file.

F-I has22 physically framed layout rows, of which20 are indexed and two have44
prefixes. Opaque002 fits the difference. Calendar E16 independently supplies
native deletion evidence for a similar state. This supports a shared retirement
convention, not common reclamation policy. E17–E19 warn against treating retained
text as live rows or assuming any sufficiently large retired slot is reused.
Filer deletion remains future native work outside F00–F02.

Exact96-byte-window comparisons found short DMDBRD/application matches, but the
strongest also occur in TEXT.PDM, the negative control. Common library code can
explain them; these matches do not identify database routines. This failed
discriminant is retained in `module_relations.json`.

## Next work and research status

See [component findings](database-components.md), [tool instructions](structural-inspection.md)
and [F00–F02 runbook](filer-native-runbook.md). F00 before/run evidence is intact.
No native Filer experiment is represented as complete.

1. Complete F00 no-edit launch/exit; identify actual entry point and Filer/Form
   Setup schema workflow; measure complete-tree differences.
2. F01 minimal empty native schema: compare directory/self-schema/index grammar,
   five-versus-six fields and signature with shipped samples.
3. F02 one exact record: test framing, count/ID/index transitions and actual
   stored bytes; separate defaults from entered values.
4. After separate authorization, two records inserted against sort order, then
   one deletion: test trailing tokens and44/opaque-token correspondence.
5. Resolve DM89 import/dispatch structures and a bounded database call path from
   each application. This would distinguish common service use from copied code.
6. Only then study Filer allocation under pressure or generalize container code.
   Header map, ID codec, non-ASCII, numeric/date encoding and escaping remain open.

Verification and preservation results are recorded in
[verification checkpoint](cross-application-verification.md). No universal parser,
writer or application module was introduced.
