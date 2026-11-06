# Read-only 86Box browser observatory

For planned agent activity telemetry, LAN viewing and read-only operations,
see the [Observatory v2 specification](observatory-v2-spec.md). The separate
[Codex supervisor proposal](codex-supervisor-design.md) covers privileged
work scheduling, managed turns, and Git checkpoints; those actions are never
part of this browser interface.

The observatory displays observations explicitly approved by the owner of an
86Box automation connection. The native MCP service can host the observer in
its process. The standalone demo supplies synthetic observations for local
testing.

~~~mermaid
flowchart LR
    E[86Box] <-->|one authenticated socket per instance| H[Native MCP owner]
    H -->|approved display and status| P[In-memory publication]
    D[Synthetic demo] -->|fictional fixtures| P
    P -->|immutable latest view| W[Loopback HTTP observer]
    W --> M[Modern dashboard]
    W --> L[Classic HTML / GIF / text]
~~~

## Run the synthetic lab

From a checkout with Python 3.13 or newer, install the optional image extra and
run the demo in a foreground terminal.

~~~console
python -m pip install ".[observer]"
deskmate-86box-observer --instances 3 --interval 2 --port 8086
~~~

Open [the modern dashboard](http://127.0.0.1:8086/) or
[the classic page](http://127.0.0.1:8086/legacy/) on the same host. Stop with
Ctrl+C. The command closes the listener, joins the HTTP workers, and stops the
synthetic publishers. Select a different local port if 8086 is occupied. Port
0 requests an ephemeral port and prints the selected address. One machine is
the default. Each station in the three-machine demo has its own clock,
generation, timeline, display, and connection state.

The base package uses Python's standard library. It can serve status and text
with `python -m pip install .` and `deskmate-86box-observer --text-only`. The
optional `observer` extra adds Pillow `>=13.0.0,<14` for PNG decoding, GIF encoding,
and synthetic raster generation. Pillow 13.0.0 declares MIT-CMU in its wheel
metadata. Its license and fonts stay with the Pillow distribution.
[Pillow license](https://pillow.readthedocs.io/en/stable/about.html#license)

The fixture cycles through independently authored firmware, a DOS-style
prompt, diagnostics, a boxed result, and a simulated disconnect. The demo
starts no emulator and opens no native connection. Each fictional cycle
advances the published guest clock through 0, 1,200, 4,250, and 7,330 ms, then
keeps it at 7,330 ms during disconnect. The last frame reports 7,290 emulated
ms to exercise separate guest and render times. Only the synthetic publisher
moves this clock. HTTP requests can sample the same state repeatedly.

## Publication API

Create a registry with one to eight explicitly configured `Machine` identities.
The first machine is the default. A producer owns the sequence for each
`ObservationStream` and publishes immutable, typed `Observation` objects.
This example uses synthetic text.

~~~python
from deskmate_formats.observer.http import ObserverServer
from deskmate_formats.observer.publication import (
    Action, Machine, Observation, ObservationRegistry, decode_cp437, host_time_ms,
)

registry = ObservationRegistry(
    [Machine("fixture", "Synthetic station")], history_limit=24, stale_after=10,
)
stream = registry.stream("fixture")
stream.publish(Observation(
    instance_id="fixture",
    sequence=0,
    generation=0,
    observed_at_ms=host_time_ms(),
    emulated_ms=1200,
    held=True,
    paused=False,
    action=Action.OBSERVE,
    milestone="Prompt ready",
    screen=decode_cp437([b"LAB DOS", b"C:\\>"]),
))

with ObserverServer(registry, port=8086) as server:
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
~~~

For an embedded listener, run `serve_forever()` in a dedicated thread. Stop it
with `shutdown()` from another thread, join that listener thread, and call
`server_close()` or exit its context. The listener accepts only IPv4 loopback.

- `sequence` strictly increases per instance, including across generation changes.
  Increment `generation` when reset, relaunch or reconnect breaks continuity.
  The guest clock can start again at a lower value in a new generation. The
  registry also assigns an opaque publication session ID when it creates a
  stream so frame links from a previous service process cannot match.
- `observed_at_ms` is UTC host time in milliseconds since the Unix epoch.
  `emulated_ms` is the sampled guest clock. `held` and `paused` are booleans
  while connected and become unknown on connection loss. Host time used to
  serve the HTTP reply is a separate field.
- `Action` and `ErrorCode` are fixed vocabularies. `milestone` is a short,
  independently authored checkpoint label. `dropped_updates` is cumulative
  across generations and supplied by the producer, which knows how many
  updates it skipped or coalesced.
- Attach `Frame(approved_png, generation=…, captured_at_ms=…)` from
  `deskmate_formats.observer.frames` only after explicitly approving those
  pixels. Frame generation increases for a new still within a session/reset
  generation. Reuse the current immutable `Frame` object when publishing a
  status-only update that keeps the display. Frame timestamps may include
  `rendered_at_ms` in UTC host time and `rendered_emulated_ms` when known.
  Frame age uses host render time when available and is explicitly measured
  from capture otherwise. Leave unknown timestamps unset.
- Pass decoded, approved display text in `screen`. `decode_cp437()` accepts
  rows of display character bytes up to 132 columns by 60 rows. It handles
  CP437 box drawing, accents, and low-byte display glyphs.
- Omit screen or frame on a new observation to withhold the corresponding
  display. Call `mark_unavailable(sequence=…, observed_at_ms=…, error=…)`
  to mark a disconnect or fixed error and preserve the latest approved
  display and last guest clock. If the producer falls silent, the stream
  marks the latest view stale after `stale_after` seconds of monotonic host
  time since publication. A held producer can publish approved status
  heartbeats to keep the observation fresh.

The timeline keeps up to 24 events by default, with a configurable limit of 64,
and holds metadata only. The latest observation holds the approved display in
memory. Accepted PNG input is limited to 1 MiB and 2,048 × 1,536 pixels. Frame
preparation re-encodes visible RGB at its native size, discards original
chunks, and composites transparency onto black. The GIF is a single still of
at most 640 × 480 pixels and 64 colors. Prepare images before calling
`publish()`. Readers take a short lock to obtain a consistent snapshot and
timeline, then release it before rendering or writing to the browser. Up to
16 requests can hold a snapshot during a reply, with bounded socket deadlines.

## HTTP views

All routes support GET and HEAD. Responses use HTTP/1.0 framing and explicit
Content-Type and Content-Length. HTTP/1.1 requests require the listener's
Host header. HTTP/1.0 requests may omit it.

| Route | Published response |
| --- | --- |
| `/` | Modern dashboard with PNG, screen text, execution state, clocks, frame age, warnings, and a recent timeline |
| `/legacy/` | HTML 2.0-style station report, GIF, screen transcript, and manual Refresh |
| `/api/status` | UTF-8 JSON with identity, freshness, latest approved observation, and metadata-only timeline |
| `/status.txt` | Plain ASCII status and screen transcript |
| `/frame.png` | Latest approved native-size still, with metadata removed |
| `/frame.gif` | Latest approved palette-limited still |
| `/healthz` | Minimal listener health, including before the first publication |
| `/dashboard.css`, `/dashboard.js` | Packaged assets for the modern view |

Machine routes also work under `/i/<instance-id>/`, for example
`/i/synthetic-at/legacy/`. PNG and GIF accept an optional
`?frame=<publication-session>.<generation>.<frame-generation>` selector.
The views use it to keep frame metadata and pixels matched. Images return 404
if none is approved or the requested frame has been superseded. In the
classic view, use Refresh if a frame link has just been superseded. Other
query strings are rejected.

The modern page polls the published snapshot every 1.2 seconds after a reply
and keeps the last rendered view with a stale warning if HTTP goes away. It
uses Unicode for the approved CP437 transcript. The classic page uses
headings, links, PRE, a GIF, and ASCII approximations of box-drawing and
accented characters. It works without scripts, stylesheets, or cookies.
Raw HTTP/1.0 tests check the protocol and markup subset. Compatibility with
Mosaic, Netscape Navigator, or other historical browser versions requires
tests on those browsers. HTTP/0.9 and network access from period hardware
are outside this local prototype.

## Native MCP integration and security

The listener accepts `127.0.0.1` and `localhost` authorities for its port,
validates Origin when provided, sends no CORS grants, and sets no-store and
same-origin resource policy headers. Requests have bounded headers, read
and write deadlines, and a worker limit. Routes provide only observations
and static assets. Local processes can read this listener, so publish only
data approved for those readers. LAN or public deployment needs separate
access control and review.

The explicit schema excludes tokens, paths, registers, raw memory, native
protocol responses, journals, and disk/media data. The producer still has to
review exported text and visible pixels for secrets. Approved display content
could contain a guest path, typed password, or other sensitive data. The
repository and distributions include only the source of the synthetic fixtures.

The [MCP operator guide](86box-readonly-mcp.md#enable-browser-publication)
describes the listener and exact-checkpoint display approval. Every publication
comes from an explicit MCP observation on the existing native connection.
Discovery, browser requests and the passage of host time never open or poll a
native socket. The listener receives only the registry.

- Each owner assigns a sequence under its instance lock. Browser generation
  matches the owner's sampled generation. Reset counter changes, a regressed
  guest clock or frame count, and reconnection can break continuity. RAM
  approval retirement can also increment the owner generation. No native
  process UUID is available. The configured ID and publication-session ID
  identify the browser stream.
- Connection loss marks the view stale immediately, with unknown execution
  flags and the last confirmed clock when available. A previously approved
  display can remain in that stale view. An inconsistent group or target
  mismatch clears the display. A successful reconnect starts a new generation
  with no display, even if the target counters match. Explicit observations
  resume status updates.
- Without a new sample the view becomes stale after ten seconds of monotonic
  host time. Image preparation consumes part of that interval. Status-only
  updates at the same approved checkpoint preserve the original frame capture
  timestamp. A stale still can be retrieved while it is the latest approved
  image. Superseded keys return 404.
- Approved PNG/GIF preparation uses one slot per instance outside the native
  lock. A newer observation can supersede pending work. It takes precedence
  even if the encoder completes later. The stream counts discarded display
  updates and publishes status without waiting for the encoder to free its
  slot. The frame generation uses the producer sequence, independent of native
  frame count. Native frames are labeled as the latest render at capture. The
  browser reports capture-based age and leaves both render timestamps unknown.

The `deskmate_formats.observer` package can move to a future
`86box-agent-bridge` package with its publication code, frame preparation,
HTTP server, assets, and synthetic fixtures. The adapter remains with the
native connection owner.

## Reproduce validation

Run the synthetic tests against an installed wheel. The same checks run on
Windows and Linux with Python 3.13 and 3.14 in CI. Image tests skip when
Pillow is absent and run after installing the extra.

~~~console
python -m build
python tools/install_wheel.py
python tools/check_install.py
python -m unittest discover -s tests/portable -p "test_observer*.py" -v
python tools/install_wheel.py --observer
python -m unittest discover -s tests/portable -v
python -m ruff check src tests/portable tools
python -m reuse lint
python tools/audit_repository.py
~~~

Tests use actual localhost requests to cover both views, three independent
producers, unchanged guest time under polling, host and path validation,
stalled clients, display escaping, image sanitization, and shutdown. The
integrated tests use authenticated synthetic native peers to verify approval,
reset and reconnect handling, encoder ordering, independent instances, and
zero native commands or guest milliseconds during browser refreshes.
