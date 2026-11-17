# Bounded Calendar maintenance and native acceptance — 2026-11-17

The new `calendar.maintenance` module provides two opt-in operations for the
measured eight-page, single-PERSONAL month profile:

* `normalize_index(source, experimental=True)` splits `[41,19/21,0,0]` into
  `[20,21,19/21,0]`, preserving every other byte. Already normalized input is
  returned unchanged. Counts include the configuration row: 59 or 61 events.
* `replace_description(source, record_id, description, normalize=False,
  experimental=True)` replaces a printable-ASCII description of exactly the
  existing byte length. It preserves row addresses, lengths, IDs, all other
  fields and all other bytes. `normalize=True` additionally applies that split.

Both validate complete SDK/common structure, exact table/page roles, supported
counts and subdivision occupancies, endpoint routes, counters, schema, ordinary
field encodings and unique date/start keys. Other counts, multi-calendar sources,
retired rows, tied starts, unmeasured routes, full later groups and general
allocation/rebalancing fail closed. This is a bounded structural profile, not
hash-only replay: valid description variants may be edited repeatedly, but new
variants have only offline checks until independently exercised in DeskMate.

The ordinary Calendar prefix fills ten bytes with date, day-of-week, start and
end, before Description. The code additionally verifies that the replacement
cannot change that prefix. Unique date/start keys ensure a description change
cannot change index ordering. The configuration row is never a selectable edit
target. No date/time/alarm mutation, variable-length replacement or overwrite
API is introduced. Source snapshots are immutable; `write_description` uses
exclusive atomic publication to a new path.

## Reproduction and exact identities

```powershell
$env:PYTHONPATH='src'
python tools/experimental/edit_calendar_description.py `
  tests/fixtures/application-generated/calendar/sdk-30-days-allocator-tool-generated.cln `
  NEW-check.cln 77 'Plan 01 / allocator check' --normalize-index --experimental
```

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Original month source | 8192 | `d35b10c8e8f0b04e41cd6d16a27b9825531353b00ab503e94b7abd3a11499106` |
| [Actual tool candidate](../../tests/fixtures/application-generated/calendar/writer-normalized-check-tool-generated.cln) | 8192 | `b0db0f9a8978f37f9996ace0b4d1d2179941d3982ba76fd6c6faf1019cf73402` |
| [Actual native saved output](../../tests/fixtures/application-generated/calendar/native-writer-normalized-final-20261117.cln) | 8192 | `093c8ff83805b658c9b2c71748d85be2b487256db964dfb50a85e818781c915a` |
| Independent saved-installation reopen | 8192 | `093c8ff83805b658c9b2c71748d85be2b487256db964dfb50a85e818781c915a` |

The candidate remains **tool-generated, not application-produced**. Native
acceptance below qualifies this exact candidate and selected event, not every
structurally accepted input. The saved output is the actual application-written
file. Both exact binaries have manifest provenance and REUSE sidecars.

## Serialized native acceptance

All trials used the same pinned 86Box/ROM/hardware and authenticated native
socket guards as the [trigger controls](calendar-index-trigger-20261117.md).
Every launch was visible, started held at 0 ms, and had exclusive ownership on
port 8901. Every clean DOS exit and owned process termination preceded offline
whole-disk copying and independent FAT16/7-Zip extraction. Full original and
before/after installed-tree manifests, configuration/NVRAM and action/capture
receipts remain in private archive `native-index-campaign-20261117`.

| Trial / PID | Native actions | Observed Calendar result | Emulated ms |
| --- | --- | --- | ---: |
| G / 3400 | Fresh clone with candidate; boot/VER, set date/time; launch Calendar; extended Down, Enter; inspect ID 77, Escape cancel, Escape exit, quit | Description `check`, 09:30–10:15, Alarm off; **zero Calendar or installed-file byte changes** | 22684 |
| Gsave / 12244 | Independently fresh candidate clone; same verified detail; type `Plan 01 / allocator final`; inspect all fields; Enter once; observe schedule, Escape exit, quit | **Only five description bytes change on page 7**; index and all other bytes unchanged; only PERSONAL.CLN changes among 143 files | 23588 |
| H / 10184 | Exact copy of Gsave's stopped disk, config and NVRAM; boot/VER, launch Calendar; extended Down, Enter; inspect `final`, original times and Alarm off; cancel/exit/quit | **Zero Calendar or installed-file byte changes** | 21572 |

Total measured elapsed emulated time for acceptance: **67844 ms**; including
the five trigger/timing controls, **162928 ms** across eight sequential processes.
Guest wall-clock delta was not independently measured. No further save in H,
no automatic replay, no host keyboard/mouse injection, no private memory or
commercial binary publication. The [sanitized receipt](../evidence/calendar-writer-maintenance-20261117.json)
records exact before/launch/after config/NVRAM and disk hashes and tree-manifest
hashes; original media/evidence remain unchanged.

Visual scope is the initial October 23 schedule and declared ID 77 detail.
This does not visually inspect every date, fire alarms, test other counts,
qualify general native index propagation or establish arbitrary multicalendar
writing. Native G proves the normalized writer candidate survives an
open/detail/cancel/close unchanged. Gsave/H additionally prove selected native
edit/save/reopen persistence without rewriting that generated index layout.

## Independent verification and limitations

No native output bytes are loaded by the implementation. The raw oracle in
`test_calendar_index_controls.py` constructs the page split from fixed physical
slots and endpoint fields without importing production codecs. It equals both
native open/close outputs. Replacing only the unique ASCII source description
in that independently native-verified page reproduces the complete candidate.
Replacing `check` with `final` reproduces the entire native save and reopen.
The feature also reproduces the earlier native `trial` to `saved` file exactly.

Adversarial tests cover malformed finite routes, valid but unmeasured routes,
interior/foreign/invalid row targets, ID mismatch, holes, count/schema ownership,
full second/fourth groups, off-by-one split boundaries, unsupported files/types,
tied starts, immutable source and existing destination refusal. Every user
appointment in both split/unsplit 59/61-event files is independently edited and
checked against a one-range raw-byte substitution oracle. Those multiple edits
are **offline demonstrations**, not multiple native trials.

## Validation checkpoint

A worktree-specific private Python 3.13.17 environment built and installed this
worktree's wheel before full validation. **454 portable tests passed in
955.778 seconds**; all **91 Calendar tests**, including the two exact
writer-acceptance tests, passed in a final focused run. Ten maintenance tests
passed, including edits to every appointment in
the four supported source layouts. Six opt-in hash-pinned static source tests
passed. Deployment tests: **31 run, two platform skips**. Ruff, REUSE,
wheel/sdist build, installed-wheel imports/CLI checks and repository/package
audit passed. CI results are recorded separately after the final push; local
tests are not represented as GitHub CI.

The frozen private native evidence index contains **2516 files**, SHA-256
`dccfd65c17cf6a0f1628ea4734b3aa24a24b5814b78efa37a8b3ac938925cf74`.
It covers all eight trials' exact starting/stopped disks, extracted installed
trees, actions, observations, launch receipts and config/NVRAM, plus private
experiment/source probes. Validation logs/environments are preserved separately.
The two original source disks, emulator executable and RSX ROM were rehashed
unchanged after all experiments.
