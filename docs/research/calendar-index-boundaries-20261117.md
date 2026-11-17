# Calendar index boundary validation — 2026-11-17

Campaign base: `93e164f4827f2f08685ada512f65924280a756aa`.
This is offline fixture analysis and synthetic validation, without guest actions.

Issue #81's original common-parser refusal at `0x1400` is historical. The
merged named-calendar implementation already accepts both published native
specimens through `database.parse_bytes` and Calendar `profile='sdk'`.
The default `observed` Calendar profile intentionally retains its six-page
single-calendar limit. No structural check was relaxed in this follow-up.

The original specimen hashes were rechecked by the existing independent
validator and portable tests:

| Specimen | Bytes | SHA-256 |
| --- | ---: | --- |
| Native empty SECOND | 10240 | `338487558d9992452db15858de1ba9cf790c26abf990ba70b47bbc9dc8d011f5` |
| Native first SECOND event | 10240 | `b9c9a4cae3cffac1bc337f7b378ea25df74efd3b6771e117c6e0fc3f81b77084` |
| Tool-generated single-calendar month | 8192 | `d35b10c8e8f0b04e41cd6d16a27b9825531353b00ab503e94b7abd3a11499106` |

PERSONAL index page 5 occupies `0x1400..0x17FF`. Four ten-byte routes precede
four 246-byte groups starting at `0x1428`, `0x151E`, `0x1614`, `0x170A`.
Each group has 41 six-byte little-endian `(page, offset, ID)` slots. Both native
files use `[20,21,21,0]`; only the first route is finite. The populated second
and third groups retain sentinel routes. Treating sentinel as empty loses data.
The finite key `8f6b80016801b901bd01` matches the endpoint row's sort-field
prefix. The logical PERSONAL locators and data pages match the month source.
See the [source-backed investigation](calendar-multicalendar-reader-writer.md)
for exact source identities and algorithm limits.

SDK metadata now reports each group's `routing_kind` (`sentinel` or
`endpoint-prefix`) and `endpoint` (last locator's `index_offset`, target
`record_offset`, and table-local `record_id`; null for an empty group).
These fields are derived from already validated locators. They add diagnostic
visibility without decoding K collation or changing record/JSON field values.
An endpoint is local to its named table; IDs are not database-global.

New tests derive endpoints directly from the original A/B bytes, independently
of the production group decoder. Additional synthetic controls repack the same
62 native locators as `[41,21,0,0]`, `[1,41,20,0]`, `[20,1,41,0]`,
`[20,20,21,1]`, `[1,20,20,21]`, and `[1,1,19,41]`, using sentinel routes or
independently constructed finite endpoint prefixes. They verify unchanged
records, order, payloads and ownership, allowing only expected physical index
offset changes. Corruptions at the first and last locator of every occupied
group and every route must fail both the production reader and independent
raw-byte checker. The final layout exercises a full fourth group ending at
`0x17FF`, without requiring a padding locator beyond the page.

These partitions are synthetic regression inputs, not observed native layouts
or a newly qualified writer/balancer. No arbitrary calendar creation, splitting,
rename/delete, active-selection persistence or native save support is claimed.
The existing native specimens justify retaining the current conservative reader;
they do not justify broadening its page, ID or schema limits.

Use a separate Python environment per worktree with the project development
dependencies. Build and install that worktree's wheel before the full suite:
the supervisor's `-I` child imports the installed package and checks hashes of
**all** project Python files. `PYTHONPATH=src` alone does not select its code.
Sharing a different worktree's installed wheel caused an initial isolated-owner
test refusal during this campaign; that failed log is preserved privately.

```powershell
python -m build
python tools/install_wheel.py
python tools/check_install.py
$env:PYTHONPATH='src'
python -m unittest discover -s tests/portable -p test_calendar_multicalendar.py -v
python -m unittest discover -s tests/portable -v
python -m ruff check src tests/portable tools
python -m reuse lint
python tools/audit_repository.py
```

No new binary fixtures are needed; original fixture bytes and provenance remain
unchanged. This follow-up leaves general balancing and full K-field collation
unresolved. The smallest discriminating future control remains an untouched
month-file open/close trial compared with a declared edit/save trial.

Final local validation (Windows 10, Python 3.13.17): 19 focused tests and
437 full portable tests passed; 31 deployment tests ran with two platform
skips. Ruff, REUSE, build, installed-wheel CLI/import checks, independent A/B
validation, repository/package audit and staged diff checks passed. The initial
mismatched-wheel run failed one unchanged isolated-owner test; matching-wheel
focused and full reruns passed. Both logs are retained in the campaign archive.
