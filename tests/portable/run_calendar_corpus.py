"""Generate and validate synthetic Calendar batches in a new output directory."""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import platform
from time import perf_counter
import unittest

from calendar_corpus import (
    DEFAULT_SEED, DATES, NORMAL_COUNT, STRESS_COUNT, TIMES, manifest_bytes, probes, specimen_cases,
)
from test_calendar_corpus import check_case, check_probe, check_writer, clock


def run_batch(root, seed, count, repeats, emit):
    started = perf_counter()
    cases = {}
    failures = []
    features = {key: Counter() for key in (
        'category', 'appointments_per_case', 'date', 'weekday', 'time_pair',
        'duration_minutes', 'description_length', 'ordering', 'date_distribution', 'probe_outcome',
    )}
    checks = Counter()
    test = unittest.TestCase()

    def record_failure(name, stage, exc, data):
        failure = {'case': name, 'stage': stage, 'detail': str(exc)}
        if data is not None:
            path = root / f'{name}-{stage}.cln'
            path.write_bytes(data)
            failure.update(file=path.name, sha256=sha256(data).hexdigest())
        failures.append(failure)

    for case in specimen_cases(seed, count):
        features['category'][case.category] += 1
        features['appointments_per_case'][len(case.events)] += 1
        features['ordering']['chronological' if case.index_order == list(range(len(case.events)))
                             else 'reordered'] += 1
        days = {event.day for event in case.events}
        if len(case.events) > 1:
            features['date_distribution']['same-day' if len(days) == 1 else 'multi-day'] += 1
        for event in case.events:
            day, weekday, _, _ = DATES[event.day]
            start, end = TIMES[event.start], TIMES[event.end]
            features['date'][day.isoformat()] += 1
            features['weekday'][weekday] += 1
            features['time_pair'][f'{clock(start)}-{clock(end)}'] += 1
            features['duration_minutes'][end - start] += 1
            features['description_length'][len(event.description)] += 1
        try:
            data = case.build()
        except Exception as exc:
            record_failure(case.name, 'possible-generator-defect', exc, None)
            continue
        cases[case.name] = data
        if emit:
            (root / f'{case.name}.cln').write_bytes(data)
        try:
            check_case(test, case, data)
        except Exception as exc:
            record_failure(case.name, 'parser-or-generator', exc, data)
            continue
        checks['parsed'] += 1
        if case.events:
            try:
                check_writer(test, case, data)
            except Exception as exc:
                record_failure(case.name, 'writer-or-generator', exc, data)
            else:
                checks['writer_round_trip'] += 1
                if case.category == 'exact-fit':
                    checks['writer_overflow_rejected'] += 1

    for probe in probes():
        cases[probe.name] = probe.data
        if emit:
            (root / f'{probe.name}.cln').write_bytes(probe.data)
        features['probe_outcome'][probe.error or 'opaque-description'] += 1
        try:
            check_probe(test, probe, probe.data)
        except Exception as exc:
            record_failure(probe.name, 'parser-or-unresolved-behavior', exc, probe.data)
        else:
            checks['probes_passed'] += 1

    if len(set(cases.values())) != len(cases):
        record_failure('batch', 'possible-generator-defect', 'duplicate specimen bytes', None)

    for repeat in range(1, repeats):
        regenerated = ((case.name, case.build) for case in specimen_cases(seed, count))
        for name, build in regenerated:
            try:
                data = build()
            except Exception as exc:
                record_failure(name, f'repeat-{repeat}-generator', exc, None)
                continue
            if data != cases.get(name):
                record_failure(name, f'repeat-{repeat}-mismatch', 'bytes differ', data)
            else:
                checks['byte_identity_comparisons'] += 1
        for probe in probes():
            if probe.data != cases[probe.name]:
                record_failure(probe.name, f'repeat-{repeat}-mismatch', 'bytes differ', probe.data)
            else:
                checks['byte_identity_comparisons'] += 1

    hashes = {name: sha256(data).hexdigest() for name, data in cases.items()}
    manifest = manifest_bytes(hashes)
    if emit:
        (root / 'sha256.txt').write_bytes(manifest)
    return {
        'seed': seed,
        'valid_requested': count,
        'distinct_specimens': len(set(cases.values())),
        'generations': repeats,
        'manifest_sha256': sha256(manifest).hexdigest(),
        'coverage': features,
        'checks_passed': checks,
        'failures': failures,
        'elapsed_seconds': round(perf_counter() - started, 3),
    }, set(hashes.values())


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path, help='new directory for report and failure specimens')
    parser.add_argument('--seed', type=int, action='append', help='repeat for multiple seeds')
    parser.add_argument('--stress', action='store_true', help=f'{STRESS_COUNT} valid cases per seed')
    parser.add_argument('--repeat', type=int, default=2, help='generations per seed (default: 2)')
    parser.add_argument('--emit', action='store_true', help='also save all CLNs and their hashes')
    args = parser.parse_args(argv)
    if args.repeat < 1:
        parser.error('--repeat must be positive')
    seeds = args.seed or [DEFAULT_SEED]
    if len(set(seeds)) != len(seeds):
        parser.error('use --repeat to regenerate a seed')
    args.output.mkdir()
    batches = []
    distinct = set()
    for seed in seeds:
        root = args.output / f'seed-{seed}'
        root.mkdir()
        batch, hashes = run_batch(root, seed, STRESS_COUNT if args.stress else NORMAL_COUNT,
                                  args.repeat, args.emit)
        batches.append(batch)
        distinct.update(hashes)
    report = {
        'python': platform.python_version(),
        'system': platform.system(),
        'mode': 'stress' if args.stress else 'normal',
        'emit': args.emit,
        'distinct_specimens_across_batches': len(distinct),
        'batches': batches,
    }
    (args.output / 'report.json').write_bytes(
        (json.dumps(report, indent=2, sort_keys=True) + '\n').encode('utf-8'))
    return int(any(batch['failures'] for batch in batches))


if __name__ == '__main__':
    raise SystemExit(main())
