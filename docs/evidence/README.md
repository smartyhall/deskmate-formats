# Public and private evidence

DOSLAB is the authoritative private archive. No executables, disk images, installed
trees, screenshots, archived .CLN files, access tokens or downloaded archives ship
in this proposed repository. Package code and authored documentation are staged;
their approved per-file licenses are defined in [LICENSING.md](../../LICENSING.md).
Private evidence remains outside those grants.

## Portable tests

`python -m unittest discover -s tests/portable -v` needs only the installed package.
`synthetic.py` assembles schema, metadata, internal framing and invented appointments
from documented constants without importing the production parser/writer or opening
any external file. Unknown header bytes contain an independent synthetic marker and
therefore do not copy an archival database. Specimens are generated in memory or
temporary test directories; no binary fixture is committed. Synthetic expected
records are assembled independently of the writer under test.

Original adversarial parser tests are reused with synthetic inputs. Portable golden
construction verifies synthetic one→two/five states; **those are not E07/E08 files**.
The fixed `@PaSsWoRd@=` internal signature is a documented format marker, not a user
credential. This marker's presence is explicitly allowed in source/specification.
Other personal/calendar data must not be submitted without review.

## Private archival integration tests

Set `DOSLAB_ROOT` explicitly to your own private archive; there is no machine-specific
fallback. In PowerShell, use `$env:DOSLAB_ROOT = '<your-private-lab-directory>'`;
on POSIX use `export DOSLAB_ROOT='<your-private-lab-directory>'`. Then:

```sh
python -m unittest discover -s tests/private -v
```

Missing fixtures/metadata fail rather than skip. This suite preserves the original
72 test bodies, adapting only package/mock imports and explicit fixture selection;
two additional direct archival tests check E07→E08 and E09→E10. It needs the E00–E14
`EXPERIMENTS/PHASE2` snapshots/manifests plus the PhaseIII-A generated and closed
database. No emulator is needed to run these byte-level regressions. The original
suite remains unchanged in DOSLAB and is run separately during migration validation.

The specification retains original relative evidence references and experiment
hashes, not distributable source data. Historical references may point to private
files that are deliberately absent. Add an original .CLN fixture only after a
separate provenance and redistribution-rights decision; none is inferred here.

source-provenance.json records source hashes and import-only migration changes.
Public verification results omit host paths, author identity and private output.
Private logs remain outside Git. See tools/audit_repository.py for publication
checks; automated scanning supplements manual file/provenance review.

E15 private tests additionally require the external E15_data_page_boundary
pre_before/pre_after/after snapshots, generated database and preflight comparison.
They verify byte-perfect generation, the exact observed allocation delta and safe
rejection of the seven-page result; they do not implement allocation. Portable
pre-boundary tests use synthetic bytes and require none of this evidence.
