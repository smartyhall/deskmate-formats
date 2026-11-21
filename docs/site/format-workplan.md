# Core format and application recovery workplan

Purpose: put primary document recovery and original application behavior ahead
of ancillary historical-format research. Each row identifies **what is
evidenced**, what remains **unproven**, and a reproducible next comparison.
See the [manufacturer appendix crosswalk](../reference/tandy-format-crosswalk.md),
[format inventory](../inventory.md), and
[compatibility](../compatibility.md). Treat these links as different types
of evidence, not interchangeable endorsements.

## Shared infrastructure is a hypothesis to test

Tandy describes a Database Resource for Address Book, Calendar and Filer, and
a Core Services Form Manager for Draw. Native modules and files expose common
DMDB/DBCOLS structures. Help resources provide a particularly useful additional
case. The structurally qualified Help reader from
[PR #140](https://github.com/smartyhall/deskmate-formats/pull/140) is now
integrated, while Help topic semantics and rule execution remain unresolved.

**A common record engine does not establish common application semantics,
allocation behavior, index ordering, or serialized document envelopes.**
Record and distinguish these layers:

1. Container/header and version discrimination.
2. Shared page, descriptor, index and row framing.
3. Application-owned schema, fields and related resources.
4. Runtime operations: load, create, edit, delete, save, reopen and print.
5. Cross-application payload transfer and fidelity.
6. Independent recovery/export and the consequences of unsupported constructs.

## Controlled comparison backlog

| Domain | Existing anchor | Next distinguishing experiment | Desired recovery result |
| --- | --- | --- | --- |
| Shared database | [database call study](../research/database-call-review.md) | Trace one matched read and one record mutation in Calendar, Filer and Address Book; compare actual service dispatch and physical allocation, not module names alone | Explicit common-core profile with application-specific constraints |
| Help resources | [shared database components](../research/database-components.md); [Help investigation PR #140](https://github.com/smartyhall/deskmate-formats/pull/140) | Resolve Help Rules-to-Text topic lookup with native F1 state and exact indexed bytes; test final-page boundary without relaxing unrelated validation | Recoverable Help text and topic navigation with version identification |
| Common Page Setup | [Appendix A common header](../reference/tandy-common-headers.md) | Change one Page Setup option at a time in Draw, Worksheet, Calendar and formatted Text; compare measured field bytes and exceptions | Qualified common header projection, without inventing a universal signature |
| Calendar | [laboratory specification](../formats/calendar/CALENDAR_FORMAT.md) | Probe unimplemented page growth, alarms, long descriptions, overlapping starts and deletion with exact native before/after bytes | Safer, versioned write profile beyond bounded append |
| Address Book | [native insertion report](../research/addressbook-two-contact-native-20261117.md) | Populate multiple contacts with field changes, sort and deletion; compare directory/index/page growth | Reproducible multi-record recovery and qualified writer |
| Filer and Filler | [Filer native study](../research/filer-native-20261117.md) | Compare schema-only and populated records; save/open cross-application samples and characterize GRAPHICS encoding | Independent records/forms extraction plus honest incompatibility reporting |
| Text | [native Text study](../research/text-native-20261117.md) | Independently compare plain, formatted and embedded-Draw documents across edit, save and reopen | Loss-minimizing document structure and text/graphics export |
| Draw | [native graphics study](../research/graphics-native-20261117.md) | Examine changed style bits, text, arcs and font references against native framebuffer and source bytes | Higher fidelity renderer and conservative editing |
| Worksheet | [native Worksheet study](../research/worksheet-native-20261117.md) | Compare formulas, cached results, references and edited cells across native save and reopening | Explicit formula/cached-value fidelity in modern export |
| Sound and Music | [native Sound](../research/sound-native-20261118.md) / [Music](../research/music-native-20261118.md) | Close invalid/truncated sample behavior and unqualified musical control flow; keep MIDI/HDS as independent corroboration rather than a new primary project | Recover source recordings and scores with known playback limitations |
| Print and shared resources | [SDK reference](../reference/tandy-format-crosswalk.md) | Compare identical content printed or exported by two built-in applications; identify shared printer/resource structures | Explain document layout and export limits across applications |

The Sound corpus and expanded MidiMapper investigations are integrated in
[#141](https://github.com/smartyhall/deskmate-formats/pull/141) and
[#143](https://github.com/smartyhall/deskmate-formats/pull/143).
The Draw style-word work in
[#142](https://github.com/smartyhall/deskmate-formats/pull/142) is awaiting
its final standalone-Workbench CI checks. Synthesize the relevant maintained
references after reviewing those results; preserve dated reports intact.

## Other DeskMate software: one comparable questionnaire

For each newly identified native/runtime application or peripheral module,
including the independently inventoried third-party ecosystem:

- Identify exact release, runtime version, executable/resource dependencies,
  original media hashes and whether it is actually DeskMate-native.
- Enumerate files created, opened and modified by a new blank document/session.
- Determine if the file is a document, shared DB, resource, template, cache or
  application configuration; extension alone is not sufficient.
- Compare a schema-only state, one meaningful record/object and a changed
  record/object where the application offers these operations.
- Check for Page Setup, DMDB descriptors, Form Manager records, Draw payloads,
  Text streams, font resources and shared printing conventions; report
  **negative** findings too.
- Record exact native UI behavior (including errors) and portable synthetic
  fixtures, not only a disassembly or filename inference.
- Publish no unreviewed original application bytes or captures.

Start with the built-in applications and qualified historical acquisitions
already listed in the [ecosystem catalog](../ecosystem/README.md). Keep
third-party format implementations separable when the storage architecture
really differs; share only empirically verified core mechanisms.

## Documentation completion rule

A maintained format entry is ready for the reference site when it has:
a release/version scope; evidence-backed signature and layout; confidence
levels; a field/control crosswalk; a reader/writer/renderer capability matrix;
at least one byte-verified test; loss and unsupported-case disclosures;
references to dated reports; and a small set of executable recovery examples.

The unanswered questions above are a research backlog, not features currently
supported by the recovery tools.
