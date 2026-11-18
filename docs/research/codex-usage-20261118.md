# Initial DeskMate Codex usage analysis

The [historical ledger](../evidence/codex-usage/20261118-historical-backfill-01.json)
covers 21 project sessions and 2,457 token observations across November 11–18
UTC. The analysis accepts a positive last increment when all five fields match
the cumulative difference. Twelve repeated cumulative snapshots were excluded.
The isolated S0 and S2 one-request observations match the dated supervisor
experiments. The Sound and Music session `a6df8bb25b192d45b9d491f0` contains
local command evidence for the first two campaign checkpoints, `8ffb8e3` and
`db2884b`. The campaign was subsequently recovered and merged through PR #115.
[S0 experiment](codex-supervisor-s0-second-live-result-20261116.md) ·
[S2 experiment](codex-supervisor-s2-first-live-result-20261116.md) ·
[Audio PR](https://github.com/smartyhall/deskmate-formats/pull/115)

## Account windows

Of 2,417 adjacent within-session pairs where both meters were observed and
both reset epochs held steady, 600 showed an increase only on the five-hour
meter, 64 only on the weekly meter, 38 on both and 1,715 on neither. The
remaining pairs included missing or expired snapshots and epoch changes.
Observed within-session epoch advances were 14 for five hours and two for the
weekly window. Three epoch regressions show why a changed epoch alone cannot
establish a completed reset. Snapshot timing, account-wide work and
percentage granularity limit comparisons. This record gives no conversion
factor between the windows or between raw tokens and quota.

## Request counters and context

| Model | Effort | Matched increments | Median total tokens | Median reasoning-output tokens | Cached share of input |
| --- | --- | ---: | ---: | ---: | ---: |
| gpt-6-luna | low | 2 | 14,023.5 | 0 | 0% |
| gpt-6.1-sol | medium | 798 | 123,303.5 | 57 | 98.44% |
| gpt-6.1-sol | high | 305 | 145,373 | 134 | 98.79% |
| gpt-6.2-sol | high | 1,340 | 170,306 | 51 | 98.96% |

The table describes workloads with different tasks and conversation lengths.
The two Luna observations came from separate one-request supervisor runs.
Cached share is the ratio of summed cached input to summed input. Input and
output totals include their respective cached and reasoning portions.

Two logged compactions reduced the next verified request's input from 444,378
to 31,695 and from 449,649 to 27,552 tokens, compared with the previous
verified requests. Their cached shares dropped from above 99.8% to 42.0% and
45.1%, then reached 89.4% and 99.0% on the following requests. These two
examples establish a context-size effect in the captured counters. Longer
conversation cost per useful milestone and the meter impact of compaction
remain unmeasured.

## Checkpoint policy

The current campaign began with 98% five-hour headroom and 4% weekly headroom.
Treat 5% remaining in either window as a practical trigger to reduce
assignment size and push each independent result as soon as it verifies.
This is a scheduling heuristic. The corpus lacks repeated, comparable
milestones near exhaustion to estimate a safe final-work budget.
For stronger evidence, log before/after account reads at comparable published
milestones, record task size and continuity, keep meter epochs stable, and
identify concurrent account work where possible. Compare model and effort on
matched tasks and report cache state and context length alongside output.

Run the summary from the repository root.

```powershell
python tools/experimental/codex_usage_summary.py docs/evidence/codex-usage/20261118-historical-backfill-01.json
```
