"""Pure presentation of one captured view, shared by the HTTP routes."""

from datetime import UTC, datetime, timedelta
from html import escape
from unicodedata import combining, normalize

from .publication import Connection


def frame_key(view):
    snapshot = view.observation
    return f"{view.publication_session}.{snapshot.generation}.{snapshot.frame.generation}"


def frame_metadata(view, now):
    frame = view.observation.frame
    if frame is None:
        return None
    age_basis = "render" if frame.rendered_at_ms is not None else "capture"
    age_from = frame.rendered_at_ms if age_basis == "render" else frame.captured_at_ms
    return {
        "key": frame_key(view),
        "generation": frame.generation,
        "width": frame.width,
        "height": frame.height,
        "captured_at_ms": frame.captured_at_ms,
        "rendered_at_ms": frame.rendered_at_ms,
        "rendered_emulated_ms": frame.rendered_emulated_ms,
        "latest_rendered": frame.latest_rendered,
        "age_ms": now - age_from if now >= age_from else None,
        "age_basis": age_basis,
    }


def _event_fields(event):
    return {
        "sequence": event.sequence,
        "generation": event.generation,
        "observed_at_ms": event.observed_at_ms,
        "emulated_ms": event.emulated_ms,
        "action": event.action,
        "milestone": event.milestone,
        "connection": event.connection,
        "error": event.error,
    }


def status(machine, view, now):
    """The only public JSON schema. Never serialize producer objects generically."""
    snapshot = view.observation
    observation = None
    if snapshot is not None:
        observation = {
            **_event_fields(snapshot),
            "held": snapshot.held,
            "paused": snapshot.paused,
            "dropped_updates": snapshot.dropped_updates,
            "screen": snapshot.screen,
            "frame": frame_metadata(view, now),
        }
    return {
        "machine": {"id": machine.instance_id, "label": machine.label},
        "publication_session": view.publication_session,
        "served_at_ms": now,
        "stale": view.stale,
        "observation": observation,
        "timeline": [_event_fields(event) for event in view.history],
    }


_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
_ASCII_GLYPHS = str.maketrans({
    "─": "-", "═": "=", "│": "|", "║": "|", "░": ".", "▒": ":", "▓": "#",
    "█": "#", "▄": "_", "▀": "-", "■": "#", "←": "<", "→": ">", "↑": "^", "↓": "v",
})


def ascii_display(text):
    text = normalize("NFKD", text.translate(_ASCII_GLYPHS))
    text = "".join("+" if "\u2500" <= char <= "\u257f" else char
                   for char in text if not combining(char))
    return text.encode("ascii", "replace").decode("ascii")


def _utc(value):
    if value is None:
        return "unknown"
    return (_EPOCH + timedelta(milliseconds=value)).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _ms(value):
    return "unknown" if value is None else f"{value:,} ms"


def _status_lines(machine, view, now):
    snapshot = view.observation
    lines = [f"Machine          {machine.label} [{machine.instance_id}]",
             f"Host served      {_utc(now)}"]
    if snapshot is None:
        return lines + ["State            Waiting for first approved observation"]
    if snapshot.connection is Connection.CONNECTED:
        state = "Paused" if snapshot.paused else "Held" if snapshot.held else "Running"
        if view.stale:
            state = f"STALE - last reported {state.lower()}"
    else:
        state = f"STALE - {snapshot.connection}"
        if snapshot.error:
            state += f" ({snapshot.error})"
    lines.extend([
        f"State            {state}",
        f"Host observation {_utc(snapshot.observed_at_ms)}",
        f"Emulated clock   {_ms(snapshot.emulated_ms)}",
        f"Generation       {snapshot.generation} / observation {snapshot.sequence}",
        f"Action           {snapshot.action}",
        f"Milestone        {snapshot.milestone or '(none)'}",
        f"Dropped updates  {snapshot.dropped_updates}",
    ])
    frame = frame_metadata(view, now)
    if frame is not None:
        source = " (latest render at capture)" if frame["latest_rendered"] else ""
        lines.extend([
            f"Framebuffer      {frame['width']} x {frame['height']} / frame {frame['generation']}{source}",
            f"Frame age        {_ms(frame['age_ms'])} since {frame['age_basis']}",
            f"Frame captured   {_utc(frame['captured_at_ms'])}",
            f"Frame rendered   {_utc(frame['rendered_at_ms'])} / guest {_ms(frame['rendered_emulated_ms'])}",
        ])
    else:
        lines.append("Framebuffer      No approved image")
    return lines


def _screen(view):
    snapshot = view.observation
    if snapshot is None or snapshot.screen is None:
        return "(No approved text screen)"
    return snapshot.screen


def plain_status(machine, view, now):
    lines = _status_lines(machine, view, now)
    return ascii_display("\n".join([*lines, "", "APPROVED SCREEN TEXT", _screen(view), ""]))


def _machine_links(machines, *, legacy=False):
    suffix = "legacy/" if legacy else ""
    return " | ".join(
        f'<a href="/i/{machine.instance_id}/{suffix}">'
        f'{escape(ascii_display(machine.label) if legacy else machine.label, quote=False)}</a>'
        for machine in machines
    )


def legacy_page(machine, machines, view, now):
    machine_name = escape(ascii_display(machine.label), quote=False)
    details = escape(ascii_display("\n".join(_status_lines(machine, view, now))), quote=False)
    screen = escape(ascii_display(_screen(view)), quote=False)
    snapshot = view.observation
    image = "<p>No approved image.</p>"
    if snapshot is not None and snapshot.frame is not None:
        href = f"../frame.gif?frame={frame_key(view)}"
        image = f'<p><a href="{href}"><img src="{href}" alt="Open approved framebuffer GIF"></a></p>'
    return f"""<!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML 2.0//EN">
<html>
<head><title>86Box Observatory - {machine_name}</title></head>
<body>
<h1>86Box Observatory</h1>
<p>CLASSIC TERMINAL / {machine_name}</p>
<p><a href="./">Refresh</a> | <a href="../status.txt">Plain text</a> |
<a href="../">Modern view</a></p>
<p>Machines: {_machine_links(machines, legacy=True)}</p>
<hr>
<h2>1. Station report</h2>
<pre>{details}</pre>
<h2>2. Latest approved framebuffer</h2>
{image}
<h2>3. Screen transcript</h2>
<pre>
{screen}
</pre>
<hr>
<p>Read-only observer. Refresh retrieves the latest publication.</p>
</body>
</html>
"""


def dashboard(machine, machines):
    label = escape(machine.label, quote=False)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{label} | 86Box Observatory</title>
  <link rel="stylesheet" href="/dashboard.css">
  <script src="/dashboard.js" defer></script>
</head>
<body>
  <header>
    <div class="eyebrow">86Box Observatory <span> / </span> Read-only station</div>
    <nav aria-label="View modes"><a href="legacy/">Classic view</a><a href="status.txt">Plain text</a></nav>
  </header>
  <main>
    <div class="station">
      <div><h1>{label}</h1><p class="machine-id">{machine.instance_id}</p></div>
      <p id="state" class="badge" role="status">Waiting for publication</p>
    </div>
    <nav class="machines" aria-label="Machines">{_machine_links(machines)}</nav>
    <p id="warning" class="warning" role="status" hidden></p>
    <noscript><p><a href="legacy/">Open the classic view</a> for the latest observation without scripts.</p></noscript>
    <div class="layout">
      <section class="panel display" aria-labelledby="display-title">
        <h2 id="display-title">Approved framebuffer</h2>
        <div class="display-area"><div id="frame"></div><p id="frame-placeholder">Waiting for an approved frame</p></div>
        <p id="frame-meta" class="muted"></p>
      </section>
      <section class="panel" aria-labelledby="status-title">
        <h2 id="status-title">Observation</h2>
        <dl>
          <dt>Emulated clock</dt><dd id="guest-clock">—</dd>
          <dt>Host observation (UTC)</dt><dd id="host-clock">—</dd>
          <dt>HTTP sample (UTC)</dt><dd id="served-clock">—</dd>
          <dt>Generation / sequence</dt><dd id="sequence">—</dd>
          <dt>Dropped updates</dt><dd id="dropped">—</dd>
          <dt>Milestone</dt><dd id="milestone">—</dd>
        </dl>
      </section>
      <section class="panel screen" aria-labelledby="screen-title">
        <h2 id="screen-title">Approved screen text</h2>
        <pre id="screen">Waiting for an approved screen</pre>
      </section>
      <section class="panel" aria-labelledby="timeline-title">
        <h2 id="timeline-title">Recent observations</h2>
        <ol id="timeline"><li>Waiting for publication</li></ol>
      </section>
      <section class="panel agent-panel" aria-labelledby="agent-title">
        <h2 id="agent-title">Agent activity</h2>
        <p id="agent-collector" class="muted" role="status">Waiting for the agent feed</p>
        <ul id="agent-runs" class="activity-list"></ul>
        <h3>Recent published events</h3>
        <ol id="agent-events" class="activity-list"></ol>
      </section>
    </div>
  </main>
</body>
</html>
"""
