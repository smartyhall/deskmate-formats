"""Summarize a compact v1 Codex usage history without estimating charges."""

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from statistics import median


def summarize(receipt):
    history = receipt["history"]
    models = defaultdict(list)
    transitions = Counter()
    boundaries = Counter()
    rejected = Counter()
    compactions = []
    for events in history["sessions"].values():
        previous = None
        before_compaction = None
        for row in events:
            event = dict(zip(history["columns"], row))
            if event["kind"] == "compaction":
                before_compaction = previous
                continue
            start = previous["cumulative"] if previous else [0] * len(history["token_columns"])
            end = event["cumulative"]
            verified = False
            if all(type(n) is int for n in (*start, *end)):
                delta = [after - before for before, after in zip(start, end)]
                if delta == event["reported_last"] and delta[-1] > 0 and min(delta) >= 0:
                    verified = True
                    models[(event["model"], event["effort"])].append(delta)
                else:
                    rejected[event["counter_state"]] += 1
            else:
                rejected["incomplete_counters"] += 1
            if before_compaction is not None and verified:
                compactions.append([
                    before_compaction["reported_last"][:2], event["reported_last"][:2]
                ])
                before_compaction = None
            if previous:
                changes = {}
                for window in ("300", "10080"):
                    old_used, old_epoch, old_status, _ = previous[window]
                    used, epoch, status, boundary = event[window]
                    if boundary:
                        boundaries[f"{window}:{boundary}"] += 1
                    if (status == old_status == "observed" and epoch is not None
                            and epoch == old_epoch and used >= old_used):
                        changes[window] = used > old_used
                if len(changes) == 2:
                    key = f"5h_{int(changes['300'])}_weekly_{int(changes['10080'])}"
                    transitions[key] += 1
            previous = event
    return {
        "meter_transitions": dict(transitions),
        "boundaries": dict(boundaries),
        "excluded_token_samples": dict(rejected),
        "compaction_before_after_input_cached_pairs": compactions,
        "configuration": [
            {
                "model": model, "effort": effort, "verified_increments": len(samples),
                "median_total": median(row[-1] for row in samples),
                "median_output": median(row[2] for row in samples),
                "median_reasoning_output": median(row[3] for row in samples),
                "cached_input_percent": round(100 * sum(row[1] for row in samples)
                                              / max(1, sum(row[0] for row in samples)), 2),
            }
            for (model, effort), samples in sorted(models.items(), key=str)
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", type=Path)
    arguments = parser.parse_args()
    print(json.dumps(summarize(json.loads(arguments.receipt.read_bytes())), indent=2))
