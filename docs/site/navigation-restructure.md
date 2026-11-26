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
external link resolutions. Of those 532 listed outcomes, 209 were repository
links; the report also cited 571 total resolutions (an unreconciled
denominator). Of the 390 on-site/repository outcomes, 209 were repository
links. Do not use an arbitrary reduction percentage as a release gate.
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
not independently measured production availability. Capture the exact
rendered anchor set from this revision before changing content or layout.

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

## Implementation phases and acceptance

0. **Foundation, before visible change.** Record this plan and editorial
   rules; capture the route inventory and implement automated route
   preservation. Build the pinned baseline revision with the actual
   Eleventy renderer, capture existing HTML IDs/legacy named anchors
   into the baseline and review it. Verify all routes/anchors in subsequent
   preview and publish builds. Test deliberately missing route/anchor
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
5. **Ongoing editorial governance.** Extend validation for summaries,
   section/subsection membership, hub uniqueness, and navigation reachability.
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

The ChatGPT foundation PR is intended to implement the route baseline,
automated compatibility checking, and the editorial record only. It does
not implement the five hubs, metadata migration, a sidebar redesign, or
actual anchor capture. The baseline has explicit null anchor sets until
the pinned pre-redesign build is inspected. The next producing agent should
finish Phase 0 anchor capture before modifying rendered pages, then
implement the remaining phases in reviewable checkpoints. Prefer the
Freebuff local Worktree mode (or a separately owned local checkout) on a
fresh main-based branch once the relevant policy and foundation changes
are reviewed and merged. Avoid the existing Codex checkout. Use the
operator-approved governance, provider-specific usage receipts, and
independent review. No live emulator, provider connection, or cloud
execution is required for this campaign.
