# Screen-state Phase III: repeated MCP reads and interface-dependent RAM

## Completed and incomplete work

A fresh disposable session completed **30 MCP requests with no timeouts**, including
repeated DOS PING/HELP, two native pause/read/resume tests, Calendar reads, dialog
navigation, clean Calendar exits and restarts. All14 memory reads produced files
of the requested length. The earlier timeout was not reproduced under these
conditions; its root cause remains unknown. No AUTOTYPE was used in this session.

The same160-byte window reproduces a Calendar schedule row and, in Find Date,
two copies of the displayed date. Both interface views reproduce across Calendar
restarts. This is useful partial text observation, not a full screen reader.
The requested **two different schedule dates** remain untested in this run:
bounded date-entry attempts did not visibly change the field. Live E17 was therefore skipped; the optional Address Book survey was not attempted. An independent E17 preflight
and [test plan](../experiments/e17-reuse-plan.md) were completed without creating
application output.

Main was clean before fetch and fast-forward-only synchronization to
1f1142bcf2183f6f87854abcd680a53b2bc9da6f. Work is on
research/screen-state-phase3, with separate tooling, research and application-plan
commits. Prior PR6 and its four passing jobs are owner-reported completed work.
The protected main branch, original profiles, executable, archive and CI settings
were not modified. No PR or merge is performed by this sprint.

## Stalled-state preservation and fresh conditions

The previous disposable instance was preserved first: screenshot, host process
and connection observations, current server log and complete126-file installed
tree. Its ordinary window close did not complete; Windows then showed Not
Responding. A full host-process dump was saved privately before terminating only
that identified disposable DOS process. Calendar had already exited cleanly in
the preceding run. The old436-entry artifact manifest retains its original hash.
No process dump or original executable is redistributed.

A new complete copy of the verified PhaseIII-A installation was used. The existing
server stayed running. Its native port-reporting tool again returned56681; the
temporary SDL1/software profile changes the native port and mounted path and
omits automatic Calendar startup so the DOS baseline can be tested separately.
All rendering and machine settings are inherited. Query the port each session;
56681 is an observed fallback, not a permanent default. Original configuration
and both emulator/server executable hashes and timestamps are guarded.

## Controlled command matrix

| Condition | Observation |
|---|---|
| Fresh DOS, before DeskMate/AUTOTYPE |Two PING/HELP pairs succeeded|
| Native debugger pause at DOS |160-byte read succeeded; RUN acknowledged|
| Resume, second native debugger entry |Second160-byte read succeeded; RUN acknowledged; both dumps identical|
| Back at DOS |Another PING/HELP pair and RUN succeeded|
| Calendar schedule, no navigation |Two160-byte read/resume groups succeeded|
| Find Date and unsuccessful bounded field entry |Read/resume succeeded; no timeout followed the input failure|
| Clean Calendar exit to DOS |Candidate window and two small negative controls read successfully; RUN succeeded|
| Calendar restart |Schedule window and controls read successfully; RUN succeeded|
| Another restart, repeated Find Date view |160-byte read/resume succeeded; dialog window matched its earlier capture|

Native debugger entry was independently visible through the installed window's
DEBUGGER title. Live HELP confirmed MEMDUMPBIN syntax. PONG, HELP, actual dump-file
lengths, raw contents, RUN replies, screenshots and server response logs jointly
establish command handling; a TCP connection alone would not.

The matrix rules out an unconditional DOS-prompt failure. It also shows that the
observed date-entry problem can occur while MCP remains operational. It does not
identify why the previous instance stopped answering, nor prove AUTOTYPE innocent
or responsible. A separate AUTOTYPE test was deferred because GUI field entry was
not sufficiently predictable; the successful fresh-session controls were kept
free of that extra variable. No failed MCP condition was repeatedly retried here.

Earlier logs show requests accepted/forwarded by the server followed by no reply,
disconnect and reconnect; those are neither missing-tool errors nor proof that
the emulator parsed a command. The later host nonresponse supplies a further
observation, not a causal diagnosis. The private process dump is available for a
future narrowly scoped correction if needed.

## Actual targeted-read workflow

After verifying the disposable installation and port alignment, obtain live HELP.
For this investigated region, use MCP debug_exec with:

```text
MEMDUMPBIN 1264:0 A0 <new-private-host-output>
```

All numbers are hexadecimal. The result must contain160bytes covering physical
0x12640..0x126DF, with capture-relative offsets0..159. Preserve those raw bytes
before selecting text. Reject ERR text even when the wrapper's isError flag is
false; verify actual file creation and size rather than trusting a success string
alone. Use debug_run(mode=run) to resume after a successful read and record its
acknowledgement. Preserve state/logs and stop a failing condition after at most
two consecutive failures. No debugger memory writes, patches, stepping, guest-key
injection, new service or external listener is involved.

The improved [offline helper](ram-analysis.md) accepts the physical base of this
short capture, avoiding confusion with an earlier full-RAM file:

```text
python tools/read_ram_text.py <capture> 0x1266e 44 --base-address 0x12640 --physical
python tools/read_ram_text.py <before> 0x12640 160 --base-address 0x12640 --physical --compare <after>
```

It preserves full bounded raw context and all changed bytes, adds size/base/SHA-256
provenance, and reports candidate ASCII without claiming visibility, focus or
screen coordinates. It does not discover addresses or automate an emulator.

## Screen-related observations and negative controls

Every listed view was checked against an independent screenshot. Addresses below
are physical guest RAM, not screen coordinates or stable public interfaces.

| Verified view | Observed text/bytes within the same160-byte window |
|---|---|
| October31,2026 schedule |44-byte `Holiday               Halloween             ` at0x1266E;01 00 at0x1269A|
| Same schedule repeated |Same row and suffix;32 other bytes changed, all within0x126BD..0x126DF|
| Find Date, existing value unchanged |Two10-byte `10/31/2026` copies at0x1264C and0x1266D, each followed by00|
| DOS after clean Calendar exit |Unrelated filename/prompt material;150of160bytes differ from the repeated schedule|
| Schedule after Calendar restart |Entire160-byte window matches the earlier repeated schedule capture|
| Find Date after another restart |Entire160-byte window matches the earlier Find Date capture|

The dialog changes140of160bytes relative to the repeated schedule. At physical
0x1269A..0x1269B it contains **4F 01**, while the DOS capture contains B0 09.
Therefore **0x1269A is not a universal screen-buffer terminator**. The01 00
observation belongs to the limited schedule-row conditions. No meaning is assigned
to4F01, the two date copies, surrounding words or the32 varying tail bytes.

The first125bytes of the two unchanged-schedule captures match; the tail varies
despite unchanged displayed row text. That is evidence against requiring the whole
region to be immutable as a screen-verification signature. No character/attribute
stride, text grid, stable buffer extent, focus flag or widget schema is established.
The region may be reused for text preparation or UI state; that is a hypothesis,
not identification of a complete logical screen buffer.

Two additional bounded controls were read in the dialog, after exit at DOS and
on restart: Halloween plus00 at0xA296 and EARLY26 at0x98BAC remained unchanged.
Neither is proof of visibility: EARLY26 was not shown in these views, and neither
Calendar string was displayed at DOS. This independently distinguishes dynamic
view-associated text from resource-looking or cached strings that survive exit.
The changed candidate window does not recover every visible background label or
all dialog fields. It must not be treated as a screen identity oracle.

The October23 EARLY26 schedule was not reached. Find Date remained10/31/2026
after native paste and a separate direct-key attempt following a field-focus
attempt. Focus itself was not verified or inferred from RAM. The unchanged dialog
was cancelled. No event dialog was edited or submitted. Consequently no conclusion
is drawn about current-value updates after a successful date edit.

## Measured cost and scope

There were30successful MCP requests,14memory reads totalling1,331bytes, and no
read larger than160bytes. Nine read/resume groups succeeded; another resume
followed the DOS HELP checks. One normal targeted observation needs a memory-read
call and a resume call plus local file validation/decoding. Negative controls add
their own7-byte and10-byte reads.

Across the fourteen7/10/160-byte reads, tool elapsed time was4.127–7.694seconds,
median5.415seconds. Server queue-to-response time was29.512–140.752milliseconds,
median54.047milliseconds. These measure different layers and exclude screenshot
interpretation. A160-byte window uses4,096times fewer bytes and one rather than
ten dump commands compared with a640KiB acquisition. Earlier work was batched,
so fewer model-facing tool calls or an overall UI wall-time improvement is **not**
established. Input/navigation delays still dominate this research workflow.

This is one fresh session, not a long-running reliability benchmark. Repeatability
is established for the documented controls and two interface views only. Arbitrary
dates, edited field values, other dialogs/applications and future launches may
move or repurpose the region. Screenshots remain independent ground truth.

## Preservation, verification and next step

All126 research installation files are byte-identical before/after clean Calendar
and emulator exits. All14 original profile/emulator/server guards retain hashes
and modification times. The complete E16 source and separate E17 preparation copy
also match their126-file manifests; no E17 output exists. Raw captures, screenshots,
host dump, full trees, command replies, exact byte comparisons, timings, scripts
and SHA-256 manifests remain privately under DOSLAB
EXPERIMENTS/RESEARCH/screen_state_phase3. E17 preparation is separate at
EXPERIMENTS/PREPARATIONS/E17_reuse. No proprietary evidence enters Git.

The tool's14focused synthetic tests passed during development, and it successfully
analyzed both new captures and preserved PhaseI A/B evidence without modifying it.
Final portable, relevant private, licensing and privacy checks are recorded below.
Calendar production code, schema interpretation, writer bounds, CI/dependencies
and historical fixtures are unchanged. No general allocator or new format was added.

The next useful controlled task is to establish predictable field entry in the
non-editing Find Date dialog on a separate copy. Confirm a changed date through
both screenshot and targeted RAM, then repeat the two-date restart comparison.
Only after that gate passes should live E17 proceed. The original timeout's cause
remains an independent open question; the preserved old process state supports
future investigation without blaming AUTOTYPE from correlation alone.

## Final local checks

* **65 portable tests passed**, once on Windows Python3.13, including the10new
  synthetic tests and four unchanged original helper tests (14focused tests also
  passed during development).
* **Three focused private E16 tests passed** for the exact baseline used by E17's
  offline preparation. New and preserved private RAM captures also passed the
  new helper's extraction/comparison checks.
* REUSE/SPDX, canonical license-text hashes, focused Ruff and repository plus
  existing-distribution privacy/content audits passed. The Calendar runtime,
  format specification, CI/dependencies and proprietary fixtures are unchanged.
* Relevant complete installations and original preservation guards verified.
  Unchanged historical suites were not rerun; packaging and the multi-platform
  matrix were left to CI. No new hosted CI result is asserted here.
