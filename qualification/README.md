# Browser qualification harness

Cross-engine visual, layout, and accessibility qualification for the DeskMate
reference site, written so the same procedures can qualify other project
interfaces later.

This package is deliberately separate from `website/`: the site build keeps only
its Eleventy dependencies, and the harness can point at any HTTP origin.

## Install

```sh
cd qualification
npm install --no-audit --no-fund
npx playwright install chromium firefox webkit      # add msedge/chrome for branded browsers
```

## Run

```sh
# Build the site, then qualify the built output with a temporary local server
node cli.cjs --serve-dir ../website/_site --axe

# Qualify a deployed site with a wider matrix
node cli.cjs --base https://deskmate.retroconnect.org \
  --engines chromium,firefox,webkit \
  --profiles desktop,mobile,no-js,keyboard \
  --pages /,/research/ --axe --out local-results/qualification
```

Exit status is `0` when every executed rendering passed, `1` when a rendering
failed or was inconclusive, when no rendering ran, or when the matrix is
incomplete with `--require-matrix`, and `2` for a usage error.
`--allow-findings` explicitly permits failed or inconclusive renderings for
exploratory reporting; it does not permit an empty run or override
`--require-matrix`. Routine and comprehensive CI use `--require-matrix` without this override; focused dispatch has an explicit opt-in `allow_findings` input. Focused runs retain the full required matrix even with that opt-in.

## Engines

| Name | What it actually is |
| --- | --- |
| `chromium` | Playwright's bundled Chromium |
| `firefox` | Playwright's patched Firefox build |
| `webkit` | Playwright's WebKit build — **not Apple Safari** |
| `chrome` | Branded Google Chrome installed on the machine |
| `msedge` | Branded Microsoft Edge installed on the machine |

An engine that cannot start is reported as skipped with the reason, never
counted as a pass. Playwright's WebKit build shares an engine with Safari but
differs in version, platform integration, and font handling; a WebKit result is
evidence about WebKit, not a claim about shipping Safari.

## Profiles

`desktop`, `tablet`, `mobile`, `landscape`, `reflow` (320 CSS pixels), `no-js`,
`forced-colors`, `reduced-motion`, `print`, `keyboard`, `deep-link`, `search`.

Every profile is a **simulation**: a 390x844 context is an emulated phone
viewport, not a physical device, and `forced-colors` is a simulated preference,
not a real high-contrast configuration.

## What a run verifies

A rendering is accepted only when:

- the document answered `200`;
- the rendered origin/path match the requested base/route, and the canonical URL matches the expected canonical origin and route (local preview defaults to the published DeskMate domain; override with `--canonical-origin` for another site);
- the title contains the page map's title;
- the viewport matches the requested width and height;
- loading settled (load event, then a quiet network);
- no request failed and no page error was raised.

Then the profile's checks run: layout overflow, image alt text and loading,
navigation without scripting, in-page anchors, table scroll containers, focus
order and focus visibility, print presentation, and search behavior.

With `--axe`, axe-core runs in every scripting-enabled profile. Serious and
critical violations are findings; all violations are recorded.

## Artifacts

`--out` receives:

- `<engine>-<profile>-<route>.png` full-page screenshots with SHA-256 digests;
- `qualification-summary.json` — engines with versions, per-rendering status,
  observed dimensions, checks, console messages, failed requests, axe results;
- `contact-sheet.html` — grouped by engine and profile, failures highlighted;
- `summary.md` — a table suitable for a pull request comment.

Artifacts are temporary review material. They are uploaded as workflow
artifacts, never committed.

## Limitations

Automated checks do not establish WCAG conformance, and simulated preferences
are not assistive-technology testing. Nothing here replaces a screen-reader
review, a contrast audit by a person, or testing on physical devices. A passing
run means the specific assertions above held in these engines at these sizes.

Keyboard qualification distinguishes three outcomes: a pass, a failure, and
*inconclusive* — WebKit moves Tab between form controls only, so a zero-stop
result there is recorded as inconclusive rather than as a pass or a defect. Traversal reaching the 40-stop cap or any repeated element identity (including the first stop) is inconclusive; only the null/body focus observation ends a nonempty traversal. Repeated labels are not identity. A cycle may indicate a focus trap; do not count it as a pass. Unsettled images receive a bounded wait and remain inconclusive if pending, while broken images and absent alt attributes are findings.

## Extending to other interfaces

The runner takes a base URL and a list of routes, so another interface only
needs its own route list and, where relevant, its own page-level checks in
`lib/checks.cjs`. Backends are interchangeable by design: the same command can
target a local build, a GitHub Actions job, or an approved remote browser
service that exposes an equivalent origin.
