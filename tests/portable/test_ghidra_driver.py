"""Portable probes for the Ghidra import driver's supervision logic.

These tests never start a JVM. The driver's supervisor mode is pure Python: it
validates its inputs, spawns a worker, reads that worker's receipt and decides
a result state. Faking the worker is therefore a faithful test of the part that
decides whether a run is a success, and it lets us exercise failures that are
hard to provoke with a real Ghidra installation (hangs, crashes, locked
projects, mismatched reopen payloads).
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


class FakeWorker:
    """A stand-in for ``_spawn`` that behaves like a worker process."""

    def __init__(self, receipts=None, reopen=None, returncode=0, stderr=''):
        self.receipts = list(receipts or [])
        self.reopen = list(reopen or [])
        self.returncode = returncode
        self.stderr = stderr
        self.calls = []

    def __call__(self, mode_args, timeout, python=None):
        self.calls.append((list(mode_args), timeout))
        if '--import-worker' in mode_args:
            output = Path(mode_args[mode_args.index('--output') + 1])
            payload = self.receipts.pop(0)
            if payload is not None:
                output.write_text(json.dumps(payload), encoding='utf-8')
            return driver.subprocess.CompletedProcess(mode_args, self.returncode,
                                                     '', self.stderr), False
        payload = self.reopen.pop(0)
        if isinstance(payload, Exception):
            return payload, True
        return driver.subprocess.CompletedProcess(
            mode_args, 0 if payload.get('ok') else 1, json.dumps(payload), ''
        ), False


class DriverTestCase(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.input = self.dir / 'SPECIMEN.EXE'
        self.input.write_bytes(b'MZ' + bytes(62))
        self.output = self.dir / 'receipt.json'

    def tearDown(self):
        for path in sorted(self.dir.rglob('*'), reverse=True):
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


class ValidationTests(DriverTestCase):
    def args(self, **overrides):
        parser = driver.build_parser()
        base = {
            'project_dir': str(self.dir), 'project': 'probe',
            'input': str(self.input), 'language': driver.DEFAULT_LANGUAGE,
            'timeout': 10, 'expect_sha256': None, 'reopen_only': False,
            'allow_existing_project': False,
        }
        base.update(overrides)
        return parser.parse_args([
            '--project-dir', base['project_dir'], '--project', base['project'],
            '--input', base['input'], '--language', base['language'],
            '--timeout', str(base['timeout']),
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

    def test_refuses_an_unexpected_existing_project(self):
        (self.dir / 'probe.gpr').write_bytes(b'x')
        errors = driver.validate_args(self.args())
        self.assertTrue(any('already exists' in error for error in errors))
        self.assertEqual(
            driver.validate_args(self.args(allow_existing_project=True)), []
        )

    def test_usage_error_writes_a_receipt_and_exits_two(self):
        code = driver.main(['--project-dir', str(self.dir), '--project', 'bad/name',
                            '--input', str(self.input), '--output', str(self.output)])
        self.assertEqual(code, driver.EXIT_USAGE)
        self.assertEqual(self.receipt()['status'], 'usage_error')


class HashIdentityTests(DriverTestCase):
    def test_worker_refuses_a_mismatched_digest_before_starting_the_jvm(self):
        # run_import hashes the input and returns before importing pyghidra, so
        # this exercises identity checking without a Ghidra installation.
        args = driver.build_parser().parse_args([
            '--project-dir', str(self.dir / 'projects'), '--project', 'probe',
            '--input', str(self.input), '--expect-sha256', '0' * 64,
        ])
        receipt = driver.run_import(args)
        self.assertEqual(receipt['status'], 'import_failed')
        self.assertFalse(receipt['input']['matches_expected'])
        self.assertIn('SHA-256', receipt['error'])
        self.assertNotIn('ghidra', receipt)


class StatusPropagationTests(DriverTestCase):
    def test_successful_import_is_ok(self):
        worker = FakeWorker(receipts=[{'status': 'ok', 'program': summary()}])
        self.assertEqual(self.run_main(worker), driver.EXIT_OK)
        self.assertEqual(self.receipt()['status'], 'ok')

    def test_failed_import_exits_three(self):
        worker = FakeWorker(
            receipts=[{'status': 'import_failed', 'error': 'unknown language'}]
        )
        self.assertEqual(self.run_main(worker), driver.EXIT_IMPORT_FAILED)
        self.assertEqual(self.receipt()['status'], 'import_failed')

    def test_failed_autoanalysis_is_not_a_success(self):
        worker = FakeWorker(receipts=[{
            'status': 'analysis_failed',
            'program': summary(),
            'analysis': {'requested': True, 'ok': False, 'error': 'boom'},
        }])
        self.assertEqual(self.run_main(worker, '--analyze'), driver.EXIT_ANALYSIS_FAILED)
        receipt = self.receipt()
        self.assertEqual(receipt['status'], 'analysis_failed')
        self.assertNotEqual(receipt['status'], 'ok')
        self.assertFalse(receipt['analysis']['ok'])

    def test_missing_receipt_is_a_failure_with_worker_output(self):
        worker = FakeWorker(receipts=[None], returncode=134, stderr='JVM died')
        self.assertEqual(self.run_main(worker), driver.EXIT_IMPORT_FAILED)
        receipt = self.receipt()
        self.assertEqual(receipt['status'], 'import_failed')
        self.assertIn('JVM died', receipt['worker_stderr'])
        self.assertEqual(receipt['worker_exit_code'], 134)

    def test_timeout_terminates_the_worker_and_reports_the_project_as_unsafe(self):
        def spawn(mode_args, timeout, python=None):
            return driver.subprocess.TimeoutExpired(mode_args, timeout), True

        self.assertEqual(self.run_main(spawn), driver.EXIT_TIMEOUT)
        receipt = self.receipt()
        self.assertEqual(receipt['status'], 'import_timeout')
        self.assertIn('unknown state', receipt['guidance'])
        self.assertIn('lock_after_failure', receipt)
        self.assertEqual(receipt['elapsed_seconds'] >= 0, True)

    def test_no_reopen_check_is_requested_by_default(self):
        worker = FakeWorker(receipts=[{'status': 'ok', 'program': summary()}])
        self.run_main(worker)
        self.assertEqual(len(worker.calls), 1)
        self.assertNotIn('reopen', self.receipt())


class ReopenTests(DriverTestCase):
    def setUp(self):
        super().setUp()
        self.imported = {'status': 'ok', 'program': summary()}

    def test_matching_reopen_is_ok(self):
        worker = FakeWorker(
            receipts=[self.imported],
            reopen=[{'ok': True, 'program': summary(), 'project_files': ['/PROGRAM']}],
        )
        self.assertEqual(self.run_main(worker, '--reopen-check'), driver.EXIT_OK)
        reopen = self.receipt()['reopen']
        self.assertEqual(reopen['status'], 'ok')
        self.assertTrue(reopen['comparison']['match'])
        self.assertEqual(reopen['project_files'], ['/PROGRAM'])

    def test_differing_bytes_are_a_mismatch_even_when_the_summary_matches(self):
        drifted = summary(content_sha256='c' * 64)
        worker = FakeWorker(
            receipts=[self.imported],
            reopen=[{'ok': True, 'program': drifted, 'project_files': ['/PROGRAM']}],
        )
        self.assertEqual(self.run_main(worker, '--reopen-check'),
                         driver.EXIT_REOPEN_MISMATCH)
        receipt = self.receipt()
        self.assertEqual(receipt['status'], 'reopen_mismatch')
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
        self.assertEqual(receipt['status'], 'reopen_failed')
        self.assertEqual(receipt['reopen']['reason'], 'program_missing')

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
        worker = FakeWorker(
            receipts=[{'status': 'ok', 'program': {}}],
            reopen=[],
        )
        self.assertEqual(self.run_main(worker, '--reopen-check'),
                         driver.EXIT_REOPEN_FAILED)
        self.assertIn('no project path', self.receipt()['reopen']['error'])


class LockTests(DriverTestCase):
    def test_lock_files_are_reported_without_being_removed(self):
        projects = self.dir / 'projects'
        projects.mkdir()
        lock = projects / 'probe.lock'
        lock.write_text('<lock><host>HOST</host><user>USER</user></lock>',
                        encoding='utf-8')
        state = driver.project_lock_state(projects, 'probe')
        self.assertTrue(state['present'])
        self.assertEqual(state['files'][0]['owner_record']['host'], 'HOST')
        self.assertTrue(lock.exists())

    def test_quarantine_renames_rather_than_deletes(self):
        projects = self.dir / 'projects'
        projects.mkdir()
        lock = projects / 'probe.lock'
        lock.write_text('owner', encoding='utf-8')
        result = driver.quarantine_lock(projects, 'probe')
        self.assertFalse(lock.exists())
        self.assertEqual(len(result['moved']), 1)
        moved = projects / result['moved'][0]['to']
        self.assertTrue(moved.exists())
        self.assertEqual(moved.read_text(encoding='utf-8'), 'owner')


class ComparisonTests(unittest.TestCase):
    def test_identical_summaries_match(self):
        self.assertTrue(driver.compare_programs(summary(), summary())['match'])

    def test_every_compared_field_is_reported(self):
        self.assertEqual(
            set(driver.COMPARED_FIELDS),
            {'language_id', 'compiler_spec', 'image_base', 'min_address',
             'max_address', 'block_count', 'content_sha256'},
        )

    def test_a_missing_field_counts_as_a_difference(self):
        result = driver.compare_programs(summary(), {'language_id': 'x86:LE:16:Real Mode'})
        self.assertFalse(result['match'])
        self.assertGreaterEqual(len(result['differences']), 6)


class ParserTests(unittest.TestCase):
    def test_documented_exit_codes_are_distinct(self):
        codes = [driver.EXIT_OK, driver.EXIT_USAGE, driver.EXIT_IMPORT_FAILED,
                 driver.EXIT_TIMEOUT, driver.EXIT_ANALYSIS_FAILED,
                 driver.EXIT_REOPEN_FAILED, driver.EXIT_REOPEN_MISMATCH]
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
