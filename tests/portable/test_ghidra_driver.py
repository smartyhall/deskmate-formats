"""Portable probes for the Ghidra import driver's supervision logic.

These tests never start a JVM. The driver's supervisor mode is pure Python: it
validates its inputs, spawns a worker, validates that worker's receipt against
the attempt, the input and the project, reconciles the receipt with the
worker's exit status and decides a terminal outcome. Faking the worker is
therefore a faithful test of the part that decides whether a run is a success,
and it lets us exercise failures that are hard to provoke with a real Ghidra
installation: hung workers, crashed workers, a receipt left behind by an
earlier attempt, malformed receipts and locked projects.
"""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    'ghidra_dos_import', ROOT / 'tools/ghidra/ghidra_dos_import.py'
)
driver = importlib.util.module_from_spec(spec)
sys.path.insert(0, str(ROOT / 'src'))
spec.loader.exec_module(driver)

SHA = 'a' * 64


def summary(**overrides):
    base = {
        'name': 'PROGRAM',
        'language_id': 'x86:LE:16:Real Mode',
        'compiler_spec': 'default',
        'image_base': '1000:0000',
        'min_address': '1000:0000',
        'max_address': '1012:0000',
        'blocks': [{'name': 'CODE_0', 'start': '1000:0000', 'end': '1000:00ff',
                    'size': 0x100, 'initialized': True, 'read': True,
                    'write': False, 'execute': True}],
        'instruction_count': 0,
        'function_count': 0,
        'content_sha256': 'b' * 64,
        'block_count': 1,
        'project_path': '/PROGRAM',
    }
    base.update(overrides)
    return base


def envelope(payload, *, attempt, sha, project, project_dir):
    """Add the fields every receipt must carry, leaving the outcome intact."""
    body = dict(payload)
    body.setdefault('schema', driver.RECEIPT_SCHEMA)
    body.setdefault('tool', 'tools/ghidra/ghidra_dos_import.py')
    body.setdefault('attempt', {'id': attempt, 'started_utc': '2026-11-27T00:00:00Z'})
    body.setdefault('input', {'name': 'SPECIMEN.EXE', 'size': 64, 'sha256': sha,
                              'expected_sha256': None, 'matches_expected': True})
    body.setdefault('requested', {'language': driver.DEFAULT_LANGUAGE,
                                  'analyze': False, 'project': project,
                                  'project_dir': project_dir})
    return body


class FakeWorker:
    """A stand-in for ``_spawn`` that behaves like a worker process."""

    def __init__(self, receipts=None, reopen=None, returncode=0, stderr='',
                 stamp=True):
        self.receipts = list(receipts or [])
        self.reopen = list(reopen or [])
        self.returncode = returncode
        self.stderr = stderr
        self.stamp = stamp
        self.calls = []

    def __call__(self, mode_args, timeout, python=None):
        self.calls.append((list(mode_args), timeout))
        attempt = None
        if '--attempt-id' in mode_args:
            attempt = mode_args[mode_args.index('--attempt-id') + 1]
        if '--import-worker' in mode_args:
            output = Path(mode_args[mode_args.index('--output') + 1])
            source = Path(mode_args[mode_args.index('--input') + 1])
            payload = self.receipts.pop(0)
            if payload is not None:
                body = dict(payload)
                if self.stamp:
                    body = envelope(
                        body,
                        attempt=attempt,
                        sha=driver._sha256(source),
                        project=mode_args[mode_args.index('--project') + 1],
                        project_dir=mode_args[mode_args.index('--project-dir') + 1],
                    )
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(json.dumps(body), encoding='utf-8')
            return driver.subprocess.CompletedProcess(
                mode_args, self.returncode, '', self.stderr), False
        payload = self.reopen.pop(0)
        if isinstance(payload, Exception):
            return payload, True
        if isinstance(payload, dict):
            payload = dict(payload)
            # The real worker echoes these fields. Tests omit them to simulate
            # a payload that does not name its attempt or its project, so they
            # are only supplied here when a test has not replaced them.
            payload.setdefault('schema', driver.RECEIPT_SCHEMA)
            payload.setdefault('mode', 'reopen_only')
            payload.setdefault('attempt_id', attempt)
            payload.setdefault('project', {
                'name': mode_args[mode_args.index('--project') + 1],
                'dir': mode_args[mode_args.index('--project-dir') + 1],
            })
        return driver.subprocess.CompletedProcess(
            mode_args, 0 if payload.get('ok') is True else 1,
            json.dumps(payload), ''
        ), False


class DriverTestCase(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.input = self.dir / 'SPECIMEN.EXE'
        self.input.write_bytes(b'MZ' + bytes(62))
        self.output = self.dir / 'receipt.json'

    def tearDown(self):
        for path in sorted(self.dir.rglob('*'), key=lambda p: len(p.parts),
                           reverse=True):
            path.unlink() if path.is_file() else path.rmdir()
        self.dir.rmdir()

    def run_main(self, worker, *extra):
        original = driver._spawn
        driver._spawn = worker
        try:
            return driver.main([
                '--project-dir', str(self.dir / 'projects'),
                '--project', 'probe',
                '--input', str(self.input),
                '--output', str(self.output),
                '--timeout', '5',
                '--lock-wait', '1',
                *extra,
            ])
        finally:
            driver._spawn = original

    def receipt(self):
        return json.loads(self.output.read_text(encoding='utf-8'))


def imported(**overrides):
    payload = {
        'outcome': 'succeeded',
        'project': {'name': 'probe', 'dir': str(Path('/projects'))},
        'resolved_language': {'language_id': driver.DEFAULT_LANGUAGE},
        'program': summary(),
        'persistence': {'save': 'ok', 'close': 'ok'},
        'toolchain': {'requested': {}, 'resolved': {}},
    }
    payload.update(overrides)
    return payload


class ValidationTests(DriverTestCase):
    def args(self, **overrides):
        parser = driver.build_parser()
        base = {
            'project_dir': str(self.dir), 'project': 'probe',
            'input': str(self.input), 'language': driver.DEFAULT_LANGUAGE,
            'timeout': 10, 'expect_sha256': None, 'reopen_only': False,
            'allow_existing_project': False, 'output': str(self.output),
            'import_worker': False,
        }
        base.update(overrides)
        return parser.parse_args([
            '--project-dir', base['project_dir'], '--project', base['project'],
            '--input', base['input'], '--language', base['language'],
            '--timeout', str(base['timeout']), '--output', base['output'],
        ] + (['--expect-sha256', base['expect_sha256']] if base['expect_sha256'] else [])
          + (['--allow-existing-project'] if base['allow_existing_project'] else []))

    def test_accepts_a_well_formed_request(self):
        self.assertEqual(driver.validate_args(self.args()), [])

    def test_rejects_unsafe_project_names(self):
        for name in ('..\\evil', 'a/b', '.hidden', '', 'x' * 65):
            with self.subTest(name=name):
                self.assertTrue(driver.validate_args(self.args(project=name)))

    def test_rejects_a_vague_language(self):
        for language in ('', 'x86', 'x86:LE'):
            with self.subTest(language=language):
                self.assertTrue(driver.validate_args(self.args(language=language)))

    def test_rejects_impossible_timeouts(self):
        for timeout in (0, -1, 200000):
            with self.subTest(timeout=timeout):
                self.assertTrue(driver.validate_args(self.args(timeout=timeout)))

    def test_rejects_a_malformed_digest(self):
        self.assertTrue(driver.validate_args(self.args(expect_sha256='abc')))

    def test_rejects_missing_empty_and_directory_inputs(self):
        missing = self.dir / 'absent.bin'
        empty = self.dir / 'empty.bin'
        empty.write_bytes(b'')
        for candidate in (missing, empty, self.dir):
            with self.subTest(path=candidate.name):
                self.assertTrue(driver.validate_args(self.args(input=str(candidate))))

    def test_requires_an_explicit_receipt_path(self):
        # A default name in the working directory is shared between
        # invocations, which is how one attempt's receipt is mistaken for
        # another's.
        parser = driver.build_parser()
        args = parser.parse_args([
            '--project-dir', str(self.dir), '--project', 'probe',
            '--input', str(self.input),
        ])
        errors = driver.validate_args(args)
        self.assertTrue(any('--output is required' in error for error in errors))

    def test_refuses_an_unexpected_existing_project(self):
        (self.dir / 'probe.gpr').write_bytes(b'x')
        errors = driver.validate_args(self.args())
        self.assertTrue(any('already exists' in error for error in errors))
        self.assertEqual(
            driver.validate_args(self.args(allow_existing_project=True)), []
        )

    def test_usage_error_writes_a_receipt_and_exits_two(self):
        code = driver.main(['--project-dir', str(self.dir), '--project', 'bad/name',
                            '--input', str(self.input),
                            '--output', str(self.output)])
        self.assertEqual(code, driver.EXIT_USAGE)
        receipt = self.receipt()
        self.assertEqual(receipt['outcome'], 'invalid_request')
        self.assertIn('attempt', receipt)


class HashIdentityTests(DriverTestCase):
    def test_worker_refuses_a_mismatched_digest_before_starting_the_jvm(self):
        # run_import hashes the input and returns before importing pyghidra, so
        # this exercises identity checking without a Ghidra installation.
        args = driver.build_parser().parse_args([
            '--project-dir', str(self.dir / 'projects'), '--project', 'probe',
            '--input', str(self.input), '--expect-sha256', '0' * 64,
        ])
        receipt = driver.run_import(args)
        self.assertEqual(receipt['outcome'], 'input_mismatch')
        self.assertFalse(receipt['input']['matches_expected'])
        self.assertIn('SHA-256', receipt['error'])
        self.assertNotIn('toolchain', receipt)

    def test_supervisor_refuses_a_mismatched_digest_without_spawning(self):
        worker = FakeWorker(receipts=[imported()])
        code = self.run_main(worker, '--expect-sha256', '0' * 64)
        self.assertEqual(code, driver.EXIT_USAGE)
        receipt = self.receipt()
        self.assertEqual(receipt['outcome'], 'input_mismatch')
        self.assertFalse(receipt['worker_started'])
        self.assertEqual(worker.calls, [])


class ReceiptIdentityTests(DriverTestCase):
    def test_success_publishes_an_attempt_scoped_receipt(self):
        worker = FakeWorker(receipts=[imported()])
        self.assertEqual(self.run_main(worker), driver.EXIT_OK)
        receipt = self.receipt()
        self.assertEqual(receipt['outcome'], 'succeeded')
        self.assertRegex(receipt['attempt']['id'], driver.ATTEMPT_ID_RE)
        self.assertEqual(receipt['worker']['exit_code'], 0)
        self.assertEqual(receipt['worker']['readable'], True)
        work_dir = Path(receipt['attempt']['work_dir'])
        self.assertTrue(work_dir.is_dir())
        self.assertEqual(work_dir.parent.name, 'receipt.json.attempts')
        self.assertTrue((work_dir / 'import-worker.json').is_file())

    def test_two_attempts_do_not_share_a_working_directory(self):
        first = FakeWorker(receipts=[imported()])
        self.run_main(first)
        first_dir = Path(self.receipt()['attempt']['work_dir'])
        second = FakeWorker(receipts=[imported()])
        self.run_main(second)
        second_dir = Path(self.receipt()['attempt']['work_dir'])
        self.assertNotEqual(first_dir, second_dir)
        self.assertTrue(first_dir.is_dir())

    def test_a_receipt_left_at_the_old_predictable_path_is_ignored(self):
        # The previous implementation wrote <output>.import.json. A worker that
        # crashes before writing must not inherit an earlier success.
        stale = Path(str(self.output) + '.import.json')
        stale.write_text(json.dumps(imported()), encoding='utf-8')
        worker = FakeWorker(receipts=[None], returncode=134, stderr='JVM died')
        self.assertEqual(self.run_main(worker), driver.EXIT_IMPORT_FAILED)
        receipt = self.receipt()
        self.assertEqual(receipt['outcome'], 'import_failed')
        self.assertFalse(receipt['worker']['readable'])
        self.assertIn('JVM died', receipt['worker_stderr'])
        self.assertEqual(receipt['worker']['exit_code'], 134)

    def test_a_success_claim_cannot_outrank_a_failed_worker_exit(self):
        worker = FakeWorker(receipts=[imported()], returncode=1, stderr='boom')
        self.assertEqual(self.run_main(worker), driver.EXIT_RECEIPT_REJECTED)
        receipt = self.receipt()
        self.assertEqual(receipt['outcome'], 'receipt_inconsistent')
        self.assertEqual(receipt['claimed_outcome'], 'succeeded')
        self.assertEqual(receipt['worker']['exit_code'], 1)

    def test_a_zero_exit_cannot_promote_a_failed_receipt(self):
        worker = FakeWorker(
            receipts=[{'outcome': 'analysis_failed', 'program': summary(),
                       'analysis': {'requested': True, 'ok': False, 'error': 'boom'}}],
            returncode=0,
        )
        self.assertEqual(self.run_main(worker, '--analyze'),
                         driver.EXIT_ANALYSIS_FAILED)
        receipt = self.receipt()
        self.assertEqual(receipt['outcome'], 'analysis_failed')
        self.assertTrue(receipt['worker_exit_disagrees'])

    def test_a_receipt_from_another_attempt_is_rejected(self):
        payload = imported()
        payload['attempt'] = {'id': 'f' * 32,
                              'started_utc': '2026-11-27T00:00:00Z'}
        payload['input'] = {'name': 'SPECIMEN.EXE', 'size': 64,
                            'sha256': driver._sha256(self.input),
                            'expected_sha256': None, 'matches_expected': True}
        payload['requested'] = {'language': driver.DEFAULT_LANGUAGE,
                                'analyze': False, 'project': 'probe',
                                'project_dir': str(self.dir / 'projects')}

        def spawn(mode_args, timeout, python=None):
            return self._write_and_return(mode_args, payload)

        self.assertEqual(self.run_main(spawn), driver.EXIT_RECEIPT_REJECTED)
        receipt = self.receipt()
        self.assertEqual(receipt['outcome'], 'receipt_malformed')
        self.assertTrue(any('different attempt' in problem
                            for problem in receipt['schema_problems']))

    def _write_and_return(self, mode_args, payload):
        output = Path(mode_args[mode_args.index('--output') + 1])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload), encoding='utf-8')
        return driver.subprocess.CompletedProcess(mode_args, 0, '', ''), False

    def test_a_receipt_describing_another_input_is_rejected(self):
        payload = imported()
        payload['input'] = {'name': 'OTHER.EXE', 'size': 1, 'sha256': 'c' * 64,
                            'expected_sha256': None, 'matches_expected': True}
        payload['attempt'] = {'id': 'a' * 32, 'started_utc': 'x'}
        payload['requested'] = {'language': driver.DEFAULT_LANGUAGE,
                                'analyze': False, 'project': 'probe',
                                'project_dir': str(self.dir / 'projects')}

        def spawn(mode_args, timeout, python=None):
            return self._write_and_return(mode_args, payload)

        self.assertEqual(self.run_main(spawn), driver.EXIT_RECEIPT_REJECTED)
        receipt = self.receipt()
        self.assertTrue(any('input.sha256' in problem
                            for problem in receipt['schema_problems']))

    def test_a_receipt_without_required_fields_is_rejected(self):
        worker = FakeWorker(receipts=[{'outcome': 'succeeded'}], stamp=False)
        self.assertEqual(self.run_main(worker), driver.EXIT_RECEIPT_REJECTED)
        receipt = self.receipt()
        self.assertEqual(receipt['outcome'], 'receipt_malformed')
        self.assertTrue(any(problem.startswith('attempt.')
                            for problem in receipt['schema_problems']))
        self.assertTrue(any(problem.startswith('input.')
                            for problem in receipt['schema_problems']))

    def test_an_unpersisted_analysis_is_not_a_success(self):
        worker = FakeWorker(
            receipts=[imported(persistence={'save': 'ok', 'close': 'failed'})]
        )
        self.assertEqual(self.run_main(worker), driver.EXIT_RECEIPT_REJECTED)
        receipt = self.receipt()
        self.assertEqual(receipt['outcome'], 'receipt_malformed')
        self.assertTrue(any('persistence.save' in problem or 'persistence.close' in problem
                            for problem in receipt['schema_problems']))
        # The worker's own persistence outcome is preserved so the failure is
        # diagnosable, not just rejected.
        self.assertEqual(receipt['persistence']['close'], 'failed')

    def test_a_persisted_analysis_with_a_failed_save_is_reported_as_such(self):
        worker = FakeWorker(
            receipts=[imported(persistence={'save': 'failed', 'close': 'ok'})]
        )
        self.assertEqual(self.run_main(worker), driver.EXIT_RECEIPT_REJECTED)
        self.assertEqual(self.receipt()['outcome'], 'receipt_malformed')

    def test_timeout_preserves_partial_evidence_without_reading_it(self):
        def spawn(mode_args, timeout, python=None):
            output = Path(mode_args[mode_args.index('--output') + 1])
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(imported()), encoding='utf-8')
            return driver.subprocess.TimeoutExpired(mode_args, timeout), True

        self.assertEqual(self.run_main(spawn), driver.EXIT_TIMEOUT)
        receipt = self.receipt()
        self.assertEqual(receipt['outcome'], 'import_timeout')
        self.assertIn('unknown state', receipt['guidance'])
        self.assertIn('lock_after_failure', receipt)
        self.assertTrue(receipt['partial_worker_receipt']['present'])
        self.assertFalse(receipt['partial_worker_receipt']['used_as_result'])
        self.assertTrue(Path(receipt['partial_worker_receipt']['path']).is_file())


class ReopenTests(DriverTestCase):
    # Sentinels for ``_spawn_reopen``: fill this field in from the worker's
    # arguments, or leave it out of the payload entirely.
    STAMP = object()
    OMIT = object()

    def setUp(self):
        super().setUp()
        self.imported = imported()

    def test_matching_reopen_is_ok_and_carries_the_attempt(self):
        worker = FakeWorker(
            receipts=[self.imported],
            reopen=[{'ok': True, 'program': summary(), 'project_files': ['/PROGRAM']}],
        )
        self.assertEqual(self.run_main(worker, '--reopen-check'), driver.EXIT_OK)
        reopen = self.receipt()['reopen']
        self.assertEqual(reopen['status'], 'ok')
        self.assertTrue(reopen['comparison']['match'])
        self.assertEqual(reopen['attempt_id'], self.receipt()['attempt']['id'])
        self.assertEqual(reopen['project_files'], ['/PROGRAM'])

    def test_the_reopen_carries_the_expected_content_digest(self):
        worker = FakeWorker(
            receipts=[self.imported],
            reopen=[{'ok': True, 'program': summary(), 'project_files': ['/PROGRAM']}],
        )
        self.run_main(worker, '--reopen-check')
        reopen_args = worker.calls[1][0]
        digest = reopen_args[reopen_args.index('--expect-program-sha256') + 1]
        self.assertEqual(digest, 'b' * 64)
        attempt = reopen_args[reopen_args.index('--attempt-id') + 1]
        self.assertEqual(attempt, self.receipt()['attempt']['id'])

    def test_a_payload_from_another_attempt_is_not_a_reopen(self):
        worker = FakeWorker(
            receipts=[self.imported],
            reopen=[{'ok': True, 'attempt_id': 'f' * 32, 'program': summary(),
                     'project_files': ['/PROGRAM']}],
        )
        self.assertEqual(self.run_main(worker, '--reopen-check'),
                         driver.EXIT_RECEIPT_REJECTED)
        reopen = self.receipt()['reopen']
        self.assertEqual(reopen['status'], 'reopen_malformed')
        self.assertEqual(reopen['reason'], 'payload_malformed')
        self.assertIn('attempt_id', ' '.join(reopen['errors']))

    def _spawn_reopen(self, payload, exit_code, *, attempt_id=STAMP,
                      project=STAMP):
        """A reopen worker that emits exactly this payload.

        ``attempt_id`` and ``project`` default to the values the driver asked
        for, because that is what the real worker echoes. Passing a value
        overrides it, and the ``OMIT`` sentinel removes the field, so a test can
        express a payload that never names its attempt or names another project.
        ``None`` as the payload writes unreadable output.
        """
        imported = self.imported
        sentinel = self.STAMP
        omit = self.OMIT

        def spawn(mode_args, timeout, python=None):
            if '--import-worker' in mode_args:
                output = Path(mode_args[mode_args.index('--output') + 1])
                output.parent.mkdir(parents=True, exist_ok=True)
                body = envelope(
                    dict(imported),
                    attempt=mode_args[mode_args.index('--attempt-id') + 1],
                    sha=driver._sha256(
                        Path(mode_args[mode_args.index('--input') + 1])
                    ),
                    project='probe',
                    project_dir=mode_args[mode_args.index('--project-dir') + 1],
                )
                output.write_text(json.dumps(body), encoding='utf-8')
                return driver.subprocess.CompletedProcess(
                    mode_args, 0, '', ''
                ), False
            if not isinstance(payload, dict):
                return driver.subprocess.CompletedProcess(
                    mode_args, exit_code, 'not json', ''
                ), False
            body = dict(payload)
            for field, wanted, fallback in (
                ('attempt_id', attempt_id,
                 mode_args[mode_args.index('--attempt-id') + 1]),
                ('project', project, {
                    'name': mode_args[mode_args.index('--project') + 1],
                    'dir': mode_args[mode_args.index('--project-dir') + 1],
                }),
            ):
                if wanted is omit:
                    body.pop(field, None)
                elif wanted is sentinel:
                    body.setdefault(field, fallback)
                else:
                    body[field] = wanted
            return driver.subprocess.CompletedProcess(
                mode_args, exit_code, json.dumps(body), ''
            ), False

        return spawn

    def _reopen_payload(self, **overrides):
        """A reopen payload with every field the real worker writes."""
        body = {
            'schema': driver.RECEIPT_SCHEMA,
            'mode': 'reopen_only',
            'ok': True,
            'program': summary(),
            'project_files': ['/PROGRAM'],
        }
        body.update(overrides)
        return body

    def test_a_success_payload_without_an_attempt_id_is_rejected(self):
        # A zero-exit success payload that names no attempt at all is the case
        # the independent reviewer found: absence of identity was being read as
        # agreement with the expected attempt.
        self.assertEqual(
            self.run_main(
                self._spawn_reopen(
                    self._reopen_payload(), 0, attempt_id=self.OMIT
                ),
                '--reopen-check',
            ),
            driver.EXIT_RECEIPT_REJECTED,
        )
        receipt = self.receipt()
        self.assertEqual(receipt['outcome'], 'receipt_malformed')
        self.assertEqual(receipt['reopen']['status'], 'reopen_malformed')
        self.assertIn('attempt_id', ' '.join(receipt['reopen']['errors']))

    def test_a_null_attempt_id_is_recorded_as_an_attempt_identity_problem(self):
        self.run_main(
            self._spawn_reopen(
                self._reopen_payload(), 0, attempt_id=None
            ),
            '--reopen-check',
        )
        errors = self.receipt()['reopen']['errors']
        self.assertTrue(
            any('None' in e and 'attempt_id' in e for e in errors), errors
        )

    def test_a_truthy_but_not_boolean_ok_is_rejected(self):
        for value in ('yes', 1, [], {}):
            with self.subTest(ok=value):
                payload = self._reopen_payload(ok=value)
                self.assertEqual(
                    self.run_main(self._spawn_reopen(payload, 0), '--reopen-check'),
                    driver.EXIT_RECEIPT_REJECTED,
                )
                receipt = self.receipt()
                self.assertEqual(receipt['outcome'], 'receipt_malformed')
                self.assertIn(
                    'not a boolean', ' '.join(receipt['reopen']['errors'])
                )

    def test_a_success_payload_without_a_program_fingerprint_is_rejected(self):
        payload = self._reopen_payload(program={'project_path': '/PROGRAM'})
        self.assertEqual(
            self.run_main(self._spawn_reopen(payload, 0), '--reopen-check'),
            driver.EXIT_RECEIPT_REJECTED,
        )
        errors = ' '.join(self.receipt()['reopen']['errors'])
        self.assertIn('program.content_sha256', errors)
        self.assertIn('program.block_count', errors)

    def test_a_payload_whose_fingerprint_drifted_is_a_mismatch(self):
        # The worker was asked to corroborate 'b' * 64 and reported 'c' * 64.
        # That is a well-formed document describing different bytes, so the
        # result is a mismatch that names the field, not an unreadable payload.
        payload = self._reopen_payload(program=summary(content_sha256='c' * 64))
        self.assertEqual(
            self.run_main(self._spawn_reopen(payload, 0), '--reopen-check'),
            driver.EXIT_REOPEN_MISMATCH,
        )
        reopen = self.receipt()['reopen']
        self.assertEqual(reopen['status'], 'reopen_mismatch')
        self.assertEqual(
            reopen['comparison']['differences'],
            [{'field': 'content_sha256', 'before': 'b' * 64, 'after': 'c' * 64}],
        )

    def test_a_payload_for_another_project_is_rejected(self):
        self.assertEqual(
            self.run_main(
                self._spawn_reopen(
                    self._reopen_payload(),
                    0,
                    project={'name': 'someone-else',
                             'dir': str((self.dir / 'projects').resolve())},
                ),
                '--reopen-check',
            ),
            driver.EXIT_RECEIPT_REJECTED,
        )
        self.assertIn(
            'project.name', ' '.join(self.receipt()['reopen']['errors'])
        )

    def test_an_unreadable_payload_is_a_failure_not_a_success(self):
        self.assertEqual(
            self.run_main(self._spawn_reopen(None, 0), '--reopen-check'),
            driver.EXIT_REOPEN_FAILED,
        )
        reopen = self.receipt()['reopen']
        self.assertEqual(reopen['status'], 'reopen_failed')
        self.assertEqual(reopen['reason'], 'payload_unreadable')
        self.assertFalse(reopen.get('comparison'))

    def test_a_failure_payload_from_a_zero_exit_worker_is_still_a_failure(self):
        payload = self._reopen_payload(ok=False, reason='program_missing',
                                       error='/PROGRAM is not present')
        self.assertEqual(
            self.run_main(self._spawn_reopen(payload, 0), '--reopen-check'),
            driver.EXIT_REOPEN_FAILED,
        )
        reopen = self.receipt()['reopen']
        self.assertEqual(reopen['reason'], 'program_missing')
        self.assertTrue(reopen['worker_exit_disagrees'])

    def test_a_reopen_success_claim_with_a_failed_exit_is_rejected(self):
        # Everything else about this payload is well formed, so the only
        # disagreement is between the claim and the process exit status.
        spawn = self._spawn_reopen(self._reopen_payload(), 3)
        self.assertEqual(self.run_main(spawn, '--reopen-check'),
                         driver.EXIT_RECEIPT_REJECTED)
        receipt = self.receipt()
        self.assertEqual(receipt['outcome'], 'receipt_malformed')
        self.assertEqual(receipt['reopen']['reason'], 'exit_disagrees')

    def test_differing_bytes_are_a_mismatch_even_when_the_summary_matches(self):
        drifted = summary(content_sha256='c' * 64)
        worker = FakeWorker(
            receipts=[self.imported],
            reopen=[{'ok': True, 'program': drifted, 'project_files': ['/PROGRAM']}],
        )
        self.assertEqual(self.run_main(worker, '--reopen-check'),
                         driver.EXIT_REOPEN_MISMATCH)
        receipt = self.receipt()
        self.assertEqual(receipt['outcome'], 'reopen_mismatch')
        self.assertEqual(receipt['reopen']['comparison']['differences'],
                         [{'field': 'content_sha256', 'before': 'b' * 64,
                           'after': 'c' * 64}])

    def test_a_different_program_identity_is_a_mismatch(self):
        other = summary(language_id='x86:LE:32:default', block_count=2,
                        content_sha256='d' * 64, name='OTHER')
        worker = FakeWorker(
            receipts=[self.imported],
            reopen=[{'ok': True, 'program': other, 'project_files': ['/OTHER']}],
        )
        self.assertEqual(self.run_main(worker, '--reopen-check'),
                         driver.EXIT_REOPEN_MISMATCH)
        fields = {d['field'] for d in self.receipt()['reopen']['comparison']['differences']}
        self.assertEqual(fields, {'language_id', 'block_count', 'content_sha256'})

    def test_missing_program_after_reopen_is_a_failure(self):
        worker = FakeWorker(
            receipts=[self.imported],
            reopen=[{'ok': False, 'reason': 'program_missing',
                     'error': '/PROGRAM is not present after reopening',
                     'project_files': []}],
        )
        self.assertEqual(self.run_main(worker, '--reopen-check'),
                         driver.EXIT_REOPEN_FAILED)
        receipt = self.receipt()
        self.assertEqual(receipt['outcome'], 'reopen_failed')
        self.assertEqual(receipt['reopen']['reason'], 'program_missing')

    def test_a_missing_project_is_not_created_by_a_reopen(self):
        worker = FakeWorker(
            receipts=[self.imported],
            reopen=[{'ok': False, 'reason': 'project_missing',
                     'error': 'project probe does not exist',
                     'project_files': []}],
        )
        self.assertEqual(self.run_main(worker, '--reopen-check'),
                         driver.EXIT_REOPEN_FAILED)
        self.assertEqual(self.receipt()['reopen']['reason'], 'project_missing')

    def test_reopen_timeout_is_a_failure(self):
        worker = FakeWorker(
            receipts=[self.imported],
            reopen=[driver.subprocess.TimeoutExpired(['worker'], 5)],
        )
        self.assertEqual(self.run_main(worker, '--reopen-check'),
                         driver.EXIT_REOPEN_FAILED)
        self.assertEqual(self.receipt()['reopen']['reason'], 'timeout')

    def test_a_locked_project_is_retried_before_failing(self):
        worker = FakeWorker(
            receipts=[self.imported],
            reopen=[
                {'ok': False, 'reason': 'project_locked_or_unopenable',
                 'error': 'LockException'},
                {'ok': True, 'program': summary(), 'project_files': ['/PROGRAM']},
            ],
        )
        self.assertEqual(self.run_main(worker, '--reopen-check'), driver.EXIT_OK)
        reopen = self.receipt()['reopen']
        self.assertEqual(reopen['attempts'], 2)
        self.assertEqual(len(reopen['history']), 2)
        self.assertEqual(reopen['status'], 'ok')

    def test_an_import_without_a_program_path_cannot_be_verified(self):
        worker = FakeWorker(receipts=[imported(program={})], reopen=[])
        self.assertEqual(self.run_main(worker, '--reopen-check'),
                         driver.EXIT_RECEIPT_REJECTED)


class ReopenReceiptTests(DriverTestCase):
    """A published receipt must not carry an unverifiable reopen section."""

    def receipt_with(self, reopen):
        return driver.validate_receipt(
            envelope(
                imported(),
                attempt='a' * 32,
                sha=SHA,
                project='probe',
                project_dir='/projects',
            ) | {'reopen': reopen},
            attempt_id='a' * 32,
            input_sha256=SHA,
            project='probe',
        )

    def test_a_reopen_section_without_an_attempt_is_a_problem(self):
        problems = self.receipt_with(
            {'status': 'ok', 'comparison': {'match': True, 'complete': True}}
        )
        self.assertTrue(any('reopen.attempt_id' in p for p in problems), problems)

    def test_a_reopen_section_for_another_attempt_is_a_problem(self):
        problems = self.receipt_with(
            {'attempt_id': 'b' * 32, 'status': 'ok',
             'comparison': {'match': True, 'complete': True}}
        )
        self.assertTrue(any('reopen.attempt_id' in p for p in problems), problems)

    def test_a_reopen_claimed_ok_without_a_complete_comparison_is_a_problem(self):
        for comparison in (
            {'match': True},
            {'match': 'yes', 'complete': 1},
            {'match': True, 'complete': False},
        ):
            with self.subTest(comparison=comparison):
                problems = self.receipt_with(
                    {'attempt_id': 'a' * 32, 'status': 'ok',
                     'comparison': comparison}
                )
                self.assertTrue(
                    any('reopen.comparison' in p for p in problems), problems
                )

    def test_a_well_formed_reopen_section_is_accepted(self):
        problems = self.receipt_with(
            {'attempt_id': 'a' * 32, 'status': 'ok',
             'comparison': {'match': True, 'complete': True}}
        )
        self.assertEqual(problems, [])

    def test_an_unknown_reopen_status_is_a_problem(self):
        problems = self.receipt_with(
            {'attempt_id': 'a' * 32, 'status': 'probably_fine'}
        )
        self.assertTrue(any('reopen.status' in p for p in problems), problems)


class LockTests(DriverTestCase):
    def test_lock_files_are_reported_without_being_touched(self):
        projects = self.dir / 'projects'
        projects.mkdir()
        lock = projects / 'probe.lock'
        lock.write_text('<lock><host>HOST</host><user>USER</user></lock>',
                        encoding='utf-8')
        state = driver.project_lock_state(projects, 'probe')
        self.assertTrue(state['present'])
        self.assertEqual(state['files'][0]['owner_record']['host'], 'HOST')
        self.assertFalse(state['ownership_established'])
        self.assertEqual(state['action_taken'], 'none')
        self.assertTrue(lock.exists())
        self.assertEqual(sorted(p.name for p in projects.iterdir()), ['probe.lock'])

    def test_the_driver_offers_no_lock_reclamation(self):
        # A flag is not proof of ownership, so the driver does not move a lock
        # at all; recovery has to be a separately reviewed operation.
        self.assertFalse(hasattr(driver, 'quarantine_lock'))
        with self.assertRaises(SystemExit) as raised:
            driver.build_parser().parse_args(
                ['--project-dir', 'x', '--project', 'p', '--input', 'i',
                 '--quarantine-stale-lock']
            )
        self.assertEqual(raised.exception.code, 2)

    def test_a_lock_sample_is_recorded_on_success_and_left_alone(self):
        projects = self.dir / 'projects'
        projects.mkdir()
        lock = projects / 'probe.lock'
        lock.write_text('owner', encoding='utf-8')
        worker = FakeWorker(receipts=[imported()])
        self.assertEqual(self.run_main(worker), driver.EXIT_OK)
        receipt = self.receipt()
        self.assertTrue(receipt['lock_after_exit']['present'])
        self.assertEqual(receipt['lock_after_exit']['action_taken'], 'none')
        self.assertTrue(lock.exists())
        self.assertEqual(lock.read_text(encoding='utf-8'), 'owner')


class ComparisonTests(unittest.TestCase):
    def test_identical_summaries_match(self):
        result = driver.compare_programs(summary(), summary())
        self.assertTrue(result['match'])
        self.assertTrue(result['complete'])

    def test_every_compared_field_is_reported(self):
        self.assertEqual(
            set(driver.COMPARED_FIELDS),
            {'language_id', 'compiler_spec', 'image_base', 'min_address',
             'max_address', 'block_count', 'content_sha256'},
        )

    def test_a_missing_field_counts_against_the_match(self):
        result = driver.compare_programs(summary(), {'language_id': 'x86:LE:16:Real Mode'})
        self.assertFalse(result['match'])
        self.assertFalse(result['complete'])
        self.assertEqual(len(result['missing']), 6)
        self.assertEqual({entry['field'] for entry in result['missing']},
                         set(driver.COMPARED_FIELDS) - {'language_id'})

    def test_two_incomplete_summaries_do_not_compare_equal(self):
        # Emptiness must not be mistaken for agreement.
        result = driver.compare_programs({}, {})
        self.assertFalse(result['match'])
        self.assertFalse(result['complete'])
        self.assertEqual(len(result['missing']), len(driver.COMPARED_FIELDS))
        self.assertEqual(result['differences'], [])

    def test_a_field_missing_on_one_side_is_reported(self):
        partial = summary()
        del partial['content_sha256']
        result = driver.compare_programs(summary(), partial)
        self.assertFalse(result['match'])
        self.assertEqual(result['missing'][0]['field'], 'content_sha256')
        self.assertEqual(result['missing'][0]['missing_in'], ['reopened'])


class SchemaTests(unittest.TestCase):
    def test_a_well_formed_receipt_has_no_problems(self):
        receipt = envelope(dict(imported()), attempt='a' * 32, sha=SHA,
                           project='probe', project_dir='/projects')
        self.assertEqual(
            driver.validate_receipt(receipt, attempt_id='a' * 32,
                                    input_sha256=SHA, project='probe',
                                    project_dir='/projects'),
            [],
        )

    def test_unknown_outcomes_and_schemas_are_rejected(self):
        receipt = envelope(dict(imported(outcome='fine')), attempt='a' * 32,
                           sha=SHA, project='probe', project_dir='/projects')
        receipt['schema'] = 'ghidra-dos-import/2'
        problems = driver.validate_receipt(receipt, attempt_id='a' * 32)
        self.assertTrue(any('outcome' in problem for problem in problems))
        self.assertTrue(any('schema' in problem for problem in problems))

    def test_every_outcome_has_an_exit_code(self):
        for outcome in driver.OUTCOMES:
            self.assertIn(outcome, driver.EXIT_FOR_OUTCOME)


class MalformedSectionTests(DriverTestCase):
    """A section of the wrong type is a reported defect, not a crash."""

    SECTIONS = ('attempt', 'input', 'requested', 'project', 'program',
                'persistence', 'resolved_language', 'reopen')

    def unit_receipt(self):
        return envelope(dict(imported()), attempt='a' * 32, sha=SHA,
                        project='probe', project_dir='/projects')

    def test_every_section_of_a_wrong_type_is_reported_as_a_shape_problem(self):
        for section in self.SECTIONS:
            for value in ('text', ['text'], 0):
                with self.subTest(section=section, value=value):
                    receipt = self.unit_receipt()
                    receipt[section] = value
                    problems = driver.validate_receipt(
                        receipt, attempt_id='a' * 32, input_sha256=SHA,
                        project='probe', project_dir='/projects',
                    )
                    self.assertTrue(
                        any(problem.startswith(f'{section} is ')
                            and 'not a JSON object' in problem
                            for problem in problems),
                        problems,
                    )

    def test_a_string_program_is_rejected_instead_of_raised(self):
        worker = FakeWorker(receipts=[imported(program='PROGRAM')])
        self.assertEqual(self.run_main(worker), driver.EXIT_RECEIPT_REJECTED)
        receipt = self.receipt()
        self.assertEqual(receipt['outcome'], 'receipt_malformed')
        self.assertTrue(any(problem.startswith('program.')
                            for problem in receipt['schema_problems']))

    def test_a_list_input_section_is_rejected_with_its_shape_named(self):
        worker = FakeWorker(receipts=[imported(input=['SPECIMEN.EXE'])])
        self.assertEqual(self.run_main(worker), driver.EXIT_RECEIPT_REJECTED)
        receipt = self.receipt()
        self.assertEqual(receipt['outcome'], 'receipt_malformed')
        self.assertTrue(any(problem.startswith('input.')
                            for problem in receipt['schema_problems']))
        self.assertTrue(any('input is list' in problem
                            for problem in receipt['schema_problems']))

    def test_a_numeric_requested_section_is_rejected(self):
        worker = FakeWorker(receipts=[imported(requested=7)])
        self.assertEqual(self.run_main(worker), driver.EXIT_RECEIPT_REJECTED)
        receipt = self.receipt()
        self.assertTrue(any('requested is int' in problem
                            for problem in receipt['schema_problems']))


class ParserTests(unittest.TestCase):
    def test_documented_exit_codes_are_distinct(self):
        codes = [driver.EXIT_OK, driver.EXIT_USAGE, driver.EXIT_IMPORT_FAILED,
                 driver.EXIT_TIMEOUT, driver.EXIT_ANALYSIS_FAILED,
                 driver.EXIT_REOPEN_FAILED, driver.EXIT_REOPEN_MISMATCH,
                 driver.EXIT_RECEIPT_REJECTED, driver.EXIT_PERSISTENCE_FAILED]
        self.assertEqual(len(set(codes)), len(codes))
        self.assertIn('Exit codes: 0 ok', driver.build_parser().epilog)

    def test_help_needs_no_ghidra_installation(self):
        import contextlib
        import io
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            with self.assertRaises(SystemExit) as raised:
                driver.build_parser().parse_args(['--help'])
        self.assertEqual(raised.exception.code, 0)
        self.assertIn('--expect-sha256', buffer.getvalue())


if __name__ == '__main__':
    unittest.main()
