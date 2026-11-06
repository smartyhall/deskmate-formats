# Offline Calendar regression corpus

The corpus exercises the implemented six-page PERSONAL.CLN profile. The
[generator](../../../tests/portable/calendar_corpus.py) extends the existing
independent synthetic constructor. It assembles rows, metadata and index entries
without loading an original file or importing the production writer. These are
programmatically generated specimens. The
[application-generated fixtures](../../../tests/fixtures/application-generated/README.md)
have separate provenance.

## Support matrix

| Area | Exercised behavior | Scope |
| --- | --- | --- |
| Empty and single appointment | Internal row only, then one case for each observed date and increasing time pair | Writer can append to an empty database with the known internal row |
| Multiple appointments | Same-day and multi-day cases, different physical and index orders, and one database using all 20 supported date/start keys | Bounded append within one PERSONAL data page |
| Dates and times | 2026-10-23, 2026-10-24, 2026-11-01, 2027-11-01 and all 15 increasing pairs of 09:00, 09:15, 10:00, 10:15, 11:00, 12:00 | Elapsed times follow from start/end; the stored Duration field stays opaque |
| Description | Lengths 1, 7, 8, 10, 60, 95, 119 and 120, all 95 printable ASCII characters, and a separate raw-byte probe | 1–120 printable ASCII for append. The reader retains an opaque non-ASCII byte. General text encoding and escaping are unresolved |
| Alarm and opaque fields | Empty Duration and Protected byte `31` in the batch corpus. Separate synthetic tests assemble `31`, `71` and unsupported cases. | The reader interprets both confirmed Alarm states and preserves raw fields. The writer accepts the empty/`31` profile. |
| Index and ordering | Chronological date/start order, physical insertion order, low IDs, index triples, count and next-ID candidate | Writer rejects tied date/start keys; tie ordering remains unresolved |
| Capacity | Final append fills the data page through its list marker; a one-byte-larger append to the same prefix is rejected | This is the single-page writer capacity boundary. Allocation, linked pages, deletion, ID reuse, reclamation and long IDs are outside the corpus |
| Rejection and raw fallback | Truncated file, extra page, bad magic, duplicate index, 121-byte description, reversed time and opaque description | Checks profile-specific outcomes. Overnight or zero-length events, unobserved dates and times, and alternate layouts are outside the valid matrix |

See the [parser notes](README_PARSER.md) and [writer notes](writer-lab-notes.md)
for the documented profile. The matrix varies combinations within the software's
supported subset. It supplies synthetic regression evidence for those
combinations and structural boundaries.

## Run and regenerate

Use Python 3.13 or newer with the project installed, or set `PYTHONPATH` to the
repository's `src` directory. From the repository root, give each runner command
a new output directory under an existing temporary directory.

```sh
python -m unittest discover -s tests/portable -v
python tests/portable/run_calendar_corpus.py <new-output-directory> --emit
python tests/portable/run_calendar_corpus.py <new-stress-directory> --stress --seed 20261105 --seed 17 --seed 8675309
```

The portable run checks 256 valid specimens and seven separate probes. Stress
mode checks 1,024 valid specimens and the same seven probes per seed. The default
seed is 20261105. Four fixed cases cover the empty, exact-fit, full printable
ASCII and all-start-key profiles. The next 60 single-event cases enumerate the
date/time matrix. Multi-event cases use a SHA-256 token of the ASCII
`seed:case-number` string to vary compatible keys, end times and text. Fixed
mappings, explicit little-endian index triples and binary writes give a
platform-independent byte definition. Each nonempty valid case checks the
writer's final append against a complete independently generated database.

The runner generates twice per seed by default and compares every specimen
byte for byte. `--repeat` controls the number of generations. The JSON report
includes the seed, case and feature counts, per-batch elapsed host seconds,
failure details and a SHA-256 digest of the sorted per-specimen manifest.
Use `--emit` to retain the CLNs and manifest. Failures return a nonzero exit code
and retain any available failing specimen in the seed's output directory.
The report identifies the stage where validation failed so the parser, writer
or generator can be investigated with that specimen and seed.

The [recorded batch report](synthetic-corpus-validation.json) pins the source
and generator revisions. It includes the comparison of two independent
processes emitting the default-seed corpus. All reported measurements are host
observations from synthetic runs. Elapsed emulated time was zero.
