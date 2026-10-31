# Screen-state Phase II: MCP port alignment and targeted-read blocker

## Outcome

The existing MCP connection was corrected without replacing software or modifying
the working profile. PING returned PONG, live HELP returned the installed command
list, and one 160-byte MEMDUMPBIN read recovered the displayed Calendar Halloween
row. **Reliable repeated operation is not established.** Later requests at the
DOS prompt timed out after navigation and AUTOTYPE attempts. The task stops at
that specific blocker rather than claiming a completed stability experiment.

Main was clean before fetch and fast-forward-only synchronization to
dae38c28f4a18ea456f9d52468145dddc92313fa, which includes merged PRs4 and2.
Work is on research/screen-state-mcp. No PR was created or merged; the accepted
setup-python update and prior research were not recreated or changed.

## Connection findings and reproduction

The existing external server executable is version0.1.2. Its MCP port-reporting
tool returned **56681** for native TCP. Process inspection confirmed loopback
listeners56681/56682 belonging to that existing server. The original emulator
profile contains mcp_server=58991; the old emulator occupied that port with a
bound/self-addressed connection, not an external debugger listener. Shared server
logs record default-port-in-use errors10048 and fallback selection of56681/56682.
The exact historical owner at the instant of fallback is not established.

The documented [server architecture](https://github.com/caiiiycuk/dosbox-x-mcp-server/blob/main/docs/ARCHITECTURE.md)
explains that the server may choose an available loopback port and that native
DOSBox-X connects as a client. Query the running server's **native TCP** port,
not its WebSocket port, before starting an emulator. Logs are shared across
server instances, so old successful connections do not prove the current one.

The old emulator was visibly at a clean DOS prompt and closed normally. The
existing server remained running. A complete verified126-file PhaseIII-A
installation was copied to a new disposable directory. A temporary copy of the
SDL1/software profile changed only the native port and mounted disposable path.
The original profile and executable were preserved. The temporary emulator was
then launched after the server. An early PING issued before launch completed
reported disconnected; after the logged connection, PING and live HELP succeeded.
This confirms that neither an absent server, missing tools nor an executable
without this MCP support explained the original port mismatch.

No server install/rebuild/restart, external listener, rendering-profile change or
new middleware was required. All server listeners observed here were loopback.
A legacy console-reading helper returned AttachConsole error6 because the MCP
path had not created a native console; direct guest screenshots still worked.

## The successful read

The independent screenshot shows Calendar's October31,2026 schedule, Holiday /
Halloween. After live HELP confirmed the syntax, the MCP debug_exec tool ran:

```text
MEMDUMPBIN 1264:0 A0 <private-host-output>
```

Arguments are hexadecimal. Segment0x1264 plus offset0 resolves physical0x12640;
length0xA0 is160bytes, ending0x126DF. This span does not cross a16-bit segment
offset boundary. The installed debugger writes raw binary to the specified host
file. Its success reply alone was insufficient: the resulting file was checked
for exact length and preserved before text decoding. A separate debug_run with
mode run returned OK. No debugger memory writes, code patches or guest keys
were used through the debugger.

The file contains the same44-byte formatted row at physical0x1266E as the prior
PhaseI Halloween capture. The adjacent bytes at0x1269A..0x1269B remain01,00.
The entire160-byte region was compared with the prior capture and all changed
offsets/values retained privately. Thus this **one screen** matched across two
emulator launches. It does not prove a universal terminator, fixed grid, character
attributes, screen identity, focus or a stable pointer layout. All160bytes matched the earlier Halloween capture; the adjacent opaque values
remain uninterpreted.

For offline decoding with the unchanged explicit-span helper:

```text
python tools/read_ram_text.py <private-160-byte-capture> 0x2e 44
```

The offset is relative to the bounded file, not an absolute physical address.
JSON continues to label extracted text unclassified RAM text; screenshot checking
establishes its association here. Do not feed a short capture to the earlier
full-RAM absolute-offset example without adjusting its origin.

## Navigation and repeated-read blocker

The planned second date was October23,2026 (EARLY26,9:00–10:00AM). Host function
keys opened the Search menu and Find Date dialog. Native BIOS paste, ordinary
character keys and a temporary switch to keyboard-style native paste did not
produce a visibly changed date. The unchanged navigation dialog was cancelled;
no event dialog was edited. The runtime paste option was restored without saving
emulator settings. One malformed host key-list argument was rejected before input.

Calendar exited cleanly to DOS. The installed AUTOTYPE help was inspected, then
a bounded sequence was queued to open Find Date and enter the navigation date,
stopping before confirmation. The DOS desk calendar command became visible, but
its execution/restart was never confirmed. Further attempts were stopped. These
screenshots must not be mislabeled as a second date or successful restart.

Subsequent targeted requests for the candidate region and two small negative
controls returned request-timeout text. None produced a dump file. RUN timed out
as well. The server log shows requests sent, timeout, disconnect and automatic
reconnect; therefore a TCP connection alone does not establish command handling.
The process still reported Responding=true at the DOS command screen. Whether
internal-shell execution, pending AUTOTYPE/input, debugger polling or another
condition caused this is **unresolved**. Do not assert a process crash or a
general DOS-prompt limitation from this observation. Four failed requests were
recorded; no further retries, service changes or forced termination were made.

The intended current two-date/restart comparison was not completed. Static
Halloween and cached EARLY26 negative controls from PhaseI remain relevant prior
evidence, but were not successfully recaptured here. The known native-debugger
method remains available as documented previously; recovery after this stalled
state was not tested. The disposable emulator is retained for inspection.

## Measured efficiency and limits

* Successful acquisition: one160-byte dump instead of ten65,536-byte dumps
  (4,096times fewer bytes and one rather than ten memory-dump commands).
* MCP read tool elapsed time:4,584ms. The server log measures63.621ms from its
  queued read to response; the larger tool duration includes external overhead.
* Server-side RUN queued-to-response:68.332ms. The logged interval from read
  queue to resume response was7.619347seconds, including time between requests.
* The successful acquisition used two MCP calls (read and resume) plus a local
  file-validation/decode step. Screenshots were independently captured and viewed.
  Earlier ten-dump work was itself batched, so this does not establish a reduction
  in model-facing tool calls relative to either that batch or one screenshot.

There is only one successful sample; no latency distribution, repeated reliability
or overall screen-verification speedup is claimed. Navigation overhead dominated
this run. The targeted read is promising while Calendar runs, but is not ready
to replace screenshots as a reliable autonomous observation mechanism.

## Preservation, checks and next step

The complete source and final126-file disposable installation manifests match
byte-for-byte, including PERSONAL.CLN. All13 guarded original emulator/profile
files retain hashes and modification times. The temporary profile still differs
only in port/mount. No appointments were modified or saved. The final file copy
was taken after verified clean Calendar exit, while the disposable emulator
remained at its unresolved DOS state; it is not an assertion of clean emulator exit.

Raw160-byte capture, previous comparison span, screenshots, all MCP replies and
timings, logs, temporary configuration, actions and full before/after trees stay
privately in DOSLAB under EXPERIMENTS/RESEARCH/screen_state_mcp. No dump, original
software, installed tree or private host path is committed. Runtime/parser/writer
code and the PhaseI helper are unchanged. Portable tests: **55 passed** in one Windows Python3.13 environment, including
the four existing helper tests. The unchanged helper also decoded the actual
160-byte capture correctly. REUSE/SPDX, canonical license hashes and the privacy/
content audit passed. Full CI matrix/packaging is left to Actions.
Historical laboratory suites/manifests are not rerun for this documentation change.

The most useful next bounded investigation is to distinguish MCP command handling
in a paused native debugger from handling at the internal DOS prompt, before any
further AUTOTYPE or date-navigation work. Preserve this stalled state first;
native debugger entry plus one read would test that hypothesis. This was not
performed here. Once command handling is reliable, repeat the two-date Calendar
restart comparison. No E17 or additional format research was undertaken.
