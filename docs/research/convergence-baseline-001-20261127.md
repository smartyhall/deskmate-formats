# Convergence baseline 001 — quiet-host Windows performance characterization

**Status: characterization baseline, accepted by the operator as the initial
laboratory performance characterization. It is *not* an optimization-qualified
baseline.** One acceptance condition in the
[qualification plan](quiet-baseline-qualification-plan-20261127.md) §4 is not
satisfied and one was not recorded in this configuration; the gates are reported
as written, not restated to fit the result. Nothing here is an optimization
claim, a regression, or a statement about DeskMate code.

- Measured revision: `2b3113c15b333f8a0718e353698e427404b2c31b`
- Campaign: `convergence-01` (issue
  [#213](https://github.com/smartyhall/deskmate-formats/issues/213)), provider
  Freebuff, interactive local session
- Measurement date: 2026-11-27, 18:06:50–19:13:21 UTC
- Proposed annotated tag for this baseline: `research-baseline-001` — **proposed,
  not created**. The tag would name the measured revision above, not the
  documentation revision that publishes this record.

## 1. Scope

The checkpoint qualifies one host and one configuration so that later
optimization arms can be compared on the same terms. It records what was
measured, what the harness could and could not prove about the source and the
host, and which findings remain open. It implements no optimization, repeats no
measurement to improve the numbers, and does not execute the deterministic
canary of issue
[#204](https://github.com/smartyhall/deskmate-formats/issues/204).

Paths to the measured checkout, the campaign environment and the private
evidence archive are recorded only in the private campaign record; this document
refers to them as `<checkout>`, `<campaign-env>` and `<private-evidence>`.

## 2. Measured identity

| Item | Value |
| --- | --- |
| Repository | `smartyhall/deskmate-formats` |
| Revision measured | `2b3113c15b333f8a0718e353698e427404b2c31b` |
| Revision context | `main` tip at measurement (merge of PR #210); remote `refs/heads/main` still this commit at 20:05Z, and unchanged when this record was prepared |
| Checkout | `<checkout>`, branch `freebuff/laboratory-synchronization-and-baseline-qualificat`, clean before and after |
| Source completeness | `source.complete: true`, `dirty: false`, `untracked_files: 0`, `untracked_truncated: false`, `source_changed: false`; worktree digest `6e340b9cffb37a989ca544e6bb780a2c78901d3fb33738768511a30617afa01d` (the digest of an empty change set) before and after — identical |
| Package | `deskmate_formats` 0.1.0.dev0, origin `<checkout>/src/deskmate_formats` |
| Package verdicts | `matches_source: true`, `source_on_path: true`, `source_first: false` (structural; §10) |
| Interpreter | CPython 3.13.17 in campaign environment `convergence-01`, executable SHA-256 `4e67d9e9a3673aa7b6219f1280d5ec3f1b6c0d5bd98ea8688c72d0cb7582d664` |
| Environment record | `verdict: qualified`; installed tree digest `9f733f809fa336d23afc4ccc1d2e627b9dd55308ea7b1bce9596d48a47838b34`; provisioning `install_mode: offline`, `index_access: false` (262 files) |
| Preflight | `qualified`, `measurement_allowed: true`, 11 of 11 checks passing, immediately before the recorded run (four separate occasions) |
| Harness | `deskmate_formats.perf` through `tools/test_performance.py`, profile `portable` |
| Harness flags | `--repeat 3 --trace-processes --trace-git-commands --sample-interval 5` (no `--sample-tests`) |
| Workload | 1602 discovered, 1594 executed per iteration; unittest discovery over `tests/portable` |

The harness was invoked through `tools/test_performance.py` rather than
`python -m deskmate_formats.perf` because only the wrapper places
`<checkout>/src` on `sys.path`, which is what makes `matches_source` true for
the parent interpreter. The wrapper is part of the measured configuration.

The revision's own required checks were green before the measurement: `Portable
tests and packaging` (four OS/Python matrix jobs, build, audit, static
analysis), `Reference site preview`, `Publish DeskMate reference`, and the
push-workflow run for `2b3113c` all concluded `success`.

Environment qualification accounted for 16:26–17:36Z; two five-minute quiet
gates were taken at 16:33Z and 17:37Z; a discarded warm-up run occupied
17:44:05–18:06:44Z; the recorded sequence ran 18:06:50–19:13:21Z. No
provisioning, gate or warm-up time is included in any iteration total.

## 3. Laboratory hardware and operating system

| Item | Value |
| --- | --- |
| Platform | Windows 10 Pro 10.0.19045 (SP0), AMD64 |
| CPU | Intel Xeon X5670, 1 socket / 6 cores / 6 logical processors |
| Memory | 8 GiB (8.59 GB visible; 2.35 GB mean available during the run) |
| System volume | 255.9 GB NTFS, 122.6 GB free (47.9 % used) |
| Host character | shared laboratory VM used by other agent sessions throughout; not an idle dedicated runner |

Host sampling during the recorded sequence (5 s interval, 799 samples,
`host_sampling.complete: true`, 0 failures): CPU mean 22.31 %, median 21.86 %,
max 56.49 %; available RAM mean 2.35 GB, min 1.94 GB; processes 205.1 mean /
215 max; threads 1844.6 mean / 1979 max. The elevated mean is the measured suite
itself, not background load. These are host-wide figures, not suite-exclusive.

## 4. Toolchain profiles

| Tool | Identity | Status |
| --- | --- | --- |
| Python | CPython 3.13.17, campaign-owned virtual environment (§2) | qualified for this campaign |
| Git | 2.56.0.windows.2 | qualified |
| Node / npm | v26.13.0 / 11.20.0 | qualified |
| Ghidra, preferred | 12.2, `PUBLIC`, build `2026-Oct-16 1220 UTC`, revision `8ca9077040cc43cd790babcfccf19475622a3e9a`, required Java major 25, selected JDK 25.0.5.1 (Eclipse Adoptium) | `compatible: true`; preferred research release since PR #198 |
| Ghidra, historical | 12.1.4, `PUBLIC`, build `2026-Sep-21 1613 UTC`, revision `8b6bbb857accdfa20dc5b2f5dea471178c2e9fbc`, required Java major 21, selected JDK 21.0.13 (Eclipse Adoptium) | `compatible: true`; retained for reproducing earlier static analyses |
| PyGhidra | 3.2.0 | present only in a private-evidence environment; not part of the qualified campaign environment |
| 86Box | qualified binary `<lab>/builds/86box-automation/src/86Box.exe`, SHA-256 `e7e1244588ea721aa239564a43fa2636611ae965ea8431672fdc06d8c12c280d`, automation `tcp:127.0.0.1:8765 --automation-hold --automation-seed 1` | qualified; 149 machine definitions present |

Both Ghidra profiles are qualified selections, not merely installed directories:
each selection record resolves the installation, its `application.properties`
and a satisfying JDK, and reports `compatible: true` with no selection error.
The install roots are recorded privately; the version, build date, revision and
JDK identity above are the publishable parts.

A separate experimental automation build exists under
`<lab>/builds/86box-automation-idq` (SHA-256
`3e56b6e9b89ac95a555b88ba875614359d63cf432d17a3dd33d2ab5520035fe1`). It
belongs to parked PR
[#193](https://github.com/smartyhall/deskmate-formats/pull/193) and is **not**
promoted by this checkpoint; the qualified `86box-automation` binary above
remains the default.

## 5. Storage and available resources

Allocated bytes under the twelve laboratory roots (read-only inventory, no
deletion or compaction):

| Root | Files | Bytes |
| --- | --- | --- |
| checkpoints | 63 | 21,880,630,451 |
| private-evidence | 278,544 | 18,101,464,648 |
| machines | 1,102 | 11,564,806,037 |
| references | 10,555 | 2,452,400,024 |
| sources | 115,948 | 2,158,366,237 |
| tools | 5,221 | 905,973,944 |
| media | 6 | 657,163,252 |
| builds | 2,837 | 484,104,259 |
| baselines | 8 | 109,071,136 |
| SDK-Uploads | 2 | 42,669,850 |
| downloads | 52 | 2,061,610 |
| archives | 1 | 1,474,560 |
| **Total** | | **≈ 58.36 GB** |

No capacity pressure exists for further baselines or checkpoints: the system
volume has 122.6 GB free. This is guest-visible volume headroom and says nothing
about the ESXi datastore.

## 6. Quiet-host qualification

Each gate is a five-minute idle window sampled every 5 s, 60 of 60 samples
recorded. The provisional plan gate is CPU mean ≤ 20 %, maximum ≤ 50 %, at most
two CPUs of background work.

| Window (UTC) | CPU mean | CPU median | CPU max | Available RAM mean / min | Attributed background CPU |
| --- | --- | --- | --- | --- | --- |
| 16:33:53–16:39:02 | 2.11 % | 1.50 % | 13.82 % | 2180 / 2165 MB | 21.53 s (7.18 % of one core) |
| 17:37:57–17:43:06 | 1.98 % | 1.39 % | 10.97 % | 2224 / 2209 MB | 19.15 s (6.38 % of one core) |

Both windows pass. The dominant background consumer in each was the PowerShell
sampler itself; the remainder was Chrome/Freebuff renderer and Codex/agent
processes. No 86Box, Java, Ghidra or test-suite process was running. The gate
was re-taken immediately before the recorded sequence rather than reused from
the earlier window.

## 7. The three recorded iterations

| Iteration | Wall | Attributed | Unattributed | Parent CPU | Outcomes | Spawns | Git calls |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 1354.418 s | 1351.566 s | 2.852 s | 246.8 s | 1545 pass / 43 skip / 5 error / 1 fail | 11,622 | 10,949 |
| 1 | 1317.602 s | 1316.195 s | 1.407 s | 231.1 s | identical | 11,616 | 10,943 |
| 2 | 1315.580 s | 1314.196 s | 1.384 s | 233.5 s | identical | 11,616 | 10,943 |

- **Suite total** 3987.6 s across 4782 records, 1594 distinct test identities and
  three iterations.
- **Totals** 4635 success, 129 skipped, 15 error, 3 failure, plus 3 suite-level
  errors. 21 of 4806 discovered identities produced no record.
- **Warm-up** (discarded, not part of the totals): 1355.5 s, 1602 discovered /
  1594 executed, the same identity set and the same outcome counts, with
  `source_changed: false`.
- `baseline_exit` was `1` because the suite is not green (the six known
  instrumentation and process-tree outcomes of §9), not because the harness
  crashed. The protocol sequence finished on its own at 19:13:22Z with no
  orphaned process.
- Host sampling was complete for the whole sequence (§3). **Per-iteration host
  means do not exist** because `--sample-tests` was not passed: every per-record
  `host` field is `null`.

### Subprocess statistics

- 34,854 traced spawns across the sequence: 32,835 Git and 1,848 Python.
- Summed process-creation latency 185.5 s, of which Git 157.1 s.
- Summed Git call duration 2673.7 s.

These are **cumulative** figures. Process-creation latency is added per call and
overlapping calls are each counted in full, so neither number is a wall-clock
interval that could be reclaimed, and neither is subtracted from any iteration
total. The exclusive wall time is the iteration wall column above.

The two heaviest tests are `test_supervisor_s2_live` live-CLI (about 121 s per
iteration, 1584 spawns) and `test_supervisor_editing` live-profile (about 103 s
per iteration, 1239 spawns). 282 of 4782 records (5.9 %) hold 80 % of attributed
wall time (3187.1 s).

## 8. Comparability and individual-test variability

`deskmate-test-perf compare` on iteration 0 against iteration 2 reports
**`comparable: true`** with every qualification dimension `matched`: schema (v2),
workload (the same 1594 identities), repetitions, outcomes, interpreter,
platform, source, package, instrumentation and host.

- Delta −38.8 s (1354.4 s → 1315.6 s, −2.9 %). The harness labels this an
  improvement, but **both arms are the same revision with no uncommitted
  change**, so it is run-to-run drift, not a code effect. Iterations 1 and 2
  differ by 2.0 s (0.15 %), so iteration 0 carries a residual ≈2.9 % start-up
  penalty that one warm-up did not absorb.
- The comparison's host dimension is structurally matched, because both
  iterations share the whole-run sampling window; it does not prove
  per-iteration host equality.

Test-level stability over the three iterations (1594 identities present in all
three): median max/min wall ratio **1.071**, p75 1.18, p90 1.65, p95 2.19, p99
5.27. 103 identities vary by more than 2× (almost all sub-100 ms records). 270
identities run ≥ 0.5 s; across those the summed first-to-last delta is −41.3 s,
concentrated in five Supervisor records.

| Test | Iteration 0 | Iteration 2 | Delta |
| --- | --- | --- | --- |
| `test_supervisor_bridge…test_exact_grant_single_dispatch_and_durable_receipt` | 14.0 s | 5.8 s | −8.2 s |
| `test_supervisor_timeouts…test_changed_deadline_invalidates_the_original_exact_grant` | 18.4 s | 11.3 s | −7.1 s |
| `test_supervisor_bridge…test_git_movement_is_inert_and_new_accepted_revision_invalidates_old_grant` | 10.5 s | 6.3 s | −4.2 s |
| `test_supervisor_s2_live.TextDispatchTests.test_faults_are_durable_and_never_replay` | 73.9 s | 81.3 s | +7.4 s |
| `test_supervisor_editing…test_a_checkpoint_without_a_qualified_environment_is_refused` | 10.2 s | 15.0 s | +4.8 s |

No identity changed outcome between iterations.

## 9. Instrumentation-related errors and the Windows process-tree failure

All six non-passing outcomes are pre-existing and were classified individually
before this record was written. None is a performance effect and none was
introduced by the measurement.

**Five `test_perf_harness.RunnerTests` errors and one blocked class.** The five
errors are `test_git_creation_latency_is_separate_from_call_duration`,
`test_git_subcommands_are_counted_when_sampled`,
`test_git_subcommands_are_not_sampled_by_default`,
`test_instrumented_runs_cannot_overlap` and
`test_subprocess_tracing_counts_spawns`. Together with the
`setUpClass (test_perf_harness.ReportTests)` suite error — which blocks that
class's seven members in every iteration — they report:

```
RuntimeError: an instrumented run is already active in this process; the
subprocess and fixture hooks are process-wide and cannot be nested or overlapped
```

The cause is the harness's own process-wide guard in
`src/deskmate_formats/perf/runner.py` (`_claim_instrumentation`). The harness is
being measured while instrumented, so a nested or overlapping claim is refused
by design. The same module is green without instrumentation: 84 tests,
`OK (skipped=1)`, 34.445 s. These outcomes are instrumentation-inherent;
`successful: false` here must not be read as a product regression.

**One deterministic process-tree failure.**
`test_supervisor_process_tree.ProcessTreeTests.test_an_owner_that_exited_still_reports_a_living_descendant`
fails reproducibly, alone, in 0.373 s:
`AssertionError: 'unknown' != 'alive'`. The library returns `unknown` with
reason `scope-loses-orphans`, which is the conservative behavior
[the process-tree observation record](process-tree-observation-20261127.md) §4
documents for `parent-chain` scope losing orphans on Windows. Production
behavior is therefore conservative and safe.

The test expectation is not established as wrong by this run. The failure is
reproducible, but it does not yet show whether the fixture, the assertion, the
implementation or the documented contract needs correction, because the
fixture's actual child lifetime, identity, visibility and parent-chain
relationship were not independently observed. That investigation is deferred and
is not a convergence blocker; it is tracked separately (§14). The assertion must
not be relaxed to accept `unknown`.

## 10. Source-identity and host-sampling limitations

- **`source_first: false` is structural, not a stale install.** The parent
  imported the campaign environment's `deskmate_formats` tree, `matches_source`
  is true, and the campaign preflight proved the tree digest. But
  `src/deskmate_formats/perf/cli.py` deliberately inserts the discovery start
  directory (`tests/portable`) at `sys.path[0]`, and package identity is read
  after that insertion, so the package origin is never "first" on the path. The
  condition was false in all four runs of this campaign. It is unsatisfiable
  under the current CLI discovery path; resolving it is a documentation and
  code decision, not a property of this measurement.
- **Child interpreters are a separate identity.** A child started with
  `python -I` ignores `PYTHONPATH` and resolves from site-packages, and the
  report records only the parent's origin. The plan (§2.2) makes such a run a
  characterization until a child's source is provable. The Supervisor tests in
  this workload spawn child interpreters.
- **No per-iteration CPU qualification.** Without `--sample-tests`, per-record
  `host` is `null`, so the plan's per-iteration CPU-band condition cannot be
  evaluated from this report. The whole-run band in §3 is the available
  evidence, and it is a host-wide band.
- **Instrumentation overhead is not subtracted anywhere.** Traced process
  creation alone accounts for at least 185.5 s of cumulative latency across the
  sequence; the hook bookkeeping cost is unmeasured. Every number here describes
  the instrumented configuration, which any future optimization arm must also
  use to stay comparable.
- **The usual harness limitations apply and are not restated as precision:**
  shared VM; parent-only CPU seconds; summed rather than exclusive subprocess
  durations; process-wide working-set high-water marks; import time outside the
  suite clock; `setUpClass` time inside the clock but outside any test. See
  [the harness report](portable-test-performance-harness.md) §7–§8.

## 11. Acceptance-gate reading (plan §4, unchanged)

| Condition | Result | Basis |
| --- | --- | --- |
| `source.complete`, `untracked_digest` present, not truncated | pass | §2 |
| `meta.source_changed` false; before/after identity identical | pass | §2 |
| `package.matches_source` true | pass | §2 |
| `package.source_first` true | **fail** | structural; §10 |
| Host sampling complete; iteration CPU inside the quiet band, spread ≤ 15 points | **partial** | sampling complete; per-iteration means not recorded |
| Workload identity set identical; no new failure or error | pass | §7, §8 |
| `compare` first vs last, all dimensions matched | pass | §8 |

The gates are quoted as the plan states them. No condition was redefined,
reweighted or moved after the result was known, and the one failing condition was
not renamed into a different requirement.

**Verdict.** Qualified as a **characterization baseline** for this host,
revision, interpreter and instrumented configuration. Not qualified as an
optimization baseline under plan §4 as written.

## 12. What this baseline supports, and what it does not

Usable now:

- Ranking the Pareto set and the Git-call mix (32,835 Git calls, 2673.7 s of
  cumulative Git call duration) — the intended first optimization target.
- Detecting a change larger than about 3 % of suite wall on this host, with the
  same instrumentation and campaign environment, comparing like iteration with
  like (not iteration 0 with iteration 0).
- Deterministic call-count comparisons, which host noise does not affect.

Not usable yet:

- Suite-wide claims smaller than about 3 %.
- Per-test claims for the 103 identities that vary by more than 2× across
  iterations.
- Any claim about tests that rely on child interpreters.
- Cross-host or cross-load-band comparison.
- Any "optimization-qualified" statement, until the open requirements in §14 are
  closed.

## 13. Published evidence and its relation to the private originals

**Published** (`docs/evidence/`, dual-licensed
`GPL-3.0-or-later OR CC-BY-SA-4.0`):

| File | Content | SHA-256 |
| --- | --- | --- |
| `convergence-baseline-001-20261127.public.json` (5,183,304 bytes) | the harness `--public-out` projection of the recorded run: metadata allowlist, environment, host summary/sampling/799 samples, all 4782 per-test records, three suite errors | `69665d67574b6d9d1e7e9ed5d0016434da0d83449a1fab8f49f6df3d46f4525d` |
| `agent-usage/freebuff-convergence-baseline-001-20261127.json` | provider-neutral usage receipt for this campaign | see that file |

The published projection is **byte-identical** to the private projection
(`<private-evidence>/quiet-baseline.public.json`, same digest above), which the
harness wrote from the private report. It was not hand-edited, and it contains no
absolute path, account name or raw process identity: the projection replaces the
interpreter with its file name, reduces the package origin to "recorded", and
redacts free text, and an independent scan of the published bytes finds no
drive-qualified, UNC or home-directory path.

**Retained private and deliberately not published** (`<private-evidence>/convergence-01-20261127/`):

| File | SHA-256 | Why it stays private |
| --- | --- | --- |
| `quiet-baseline.json` (5,184,358 bytes) | `fb8b9da343bf8ad7fcfeca3ff4550a3b47bb014ec52d61b3b6460bcc26be2a4c` | full report: interpreter and checkout paths, raw working directory |
| `quiet-baseline.summary.json` | `3241ad555f947c54abfd26999f3e2a5b5b23eab78a2078ddd23e473ad160be93` | derived summary over the private report |
| `quiet-baseline.md` | `a6bde8dc6e15dcfa8a45efe0b5b782152c2075b3956107b68182835eaaef7752` | markdown summary; duplicates the published numbers |
| `iteration-0.json` | `d0618615f0c6cf6abc975b74be269fbcb4c9565843dc6971045feca3e86b5125` | per-iteration projection derived from the private report |
| `iteration-1.json` | `793783a0f8faf2570833f56f5a2a31411184a7e70027be93da0a1ba895e053e2` | per-iteration projection derived from the private report |
| `iteration-2.json` | `a8a74cddbaa1be27f548a1c1a67966a7a4b3fbf5e70f38cace1c8b83db4d227e` | per-iteration projection derived from the private report |
| `compare-iter0-vs-iter2.json` | `ee40b252615cc086856b44f9d453f887b9be444ba7e648f9cb05ec0a356bee07` | comparability detail; reproducible from the published per-test records |
| `warmup.json` | `700ff712886788747e151593d29d3064c6d26de37e9f7aacb3c7080be8b5452b` | discarded warm-up run |
| `baseline.log` | `d9869f3d5c7c8aa6fba056e6eab2e01bfe1a883c7c40d02cdb21003626611129` | unsanitized console log |
| `protocol-final.out`, `quiet-gate*.csv/.txt`, `environment/`, `toolchains/`, `storage-inventory.*` | — | absolute paths, process inventory and private toolchain roots |

The published projection is sufficient to recompute every per-test aggregate in
this document, to re-derive the comparability verdict with
`deskmate-test-perf compare`, and to check the outcome and host-sampling counts.
The private originals are retained unchanged; this publication neither rewrites
nor supersedes them.

## 14. Outstanding qualification requirements

Optimization qualification (associated with issue
[#147](https://github.com/smartyhall/deskmate-formats/issues/147), tracked in
[#214](https://github.com/smartyhall/deskmate-formats/issues/214)):

1. Nested instrumentation conflicts affecting the five `RunnerTests` and the
   `ReportTests` class setup — the harness cannot measure itself while
   instrumented.
2. The `source_first` acceptance gate and its interaction with unittest
   discovery path ordering.
3. Incomplete per-iteration CPU qualification without `--sample-tests`.
4. Unquantified instrumentation overhead.
5. A matched uninstrumented control run, required before any optimization claim.

None of these is corrected, weakened or worked around in this checkpoint. The
gates stand as written.

Windows process-tree observation (separate, deferred, tracked in
[#215](https://github.com/smartyhall/deskmate-formats/issues/215)): establish the
actual child lifetime, identity, visibility and parent-chain relationship behind
`test_an_owner_that_exited_still_reports_a_living_descendant` before deciding
whether the fixture, the assertion, the implementation or the documented
contract requires correction. The conservative production behavior is preserved.

## 15. Deterministic canary handoff (issue #204)

The operator procedure was prepared in the previous checkpoint; the mechanism is
documented in
[the source-bound execution procedure](source-bound-execution-procedure.md)
("Handoff for issue #204") and is not duplicated here. The operator-facing
sequence is:

1. **Trusted-source acceptance.** A reviewed manifest at
   `ops/tasks/github-hash-canary.json` is accepted through the existing
   trusted-intake commands, against an exact reviewed branch tip. Acceptance does
   not execute.
2. **Exact identities.** Record the accepted revision, the manifest digest and
   the accepted checkout's package tree digest; the plan names them.
3. **Independent expected hash.** Compute the expected SHA-256 and byte count for
   `README.md` from the committed bytes, outside the Supervisor, before dispatch.
4. **Plan preparation.** `prepare-task --environment-campaign
   --environment-checkout …` freezes the plan; review `plan.execution`
   (revision, package digests, interpreter, environment record digest) and the
   plan digest.
5. **Separate operator authorization** of that exact digest, plus the registry
   lease and queue revalidation options.
6. **Single execution** — one `run`, no retry and no replay of an uncertain
   outcome.
7. **Durable result inspection.** Compare `structured_result.files` with the
   independently computed digest and size; check `execution.verified`, custody,
   lease release and `source_revision_after == source_revision_before`.
8. **Sanitized evidence return**: task id and revision, commit, manifest and
   plan digests, expected and observed hashes, terminal state, evidence limits.
   No tokens, raw output or private paths.

`hash-files` is a controller procedure: the canary proves intake, planning,
binding, lease and result return, and executes reviewed script text over accepted
bytes. It does **not** prove workspace-import qualification; a canary that
imports the checkout would use `repository-audit` or `portable-tests` and needs
the qualified environment of §2.

This checkpoint does not submit, accept, prepare an actual attempt, or execute
the canary. It remains unexecuted and separately authorized.

## 16. Baseline identity

| Item | Value |
| --- | --- |
| Proposed annotated tag | `research-baseline-001` — **proposed, not created** |
| Measured revision | `2b3113c15b333f8a0718e353698e427404b2c31b` |
| Documentation revision | any commit after the measured revision; the documentation changes in this record and the reconciled status documents were **not** present during the measurement and are not part of the measured identity |
| Baseline class | characterization, not optimization-qualified |
| Evidence | §13 |

The tag, when the operator authorizes it, must name the measured revision, not
the merge commit of this documentation. Re-running the measurement on a later
revision produces a different baseline and a different identity.

## 17. Non-goals

- No optimization implementation, no Git subprocess batching.
- No second baseline, and no relabelling of this one as optimization-qualified.
- No tuning of the harness, its expectations, its timeouts or its dependencies
  to make the suite green.
- No change to shared Python installations, no promotion of the parked
  experimental emulator build.
- No execution of the deterministic canary.
- No claim that this host, this band or these tests generalize to another
  machine or another load condition.

## Related records

- [Quiet-host baseline qualification plan](quiet-baseline-qualification-plan-20261127.md)
  — the protocol and §4 gates read above.
- [Portable test performance qualification harness](portable-test-performance-harness.md)
  — what each recorded quantity is and is not.
- [Windows test performance under concurrent load](windows-test-performance-20261126.md)
  — the earlier loaded-host observations, preserved as observations.
- [Process-tree observation semantics](process-tree-observation-20261127.md)
  — the contract the failing test contradicts.
- [Campaign Python environment isolation](campaign-python-environment-isolation-20261127.md)
  — the qualified environment used here.
- [Source-bound execution integration guide](source-bound-execution-procedure.md)
  — the canary mechanism.
- [Campaign inventory](campaign-inventory.md) — planning status after this
  checkpoint.
