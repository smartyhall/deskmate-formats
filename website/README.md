# DeskMate reference — Eleventy website

This is the **publicly deployed, locally buildable** DeskMate history and technical
reference. The homepage introduces newcomers to DeskMate before offering paths
to the native-format research and preservation tools. Reviewed documentary
screenshots are published through a manifest; commercial software and private
research archives are not distributed.

## Running the site

Install Node.js 22 or newer, enter the website directory, then run:

    npm install
    npm test
    npm run build
    npm run dev

The static output is in `website/_site`. The public GitHub Pages site uses
[deskmate.retroconnect.org](https://deskmate.retroconnect.org/), a **root-mounted**
custom domain, so the production and preview builds use:

    SITE_BASE_PATH=/ npm run build

On PowerShell:

    $env:SITE_BASE_PATH = '/'
    npm run build

For a standalone local build, the default base path is also `/`. A project-path
build for an alternate Pages address can still be made explicitly using
`SITE_BASE_PATH=/deskmate-formats/`, but is **not** the production configuration.

The GitHub Actions **Reference site preview** workflow produces a downloadable
root-path artifact and validates local links, fragments, and upstream theme files
without publishing. It also audits the publication boundaries. This preview runs
for changes to site files, documentation sources, and the site workflows.

**Publish DeskMate reference** builds, checks, and deploys the site automatically
after a push to `main` that changes `website/**`, `docs/**`, the reference page-map
checker, or the publishing workflow. A reviewed PR merged to `main` therefore
publishes automatically when relevant. The manual `workflow_dispatch` option is
still available for a forced republish. Publishing uses the repository's
**Settings → Pages → Custom domain** configuration.

For pull requests touching only `website/**`, `docs/site/**`, or the site
preview/publish workflows, the CI scope classifier skips the unrelated portable
Python matrix while preserving the job names that may be required by branch
protection. Changes to application code, general research documentation,
tests, the publication audit, or other paths still run the full matrix.

GitHub Pages custom domain: `deskmate.retroconnect.org`.
The `deskmate` DNS CNAME points to `smartyhall.github.io` (no path segment).
Domain ownership, DNS validation, and HTTPS enforcement are managed in the GitHub
Pages settings, not through the Eleventy templates or the publishing workflow.
With the custom-domain setting configured in GitHub's UI, an additional
repository `CNAME` file is not necessary for the Actions-based build.

## Navigation redesign and compatibility baseline

See the [agreed implementation handoff](../docs/site/navigation-restructure.md).
The existing generated-site audit now checks the
[pre-redesign route inventory](../docs/site/published-route-baseline.json)
as well as links and fragments. The original baseline was captured from
GitHub Actions run 45312811457, artifact 14883254568, with its ZIP digest
verified against GitHub metadata. The 334 content anchors on mapped
document pages are enforced; Home and Search are route-only. Layout IDs
are intentionally excluded from automatic capture.

For a future additive update, verify the candidate build's exact source
revision (checkout or CI artifact metadata and digest). Append reviewed
new mapped routes to a separate candidate copy of the baseline with
`anchors: []`, leaving all existing entries intact. Run:

    python website/scripts/check_generated_site.py SITE_OUTPUT / --baseline candidate.json --extend-baseline --source-revision FULL_SHA --source-kind verified-local-build --output extended.json

For a CI artifact use `--source-kind verified-ci-artifact --artifact-id ID
--artifact-sha256 DIGEST`. The supplied revision and digest are caller
attestations; verify them independently. The checker refuses missing old
anchors, duplicate targets, and malformed routes. Review the UTF-8 output,
including its capture history, before replacing the tracked baseline.
Never use extension to remove entries. Initial `--capture-anchors` is
restricted to a pending baseline at its pinned revision.

## Source and publication policy

All rendered pages come from the reviewed
[generator-independent page map](../docs/site/page-map.json), using
existing Markdown files in place. Dated research is not presented as a
current specification. Unmapped source links go to GitHub; ordinary raw Markdown image embeds
are withheld. Approved documentary figures are inserted from the verified
`website/reference-images.json` manifest. Only explicitly authored assets
under `website/src/assets` are copied into the site build.

Browser search uses a locally generated index. Navigation and documents
remain usable without JavaScript. The preview now uses **unmodified**
[BOOTSTRA.386 v5.3.1](https://github.com/kristopolous/BOOTSTRA.386)
CSS, JavaScript, fonts and supporting glyphs. A build-time script downloads
the original upstream ZIP pinned to commit
`3af1895e7212f36566d4d46e867e8c4073528e8f`, verifies its Git blob
ID and copies only the necessary distribution files without modifying them.
A build requires network access on the first run; downloaded assets are
cached locally and excluded from Git.

### Licensing and upstream contributions

All future changes to **BOOTSTRA.386 itself** and any separately reusable
site-to-theme integration will be authored under **Apache-2.0** so they can
be proposed upstream without relicensing. Existing DeskMate application,
research and documentation licenses are unchanged.

The original distribution contains separately licensed components:
BOOTSTRA.386 (Apache-2.0), the underlying Bootstrap 5 framework (MIT),
and the Px437 IBM EGA font by VileR (CC BY-SA 4.0). We preserve those
notices, including attribution to [VileR](https://int10h.org/oldschool-pc-fonts/readme/),
and do **not** claim to relicense third-party components under Apache-2.0.
The built site provides copies of upstream Apache and MIT license texts and
a separate attribution file at `assets/vendor/bootstra386/`.

Our own `src/assets/site-layout.css` adjusts site-specific layout only;
it does not patch BOOTSTRA.386 or claim to be an upstream theme change.

On systems where `python3` is not the command name, invoke
`scripts/vendor_bootstra.py` with your Python 3 interpreter before the
Eleventy build.

## Editorial style for the public website

Use the **Oxford (serial) comma** in public-facing articles, historical
introductions, explanatory website copy, navigation labels, figure captions,
and alternative text. This is a consistency and clarity convention for the
reader-facing reference, not a requirement to restyle technical source reports.
Codex-generated research reports, experiment notes, and developer-facing
technical documentation may use whichever style fits the material; do not
rewrite quoted historical passages or underlying evidence for punctuation.

For factual statements in public-facing prose, cite sourceable claims close
to their first mention. Distinguish manufacturer claims, contemporary
independent reports, and our own measured behavior. Cite project reports or
evidence receipts when those are the source, and qualify version-specific
findings.

## Publication checklist

Review the preview artifact for source eligibility, links, headings,
accessibility, mobile layout, image attribution, and search. Merging a reviewed
site or documentation PR into `main` automatically runs **Publish DeskMate
reference**. Use `workflow_dispatch` for deliberate manual republishing, not
as an ordinary extra step. Verify the resulting custom-domain URL and GitHub
Pages deployment status. The site already contains Collection 01's approved
illustrations; future collections follow the same manifest-reviewed process.
