# Ghidra integration and historical binary analysis — qualification results

Campaign `fb-ghidra-20261126`, Freebuff, 2026-11-26. Base commit
`3d3f78471ec8832f944baa4d12102fe1ed508305`, branch
`freebuff/ghidra-integration-and-binary-analysis`. Offline static work only:
no emulator, no guest, no graphical session, no additional model provider.
The [procedure document](ghidra-dos-binary-analysis.md) carries the reusable
method; this report carries the findings.

Confidence marks follow project convention: **H** original bytes, arithmetic
or reproduced tool output; **M** functional interpretation; **U** unresolved.

## Installed environment, as observed

| Component | Installed | Evidence |
| --- | --- | --- |
| Ghidra | 12.1.4 PUBLIC, build 2026-Sep-21 1613 UTC, revision `8b6bbb857accdfa20dc5b2f5dea471178c2e9fbc` | `Ghidra/application.properties`, `GHIDRA_INSTALL_DIR=C:\tools\ghidra_12.1.4_PUBLIC` |
| Java | Eclipse Temurin 21.0.13+9-LTS; Ghidra requires 21 | `java -version`, `application.java.min=21` |
| PyGhidra | 3.2.0 (installed into a campaign-local virtual environment) | import in the campaign interpreter |
| Python | 3.13.17 | `sys.version` (Ghidra supports 3.9–3.14) |
| Independent decoder | Capstone 5.0.7 | `capstone.__version__` |
| Existing Ghidra material | `tools/ghidra/CalendarBinding25.java`; private projects under `private-evidence/calendar-editor-20261105/ghidra` and `private-evidence/typography-20261119/ghidra` | read only; neither private project was opened |

Provisioning records and the installation agree, but this report takes the
installed files as authoritative. No Ghidra component was installed,
upgraded, patched or extended. The private virtual environment lives in the
campaign directory, not in the repository and not in a shared path.

## Interface qualification

| Interface | Result | Notes |
| --- | --- | --- |
| `analyzeHeadless` (batch analyzer) | **Qualified** | Import, `-processor`, `-loader BinaryLoader -loader-baseAddr`, `-noanalysis`, `-scriptPath`, `-postScript`, `-preScript`, `-analysisTimeoutPerFile`, `-max-cpu` and `-readOnly` are present in the installed usage. Two runs completed: a raw-payload import plus `BoundedDecode.java`, and a raw-payload import plus the existing `CalendarBinding25.java`. |
| PyGhidra 3.2.0 | **Qualified** | Program import with an explicit language, project creation and reopening, memory-block inspection, relocation table read, bounded decode through `PseudoDisassembler`, and structured JSON export. Recorded below. |
| Existing Java scripts | **Qualified** | `CalendarBinding25.java` ran unmodified against a payload imported at `1000:0000` and reproduced its documented windows. |
| New Java script | **Qualified** | `tools/ghidra/BoundedDecode.java` (new) ran as a post-script with arguments and printed bytes plus text for arbitrary file windows. |
| Python scripting inside Ghidra | **Qualified indirectly** | The same capability was exercised through PyGhidra's API rather than a `.py` script file. Ghidra ships `Ghidra/Features/PyGhidra` with `PyGhidraBasics.py`; a `.py` script file was not run in this campaign. |
| Project persistence | **Qualified** | Import → save → close → reopen in a **separate process** reproduced the program, its language, its address range and all nine memory blocks. |
| Analysis | **Qualified in a bounded run** | `--analyze` is opt-in in the driver and was exercised on the 1.1 KB `DMDB.R89`; autoanalysis on the larger applications was not run because no claim here needs it. |
| Timeouts and cancellation | **Bound only by the parent** | A per-stage subprocess timeout exists in the driver and `-analysisTimeoutPerFile` exists in the analyzer. Actual cancellation of a running JVM analysis was not exercised. |
| Read-only processing | **Qualified** | The two batch runs used the raw-binary loader on stripped payloads in disposable projects; no original was opened for writing and no program bytes were modified. |
| Interrupt recovery | **Not qualified** | An interrupted import was not produced deliberately. Earlier campaigns recorded import attempts that timed out; this campaign did not repeat that experiment. |
| Concurrency | **Qualified at the directory level** | Ghidra locks a project: two processes cannot open the same project. The driver therefore requires an owned project directory; concurrent analysis of *separate* projects is the operating model. A concurrent two-project run was not measured in this campaign. |
| Interactive GUI | **Not qualified** | Ghidra's UI is a native window. This agent has no non-disruptive capture path for native windows, and host keyboard/mouse injection into the operator's session is prohibited. Launching a window that cannot be observed would produce no evidence. The programmatic interfaces cover the same read operations. |

### What the PyGhidra work established

* `pyghidra.open_project()` returns a **temporary or read-only** project.
  `createProject(locator, None, False)` and `openProject(locator, False,
  False)` give a writable, persistent project. This was found by experiment
  after a `ReadOnlyException` on save.
* `Program.save()` raises `ReadOnlyException` on an unmodified program.
  Persistence belongs to `LoadResults.save(TaskMonitor)` before
  `results.release(consumer)`.
* The loader holds the program through a consumer the caller cannot name, so
  the driver creates its own consumer and passes it to
  `getPrimaryDomainObject(consumer)`.
* An in-process reopen after `close()` still fails with `LockException`, so
  the reopen check runs import and reopen as separate processes. Reopening a
  project whose lock this run created also required clearing that lock; a
  pre-existing project is never touched.
* Timings on Windows for `DESK.EXE` (19,047 bytes): JVM start 8.3–9.0 s,
  import 1.4–2.1 s, save 0.3–0.5 s, reopen in a fresh process 11–16 s.
  Import is not the expensive part; JVM lifecycle is.

### Optional integration mechanisms

A Ghidra MCP bridge is **not required** and was **not installed**. The two
capabilities an agent normally wants from one — a stable tool surface and a
way to drive analysis without the GUI — are already provided here by
`analyzeHeadless` and PyGhidra, with no listening socket.

Public information about the main bridges, for future coordination:

* `LaurieWired/GhidraMCP` and `bethington/ghidra-mcp` are Apache-2.0 Ghidra
  extensions that embed an HTTP server in Ghidra and expose it through a
  Python MCP bridge. Their 2.x/7.x lines target Ghidra 12.1.4 and Java 21.
* A public security audit of an early `GhidraMCP` release reported an
  unauthenticated HTTP server bound to all interfaces, including write
  endpoints, together with prompt-injection and comment write-back findings.
  Maintainers of the actively developed fork state that authentication, bind
  hardening and SSRF hardening followed. Any future adoption must verify the
  actual version in use rather than the changelog.
* Every bridge adds a local network port and, in the usual configuration, a
  path by which binary content and analysis output reach a model provider.

The last point is decisive for this project: bridge adoption would transmit
private commercial analysis content to an inference service, which the
campaign is not authorized to do. The provider-neutral command-line tools are
the supported path.

## The 8E segment-MOV display anomaly, resolved

The prior review recorded a display-versus-semantics discrepancy for opcode
`8E` in the installed x86 language. It is confirmed, at
`Ghidra/Processors/x86/data/languages/ia.sinc` lines 4012–4014
(`ia.sinc` SHA-256 `5112439554604933fb7f5d1afc123c0517727d4583c18bf795d0c49b66dd1570`):

```text
:MOV Sreg,m16    ... byte=0x8e; (mod != 3 & Sreg) ... & m16  { Sreg = m16; }
:MOV Rmr16,Sreg  ... byte=0x8e; mod=3 & Rmr16 & Sreg          { Sreg = Rmr16; }
```

The **p-code is correct**; the **display template is reversed**. Scope and
consequences, now established by direct experiment on one program:

| Bytes | True meaning (Capstone 5.0.7) | Ghidra 12.1.4 listing |
| --- | --- | --- |
| `8E D8` | `mov ds, ax` | `MOV AX,DS` |
| `8E C3` | `mov es, bx` | `MOV AX,ES`-shaped, i.e. general register first |
| `8E C0` | `mov es, ax` | `MOV AX,ES` |
| `8E 1E 10 00` | `mov ds, [0x10]` | `MOV DS,word ptr [0x10]` (memory form is correct) |
| `8C D8` | `mov ax, ds` | `MOV AX,DS` (correct) |

The dangerous case is `8E C0` beside `8C C0`: both list as `MOV AX,ES`, and
they mean opposite things. The campaign observed exactly this pair inside one
window of `DESK.EXE` — `FILE=37b5` (`8E 1E 10 00`), `FILE=37c1` (`8C C0`) and
later the bootstrap `FILE=4269` (`8C CE`) — so a reader following listing text
alone would invert the vector-installation logic.

Scope: the register form (`mod=3`) of `8E` in 16- and 32-bit operand size, and
the 64-bit form under long mode. Not the memory form. Not opcode `8C`. It is a
**display defect**, so decompiler output and p-code are unaffected, but any
hand transcription from a listing is unsafe. The correct workaround costs
nothing: read the opcode byte. `tools/inspect_dosimage.py disasm` prints the
original bytes for exactly this reason, and `BoundedDecode.java` does the same.

No language file was patched. A local patch would make our listings
irreproducible against a stock installation, which is worse than the defect.
Ghidra 12.2 corrects it in the shipped release (GP-7279); the 12.1.4 text in
this table is the historical observation, and the 12.2 re-run plus the
assembler and operand-indexing consequences are recorded in
[`ghidra-12.2-qualification-20261126.md`](ghidra-12.2-qualification-20261126.md).

## Independently reproduced observations

Every input hash matched the published identity. `H` marks the reproduced
byte-level results.

| Observation | Published | Reproduced |
| --- | --- | --- |
| `DESK.EXE`, `CALENDAR.PDM`, `DMDB.R89`, `DMDBRD.RES`, `ADDRESS.PDM`, `FILER.PDM` SHA-256 | see prior reports | all six match exactly (H) |
| MZ relocation counts: `DMDB.R89` 11, `DMDBRD.RES` 21, `DMDBBLD.RES` 4, `DMDBUPD.RES` 4, `FILER.PDM` 25, `FORMSET.PDM` 25 | database component review | all six match (H) |
| Calendar binding sequence at file `D7E5–D802` | `ES=DS`, `BX=2A62`, `DX=2944`, selector `0206`/`020C`, `INT E0` at `D800`, `RET` at `D802` | identical, from Capstone **and** from Ghidra's own decoder (H) |
| Calendar selects `020C` for signed `AX > 0`, else `0206` | reported | identical: `OR AX,AX` / `JG` / `MOV AX,0206` / `JMP` / `MOV AX,020C` (H) |
| Shared DMDB thunk shape in three applications | `CALLF [DS:slot]` at `DEAD`/`741B`/`A9C7`, slot `2A62`/`0FA6`/`29C4` | identical: `PUSH BP`, `MOV BP,SP`, `PUSH ES`, `PUSH BX`, …, `MOV BX,BP`, `ADD BX,4`, `LCALL [slot]` (H) |
| DMDB name data at `DS`-relative `2944`/`0E88`/`28A6` | file `113B4`/`95F8`/`E676` via the conditional DS bases | all three are the literal `DMDB` followed by NUL (H) |
| Six DMDBRD schema descriptors at `50E0`, `9`-byte stride, relative base `5080` | `cname/80/C`, `owner/80/C`, `pos/4/N`, `len/4/N`, `type/1/C`, `uniq/1/N`, `DBCOLS` at `5116` | all six names, widths and type bytes resolve exactly; `DBCOLS` at `5116` (H) |
| Draw static offsets `7BA3`, `7BD8`, `9467`, `960E` | group accessor, recursive caller, UA/UP dispatch, UA transform | all four decode to function entry or dispatch code; `9467` compares `[BX]` with `55h 'U'` then `[BX+1]` with `41h 'A'` (H for bytes and comparison, M for the roles) |
| Ghidra 12.1.4 segment-MOV anomaly | display reversed, semantics correct | confirmed from source, bytes and live listings (H) |

Two results are new rather than reproduced:

1. **Ghidra's 16-bit MZ block model is fully explained.** One block per loader
   segment, then a backward far-return scan that moves each split point
   forward. `MzImage.loader_blocks` reproduces all six `DESK.EXE` blocks and
   their sizes exactly. The practical consequence is that the segment prefix in
   a Ghidra listing is a loader artifact, not program structure. See the
   [procedure](ghidra-dos-binary-analysis.md#reproducing-ghidras-memory-blocks).
2. **The relocation-table site is not the relocated segment.** `DESK.EXE`'s
   entries sit in segments `033B`/`0355`/`0405`/`0456`, while the words they
   adjust name `0000`/`033B`/`0355`/`03F5`/`0405`/`0456`/`058A`. Reading the
   site segment as a code segment is a modelling error that the new tooling
   reports separately (`relocation_site_segments` versus `relocated_segments`).

## Historical executable support

| Format question | Result |
| --- | --- |
| DOS COM | Parsed as a raw image with `IP = 0100h`; `identify`, coordinate mapping and a single-block model implemented and tested. A COM carrier of the DOS 3 EXE format is explicitly not claimed. |
| DOS MZ | Header, declared versus stored size, relocation table, entry arithmetic, overlay bytes and far-pointer classification implemented. Malformed headers are rejected rather than repaired. |
| 16-bit segmented addressing | Four coordinate systems implemented with explicit conversions; the CLI labels every result by kind. |
| Relocation tables | Two distinct segment notions separated, as above. |
| Far pointers | Resolved only when the segment word carries a relocation; otherwise reported as unresolved with a reason. |
| Segment-register behaviour | Documented and worked around at the decoder boundary; original bytes are always reported. |
| Overlay structures | Declared-versus-stored size and trailing bytes are reported. No overlay extraction or interpretation is implemented, and no DeskMate overlay was identified. |
| DeskMate-specific components | `.R89`, `.RES` and `.PDM` files that carry `MZ` signatures are ordinary MZ images; the extension does not determine the loader. A `DM89` marker at file `0x28` was observed in the repair and conversion utilities as well as in the applications. |
| Loaders and dynamic service interfaces | Unchanged from the prior conclusion: the `INT E0` binding is statically visible, its runtime implementation is not. Nothing in this campaign narrows that edge. |
| Code and data sharing | The identical thunk shape in three applications and two utilities is evidence of a shared *calling* convention; it is not evidence of shared storage code. |

No custom loader extension was written. The observed images are all standard
MZ or raw payloads; adding a loader would have been speculative support without
a representative format that needs it.

## Reusable tooling

| Artifact | Purpose |
| --- | --- |
| `src/deskmate_formats/dosimage.py` | Standard-library COM/MZ parsing, four-coordinate conversion, far-pointer classification, loader-segment and loader-block models. No third-party dependency. |
| `tools/inspect_dosimage.py` | CLI: `identify`, `blocks`, `map`, `far`, `disasm`. JSON output with input hash; refuses a decode rather than guessing when no independent decoder is installed. |
| `tools/ghidra/ghidra_dos_import.py` | Provider-neutral PyGhidra driver: explicit language, optional analysis, `LoadResults` persistence, fresh-process reopen check, JSON receipt with per-stage timings. |
| `tools/ghidra/BoundedDecode.java` | Read-only bounded decode of explicit file windows, printing original bytes; usable as a pre- or post-script. |
| `tests/fixtures/synthetic/dos_images.py` | Deterministic synthetic MZ and COM specimens with known instructions, relocations, a far return at a segment start and an embedded string. |
| `tests/portable/test_dosimage.py` | 24 portable tests over the library and CLI; no private binary, Ghidra or emulator required. |

The deterministic/interpretive split is enforced by output shape: the tools
report structure and never name a routine's purpose. Interpretation stays in
research prose with its confidence mark.

## Deterministic integration for the Supervisor and Observatory

A Ghidra import is a good fit for a named deterministic task because it is
reproducible, expensive, cacheable and produces a hash-addressable artifact.
The candidate definition is `ops/tasks/ghidra-dos-import.json`, which follows
the existing task schema. The interface it implies:

| Concern | Contract |
| --- | --- |
| Input identity | Absolute path plus SHA-256 of the stored image; the receipt records size and hash before analysis. |
| Tool identity | Pinned Ghidra version, build date and revision from `application.properties`; Java runtime string; PyGhidra version; processor language id. |
| Project ownership | One project directory and name per run; Ghidra locks a project, so a second process cannot open one already in use. A Supervisor task must be given a fresh directory or a project it exclusively owns. |
| Analysis configuration | Language id is mandatory and recorded as resolved by Ghidra, not as requested. `--analyze` is a separate, explicit step. |
| Limits | Per-stage subprocess timeout; `-analysisTimeoutPerFile` for the batch analyzer; `-max-cpu` to bound cores. Memory limits are not exposed by the driver. |
| Cancellation | Terminating the process tree is the only supported cancellation. It leaves the project in an unknown state and must be treated as a failed run, not a partial success. |
| Progress events | Stages `jvm_start`, `import`, `autoanalysis`, `save`, `reopen_check` with seconds each; a Supervisor adapter can map these to events as they are emitted. |
| Artifact provenance | Receipt JSON plus the project directory. Both stay private; only sanitized summaries are publishable. |
| Caching | Invalidate on input SHA-256, language id, Ghidra revision or script hash. Any of those changing makes a cached result unusable, and a receipt that omits them cannot be cached. |
| Review | Inferred findings are never auto-accepted. A task may publish structure; a human or independent reviewer accepts an interpretation. |

For the Observatory, the useful fields are the specimen name and hash, the
current stage, elapsed seconds and warnings. A representative visual is not
available from the headless path — there is no rendered view — so an observer
should show the block table and the stage timeline rather than imply a screen.

## Limitations and unresolved questions

* **Interactive GUI operation is unverified.** No supported capture path
  exists for this agent, so the navigation, decompiler-view and annotation
  questions in the campaign brief are answered for the programmatic
  interfaces only.
* **Autoanalysis was bounded.** It ran on a 1.1 KB stub. Function and
  cross-reference counts on the applications are not qualified, and no
  decompiler output was reviewed.
* **Interrupted-import recovery was not tested.** The driver's failure mode
  (process killed) leaves an owned project that must be discarded.
* **Concurrency was not measured.** The locking rule is documented, not
  benchmarked.
* **`INT E0` runtime binding remains unresolved**, exactly as before. The new
  utilities add selector values `0207` and `0208` in the same register shape
  as `0206`, which widens the vocabulary but does not identify the handler.
  See the [utility analysis](historical-utility-analysis-20261126.md).
* **No MEMORY limits, no progress stream.** Events are emitted at stage
  boundaries only; there is no live progress channel from a running analysis.
* **Visual exemplars: not applicable.** This campaign produced structure,
  receipts and instruction text, not eligible imagery. No screenshot was
  fabricated or substituted; see the GUI limitation above.

## Reproduction

Portable checks:

```text
python -m unittest discover -s tests/portable -p test_dosimage.py -v
python tools/inspect_dosimage.py blocks CALENDAR.PDM
```

Private evidence for this campaign is under
`C:/DeskMateLab/private-evidence/ghidra-integration-20261126`: the campaign
registry, receipts, reproduction and utility JSON, the owned Ghidra projects,
the extracted `MzLoader` source read for the block model, and the stripped
payloads. None of it is published. Original images were read from
`C:/DeskMateLab/references/oldskool` and never modified.
