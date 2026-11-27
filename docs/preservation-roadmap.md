# Long-term preservation ecosystem roadmap

Status: agreed likely direction following the operator's planning discussion
of 2026-11-19 (local time). This is a living architectural roadmap, not an
instruction to reorganize the repository immediately. The current repository
remains the incubator for these components. Do not interrupt the ongoing
TVDog intelligence or native research campaigns to implement the split.

The objective is to separate the reusable machinery for discovering historical
software behavior, the historical and technical knowledge produced by that
research, and the implementations that apply it. Favor meaningful boundaries,
independent audiences and release lifecycles over one repository per executable.

## Intended component boundaries

### 1. General-purpose emulated research platform

Ultimately extract the automation harness, supervisor and dispatch
infrastructure, and observer as a coherent project that is not specific to
DeskMate, Tandy, DOS, x86 or a particular model provider.

- Generic campaign lifecycles, task queues, worker coordination, leases,
  recovery, explicit authority and idempotency boundaries.
- Emulator adapters, guest input, machine state, storage, memory inspection,
  framebuffer/audio capture, deterministic execution and evidence recording.
- Analysis adapters (including Ghidra), agent adapters (including Codex),
  telemetry, and the observer's live/read-only and historical views.
  Freebuff is an experimental supplementary agent, not an implemented
  dispatch or telemetry backend. Preserve the pinned Codex protocol and
  qualify provider-specific adapters separately; see the
  [multi-agent campaign rules](https://github.com/smartyhall/deskmate-formats/blob/main/AGENTS.md#multi-agent-campaign-governance).
  Prefer shared campaign identities, evidence and usage receipt contracts,
  capability discovery, resource ownership, and provider-neutral skills;
  retain provider-specific semantics and record unavailable telemetry.
  Manual supplementary-agent campaigns need not wait for adapter work.
- Subject-specific application profiles and experimental recipes outside the
  generic core. For example, a DeskMate profile owns window/control semantics;
  the platform owns guest memory access and the semantic observation interface.
- Capability discovery rather than pretending that every emulator provides
  identical facilities. 86Box is the established first backend; DOSBox-X,
  QEMU, MAME, VICE and other controlled environments are future possibilities,
  not supported-backend claims.

The observer belongs with the automation platform: its purpose is to correlate
controlled experiments, guest state, evidence and campaign activity. Keep its
read-only publication boundary separate from dispatch and machine-control
authority. Existing operator launch gates, privacy rules and approval
requirements remain unchanged.

Qualify extraction using portable synthetic tests, independently configurable
subject profiles, and at least one meaningful non-DeskMate use case where
practical. Preserve history, interfaces and deployment documentation.

### 2. General-purpose archival research toolkit

Plan a separate reusable home for the archive acquisition, extraction,
classification, deduplication, provenance, searchable-library and indexing
infrastructure. It should be useful without an emulator, AI agent, or DeskMate
installation, for example when preserving an old BBS, CP/M or Amiga collection,
manuals or historic websites.

Develop from the maintained [archive tools](../tools/archive/README.md).
Retain configuration-driven acquisition, server-friendly pacing and policy
checks, persistent resume/stop state, safe offline extraction and incremental
indexing. Directory mirrors, ordinary web archives and historical replay/WARC
acquisition are related but distinct modes; do not claim unimplemented modes
are available. Keep source-specific configurations and private holdings
separate from generic code. Subject-specific catalog enrichment belongs in
profiles or downstream projects. Share documented evidence/provenance schemas
with the automation platform without forcing either to depend on the other.

### 3. Independent DeskMate and Tandy reference knowledge base

Ultimately manage the DeskMate-related format documentation, historical
software and hardware knowledge, SDK and system reference, research evidence,
software release catalogs, annotated archive bibliography, and relevant Tandy
historical material independently of conversion and recreation software.

The likely first public home is a standalone statically generated reference
website backed by Git (GitHub Pages is a suitable starting candidate).
A reviewable wiki-like contribution workflow is desirable; the exact static
site generator is not yet decided. MkDocs was discussed as one candidate,
not a binding choice. Preserve plain source content and structured catalog
records independently of templates and rendering tools.

Proposed information architecture:

- History, release chronology, hardware platforms, peripherals and ecosystem.
- System architecture, APIs, SDKs, resources, graphics, fonts, audio, printing.
- Maintained, evidence-bounded native and adjacent-format specifications.
- Research reports, experiments, comparative results and unresolved questions.
- Software and media identification, bibliography and annotated source links.
- DeskMate: The Enthusiast's Edition as a coherent historical demonstrator,
  with separately maintained eligible original synthetic content and recipes.

Distinguish the current synthesized specification from dated discovery reports.
Update the former as hypotheses are resolved, preserve the latter as evidence,
and use stable identifiers, section anchors, versioned snapshots and citations
so implementations can pin the precise specification revision. Avoid competing
authoritative copies; implementation repos keep their own API, CLI, compatibility
and release docs and link to the relevant canonical reference. Cross-link data,
software releases, tests, original URLs and evidence. Provide readable, searchable
pages and machine-readable metadata. Keep private archives, raw forum messages,
copyrighted binaries/documents, proprietary resources, contact details and
private evidence outside public site builds.

#### Visual direction — explicit operator preference

For the initial static reference site(s), regardless of generator choice, use
a theme based on [BOOTSTRA.386](https://github.com/kristopolous/BOOTSTRA.386).
Its vintage DOS-inspired presentation fits the immediate spirit of the project.
Make the theme a replaceable presentation layer, not a dependency of the
underlying reference material or schemas. Pin and review upstream assets,
licenses, attribution, dependencies and accessibility when implementing;
do not copy proprietary assets into the site.

Eventually, prefer a theme explicitly derived from DeskMate's own design
language for DeskMate- and Tandy-specific documentation repositories.
Use measured authentic palette, typography, window/menu/control conventions,
iconography and layout as visual references, independently authoring eligible
assets. The existing classic Draw Workbench work can inform the visual system,
without requiring a shared implementation. Preserve readability, contrast,
keyboard navigation, responsive layouts, accessible search and code examples;
a nostalgic visual identity should not make the reference less usable.
The generic archive and research infrastructure can retain BOOTSTRA.386 or
another suitable retro-computing identity. No theme implementation or generator
selection is authorized by this note alone.

### 4. Core DeskMate format and preservation software

Retain deskmate-formats as the common home for closely coupled native formats,
readers/writers, converters, shared database/form/graphics/font/resource/audio
libraries, and unified file identification and recovery workflows. Shared
structures and semantics warrant common implementations rather than premature
per-application repositories. Keep public interfaces, capabilities, versioned
fixtures and compatibility declarations explicit.

For the foreseeable future, retain research-driven browser applications such as
the FIG editor/Draw Workbench in this repository so they can evolve with the
native codecs and serve as validation tools. Graduation into a standalone
application becomes worthwhile when a recreation has sufficiently developed
original-equivalent functionality, an independent audience and release
lifecycle, and a stable core library interface to consume. Preserve native
round-trip tests and avoid forking incompatible format implementations. The same
principle can apply to future Music, Text or desktop recreations.

Aim to preserve a unified whole-system recovery experience even if later
components live in different repositories.

### 5. Adjacent and third-party format implementations

When substantial conversion/reconstruction work on distinct third-party
DeskMate-adjacent formats begins, consider separate repositories. Express
Publisher, PFS First Publisher, FilePro and Q&A Write are illustrative domains,
not settled repository names or promises of support. A distinct format family,
independent layout/database engine, cross-platform lineage, or release lifecycle
may justify separation. Small extensions to demonstrably shared native
structures need not be split out.

Use documented shared-core dependencies rather than copying common codecs.
Explore a versioned format-provider/plugin interface so adjacent projects can
participate in unified identification, preservation and conversion workflows.
Authoritative historical and format reference material belongs in the knowledge
base, linked bidirectionally with implementation and verification repositories.

### 6. Optional umbrella organization

A future neutral GitHub organization could unify the projects while allowing
separate maintainers, licenses, release cycles and repository names. Its identity
should not unnecessarily bind the general-purpose infrastructure to DeskMate
or Tandy. No organization, project names or repository transfers have been
selected or authorized. The Enthusiast's Edition may later have its own
demonstrator home if independently useful; retain the existing private-media,
original content, historical evidence and collaborative fictional chronology
rules from its [plan](ecosystem/demonstrator.md).

## Migration sequence and readiness criteria

The [reference-site preparation directory](site/README.md) now stages
navigation identities for existing source documents, an evidence-led
cross-application workplan, and the private-to-public image review workflow.
These do not select a static generator, activate a website, approve image
publication, or move authoritative sources out of this repository.


1. Begin now with internal boundaries, explicit dependencies and cohesive
   modules in the current repo. Prefer generic mechanisms plus subject adapters.
   Keep useful research and tests moving; do not refactor for its own sake.
2. Prepare the knowledge base: synthesize specifications, assign stable IDs,
   organize citations and dated evidence, and keep rendering concerns separate.
   Test links, catalogs and publication boundaries.
3. Extract general-purpose tools when independently usable, tested and
   maintainable. Preserve relevant Git history, license notices, interfaces,
   portable regression tests, deployment instructions and evidence schemas.
4. Publish the standalone reference site when its content and navigation are
   ready; select and qualify the generator, BOOTSTRA.386-based theme and deployment
   workflow then. Preserve or redirect existing deep links and version references.
5. Graduate substantial adjacent implementations and mature standalone apps as
   their own requirements justify it; maintain common recovery integration.

Before a physical extraction, inventory dependencies, downstream users,
canonical documentation, fixture ownership, licensing and private/public
boundaries. Plan versioned interfaces and reproducible builds, tests across
repositories, migration/rollback, stable source links and appropriate history
preservation. Avoid circular dependencies, duplicated authority, destructive
history rewrites and publication of private data. A future split requires a
separate reviewed migration plan and operator authorization. Treat this roadmap
as the preferred direction, subject to refinement as research progresses.

## Standing direction for current campaigns

Use this document to make local architectural decisions that will reduce
eventual migration cost. Do not treat it as an immediate reorganization
assignment or a reason to divert the archive intelligence, typography, music,
or other ongoing native-format work. Follow AGENTS.md and the current research
handoff for operative authorization and priorities.

## Infrastructure priority update — 2026-11-25

The operator agreed that supplementary agent capacity makes a timely return
to Supervisor development more practical. Follow the
[revised Supervisor campaign direction](research/supervisor-next-campaign-20261125.md):
audit the existing implementation, prioritize a useful deterministic task
runner, and develop provider-neutral coordination around proven adapters.
Freebuff integration and sustainable allowance remain qualification questions.
Preserve the read-only Observatory boundary and existing live authorization
gates. Do not interrupt the website implementation or treat this direction
as an immediate repository split or live dispatch grant.
