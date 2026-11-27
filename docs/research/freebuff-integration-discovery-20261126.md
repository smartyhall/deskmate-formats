# Freebuff integration discovery — 2026-11-26

**Scope:** determine what a Supervisor Freebuff adapter could rely on, without
creating a session, spending allowance, contacting any endpoint or reading
private account data.

**What was done:** read-only inspection of the installed desktop client's file
layout, build metadata and bundled JavaScript strings; read the operator-reported
desktop telemetry; compared these against the project's
[provider-neutral usage contract](../evidence/agent-usage/README.md).

**What was not done:** no Freebuff binary was executed, no HTTP request was made
to any Freebuff or Codebuff endpoint, no credential or token was read, no
transcript, session store or account record was opened, and no model turn was
created. Running the client was avoided deliberately: the desktop application
shares the operator's live session, and launching it could disturb that session
for no qualification benefit.

## 1. Evidence classification

The distinction matters more than the finding:

| Class | Meaning | Examples here |
| --- | --- | --- |
| **Documented** | Stated in project or vendor documentation available to us | The provider-neutral receipt contract; the desktop tooltip fields the operator described |
| **Source-verified** | Present as literal strings or packages in the installed bundle | API path strings, internal package names, build metadata |
| **Locally observed** | Directory layout and file metadata on this machine | Install path, resource directory contents, app-data directory names |
| **Experimentally verified** | An interface actually called and its behaviour observed | **None.** No endpoint was contacted |
| **Unavailable** | Not present or not exposed | A CLI on `PATH`; any local control socket identified as this app's |

A string in a bundle proves that the code *can* reference a path. It does not
prove the path is supported, authorized, stable, or usable by a third party.

## 2. Locally observed installation

- Desktop application directory:
  `%LOCALAPPDATA%\Programs\@codebufffreebuff-desktop`, an Electron application
  with `Freebuff.exe`, `resources\app.asar` (about 29 MB) and a bundled
  `resources\orchestrator` tree.
- `resources\orchestrator` contains `orchestrator.js`,
  `orchestrator-bundle.cjs`, `orchestrator-loader.mjs`, a `ui\index.html`, a
  `vendor` directory and tree-sitter WASM grammars for C#, C++, Go, Java,
  JavaScript, Python, Ruby, Rust and TSX.
- Runtime helper directories `resources\bun`, `resources\node`,
  `resources\git` and `resources\vcrt` are shipped beside the orchestrator.
- Application data at `%APPDATA%\Freebuff` includes `logs`, `Preferences`,
  `Local Storage`, `Network`, `Session Storage`, `orchestrator-bundles`
  (containing `state.json`), `theme` and a `lockfile`. These are runtime state
  and private session data; they were **not** read.
- `%LOCALAPPDATA%\Freebuff` contains only `install-receipt.txt`, holding a short
  opaque receipt token. The token is withheld from this document.
- The project worktree lives under `%USERPROFILE%\.freebuff\worktrees\...`; that
  directory contains only `worktrees`, so there is no session registry there.
- No `freebuff` or `codebuff` executable is on `PATH`.

## 3. Source-verified build metadata

`resources\orchestrator\build-info.json`:

~~~json
{"commitSha":"f1641d8af2a035dfb8a1b107d7f256ce9172276c",
 "builtAt":"2026-11-23T08:15:55.413Z",
 "apiOrigin":"https://www.codebuff.com",
 "webOrigin":"https://freebuff.com"}
~~~

`resources\app-update.yml` describes a generic update feed at
`https://freebuff.com/api/desktop/updates/win-x64/`.

The client therefore distinguishes an **API origin** (`www.codebuff.com`) from a
**web origin** (`freebuff.com`). A future adapter must not assume they are the
same host, and must not derive either from a request header.

## 4. Source-verified API surface

Unique path strings found in the bundle:

| Path | Apparent purpose |
| --- | --- |
| `/api/v1/models` | Model catalogue and capability discovery |
| `/api/v1/me` | Authenticated identity |
| `/api/v1/chat/completions` | Chat-completions style inference |
| `/api/v1/agent-runs` | Agent run records |
| `/api/v1/agents/:publisher/:agent/:version` | Versioned agent definitions |
| `/api/v1/agents/` | Agent collection |
| `/api/v1/project-profile` | Project metadata |
| `/api/v1/project-understanding` | Repository understanding context |
| `/api/v1/web-fetch` | Server-side fetch |

Bundled internal packages referenced by the client:
`@codebuff/common` (most frequent), `@codebuff/agent-runtime`,
`@codebuff/code-map`, `@codebuff/llm-providers`, `@codebuff/sdk`,
`@codebuff/transcript` and `@codebuff/freebuff-desktop`.

The strings `https://freebuff.com/cli` and `https://freebuff.com/desktop` also
appear, consistent with a separate CLI product page. No CLI is installed here,
so a CLI-based adapter is **not** a locally available path.

**Do not read this table as support.** These are internal paths used by the
desktop client with its own authentication. Third-party programmatic use,
quotas, terms and stability are unverified.

The loopback ports that appear in the bundle (`127.0.0.1:3000`, `:4100`,
`:4242`, `:51234` and others) are generic fixture values. They are **not**
evidence of a local control API, and nothing was probed.

## 5. Operator-reported desktop telemetry

The desktop context tooltip exposes fields the agent tools do not: current
context utilization and capacity, the compaction threshold, cumulative thread
usage, input tokens, included cached input tokens, output tokens, included
reasoning output tokens, compaction count, latest compaction information, and a
separate daily-hours meter.

The operator reported two rounded readings from separate conversations:

- A completed website conversation: about 26 M cumulative input tokens, about
  25 M of them cached, about 206 k output tokens, about 105 k included reasoning
  tokens, and two compactions.
- The follow-up review snapshot: 170 k of 1.0 m context (16%), compacts at
  300 k, 4.8 m thread usage, 4.7 m input, 4.4 m cached input, 90 k output, 50 k
  reasoning output, one compaction, and a 30:00 daily-hours display.

These are **manual UI observations**, rounded as displayed. They are not exact
counters, not charges, and not an exchange rate. Cached and reasoning counts are
subsets of input and output respectively and must not be added again. The two
readings belong to different conversations and must not be combined into one
campaign total. The daily-hours meter's reset and charging semantics remain
unverified, and the selected model label is not an independently verified
runtime model identity.

## 6. What an adapter would need

1. **Authentication without secret handling by the adapter.** Any credential
   would have to come from the owner's own configuration; it must never be
   copied into a project file, a receipt, the Observatory or a log.
2. **A supported dispatch contract.** Creating a session and submitting a task
   must be a documented interface, not a reverse-engineered endpoint used with
   a desktop token.
3. **An event or status interface.** Progress reporting needs a documented
   stream or poll with explicit staleness, not screen observation.
4. **Usage fields with units and scopes.** `thread usage`, `context`, `cached
   input` and `daily hours` are four different measurements; see
   `scheduling.py`, which already refuses to conflate them.
5. **Cancellation semantics.** Whether a submitted task can be cancelled, and
   what an interrupted task leaves behind, is currently unknown.

## 7. Proposed qualification procedure (not executed)

This is the smallest honest test of the one path that looks most promising, and
it requires separate operator authorization before anyone runs it:

1. **Authorization required:** explicit approval for a single read-only,
   authenticated request to `GET https://www.codebuff.com/api/v1/models` using
   the owner's own credential, plus approval of the data boundary (the request
   leaves the lab and identifies the account).
2. Record the exact client version, build commit and request time.
3. Send one request with a bounded timeout; store the response privately.
4. Compare the returned model list against what the desktop selector displays,
   without assuming they match.
5. Publish only a sanitized note stating whether the endpoint answered, whether
   authentication was accepted, and which capability fields exist — no keys, no
   account identifiers, no raw response.
6. Stop. Do not follow with a completion request, a task submission or a second
   endpoint in the same authorization.

A second, separate qualification would be needed before any task submission:
one bounded completion with an explicit budget, an explicit model, a synthetic
prompt, and recorded usage. Neither step is authorized by this campaign, and
neither was attempted.

## 8. Conclusions

- A Freebuff adapter is **not** implementable today against a verified interface.
  `workers.FreebuffWorker` therefore advertises no capabilities and raises rather
  than pretending.
- Manual Freebuff operation remains fully usable and is what this campaign
  actually used. No adapter is required for manual work.
- The most valuable immediate step is not an adapter but the neutral measurement
  vocabulary: separate units, scopes, sources and freshness, with `unknown`
  preserved. That exists now in `scheduling.py`.
- The next step, if the operator wants it, is the single authorized `models`
  request in §7.
