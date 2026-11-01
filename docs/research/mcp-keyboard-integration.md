# Keyboard integration and natural date selection — 2026-11-01

## Confirmed correction

The project owner reported that Find Date initially selects the whole existing
date. Recovered private evidence and this sprint independently confirm it:
the initial date is highlighted; a lone BIOS-delivered `1` replaces it; the
remaining seven digits complete the new date without cursor/focus/clearing keys.
October 23 EARLY26 and October 31 Halloween were both accepted and visually
verified. Earlier negative attempts are retained: Home followed by digits left
the filled field unchanged. The contrast supports interference with the initial
selection, but Home alone, Tab alone and each arrow were not separately isolated.

On a fresh emulator/Calendar restart, uninterrupted eight-digit replacements
`10232026` and `10312026` also succeeded. No Home, End, Tab, Ctrl+A or Backspace
was sent after either dialog opened. The previously verified End/eight-Backspace
method remains a fallback for a selection already lost, not the normal recipe.

## Full unfocused operation

A newly launched synthetic Notepad document was positioned in the desktop corner,
leaving DOSBox-X visible. The first bounded Notepad readiness check expired before
its window appeared. One later observation identified the unique synthetic window;
one position/foreground operation succeeded. No host keyboard simulation occurred.

With Notepad foreground, `echo FOCUS26` plus Enter executed exactly once. Calendar
launched, Find Date opened, eight digits replaced the initial selection, and Enter
displayed EARLY26. A second complete Find Date operation returned to Halloween.
All eight input operations recorded the same Notepad PID/window before and after;
the emulator was not activated for screenshots. Full-desktop captures independently
show the active Notepad window and correct guest fields/schedules. The Notepad
document stayed unchanged. This closes the prior character-only focus limitation
for the tested profile and operations, not every application or host policy.

The existing debugger MCP completed a bounded 160-byte read and RUN on each
accepted schedule while the other application remained foreground. Both captures
contain the expected formatted row. Raw bytes/offsets remain private. Immediate
readback can still be transient: an empty BIOS ring is not screen readiness, as
the earlier investigation demonstrated. This sprint does not invent a full screen
buffer, focus schema or universal RAM address.

## Persistent registration versus active tools

The existing Codex config was backed up byte-for-byte privately. A separate
`doslab_keys` stdio entry was appended using the already tested pinned environment,
with only `dosbox_attach`, `dosbox_send_keys`, `dosbox_read_memory`,
`dosbox_sessions` and `dosbox_capabilities`. Every pre-existing parsed setting is
unchanged, including the actual `doslab-dosbox` config entry (normalized debugger
tool namespace `doslab_dosbox`). No arbitrary write, raw-hook or companion tool is
enabled. No dependency upgrade, emulator replacement or native port change occurred.

The persisted config parses, command paths exist, and the same server starts,
reports capabilities and attaches to explicitly identified processes through the
local MCP SDK. **The new tools are not present in this active Codex tool catalog.**
Subsequent-session activation/tool visibility remains to be checked. This is
successful persisted configuration plus local-client validation, not a claim of
using newly registered Codex tools in this chat. The existing debugger tools remain
available. The [public example](../../examples/mcp-keyboard.toml.example) remains
disabled with placeholders; actual paths and config backups stay private.

The configuration fields follow the [official MCP reference](https://developers.openai.com/codex/mcp/).
No authentication or approval-policy bypass was added.

Two recovered one-shot SDK startups failed with BrokenResourceError before any
tool call/key delivery. Their logs and unchanged-state captures are preserved.
There was no blind batch replay. For the continued sprint, a private client keeps
one actual upstream stdio connection, serializes short supervised batches and
retains per-operation raw replies, BIOS snapshots and timing. It uses the same
unmodified upstream implementation at commit
`34c106c1292f99a3f1aebd767147c5bdac7a14de`; no new service or keyboard driver was
created. No measured end-to-end speedup or root cause for startup failures is claimed.

## Procedure and preservation

1. Verify the complete disposable installation and exact process identity.
2. Validate the BIOS queue; serialize short paced upstream send_keys calls.
3. Open Find Date and inspect its whole-value highlight without preliminary keys.
4. Type eight replacement digits directly, inspect the full date, then Enter.
5. Independently verify the schedule. On an ambiguous send failure, preserve state
   and inspect delivery before considering any new input; never replay blindly.
6. Use the clearing fallback only after selection has been lost. Do not assume
   Find Date's behavior applies to Add Event or Address Book controls.

The recovered selection installation and the new focus installation each verified
all 126 before/after file hashes with no content change. All 14 protected original
emulator/profile/debugger executable hash-and-mtime guards passed. Calendar and
both emulator instances exited normally. Original archives and historical evidence
remain unchanged. Private evidence is under DOSLAB
`EXPERIMENTS/RESEARCH/date_initial_selection` and
`EXPERIMENTS/RESEARCH/overnight_sprint/focus`; backups and registration evidence
are in the private sprint root. No screenshots, RAM, databases, original binaries
or machine-specific paths are committed.

Markdown/configuration documentation only: REUSE/SPDX and repository privacy
checks are run before this checkpoint. The unchanged historical suites/builds are
not rerun. E17 is separately authorized and will use its own verified E16 copy;
neither read-only keyboard installation is its starting database.


## Recovery-session registration audit and fresh gate — 2026-11-01

The effective local MCP listing recognizes exactly one enabled `doslab_keys`
registration. Its interpreter exists, module arguments remain `-m dosbox_mcp.server`,
the five-tool allowlist above is intact, and all pre-existing parsed configuration
values are unchanged. The upstream tree remains clean at the pinned commit.
No dependency, emulator/profile, port or configuration change was needed.
The debugger MCP remains exposed and returned PONG plus two successful bounded
memory dumps/RUN operations.

**The active tool catalog in this continued chat still contains no doslab_keys
tools.** The configuration listing alone is not successful registered-tool use.
No host startup/error log was available in the inspected conventional log directory;
there is insufficient evidence to identify the catalog omission's cause. A future
newly loaded host session must expose and exercise the tools before issue #10's
registered-tool acceptance criterion can close. No application restart, package
installation, timeout/configuration change or repeated service troubleshooting was
performed to force activation during research.

A fresh explicit-PID disposable emulator passed the authorized local-SDK fallback
integration gate. Its first client initialization timed out after 30 seconds,
before attachment or any key call; the empty server stderr and failure stage were
preserved. One separately logged startup with a 45-second initialization bound
matching the existing configured bound succeeded. This does not establish that a
Codex timeout caused the catalog omission. No partially delivered input was retried.

`echo GATE19` executed once. Calendar opened, both Find Date dialogs visibly
selected the complete existing value, and direct eight-digit overtyping produced
10232026 and 10312026 without preliminary field navigation/editing keys. Completed
dates were checked before Enter. Screenshots verified EARLY26 at 9–10 AM and
Halloween on their correct dates. Independent 160-byte debugger captures around
physical 0x12640 contain the expected screen text in both states. These reads do
not define a universal screen-buffer schema or imply that a drained key ring is
screen readiness. This fresh test did not repeat the already preserved unfocused
host-window experiment; that earlier result remains evidence, not a new claim.

Calendar and the emulator exited normally. All 126 installation file contents
remained identical and all 14 protected hash-and-mtime guards passed. Complete
source/final inventories, raw replies, failure logs, BIOS bytes, screenshots and
readback evidence remain private under DOSLAB
`EXPERIMENTS/RESEARCH/recovery_sprint_20261101/integration`.
No appointments were edited. The evidence supports reliable local-client operation
for subsequent controlled experiments while registered-tool exposure remains open.
