"use strict";

const byId = (id) => document.getElementById(id);
const utc = (value) => value == null ? "unknown" : new Date(value).toISOString();
const ms = (value) => value == null ? "unknown" : value.toLocaleString() + " ms";
const frameContainer = byId("frame");
const placeholder = byId("frame-placeholder");
const warning = byId("warning");
let displayedFrame = null;
let displayedTimeline = null;

function showWarning(message) {
  warning.textContent = message;
  warning.hidden = !message;
}

function renderFrame(frame) {
  if (!frame) {
    frameContainer.replaceChildren();
    displayedFrame = null;
    placeholder.textContent = "No approved frame";
    placeholder.hidden = false;
    byId("frame-meta").textContent = "";
    return;
  }
  byId("frame-meta").textContent = [
    frame.width + " × " + frame.height + " px · frame " + frame.generation,
    ...(frame.latest_rendered ? ["Latest render at capture"] : []),
    frame.age_ms == null ? "age unknown" : ms(frame.age_ms) + " since " + frame.age_basis,
    "Captured " + utc(frame.captured_at_ms),
    "Rendered " + utc(frame.rendered_at_ms) + " / guest " + ms(frame.rendered_emulated_ms),
  ].join(" · ");
  if (displayedFrame === frame.key) return;

  displayedFrame = frame.key;
  const image = new Image();
  image.hidden = true;
  image.alt = "Latest approved framebuffer";
  placeholder.textContent = "Loading approved frame";
  placeholder.hidden = false;
  frameContainer.replaceChildren(image);
  image.onload = () => {
    if (frameContainer.firstChild !== image) return;
    image.hidden = false;
    placeholder.hidden = true;
  };
  image.onerror = () => {
    if (frameContainer.firstChild !== image) return;
    displayedFrame = null;
    placeholder.textContent = "Frame unavailable · retrying on the next poll";
  };
  image.src = "frame.png?frame=" + encodeURIComponent(frame.key);
}

function renderTimeline(events, key) {
  if (displayedTimeline === key) return;
  displayedTimeline = key;
  const items = events.slice().reverse().map((event) => {
    const item = document.createElement("li");
    const detail = document.createElement("small");
    item.textContent = event.action + (event.milestone ? " · " + event.milestone : "");
    detail.textContent = [
      "G" + event.generation + " / #" + event.sequence,
      "Guest " + ms(event.emulated_ms), utc(event.observed_at_ms), event.connection,
    ].join(" · ");
    item.append(detail);
    return item;
  });
  if (!items.length) {
    const item = document.createElement("li");
    item.textContent = "Waiting for publication";
    items.push(item);
  }
  byId("timeline").replaceChildren(...items);
}

function render(data) {
  const observation = data.observation;
  const state = byId("state");
  byId("served-clock").textContent = utc(data.served_at_ms);
  if (!observation) {
    state.textContent = "Waiting for publication";
    state.classList.remove("stale");
    for (const id of ["guest-clock", "host-clock", "sequence", "dropped", "milestone"]) {
      byId(id).textContent = "—";
    }
    byId("screen").textContent = "Waiting for an approved screen";
    showWarning("");
    renderFrame(null);
    renderTimeline([], "empty");
    return;
  }
  const label = observation.connection === "connected"
    ? (observation.paused ? "Paused" : observation.held ? "Held" : "Running")
    : observation.connection;
  state.textContent = data.stale ? "Stale · last report: " + label : label;
  state.classList.toggle("stale", data.stale);
  const warnings = [];
  if (data.stale) warnings.push("Showing the last approved observation.");
  if (observation.error) warnings.push("Observation error: " + observation.error + ".");
  const dropped = observation.dropped_updates;
  if (dropped) {
    warnings.push("Publisher skipped " + dropped.toLocaleString() + (dropped === 1 ? " update." : " updates."));
  }
  showWarning(warnings.join(" "));
  byId("guest-clock").textContent = ms(observation.emulated_ms);
  byId("host-clock").textContent = utc(observation.observed_at_ms);
  byId("sequence").textContent = observation.generation + " / " + observation.sequence;
  byId("dropped").textContent = dropped.toLocaleString();
  byId("milestone").textContent = observation.milestone || "—";
  byId("screen").textContent = observation.screen ?? "No approved screen";
  renderFrame(observation.frame);
  renderTimeline(data.timeline, [data.publication_session, observation.generation, observation.sequence].join("."));
}

async function poll() {
  try {
    const response = await fetch("api/status", {
      cache: "no-store", credentials: "omit", signal: AbortSignal.timeout(5000),
    });
    if (!response.ok) throw new Error("Status unavailable");
    render(await response.json());
  } catch {
    byId("state").textContent = "Stale · observer unreachable";
    byId("state").classList.add("stale");
    showWarning("The HTTP observer is unreachable. Any displayed observation is from the last successful poll.");
  } finally {
    setTimeout(poll, 1200);
  }
}

poll();

const agentStates = {
  "active-reporting": "Reporting activity",
  "alive-no-new-events": "Process alive · no new reported activity",
  "approval-needed": "Awaiting approval",
  disconnected: "Source disconnected",
  completed: "Completed",
  failed: "Failed",
  interrupted: "Interrupted",
  unknown: "Activity unknown",
};

function activityItem(title, ...lines) {
  const item = document.createElement("li");
  const heading = document.createElement("strong");
  heading.textContent = title;
  item.append(heading);
  for (const line of lines) {
    const detail = document.createElement("small");
    detail.textContent = line;
    item.append(detail);
  }
  return item;
}

function age(value) {
  return value == null ? "elapsed time unknown" : Math.floor(value / 1000).toLocaleString() + " s ago";
}

function renderAgent(agent) {
  const last = agent.last_activity;
  const pending = agent.pending_approval_count;
  return activityItem(
    agent.agent_id + " / " + agent.run_id + " · " + agentStates[agent.state],
    "Source " + agent.source + " (" + agent.origin_id + ") · Reported lifecycle " + agent.reported_lifecycle +
      (agent.historical ? " · Historical" : agent.stale ? " · Stale" : ""),
    "Stations " + (agent.machine_ids.join(", ") || "none") + " · Process " + agent.process +
      (agent.verified_pid == null ? "" : " (PID " + agent.verified_pid + ")") +
      " · Publication " + agent.transport + " (" + age(agent.signal_age_ms) + ")",
    agent.last_heartbeat_utc ? "Last heartbeat · " + agent.last_heartbeat_utc +
      " · " + age(agent.heartbeat_age_ms) : "No process heartbeat reported",
    last ? "Last activity · " + last.type + " · " + last.summary + " · " + last.ingested_at_utc +
      " · " + age(agent.activity_age_ms) : "No agent activity reported",
    pending ? "Approval pending · " + pending + " · " + agent.pending_approval_ids.join(", ") :
      "No pending approval reported",
  );
}

async function agentQuery(path) {
  const response = await fetch(path, {cache: "no-store", credentials: "omit", signal: AbortSignal.timeout(5000)});
  if (!response.ok) throw new Error("Agent feed unavailable");
  return response.json();
}

async function pollAgents() {
  const collector = byId("agent-collector");
  try {
    const agents = await agentQuery("/api/v1/agents?limit=12");
    if (agents.collector === "disabled") {
      collector.textContent = "Agent feed disabled";
      return;
    }
    const history = await agentQuery("/api/v1/events?tail=1&limit=12");
    collector.textContent = "Journal reader " + agents.collector +
      (agents.has_more ? " · Showing the most recent agent runs" : "");
    byId("agent-runs").replaceChildren(...(agents.agents.length ? agents.agents.map(renderAgent) :
      [activityItem("No published agent runs")]));
    byId("agent-events").replaceChildren(...(history.events.length ? history.events.reverse().map((event) =>
      activityItem(event.type + " · " + event.summary,
        event.agent_id + " / " + event.run_id + " · " + event.severity + " · " + event.ingested_at_utc)) :
      [activityItem("No published events")]));
  } catch {
    collector.textContent = "Agent feed unavailable · Any displayed data is from the last successful poll";
  }
  setTimeout(pollAgents, 2500);
}

pollAgents();
