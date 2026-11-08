# Database compatibility campaign

Started 2026-11-07 (America/New_York) from verified origin/main
`0d8c9e9cb538c65c382cd4f5478048e4397c6bb7`, on dedicated branch
`codex/database-generation-campaign`. This new record does not reconstruct an
absent historical PROJECT_STATUS.md. PRs #65/#66 were inspected, remain unmerged
and were not changed. Campaign draft: [#67](https://github.com/smartyhall/deskmate-formats/pull/67).

| Milestone | Result |
| --- | --- |
| M0 complete | Clean start, Windows 10 Pro 19045 x64, Python 3.13.17; source imports pinned with PYTHONPATH=src. Issue #35 reviewed; no launcher needed for offline work. |
| M1 complete | Bounded common directory/schema/index/record reader, opaque-byte retention and malformed/boundary tests. Commit `0158cf8e9086d0292ae43c5aab30470163418a71`. |
| M2 partial | Explicit SDK ordinary codecs; 29 appointments over 14 days generated and independently checked. Multipage reading; allocation blocked. Commit `5067da55c5ec3ac97f4d855cddec297e0e022376`. |
| M3 partial | Ten-page Address Book reader and empty-to-one writer; all four A01-A04 native hashes reproduced. 25 contacts in 25 separate files. Commit `ca06dd9a5ec5c648940c0981760c6e4bfd5e4fb3`. |
| M4 offline complete | Independent checker validates actual archived Calendar/ADR outputs and rejects six altered outputs. Native open/navigation/save NOT RUN. |
| M5 complete within codecs | Version-1 Python/JSON semantic contract, explicit loss reporting, snapshot IDs and examples. No network synchronization. |

The 30-day attempt stops at 40 total appointments with 12 row bytes free; its
incomplete capacity prefix is preserved. A full 60-90-event month and a single
20-30-contact book remain unmet. No edit/delete allocator or byte-preserving
JSON-to-native reconstruction is claimed. Default Calendar validation is preserved.

See [campaign evidence/report](docs/research/database-campaign.md),
[Address Book limits and discriminating trial](docs/research/addressbook-codec.md),
[output hashes](docs/evidence/database-campaign.json) and
[interchange contract](docs/interoperability.md).

Original commercial inputs, public native fixtures and private evidence remain
unchanged. New tool-generated outputs, receipts and validation logs are durably
archived privately. Historical DOSLAB E15-E19/A01-A04 archives remain unlocated;
only the focused local-baseline oracle tests are claimed, not the full private
suite. No host dependencies were changed; packaging used a disposable build
backend environment after the host lacked setuptools.

Final checks: **313 portable tests passed (125.563 s)** and **2 focused private
oracle tests passed (0.060 s)**. Ruff, REUSE (274/274), repository/archive audit
(555 source files), wheel/sdist build, isolated wheel smoke and link checks passed.

Next highest-value gate: separately authorize the two-contact Address Book
ordering trial, then test the generated Calendar in a disposable native clone.
Allocation-header meanings remain unresolved. No emulator/native connection, RAM inspection, guest save,
infrastructure change or model child was used. Requested emulated execution:
**0 ms**; actual guest-clock delta: **not measured**. Publication of checkpoints
and this draft was authorized by the campaign; no merge or unrelated PR changes.
