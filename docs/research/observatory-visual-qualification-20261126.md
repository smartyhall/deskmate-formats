# Observatory visual qualification — 2026-11-26

**Goal:** look at the campaign interface the way an operator will, using a real
snapshot assembled from real records, without committing screenshots or
weakening the repository's publication safeguards.

## What was generated

A demonstration run in a private state directory outside the worktree produced:

1. two real deterministic attempts (`hash-files`, `fixture-compare`), each with a
   durable plan and terminal outcome;
2. a registry holding three campaigns, two of which own distinct canonical
   worktrees and one of which is refused a claim on another campaign's worktree;
3. a frozen snapshot from `deskmate_formats.supervisor.snapshot` — the same
   collector an operator uses — plus one explicitly synthetic agent campaign;
4. the rendered text, JSON and HTML views.

## What was checked

| Check | Method | Result |
| --- | --- | --- |
| Page serves | loopback `http.server`, `curl` | 200, `text/html; charset=utf-8` |
| Stylesheet resolves | `curl /dashboard.css` | 200 |
| Table well formed | parsed rows and cells | 4 campaign rows, 8 cells each, no unclosed cell |
| Synthetic campaign is marked | substring | `(synthetic)` present in the id cell |
| Unknown usage is distinct from zero | rendered cell text | `allowance_remaining_hours unknown` |
| Empty usage is honest | rendered cell text | `not reported`, not `0` |
| Stale/unreachable wording | projection unit tests | covered |

## What could not be checked

The Desktop browser panel did not attach during this session — `preview_open`
timed out and the screenshot tool reported the page as unattached — so the page
was **not** viewed as pixels. No screenshot was committed. Everything above is
structural inspection of the emitted HTML, not a claim about appearance.

The consequence is explicit: layout, colour contrast and wrapping at narrow
widths are *unverified*. The page is simple (one table, eight columns, one
`dashboard.css`) and its column count is the main overflow risk, but "simple"
is not evidence.

## Procedure for the next pass

1. Run `python tools/experimental/heterogeneous_workers_demo.py --state <dir>`
   with a fresh state directory outside any worktree.
2. Serve `<dir>` on loopback and open the rendered `campaigns.html`.
3. Capture through the website campaign's review-capture workflow rather than
   by hand: it produces a temporary artifact with an explicit purpose and does
   not add unmanifested images to the repository.
4. Record in the handoff which widths were captured and what was concluded.
5. If a screenshot must be kept, it needs a manifest entry, a `.license` file
   and a stated reason — the same bar as any other evidence.

## Coordination with the website campaign

The website campaign has introduced a GitHub Actions review-capture workflow and
is developing cross-browser qualification infrastructure. This branch does not
contain that workflow (`.github/workflows/` here has `ci.yml`,
`reference-preview.yml` and `reference-publish.yml` only), so the capture must
run from the branch that has it, or after it merges.

Two durable requests for that campaign, recorded here so they are not lost:

1. **A capture target for a static Observatory page.** The page is a single HTML
   file plus `dashboard.css` and an accompanying JSON payload. It needs no
   server, no JavaScript and no authenticated route, so it is a cheap
   cross-browser target: one page, three browsers, one width sweep.
2. **A documented artifact location for temporary captures.** If captures are
   uploaded as workflow artifacts, the Observatory can point at them from a
   review note instead of committing images.

## Interface deficiencies found while doing this

- **No stale/unreachable banner in the page header.** The text view prints an
  unreachable section; the HTML view does not, so an operator reading the page
  cannot see that a source was missing. This is a real gap and is listed as a
  follow-up rather than patched here, because it changes the page layout that
  the capture pass is meant to review.
- **Usage columns are prose.** Unknown units, freshness and source are joined
  into one cell. Adequate for four campaigns; unreadable at forty.
- **No per-campaign link to its receipts.** The snapshot carries attempt ids, and
  the page shows them, but nothing lets an operator jump from a row to the
  attempt record.

None of these affect the text or JSON views, which are what the tests and the
snapshot collector exercise.
