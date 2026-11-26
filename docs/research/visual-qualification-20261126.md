# Visual qualification infrastructure — 2026-11-26

Campaign: `freebuff/visual-qualification-20261126`. This report records what was
verified, what was measured, and what remains a proposal. It is a research record
for review, not a published reference page.

## 1. Published artifact verified

The reference restructure merged at `b5e5250`. The automatic publish run for that
commit failed: `actions/upload-pages-artifact` uploaded the `github-pages`
artifact and the workflow's indexing wait saw it, but `actions/deploy-pages`
reported `Found 0 artifact(s)` and aborted. The live site therefore still served
the previous build, and `/research/` returned 404.

Re-dispatching the repository's own publish workflow — the recovery path its
header documents — succeeded as run `45785003695`, artifact `15099174471`, with
downloaded archive SHA-256
`4ccf5c456f8b215a5b20bfd21c5694a30d6bea2b21926828ae287509cd76b389`.

Verification of the deployed site against those bytes:

- 58 published files (51 HTML pages, sitemap, robots, search index) fetched over
  HTTPS and compared by SHA-256: **58 match, 0 differ**.
- `/research/` and `/sitemap.xml` now answer `200`.

The propagation failure is a known race between the artifact index and the Pages
deployment API. The workflow's wait step checks the Actions artifacts API, which
is not the surface `deploy-pages` reads, so a successful wait does not guarantee
a successful deploy. Recovery is a re-dispatch; the deploy step itself cannot be
retried in place without re-uploading the artifact.

### Route baseline extension

`tools/extend_route_baseline.py` was added to make the additive procedure
repeatable. It inserts routes that the page map describes and the baseline does
not, then captures anchors from a verified artifact through the existing
`check_baseline` extension path, which fails if any captured anchor disappears.

| Measure | Before | After |
| --- | --- | --- |
| Routes | 42 | 51 |
| Anchors on existing routes | 334 | 337 |
| New routes | — | 9 (`/deskmate/`, `/formats/`, `/recovery/`, `/research/`, `/project/`, `/recovery/cli/`, `/recovery/compatibility/`, `/research/evidence/`, `/research/verification/`) |
| Anchors removed | — | 0 |

The capture is recorded in `capture_history` with the revision, artifact ID,
digest, and workflow run.

## 2. Capture utility hardening

`website/scripts/capture_review.cjs` was rewritten around explicit ownership and
acceptance rules:

- **Port ownership.** The browser is launched with `--remote-debugging-port=0`
  and a private temporary profile; the port is read from `DevToolsActivePort`
  inside that profile and accepted only when `/json/version` advertises a
  debugging URL on the same port while the child is alive. A fixed port could
  have attached to an unrelated session.
- **Navigation completion.** Load event followed by a quiet-network poll, not a
  fixed sleep.
- **Page identity.** Rendered path, canonical URL, title, and `readyState` are
  checked against the requested route before a screenshot is taken.
- **Transport.** Document status must be 200; failed resource loads are findings.
- **Geometry.** Viewport must equal the request; the screenshot must match the
  clip scaled by the device pixel ratio.
- **Timeouts, cancellation, cleanup.** Per-command and per-page timeouts, signal
  handling, `Browser.close` followed by process-tree termination, and removal of
  the temporary profile.
- **Provenance.** `capture-manifest.json` records revision, browser product
  string, platform, Node version, and a SHA-256 per image.

Local evidence: 12 renders accepted, all 200, no horizontal overflow. A negative
run against a missing route was rejected with every expected reason (404, wrong
path, absent canonical, `Error response` title, wrong viewport).

Two defects in the first draft were caught by these checks rather than by
inspection: the document-response handler ran before the navigation frame was
known, and phone screenshots are device pixels, not CSS pixels.

## 3. Cross-engine qualification, measured locally

Harness: `qualification/` (Playwright 1.65.1, axe-core 4.14.1). Local machine:
Windows, Node 26.13.0.

| Engine | Version | Available |
| --- | --- | --- |
| Chromium | 159.0.8154.6 | yes |
| WebKit | 27.2 | yes |
| Firefox | — | no: `Host system is missing dependencies` |

Firefox's bundled build would not start on this workstation. That is a host
dependency gap, not a site finding; it is reported as skipped.

Matrix: home and `/research/`, profiles `desktop`, `mobile`, `no-js`, `keyboard`,
`deep-link`, engines Chromium and WebKit — 20 renderings.

**Result: 20 of 20 accepted, 0 axe violations, 1 inconclusive.** The
inconclusive entry is WebKit focus order on the home page: WebKit moves Tab
between form controls only, so a zero-stop result says nothing about keyboard
access. It is recorded as inconclusive rather than passed or failed.

### Defects found and fixed

1. **`link-in-text-block` (serious, 3–12 nodes per page).** The theme sets
   `text-decoration: none` on every link, so links in prose were distinguished
   from surrounding text by color alone. Links in `main` and `footer` now carry
   an underline; primary navigation and buttons are unchanged.
2. **`region` (moderate).** The theme injects a decorative cursor element
   (`#cursor386`) directly into the body, outside every landmark. It is now
   marked `aria-hidden="true"` after load rather than moved or removed.

Both fixes are additive and leave the accepted visual design intact.

### What this does not establish

Automated checks are not WCAG conformance. The runs did not use a screen reader,
did not test physical devices, did not measure contrast by hand, and did not
exercise Safari. `no-js` runs axe as skipped because axe-core requires scripting.

## 4. GitHub Actions qualification

`.github/workflows/reference-qualification.yml` provides three levels on
standard public-repository runners:

| Level | Trigger | Coverage | Rough cost |
| --- | --- | --- | --- |
| Routine | `pull_request` | Ubuntu, Chromium + Firefox + WebKit, home and five hubs plus changed pages, `desktop`, `mobile`, `no-js`, axe | one job, about 6–10 minutes |
| Comprehensive | dispatch | Ubuntu, Windows, macOS; per-platform engines (Linux: Chromium/Firefox/WebKit; Windows: Chromium/Firefox/Edge; macOS: WebKit/Chromium/Firefox); eight profiles; hubs | three jobs, about 15–25 minutes each |
| Focused | dispatch | caller-chosen engines, profiles, and routes on Ubuntu | one job |

Changed-page selection (`qualification/scripts/changed-pages.cjs`) maps changed
`docs/**` sources through the page map, and falls back to the hubs when templates
or stylesheets change. Routine runs always include the hubs, so site-wide chrome
is never skipped in favor of only the changed page.

Artifacts: screenshots, contact sheet, structured summary, and console/network
diagnostics, 14-day retention. Nothing is committed; the publication audits are
untouched.

## 5. Visual regression strategy

Pixel equality is only meaningful inside one pinned environment. The harness
therefore separates four tiers:

1. **Exact** — same engine build, same OS image, same DPR, same fonts. Suitable
   for a pinned container and for the CDP capture utility.
2. **Tolerance** — same engine family across runs, small per-pixel threshold and
   a bounded fraction of differing pixels.
3. **Region** — compare a named element (masthead, hub grid) rather than the page.
4. **Structural and semantic** — DOM assertions, computed styles, link and anchor
   inventories, axe results. These are portable across engines and are what the
   current harness asserts.

Known noise sources that make cross-engine pixel comparison meaningless:
engine rasterization, font availability and hinting, device pixel ratio,
scrollbar width, animations and caret blink, lazy-loaded images, and version
drift in either the browser or the harness.

Baselines should be content-addressed and stored outside the repository — as
workflow artifacts keyed by `revision + engine + platform + profile`, or as
release assets — with a reviewed manifest recording the digest of each accepted
baseline. Accepting a new baseline is a review decision, never automatic on a
failed comparison.

## 6. Hosted qualification services

Figures below were read from vendor pages on 2026-11-26 and are advertised
allowances, not entitlements granted to this project.

| Service | Free offering | Engines and devices | Notes |
| --- | --- | --- | --- |
| Percy (BrowserStack) | 5,000 screenshots/month, unlimited users and projects; builds expire after 30 days on the free plan | Renders in BrowserStack browsers; real mobile browsers on the Desktop & Mobile plan | Screenshot **comparison** service, not remote browser control. Each browser × width counts as a screenshot. Overage on paid plans is billed per screenshot. |
| BrowserStack Open Source | All products unlimited for qualifying projects, lifetime access | Live, Automate, Percy | Application form with a project URL; approval is discretionary. Automate is remote browser control and includes real iOS devices. |
| Sauce Labs | No ongoing free plan; 28-day trial with 60 minutes and 3 parallel sessions; free accounts for qualifying open-source projects | Large virtual and real-device cloud | Real Safari and physical devices are the draw. Enterprise-oriented, with contractual terms. |
| Browserless | Cloud free plan: 1,000 units/month, 2 concurrent browsers, 2-minute sessions; self-hosted open-source image free under SSPL-1.0 | Chromium, Chrome, Firefox, WebKit, Edge images | General-purpose remote browser automation, not visual comparison. SSPL-1.0 is not OSI-approved and would constrain how a derived service could be offered. |
| Argos, Chromatic (alternatives) | 5,000 screenshots/month | Chromium-focused | Comparable comparison services with different pricing models. |

### Recommended use

- **Everyday work** stays local and on GitHub Actions. Both are free for this
  public repository, produce reviewable artifacts, and need no account.
- **Hosted comparison** is reserved for publication milestones where an
  independent visual record is valuable. Percy's free allowance is large enough
  for a milestone (the six hub captures at three widths and two browsers is 36
  screenshots), but its builds expire, so it is an archive of the last month, not
  a permanent record.
- **Real Safari and physical devices** are the only capabilities local runs
  genuinely cannot provide. Those belong to an open-source application
  (BrowserStack or Sauce Labs) if the operator chooses to pursue one, not to a
  routine workflow.

No account was created, no GitHub App installed, and no credentials were
configured. Nothing unpublished was transmitted anywhere.

## 7. Dedicated rendering service

The question is whether a laboratory renderer adds enough beyond free
GitHub-hosted runners and local browsers. On the evidence above it does not add
engine coverage — the same three engines run locally and in CI. It would add
isolation from developer workstations, a stable pinned environment for exact
baselines, and capacity for long or concurrent qualification jobs.

### Candidates

| Option | Strengths | Limits |
| --- | --- | --- |
| Playwright browser server (`playwright run-server`) | Same harness code, WebSocket connect, trivial to deploy | No queueing, no per-job isolation, no resource limits; unsuitable as a shared endpoint |
| Selenium Grid | Mature queueing, session limits, per-node browsers | Heavier operation; the harness would need a WebDriver path |
| Browserless (self-hosted) | REST and WebSocket APIs, per-browser images, health checks | SSPL-1.0; enterprise features are licensed; still a general browser endpoint |
| Purpose-built job runner (recommended) | Narrow contract, deterministic inputs and outputs | Custom code to maintain |

### Proposal

A small service that accepts a **qualification job**, not a browser session:

- Inputs: repository revision, artifact digest, profile set, route selection,
  engines, resource budget, deadline, and an authorization token.
- Execution: unpack the verified artifact, serve it on loopback, run the existing
  harness in a container with CPU/memory/disk limits and a wall-clock deadline,
  then terminate the process tree.
- Outputs: a content-addressed result bundle (screenshots with digests, summary
  JSON, diagnostics) plus a signed receipt naming the harness version and engine
  versions.
- Isolation: one container per job, no inbound network, no access to laboratory
  services, no arbitrary URL fetching, and an allowlist of artifact digests.

Sizing for the preliminary VM (4 vCPU, 8 GB, 40–60 GB): one Chromium job at
1280x900 uses roughly 300–600 MB; a three-engine matrix of 20 renderings took
about 90 seconds locally. Two concurrent jobs with a 2 vCPU / 3 GB cap each fit
comfortably, leaving headroom for the image cache. Storage is dominated by
browser images (about 1.5 GB for three engines) and artifacts, which should be
pruned by age.

This remains a proposal: no VM was provisioned, no ESXi setting was touched, and
no endpoint was exposed.

## 8. Supervisor and Observatory handoff

A qualification request should be expressible as a deterministic task without
model inference:

```json
{
  "task": "reference.qualify",
  "revision": "b5e525002b150352a8995de1bcddfbc5dc18a838",
  "artifact": { "id": 15099174471, "sha256": "4ccf5c45…" },
  "profile_set": ["desktop", "mobile", "no-js"],
  "routes": ["/", "/research/"],
  "engines": ["chromium", "webkit"],
  "axe": true,
  "deadline_seconds": 900,
  "budget": { "cpu": 2, "memory_mb": 3072 }
}
```

A result should carry the rendered content identity, engine and platform
versions, measured dimensions, per-check outcomes, screenshot digests, axe
summary, diagnostics, elapsed time, and explicit failure or cancellation state.
The harness already emits most of this in `qualification-summary.json`; the
missing pieces are a signed receipt and a backend identifier.

For the Observatory, the useful views are active and queued jobs, worker
ownership, current page and profile, progress, visual regression summaries,
before-and-after comparisons, allowance consumption, and links to the associated
pull request. Qualification logic is separated from execution backends so the
same named procedure can run locally, in Actions, or on a laboratory worker, with
capability discovery reporting what each backend can actually do.

No file in the concurrent Supervisor campaign's worktree was read or modified.

## 9. Usage accounting

Tracked per run: engine and version, profile count, route count, renderings,
wall-clock duration, artifact bytes, and — for hosted services — units or
screenshots consumed. GitHub Actions minutes for this public repository are free;
the meaningful budget there is wall-clock time and concurrent-job pressure.
Hosted allowances should be treated as finite and scheduled deliberately: routine
checks never consume them.

## 10. Limitations and open questions

- Firefox could not start on the development workstation; only CI can confirm it.
- Branded Chrome and Edge were not exercised locally.
- No physical device, no Safari, no screen reader, and no manual contrast audit.
- The publish workflow's artifact race is mitigated by re-dispatch, not fixed in
  the workflow; a retry around `deploy-pages` would need a supported mechanism.
- Visual comparison is not implemented beyond structural assertions; the tiers in
  section 5 describe the intended design.
- Whether a laboratory renderer earns its maintenance cost is unresolved; the
  proposal above is the smallest version worth evaluating.

## References

- Percy plans and billing: <https://www.browserstack.com/docs/percy/overview/plans-and-billing>
- Percy pricing: <https://percy.io/pricing>
- BrowserStack open-source program: <https://www.browserstack.com/open-source>
- Sauce Labs supported platforms: <https://saucelabs.com/products/supported-browsers-devices>
- Browserless pricing: <https://www.browserless.io/pricing>
- Browserless self-hosted editions: <https://www.browserless.io/platform/self-hosted>
