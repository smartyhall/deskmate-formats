# DeskMate reference — Eleventy website

This is a **reviewable, locally buildable** technical-reference site. It does
not deploy publicly or redistribute historical media and private screenshots.

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
without publishing. The **Publish DeskMate reference** workflow only runs via
`workflow_dispatch`, and deploys the generated site to GitHub Pages using the
repository's **Settings → Pages → Custom domain** configuration. Pushing or
merging a PR never publishes automatically.

GitHub Pages custom domain: `deskmate.retroconnect.org`.
The `deskmate` DNS CNAME points to `smartyhall.github.io` (no path segment).
Domain ownership, DNS validation, and HTTPS enforcement are managed in the GitHub
Pages settings, not through the Eleventy templates or the publishing workflow.
With the custom-domain setting configured in GitHub's UI, an additional
repository `CNAME` file is not necessary for the Actions-based build.

## Source and publication policy

All rendered pages come from the reviewed
[generator-independent page map](../docs/site/page-map.json), using
existing Markdown files in place. Dated research is not presented as a
current specification. Unmapped source links go to GitHub; image embeds
are withheld pending review. Only explicitly authored assets in
website/src/assets are copied into the build.

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

## Publication checklist

Review the final preview artifact for source eligibility and private information,
links, headings, accessibility, mobile layout, and search. Merge the reviewed
change, then run **Publish DeskMate reference** manually from the Actions tab.
Verify the resulting custom-domain URL, CSS and search, and enforce HTTPS after
GitHub provisions the certificate. The future portal may add structured release
records, data-driven catalogs and approved screenshot atlases.
