# Pages publication verification and recovery

Investigation: 2026-11-27. Tracking [#200](https://github.com/smartyhall/deskmate-formats/issues/200).

## Independently inspected evidence

Both runs below used revision `b5e525002b150352a8995de1bcddfbc5dc18a838`,
upload-pages-artifact `7b1f4a7`, and deploy-pages `368f825`.

| | Failed push | Successful manual dispatch |
| --- | --- | --- |
| Run | [45782832305](https://github.com/smartyhall/deskmate-formats/actions/runs/45782832305) | [45785003695](https://github.com/smartyhall/deskmate-formats/actions/runs/45785003695) |
| Job | [139782199464](https://github.com/smartyhall/deskmate-formats/actions/runs/45782832305/job/139782199464) | [139789450950](https://github.com/smartyhall/deskmate-formats/actions/runs/45785003695/job/139789450950) |
| Uploaded artifact ID | 15099336317 | 15099174471 |
| Upload digest (archive SHA-256) | `f127073ca6e7032e7c30544ad77564de2b3ab5d1191e7aeebe02200063732f54` | `4ccf5c456f8b215a5b20bfd21c5694a30d6bea2b21926828ae287509cd76b389` |
| REST indexing wait | poll 1, 08:24:33 UTC | poll 1, 08:39:50 UTC |
| Deployment artifact selection | 0 results | 1 result, ID 15099174471 |
| Deployment creation | not reached | success |

The failed job finished upload at 08:24:31 UTC, and artifact selection returned
zero at 08:24:33 UTC. The successful run finished upload at 08:39:48 UTC and
selected the correct artifact at 08:39:51 UTC. These logs independently verify
the recorded failure and recovery; differing ZIP digests do not prove that the
underlying site files differ.

The pinned [deploy-pages source](https://github.com/actions/deploy-pages/blob/368f82528645a54fb793d4d04e342629a3f51346/src/internal/api-client.js)
uses `DefaultArtifactClient.listArtifacts()` against the runtime artifact
service, not the Actions REST run-artifacts endpoint polled by the shell.
It throws on zero or multiple matches before calling the Pages deployment
creation API. This establishes an observation discrepancy between the two
surfaces, consistent with propagation delay. It does not prove the underlying
server-side cause, a particular safe delay, or that a second deployment is
always safe. The action exposes an artifact name, not an exact artifact-ID
input.

## Recovery procedure

1. Inspect the failed job and record the run, attempt, checked-out commit,
   uploaded artifact ID/digest, REST observation and action outcome. Distinguish
   selection failure before deployment creation from uncertain completion
   after creation. Do not retry an uncertain deployment blindly.
2. Confirm the intended revision is current reviewed `main`, and that there
   is no active publication. Do not rerun the old job: it may attempt another
   upload under the same artifact name in the same run.
3. Use **Actions → Publish DeskMate reference → Run workflow**, selecting
   `main`. This creates a fresh run, rebuilds and audits the current site,
   uploads a new artifact, and requests publication through the ordinary
   Pages environment. Never use an unreviewed branch to recover production.
4. Confirm the upload's exact artifact ID is the sole unexpired
   `github-pages` artifact in that run. Check deployment logs for the
   selected ID and expected revision. Record the final deployment outcome.
5. Verify the public homepage, research hub, and sitemap against the actual
   built files, not just HTTP 200. A stale site can answer 200. Compare the
   wider route baseline and complete published artifact when qualifying
   release coverage; preserve exact checksums and any mismatch.

The proposed workflow strengthens exact-ID and current-main checks, refuses
old-run retries, and performs a bounded byte comparison of the three critical
public responses after deployment. It does not introduce automatic deployment
retries, modify permissions, or claim to eliminate the upstream race. The
current-main check is a sample, not an atomic lock against a subsequent merge.
The post-deploy check detects but does not roll back a bad or stale publication.
Only a real reviewed deployment can qualify the end-to-end behavior. No
production deployment was initiated during this investigation.

The earlier worker's 58-file byte comparison is reported in
[visual qualification report in PR #197](https://github.com/smartyhall/deskmate-formats/blob/5aee34c413ece85fd5ef62bfb2e5485d1d5afd47/docs/research/visual-qualification-20261126.md). Independent inspection here is limited to logs and source, not
downloaded archive bytes or the live site.
