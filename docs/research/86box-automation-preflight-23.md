# 86Box automation: static MCP preflight

2026-11-02; [issue 23](https://github.com/smartyhall/deskmate-formats/issues/23).
Independent source review, with no installation, compilation, emulator launch,
ROMs, guest media, configuration changes or native experiment.

## Version and evidence

Reviewed upstream commit **bc65ce3080df22dacdf78541f6455feb0ed5c446**, dated
2026-11-02, protocol **1**. The
[versioned capability matrix](86box-automation-capabilities.json) records the
exact source URLs, hashes and implementation locations. Sources were recovered
from the interrupted session and verified against their private hash manifest.
The upstream source copies remain private and retain their original notices.
This report and simulator are independently authored.

Evidence labels: **source-verified** means a concrete parser/implementation
branch exists at that revision; **documented** means upstream documentation
says so; **proposed** means local design only; **runtime-verified: none**.
Neither the mock nor this report validates an installed emulator or MCP tool
catalog. No third-party bridge implementation or registration was tested.

The [upstream guide](https://86box.readthedocs.io/en/latest/dev/automation.html)
documents an opt-in source build with AUTOMATION enabled; official builds
should not be assumed to contain it. The pinned
[protocol specification](https://github.com/86Box/86Box/blob/bc65ce3080df22dacdf78541f6455feb0ed5c446/doc/specifications/automation.md)
describes line requests and JSON replies, one client at a time, and a per-run
TCP authentication token. Do not infer build success or availability from the
presence of those instructions. Build prerequisites/host resources remain a
later isolated preflight; this task did not inventory the installing VM.

## Capability assessment

| Required capability | Verified upstream primitive | Limit / consequence |
|---|---|---|
| Hold CPU | `hold`, `release` | Scheduler hold differs from GUI `paused`; inspect both |
| Advance execution | `step <ms>` | Time step, **not one instruction**; `quantum_ms` is 1 or 10, so constrain requested durations to quantum multiples and report actual delta |
| Keyboard | `key down/up` with set-1 codes, E0 encoded with 0x100 | Consumes emulated time; source schedules two-ms gaps, whose delivery must be validated against the active quantum |
| Native framebuffer | `screenshot` with no argument returns base64 PNG | Implementation supports this even though the command table emphasizes the path form; monitor 0's most recent rendered frame can predate the CPU stop |
| Registers | `regs` | CPU-dependent fields and segment caches; reply has no timestamp/held metadata |
| Read memory | `memr addr len [view] [width]` | Source limit 65,536 bytes; default bus view differs from CPU/linear views; mapped device reads can have side effects |
| BIOS text | `text` | Text-mode screen only; not a graphics UI/accessibility tree |
| Exact breakpoint/instruction step | No automation command found | Separate validated GDB stub, or emulator work, required |
| Atomic register+memory+frame snapshot | No combined command found | Wrapper can bracket and reject inconsistency; a true atomic, timestamped response needs an upstream extension |
| Semantic DeskMate UI | No primitive found | Requires independently validated application decoding; a wrapper cannot supply unknown field/dialog semantics |

The implementation returns time/frames/hold fields selectively: `regs` and
`memr` omit them, while `screenshot` includes time and frame count but not held.
Consequently collecting several replies while the guest runs is not a coherent
observation. Use hold and an exclusive session, with status/info before and
after the read group. Reject a change in time, frames, reset counters, mode or
identity. A held framebuffer is still the last rendered frame; matching a
frame counter does not prove that it depicts the exact stopped instruction.

The protocol specification documents GDB-stub coexistence: a debugger stop
can end a timed automation command early with `stopped=debugger`. The source
has that branch under USE_GDBSTUB. Validate breakpoint behavior, address mapping
and CPU-core/build compatibility separately; this review did not establish
GDB's impact on DYNAREC or prove any debugger command on a real instance.

## Proposed MCP contract, version 0.1 (not registered)

Use a separate fixture/profile directory and loopback TCP with its per-run
token on Windows. Bind the transport to an out-of-band launch receipt containing
process lifetime, endpoint, source/build/config/fixture hashes and token-file
identity. Keep that receipt private. `status`/`info` similarity alone cannot
authenticate the right emulator: two instances can report identical metadata.
Do not expose a user-supplied arbitrary endpoint or arbitrary protocol line.

| Proposed tool | Arguments / result | Implementation policy |
|---|---|---|
| `emu.attach` | allowlisted profile ID → opaque epoch/lease, capabilities | Authenticate, check protocol/version and private per-run identity, hold, read reset counters; no guest launch |
| `emu.hold` | lease → observed hold/time | `hold`, then status verification; GUI pause treated separately |
| `emu.advance_ms` | lease, 1..1000 ms → actual delta/stop reason/new epoch | Require held and duration multiple of validated quantum; no automatic retry |
| `emu.key` | lease, down/up, 1..8 validated codes → actual delta/new epoch | Serialize; journal uncertain delivery; input explicitly changes guest state |
| `emu.registers` | lease → registers/mode, bracket metadata | Held-only; validate required fields for CPU profile |
| `emu.memory_read` | lease, approved RAM region ID, offset, 1..4096 bytes → hex/metadata | Reject boundary crossing, MMIO, BIOS/video/ROM ranges unless independently authorized as harmless for the fixture; explicit view `normal`, width 1 |
| `emu.framebuffer` | lease → PNG resource, dimensions, render generation | No-argument screenshot; bounded base64/PNG decoding, private resource storage; never arbitrary host path |
| `emu.observe` | lease, bounded read list, optional frame → grouped observation | Hold, serialized status/info bracket around reads; reject inconsistent group |

Observation tools do not advance time. Do not expose `memw`, I/O access,
reset/media/quit commands, remote listen, raw socket commands or host paths.
Restrict the allowed RAM map to the validated disposable machine, including
separately approved IVT bytes needed by the Calendar experiment. Real-mode
segment arithmetic requires observed mode/base/A20 state; `memr` addresses
are not MZ file offsets.

Every result should state build identity, lease/epoch, request sequence,
emulated time bracket, reset counters and whether data are live or mocked.
No upstream command currently supplies the proposed opaque instance/epoch ID;
the wrapper must maintain it. A malicious or independently controlling peer
cannot be excluded merely by bracketing, so coordinate the GDB and automation
clients under one lease. A true combined snapshot or application event stream
would require emulator instrumentation; DeskMate semantic decoding is separate
research rather than a protocol spelling change.

## Failure and recovery policy

* **EOF, timeout, fatal JSON or malformed/oversized reply:** invalidate lease and
  all observations; close transport. Upstream may have applied a request before
  its reply was lost. Never replay step or key requests automatically. The
  source does not implement an implicit hold on client disconnect.
* **Reconnect or wrong instance:** reauthenticate against a fresh private run
  receipt and recheck status/info. Old epochs cannot be reused. Similar machine
  names, matching registers or matching byte sentinels are insufficient identity.
* **Reset, backward time or stale state:** invalidate all translated addresses,
  symbol mappings, key-state assumptions and observations. Re-establish fixture
  and load-map identity before further reads. Do not reset the guest as automatic
  recovery. Uncertain key-down delivery requires explicit reconciliation.
* **Timing inconsistency:** discard the entire group. UI pause, debugger stop,
  frame-size change and stopped timed commands have distinct outcomes. Do not
  report a requested elapsed time as actual time or treat a sampled memory
  match as an execution breakpoint.
* **No rendered frame:** preserve the error; do not substitute a host screenshot
  or silently run the guest to manufacture a frame. Report unsupported commands
  and capability mismatch without guessing aliases.

Use finite wall-clock timeouts, bounded line/image sizes, a single outstanding
request and explicit private journals. The source supports an unsolicited fatal
JSON line; parsers must handle it even when no request is outstanding. Tokens,
raw register/memory responses and guest screenshots never enter public logs.

## ROM-free mock and validation scope

[automation23_mock.py](../../tools/experimental/automation23_mock.py) models a
strict subset of line/JSON commands with synthetic RAM/registers/image markers.
It has no socket connector, emulator code, SDK dependency, ROM or guest file.
The observation harness is an experimental policy example, not a production
bridge: its SYNTHETIC identity and 64-KiB RAM bounds are fixture conventions.
Its screenshot marker is deliberately not a real PNG. Do not use it as proof
of upstream error strings, rendering, authentication or timing behavior.

Eight portable tests exercise stable held reads, wrong targets, stale epochs,
disconnect/reconnect, changed time/reset state, truncated memory, bounds,
protocol injection, denied writes and ambiguous key delivery. The complete
portable suite remains runnable offline. A later wire adapter must additionally
test TCP fragmentation/coalescing, authentication, oversized/unsolicited JSON,
PNG validation, partial delivery and fatal disconnect using a socket-level
fixture before connecting to a guest.

## First validated-emulator experiment and semantic suitability

First validate the protocol on independently authored boot code that exposes a
known RAM canary and register values, and renders a known pattern. Confirm hold,
actual quantum, input delivery, framebuffer age and reset/disconnect handling.
Record source/build hashes and private fixture identity. Validate GDB execution
breakpoints without software patching before any DeskMate observation.

Only afterward, under separate native-experiment authorization, use the
[Calendar binding plan](https://github.com/smartyhall/deskmate-formats/blob/1a2a1abf75fd8ac3e83677ecbb79c8ee589a0880/docs/research/calendar-binding-25.md): capture the E0 IVT vector,
registers, DMDB name and DS:2A62 before binding, handler entry, return and first
CALLF. Automation can collect held RAM/register/frame evidence, while the
debugger supplies the exact stop. A slot change alone does not identify an
export without target bytes and the loaded-image map. If the debugger cannot
stop exactly, restrict the result to coarse observations and leave the binding
unresolved.

This interface is suitable as an **observation substrate** for semantic UI
research. It supplies stable pixels and bounded memory evidence without host
window-control dependence. It does not identify focused fields, active dialogs,
record identities or menu intent. Existing OCR results remain supplementary;
each future semantic decoder needs independent positive/negative controls and
confidence-labelled outputs. No semantic DeskMate control is claimed here.
