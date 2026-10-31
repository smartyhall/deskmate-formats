# Repository transition verification — 2026-10-31

This is local verification of the staging project, not a GitHub Actions run or a
new format experiment. No remote repository/public access was created.

| Check | Result |
|---|---|
| Portable synthetic suite, installed wheel, Windows Python 3.13.15 | 47 passed |
| Portable synthetic suite, installed wheel, Windows Python 3.14.7 | 47 passed |
| Migrated private archival suite, Windows Python 3.13/3.14 | 74 passed on each |
| Original unchanged DOSLAB suite, separately executed Python 3.13 | 72 passed |
| Installed package imports and both CLI entry points | Passed on both Python versions |
| Wheel and source archive build | Passed; distribution content audited |
| Focused Ruff correctness rules F63/F7/F82 | Passed |
| AST parse and proposed source content audit | Passed |
| E00–E14 exact fixture inventories and file hashes | 1,890 matched |
| Lab parser/writer/CLI/test/spec source hashes | Unchanged |
| Linux and hosted GitHub Actions | Prepared in CI; not executed locally |

Portable commands ran in separate virtual environments with PYTHONPATH and
DOSLAB_ROOT removed, from this repository using installed-wheel imports. Synthetic
test data opens no archive and is not represented as an application-produced file.
Local integration explicitly supplied the external archive path. Its 74 tests are
the original 72 unchanged assertions with package/mock imports and explicit fixture
opt-in adapted, plus direct E07→E08 and E09→E10 byte-equality regressions. The original
suite remains in place with no coverage reduction.

The full Calendar specification was copied with an added provenance note; historical
confidence distinctions and limitations were retained. Package modules are exact
source copies apart from relative imports. The source hash record and migration
checks support this limited-change claim. Parser/writer functionality was not
refactored into speculative common engines.

No proprietary executables, disk images, snapshots, real .CLN files, screenshots,
personal data, credentials, archive tokens or absolute host-user paths were staged.
Only authored analysis/specification and independently assembled fixture sources
are proposed for distribution. The fixed internal format signature is documented
as such; it is not a user password. Automated source/distribution checks supplement
manual provenance review and cannot grant rights to third-party evidence.

The repository has a local main branch, no remote and no release/publication
workflow. Audited files form the initial local commit. The owner supplied an author identity
after initial verification; it is configured only in this repository.
At that repository-preparation checkpoint no license was selected. This historical
state is superseded by the approved [licensing policy](../LICENSING.md); see the
[licensing review](licensing-review.md) for its subsequent verification.
The owner still controls licensing, contribution attribution and any publication.

Private execution logs and environment paths remain outside Git; public results
are summarized here. Build products, virtual environments, local results and any
future private-fixtures directory are ignored. E15 and additional format work
were not started.
