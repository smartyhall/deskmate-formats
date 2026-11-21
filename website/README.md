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
remain usable without JavaScript. The first stylesheet is independently
authored in the color and typographic vocabulary of
[BOOTSTRA.386](https://github.com/kristopolous/BOOTSTRA.386), not a
bundled BOOTSTRA.386 release. We have not copied the upstream fonts or glyph
assets; their licensing and accessible fallbacks require separate review.

## Before enabling publication

Review the static output for source eligibility, claims and private
information. Verify links, headings, accessibility, mobile layout and
search. Decide on a domain, URL permanence, asset-licensing notices and
an actual hosting deployment target. The future portal may add structured
release records, data-driven catalogs and approved screenshot atlases; the
working reference should not wait for those features.
