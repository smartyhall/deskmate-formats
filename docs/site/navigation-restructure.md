# Reference-site navigation and editorial restructuring

**Editorial direction accepted by the operator, 2026-11-25 (local time).**
This is the implementation handoff, not a claim that the redesign is deployed.
Freebuff supplied an independent, read-only information-architecture audit
of the November 23 checkout; ChatGPT reviewed it and the operator accepted
the refined direction. The audit was an agent report, not independently
verified browser or accessibility testing. Keep the reference site's
existing publication boundaries and [authoring rules](authoring.md).

## Baseline and diagnosis

Freebuff reported 38 mapped pages, eight open sidebar sections, 189 Markdown
documents, 94 approved figures, and 181 on-site, 209 repository, and 142
external link resolutions. Freebuff's follow-up review corrected the total to 534 Markdown links:
181 on-site, 209 repository, 142 external, and 2 in-page. Of the 390
on-site/repository outcomes, 209 (53.6%) were repository links. Do not use an arbitrary reduction percentage as a release gate.
Re-measure with a documented method against the actual implementation.

Current main inspected for this handoff: `a23197ac66aade3638a3178f9831f353252a2160`.
The source map now contains 40 entries, including Print Companion format
and research pages not in the audit. The renderer still groups flat sections
and opens all sidebar groups; the page map validator still requires six
fields per entry. The site remains Eleventy with the upstream BOOTSTRA.386
theme and separate layout CSS; do not fork the theme or change generator as
part of this work. Reconcile newer theme work if it lands in parallel.
The [route baseline](published-route-baseline.json) records all 40 mapped
routes plus Home and Search at this revision. It records source-map routes,
not independently measured production availability. The 334 article-content anchors across 40 mapped documents have now been
captured from the original GitHub Actions preview (run 45312811457,
artifact 14883254568); the downloaded ZIP matched the recorded SHA-256.
Home and Search are route-only, and layout chrome is not pinned. Preserve
explicitly supported public content fragments even when the layout changes.

The root problem is conflation of repository organization, evidence roles,
and readers' navigation. Preserve source roles, but classify navigation
by reader intent. Do not just collapse the old sidebar.

## Agreed primary structure and reading order

| Section | Route | Purpose and initial reading path |
| --- | --- | --- |
| DeskMate | `/deskmate/` | What it was, historical introduction (`/start/`), applications, releases, visual evolution, ecosystem. |
| File Formats | `/formats/` | Architecture, shared services and structures, manufacturer reference, maintained application format guides, limitations. |
| Recovery | `/recovery/` | Preserve originals first; compatibility and supported operations, Workbench, CLI tools, preservation practices. |
| Research | `/research/` | How claims were established, evidence vocabulary, experiments by application and date, verification, unresolved questions. |
| Project | `/project/` | Method, curated status, direction, licensing, publication and contribution; visually subordinate. |

Each destination is a substantive prose-led landing page rather than a menu:
a short introduction, ordered recommended reading, grouped annotated
resources, source/evidence boundaries, relevant illustrations, and links
to the previous and next section. The five pages together form a rational
narrative from historical orientation to contributing to the project.
The home page offers these paths and makes the DeskMate hub the newcomer
entry; keep the illustrated historical article at its existing /start/
route. Search and source repository are utility destinations; the masthead
links Home. Keep the project material public but separate from the main
historical/technical narrative.

Use a context-sensitive sidebar (roughly twelve links as a design target,
not an inflexible ceiling), breadcrumbs, and ordinary links; navigation
must work without JavaScript. Use accessible disclosure, logical focus
order, mobile layout, and readable role labels rather than raw enums.
Prefer semantic HTML and reusable layout primitives independent of theme.
Preserve existing illustrated introduction and approved image provenance.

### Initial content assignment (stable IDs and URLs)

- DeskMate: history.introduction, applications.note-pad-corkboard,
  applications.inventory, applications.installations,
  applications.installation-303, applications.installation-305,
  applications.comparison-303-305, applications.evolution-atlas,
  applications.ecosystem, applications.acquisition-gaps.
- File Formats: system.architecture, system.manufacturer-crosswalk,
  system.page-setup, formats.calendar, formats.address-book, formats.filer,
  formats.text, formats.draw, formats.worksheet, formats.corkboard,
  formats.print-companion. Preserve distinct manufacturer/current/snapshot
  roles; link to dated experiments by subject.
- Recovery: recovery.workbench. Add reviewed compatibility matrix and CLI
  reference; prioritize the archive owner who wants to recover data without
  having to read laboratory reports. Clearly distinguish supported read,
  write, export, preview and unsupported operations.
- Research: research.filer, research.corkboard, research.print-companion,
  research.text, research.draw, research.worksheet, formats.sound-research,
  formats.music-research, applications.automatic-house-x10,
  system.database-study, applications.tvdog-index-review,
  evidence.visual-catalog. Organize by subject and date; link to applicable
  maintained guides and vice versa. Add reviewed evidence/verification
  entry points and a maintained list of unresolved questions.
- Project: project.roadmap, site.workplan, site.visual-workflow,
  evidence.visual-policy, site.overview, site.authoring. Preserve these
  routes even when reorganizing or eventually consolidating related sources.

These assignments cover all 40 baseline mapped IDs. Section membership
must be independent of route prefix. Preserve existing URLs and anchors.
Full reviewed research reports remain accessible; concise summaries can
introduce them without replacing their evidentiary source. Calendar needs
a maintained successor specification in due course; retain the dated
snapshot as historical evidence. Do not rewrite it as part of this
navigation campaign. Expose a curated current-status summary rather than
blindly publishing PROJECT_STATUS.md. Select new mapped documents for
reader value and publication eligibility, not a target coverage ratio.
Label repository-bound links explicitly, keep deliberate source links,
and review important unmapped destinations (compatibility, evidence,
verification, interoperability, containers, TVDog reference) individually.
Formalize multiple image placements with a single authoritative asset
and provenance record; defer manifest changes until needed.

## Page-map v2 contract and stable hub IDs

Keep v1 support intact while adding v2 validation and tests; migrate the
whole map atomically with the renderer, not entry by entry. A v2 map has
`schema_version: 2` and `pages`, with these fields in every entry:

- `id`, `slug`, `title`, `role`, and `source` retain existing types,
  uniqueness, containment, and role validation.
- `section`: one of `deskmate`, `formats`, `recovery`, `research`,
  `project`; independent of slug and evidence role.
- `subsection`: nonempty reader-oriented label (1–80 characters, trimmed)
  for ordinary pages, null for a section hub.
- `order`: nonnegative integer for ordering within a section/subsection;
  resolve ties deterministically by ID.
- `summary`: trimmed plain text, 1–240 characters, not raw markup.
- `date`: ISO calendar date or null; record dates only when supported by
  source evidence, not inferred from an unrelated commit.
- `is_hub`: boolean; exactly one true per section, with a null subsection.

Stable hub IDs and slugs: `deskmate.overview` / deskmate,
`formats.overview` / formats, `recovery.overview` / recovery,
`research.overview` / research, and `project.overview` / project.
Use `current-guide` or `site-plan` as supported by actual editorial role;
do not create a new evidence role merely to identify a hub. All existing
IDs and slugs remain unchanged. V2 rejects missing or unknown fields and
invalid types; v1 retains its original exact six-field contract. Update
Python and Node tests before migrating, then use v2 in the renderer.
Future extensions should be versioned, not implicit.

## Rejected alternatives and deferred decisions

Do not merely collapse the eight old groups, mirror repository folders in
the nav, substitute a single exhaustive index, use facets as the sole
navigation, build release microsites, switch generators, or map every
document automatically. Facets and release-specific subsections may
supplement the agreed structure. Preserve full reviewed research and
provide approachable summaries; retain the Project material, subordinate
its prominence, and link subject/evidence views. Defer Calendar successor
specification, policy consolidation, image-placement schema changes, and
theme replacement to their appropriate reviewed campaigns. Exact subsection
names, hub prose, status summary format, and visual placement remain
implementation/editorial decisions within this direction.

## Implementation phases and acceptance

0. **Foundation, before visible change.** Record this plan and editorial
   rules; capture the route inventory and implement automated route
   preservation. The original CI build has been recovered and its article-content IDs and
   legacy named anchors captured. Verify all routes/anchors in subsequent
   preview and publish builds; preserve deliberately supported fragment
   aliases even if moved outside the article. Home/Search and layout chrome
   are excluded from automatic anchor capture. Test deliberately missing route/anchor
   failures. Do not regenerate the baseline from a changed site to hide a
   regression. Extend the page-map contract with hierarchy, ordering,
   summaries, dates where applicable, and hub identity; maintain transition
   compatibility and update both Python and Node validation/tests.
1. **Five hubs and reader navigation.** Write substantive linked source
   pages and section-to-section reading paths. Migrate all existing page
   metadata, keep IDs/slugs, make the home entry point /deskmate/, provide
   breadcrumbs, human-readable role labels, summaries and contextual sidebar.
   No unreviewed material or theme fork. Verify every existing mapped
   page remains reachable (aim for two clicks from Home via hubs), search
   coverage, no-JS navigation, and route/anchor preservation. Review
   actual desktop and mobile screenshots, keyboard access and focus order.
2. **Recovery and evidence coverage.** Map eligible compatibility and
   evidence documents, create an accurate CLI guide and improve annotated
   links. Identify which GitHub links are intentional vs unnecessary;
   report counts without an arbitrary percentage target. Verify source
   ownership, link destinations, versioned capability claims, and licensing.
3. **Scale and discovery.** Strengthen installation/ecosystem subsection
   hubs; add chronological and subject research indexes, unresolved
   questions, long-page ToCs, curated status, and cross-linking. Consider
   search facets and reviewed multi-placement figure metadata. A new
   ordinary report should not require new primary navigation.
4. **External discoverability.** Generate sitemap, robots.txt, per-page
   canonical URLs for the custom-domain production site, and a reviewed
   redirect/anchor-alias mechanism if future moves are necessary. Validate
   actual route set, preview base paths, and fragment resolution. No
   redirects are needed merely to reclassify navigation.
5. **Ongoing editorial governance.** Keep schema validation established in Phase 0; add regression checks for
   navigation reachability and editorial upkeep in this phase.
   Review hub reading paths whenever material is added; maintain the
   route/anchor baseline additively after reviewed publication. Defer
   overlapping policy-page consolidation and Calendar specification rewrite
   to separate campaigns.

Each phase is independently reviewable. Run applicable source-map and
publication audits, REUSE lint, npm test, npm run build, generated-site
link/fragment and baseline checks, and required CI. Use preview artifacts
before merging; a relevant merge to main triggers production deployment.
Report checks actually run and failures; include desktop/mobile exemplars
for visible changes. Do not perform an unrelated emulator or native
capture campaign to create illustrations.

## Handoff and current status

The ChatGPT foundation PR implements the route/anchor baseline,
automated compatibility checking, and the editorial record. It does
not implement the five hubs, metadata migration, or a sidebar redesign.
The original artifact's digest, run, and revision are recorded in the
baseline. The next producing agent should verify the captured inventory,
finish Phase 0 schema work, then implement remaining phases in reviewable
checkpoints. Prefer the
Freebuff local Worktree mode (or a separately owned local checkout) on a
fresh main-based branch once the relevant policy and foundation changes
are reviewed and merged. Avoid the existing Codex checkout. Use the
operator-approved governance, provider-specific usage receipts, and
independent review. No live emulator, provider connection, or cloud
execution is required for this campaign.
