# Review attachments for the navigation restructure

These screenshots exist so a reviewer can see the rendered result of the
navigation and editorial restructure without building the site. They are
**review attachments, not published website assets**: nothing here is copied
into `website/_site`, listed in `website/reference-images.json`, or packaged in
the source distribution (`MANIFEST.in` excludes PNGs globally).

Remove this directory once the review is closed. If any image is ever wanted on
the published site, it has to go through the ordinary route instead: an entry in
the image manifest with provenance, dimensions, digest, caption, and alt text.

## Captured states

Built from this branch with `npm run build`, served from `website/_site`, and
captured in Chrome through the DevTools protocol with an explicit device-metrics
override. The measured layout viewport and document scroll width were recorded
for each capture; `scrollWidth` equals the viewport width at both sizes, so
there is no horizontal overflow.

| File | Page | Viewport | Shows |
| --- | --- | --- | --- |
| `home-desktop-1280.png` | `/` | 1280x1000 | Five section cards and the newcomer entry |
| `research-hub-desktop-1280.png` | `/research/` | 1280x2000 | Subject groups and the new dated chronology |
| `research-report-desktop-1280.png` | `/research/filer/` | 1280x1000 | Breadcrumbs, role label with its recorded date |
| `home-mobile-390.png` | `/` | 390x844 | Navigation wrap and single-column layout |
| `research-hub-mobile-390.png` | `/research/` | 390x1500 | Chronology and undated-note wrapping |
| `recovery-hub-mobile-390.png` | `/recovery/` | 390x1100 | Reading path and sidebar order on a phone |

## Rights

The project owns the page rendering and its own prose. The home page reproduces
an existing documentary DeskMate 3.05 capture, which keeps its own terms under
`LicenseRef-DeskMate-Documentary-Capture`; these files do not extend or restate
those terms.
