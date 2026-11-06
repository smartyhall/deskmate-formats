# Live RSX/DOS canary observatory validation

On 2026-11-05 in America/New_York, the read-only MCP owner captured the verified
RSX/DOS 5.00 COM checkpoint and published its two approved display artifacts
to the loopback observatory. A line-ending assertion stopped the first
comparison before the final native sample. A separately authorized
completion run on the same emulator process verified the browser projection
and measured **0 ms** of guest advancement and **zero** additional native
connection attempts during refresh. These results cover the live validation
for [issue #39](https://github.com/smartyhall/deskmate-formats/issues/39).

## Reproduction and custody

The [live procedure](86box-observatory-canary.md) describes the operator gates,
allowed native commands, capture formats and browser routes. The experiment
used a fresh writable clone of the sealed Tandy 1000 RSX baseline and freshly
generated canary media. The sealed config, disk, NVRAM and manifest hashes
matched before and after the run. The original canary artifacts and raw
evidence stayed in private storage.

| Component | Verified revision or SHA-256 |
| --- | --- |
| MCP owner and observatory | `782fcc2f92d25846033f55d1da0a1e5e58a40877` |
| 86Box source | `855258da966f1594f568350be59e8e1eca082ed1` |
| ROM checkout | `908394b690f7da28f47727d9876774fd672c4ed3` |
| 86Box executable | `e7e1244588ea721aa239564a43fa2636611ae965ea8431672fdc06d8c12c280d` |
| Sealed baseline manifest | `27847256c686c6c944ba9ea9def8ed7143c76d8a8d8e753d1c14c7f8e8eea11b` |

The canary assembly, generator, COM and floppy hashes matched the
[original experiment](86box-guest-canary.md#original-program-and-trustworthy-construction).
The native build ran visibly with held startup, seed 1 and authenticated
IPv4 loopback. The observer ran on a separate loopback port in the MCP owner.
The validation used Python 3.13.17, MCP Python SDK 2.3.0, Pillow 13.0.0,
Node.js 26.13.0 and headless Chromium 157.0.8103.39 in a private profile.

The launcher's first status request reached its three-second reply timeout
before guest setup began. An operator-authorized read-only check on the same
process confirmed a held, unpaused guest at 0 ms and zero frames. The native
setup then stepped 12,000 ms to the DOS prompt, mounted the canary data floppy,
sent the canary command and stepped a further 3,000 ms. Scheduled key delivery
accounted for 44 ms. The native setup socket closed before the MCP owner opened
its connection. The operator separately approved the two display digests.

## First live comparison

The native setup and MCP group agreed on `tandy1000rsx` under 86Box 7.0, held
and unpaused at **15,044 emulated ms** and frame **1036**. The counters showed
one hard reset, one soft reset and last reset at 613 ms. The complete register
reply, including `CS:IP = 0448:0160`, and the 98 code and 32 data bytes
matched the archived canary reference. The MCP group reproduced the full
canonical transcript and native PNG byte for byte. All seven tools were discovered. Five
were invoked before the stop: instance listing, status, registers, approved
RAM and grouped observation.

| Evidence | Live result |
| --- | --- |
| Browser before the approved display read | Status exposed only public fields, screen and frame were absent, and both image routes returned 404. |
| Browser JSON after the approved read | Matched held flags, guest clock, generation, host observation time, full canonical CP437 transcript and capture timestamp from the MCP group. The frame was the latest render at capture and both render timestamps were unknown. |
| Browser PNG | The re-encoded 720 × 400 PNG matched the visible native RGB pixels composited onto black. |
| Classic GIF | The single 640 × 356 still matched the expected nearest-neighbor resize and palette reduction. |
| Modern and classic views | Each loaded and reloaded three times. All eight captured DOMs matched the expected transcript for their view and loaded the image keyed to that publication. |
| Browser clock and sequence | The first HTTP sample after the reloads still reported 15,044 ms, sequence 5 and the original frame key. This is a measurement of the publication. |
| Native socket audit | The Python MCP owner recorded one connection attempt in total and zero additional attempts during the observed refreshes. The pre-refresh OS TCP table showed one established connection between the owner and emulator. |

| Captured artifact | SHA-256 |
| --- | --- |
| Approved full CP437 transcript in canonical UTF-8 | `ab66c73413b4b042799293ec7ea61acd132ae3cf7298ce7a8fbc53597618350f` |
| Approved native PNG, also returned by MCP | `36ea086aa723538a28a5f7ec7d68219977916d14846614beed155e90d543df9b` |
| Published PNG | `a25cf2b61fcbbbe34a9e9a1a59101d34754da0ae44a85100cd4e23302173da32` |
| Published GIF | `74f0ee7ee6dcc0019df66f2c09f0fff55804d42ab487fbe963aa46740e5ac28a` |

## Comparator failure and correction

After the headless reloads, the harness fetched the plain status and classic
HTML for the first HTTP refresh sample. Its combined assertion normalized
line endings in the plain status and searched the raw classic HTML for an
LF-delimited multiline transcript. The HTTP server emits CRLF in both
responses. An offline check using the captured classic DOMs reproduced the
false negative with the server's CRLF encoding and verified that the
CRLF-delimited comparison matches. The synthetic rehearsal used a one-row
screen, which exercised neither the multiline HTML assertion nor this failure
condition. The harness raised before saving the raw
plain status and classic bodies. The captured classic DOM independently
verified the ASCII transcript and GIF link. The first comparison stopped
before direct plain-status verification finished.

The observation session closed its native socket and HTTP listener. The
emulator stayed running. The interruption occurred before the final MCP
status, register and RAM samples and before the post-refresh TCP table
sample. The browser's unchanged published clock cannot establish the actual
guest-time delta, and the socket audit is scoped to the owner process.

The corrected private comparator preserved raw responses before checking
them. It normalized both ASCII bodies to LF, compared the entire
plain-status transcript including the trailing blank rows and spaces,
and checked the classic HTML transcript, GIF image source and GIF link
separately. An authenticated synthetic native peer supplied a four-row
CP437 fixture with box drawing, an accent, HTML-sensitive characters and
a padded blank row. The old comparison failed against the CRLF wire body.
The corrected checks passed for CRLF and LF. Negative checks rejected
missing screen padding, changed classic text, and incorrect GIF links or
image sources. The production observatory code stayed at the pinned revision.

## Completed live comparison

A separate authorization allowed one new owner on the same process.
Before opening the socket, the harness matched the OS process ID, start
time, session, executable hash and launch arguments against the private
receipts. The new owner verified the held checkpoint, read the complete
register reply and both approved RAM spans against the saved native
capture, and observed the approved display in the same group. It
discovered and exercised all seven MCP tools. The transcript and PNG
matched their approval hashes. Browser JSON, raw plain status, classic
HTML, PNG and GIF matched the approved projection. Both browser renderings
and the three image hashes matched the first comparison.

The browser-only interval ran for **14.408 seconds** on the host clock. The
modern and classic views each loaded and reloaded three times. The harness
also made 12 rounds of direct HTTP reads of the JSON, text, classic HTML,
PNG and GIF. It issued no MCP calls during the interval. The observer's
generation, sequence and frame key remained fixed as the display aged from
fresh to stale.

| Comparison | Before refresh | After refresh |
| --- | --- | --- |
| Native emulated clock | 15,044 ms | 15,044 ms (**0 ms delta**) |
| Native frame count | 1036 | 1036 |
| Native execution state | Held, unpaused | Held, unpaused |
| Native reset counters | 1 hard, 1 soft, last at 613 ms | Identical |
| Full native registers and both approved RAM spans | Archived checkpoint match | Identical to the pre-refresh group |
| MCP owner session and connection generation | One session, connection generation 1 | Same session and generation |
| Browser publication | Generation 1, sequence 5 | Same generation, sequence, frame key and published clock |
| Native connection audit | One initial attempt and one established connection | Zero additional attempts and the same established endpoints |

The final MCP status and grouped register and RAM reads completed before the
owner closed. OS TCP samples showed both sides of the same native connection
before and after refresh. The Python audit counted connection attempts to the
native endpoint within the owner process. It did not trace unrelated host
processes. Native equality refers to the sampled state and the two approved
RAM spans. The protocol cannot establish instruction-precise render timing
or detect transitions that leave no sampled change.

The MCP socket and loopback browser listener closed at the end of the
comparison. The same emulator process remained running, last observed held
and unpaused at the verified checkpoint. The sealed baseline and canary
media hashes matched again. Both runs remain private, including the
completion run's raw wire bodies and artifact manifest. Historical browser
compatibility remains under issue #31.
