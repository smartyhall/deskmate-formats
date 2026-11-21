# DeskMate reference — Eleventy preview

This is a **reviewable, locally buildable** technical-reference site. It does
not deploy publicly or redistribute historical media and private screenshots.

## Running the site

Install Node.js 22 or newer, enter the website directory, then run:

    npm install
    npm test
    npm run build
    npm run dev

The static output is in website/_site. For a GitHub Pages project-path build:

    SITE_BASE_PATH=/deskmate-formats/ npm run build

On PowerShell:

    $env:SITE_BASE_PATH = '/deskmate-formats/'
    npm run build

Unset SITE_BASE_PATH to build for a root-mounted self-hosted domain.

The GitHub Actions **Reference site preview** workflow creates a downloadable
artifact, but does not enable public deployment.

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

## Before enabling publication

Review the static output for source eligibility, claims and private
information. Verify links, headings, accessibility, mobile layout and
search. Decide on a domain, URL permanence, asset-licensing notices and
an actual hosting deployment target. The future portal may add structured
release records, data-driven catalogs and approved screenshot atlases; the
working reference should not wait for those features.
