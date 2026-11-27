# Freebuff and Codebuff integration surfaces — upstream research, 2026-11-26

**Question:** what officially supported way exists to drive, stream from, cancel,
continue and report on Freebuff from outside a human at the keyboard — and which
third-party integrations claim to do it, on what basis, and at what risk?

**Method:** read the public source at `github.com/CodebuffAI/freebuff`
(`sdk/README.md`, `sdk/src/run.ts`), issue #947, PR #1611, the public MCP
documentation at `docs.freebuff.page/mcp-servers`, and the public READMEs of the
third-party bridges. No Desktop token was read, no authenticated endpoint was
contacted, no model turn was initiated, and no software was patched.

**Conclusion in one line:** the only supported programmatic surfaces today are
the paid `@codebuff/sdk` (a real key, metered) and — once merged — ACP served by
the official binary; everything that talks to Desktop by other means is
undocumented and one upstream policy explicitly refuses it with a ban warning.

## 1. What the official CLI does and does not support

Issue #947 (opened 2026-08-06, still the reference) established, against the
installed native binary:

| Probe | Result |
| --- | --- |
| `freebuff -p` / `--print` | `error: unknown option '-p'` |
| `freebuff --headless` | `error: unknown option '--headless'` |
| `freebuff --json` | `error: unknown option '--json'` |
| `freebuff "do something"` | no prompt argument; only `login` is accepted |
| prompt on stdin | hangs waiting for a TTY |

The reporter also noted the `--headless`/`--json` strings found inside the binary
come from the bundled `chrome-devtools-mcp` browser-use agent, not from the CLI's
own parser. Our own probe of Freebuff 0.2.36 on this machine reached the same
result: no print mode, no structured output, no cancellation channel.

The free `freebuff` binary is a thin launcher that downloads a large native
binary to `~/.config/manicode/freebuff`; its flag set is deliberately narrower
than the paid `codebuff` CLI's.

**So:** headless Freebuff operation through the official CLI does not exist. Any
integration that claims it is either driving the TUI (fragile, and against
policy — see §3), or using the paid SDK.

## 2. The SDK, and the free/paid boundary

`@codebuff/sdk` (already reviewed at `sdk/README.md`, source at
`sdk/src/run.ts`) is a genuine, documented programmatic client:

- `CodebuffClient.run()` with `handleEvent: (event: PrintModeEvent) => void`
  and a separate `handleStreamChunk`.
- Session continuation through `previousRun`.
- An optional `terminalCommandBroker` whose docstring says it "keeps terminal
  tools away from an interactive console. Headless consumers can omit it."
- Explicit knobs for `projectFiles`, `projectIndex`, `skipSymbolIndex`,
  `knowledgeFiles`, `agentDefinitions`, `agentDirs`, `maxAgentSteps`, `env`.

That last group matters for us independently of Freebuff: it is the documented
shape of a headless consumer of an agent runtime, and it names exactly the
boundaries our Supervisor already models (`agentDirs` "never the repository",
a broker that keeps terminal tools away from a console).

The boundary is licensing and billing, not capability: the SDK requires a paid
`CODEBUFF_API_KEY` (`cb_...`) and its calls are metered. Issue #947's second
request — allowing the free device-OAuth `authToken` to work with the SDK's
`CodebuffClient` — is *not* granted, and it is the thing that would let a free
account run programmatically.

**Operator consequence:** our free desktop/CLI access is a human-in-the-loop
resource. Programmatic dispatch, per-token accounting and automatic cancellation
are paid-SDK features. The Supervisor's allowance model already separates
"unknown" from "measured"; that distinction is exactly what prevents us from
budgeting against an allowance we cannot read.

## 3. The refusal policy

PR #1611 (`--acp`: serve the Agent Client Protocol over stdio) reports that when
the author tried running the free device token through an external harness, the
backend refused with:

> Freebuff free mode only works through the official Freebuff CLI, Freebuff
> Desktop and freebuff.com. This request came from a third-party client, harness
> or proxy, so it was refused. (warning, then ban)

The PR's own conclusion is that the ACP surface has to live *inside* the
official binary, reusing the TUI's `getCodebuffClient()` → SDK `run()` path and
`PrintModeEvent` handlers so free-mode admission, `freebuff_instance_id` metadata
and device signing stay byte-identical.

**This is the single most important fact in this document.** It means:

1. Driving Desktop or the free CLI through an emulated or proxied interface is
   an account-terminating action, not merely an unsupported one.
2. The previously proposed authenticated `models` endpoint probe is **withdrawn**.
   It was framed as read-only inspection, but it is precisely the class of
   third-party authenticated access the policy refuses, and the information it
   would have yielded (model list) is not needed for any current task.
3. Wait-and-integrate is the correct posture for ACP: if #1611 or an equivalent
   lands, `freebuff --acp` becomes a supported, in-binary interface that an
   orchestrator can spawn. Until then, nothing.

## 4. MCP, in the direction that is actually supported

`docs.freebuff.page/mcp-servers` documents Freebuff as an MCP **client**:

- config in `.agents/mcp.json` (project), `../.agents/mcp.json` (parent),
  `~/.agents/mcp.json` (user);
- Desktop keeps approvals and connection state in `~/.freebuff/mcp.json`;
- transports stdio, Streamable HTTP, and SSE (CLI only);
- agent tools `search_mcp_tools` / `call_mcp_tool`.

Issue #1627 (2026-11-05) reports that Desktop 0.0.201 ships the `/api/mcp`
backend — registry, approval model with hashed launch/tool manifests — with no UI
to approve a server, so a registered server stays `awaiting_launch_approval`
forever. The documented workaround is the separate CLI.

**What this means for the Observatory:** the supported integration direction is
*inbound* — expose our read-only campaign view as a stdio MCP server that
Freebuff may consume, rather than reaching *out* to Freebuff. That needs no
token, no inference and no undocumented endpoint, and it is the natural shape
for a tool that answers "what is the laboratory doing". It is not implemented
here; it is a candidate with a clear contract (§6).

## 5. Third-party bridges: what they do, and why we do not use them

Four public projects were identified. All are unofficial, and each takes a
different route into a running application.

| Project | Route | Notable claims | Concerns for us |
| --- | --- | --- | --- |
| `Praket7/freebuff-mcp` | MCP bridge to locally installed Freebuff Desktop sessions | does not read process memory; does not remove approval steps; masks common secret patterns in returned text, and says pattern checks are not a security boundary | talks to Desktop by means the vendor has not documented; its own README disclaims completeness of masking |
| `toyro396133/freebuff-bridge` | HTTP `/v1/*`, MCP stdio, web UI on port 7778; SSE streams; "wake Freebuff" | threads CRUD, send prompt, stop/resume, model switching, queue control | a local HTTP server with prompt and model-switching authority — a privilege boundary we would have to audit and harden ourselves |
| `RNK-Enterprise/freebuff-mcp-server` | npm MCP server wrapping a run loop | `freebuff_run` with `session_id`, `freebuff_stop`, `cost_mode` "free ≈ the CLI's --lite mode" | its `cost_mode` mapping implies it is driving the agent runtime directly, not the documented CLI |
| `LMLiam/freebuff-desktop-patches` | patches the installed Desktop bundle | re-signs ad-hoc on macOS; adds MCP server loading to the harness | modifies a signed application; neither supported nor stable across updates |

**Assessment.** Each claims a working integration, and some clearly do work for
their authors. None of them constitutes an authorized or stable provider
interface: they rely on undocumented internal surfaces, they change with every
Desktop build, and at least one class (proxying the free token to a third-party
client) is explicitly refused by the provider with a ban warning. For a
laboratory whose entire value is evidence integrity, "it works today" is not the
standard; "the provider supports it and will keep supporting it" is.

We also will not patch the Desktop application: it breaks code signing, voids the
update path, and would make every future receipt's provenance questionable.

## 6. Durable conclusions

| Surface | Status | Use |
| --- | --- | --- |
| `freebuff` CLI | interactive only; no print/JSON/headless through 0.2.36 | human-driven work only |
| `@codebuff/sdk` | documented, headless, streaming, cancellable | paid only; not provisioned |
| `freebuff --acp` | proposed in #1611; not merged | watch; spawn if it lands |
| Freebuff as MCP client | documented | candidate inbound Observatory server |
| Desktop `/api/*` backends | undocumented | do not contact |
| Third-party bridges/patches | unofficial | do not use |
| Device token extraction | refused; ban | never |

**Candidate, not implemented:** a stdio MCP server exposing four read-only tools
over our snapshot — `campaign_list`, `campaign_status`, `task_receipt`,
`unreachable_sources` — implemented with the same validate-then-render discipline
as `observer/campaigns.py`, and with no write path at all. Reviewed separately,
because adding a new listener or protocol surface to this repository is its own
change.

**Operator decisions this leaves open** (all of them require a human, none of
them are needed for the current campaign):

1. Whether to fund a Codebuff API key for metered headless runs.
2. Whether to adopt `--acp` if it merges upstream.
3. Whether an MCP server for the Observatory is wanted at all.
4. Whether any third-party bridge is acceptable, given the ban policy.
