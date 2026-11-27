"""Portable probes for the program-report driver's request and receipt rules.

Only the paths that resolve before a JVM is needed are exercised here: request
validation, the refusal to create a missing project, and atomic receipt
publication. The JVM-dependent read modes are qualified against a real owned
project and are not faked, because a fake Ghidra would prove nothing about
Ghidra.
"""
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    'ghidra_program_report', ROOT / 'tools/ghidra/ghidra_program_report.py'
)
report = importlib.util.module_from_spec(spec)
sys.path.insert(0, str(ROOT / 'src'))
spec.loader.exec_module(report)


class Case(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.project_dir = self.dir / 'projects'
        self.project_dir.mkdir()
        self.output = self.dir / 'report.json'

    def tearDown(self):
        for path in sorted(self.dir.rglob('*'), key=lambda p: len(p.parts),
                           reverse=True):
            path.unlink() if path.is_file() else path.rmdir()
        self.dir.rmdir()

    def project(self):
        (self.project_dir / 'probe.gpr').write_bytes(b'x')

    def run_main(self, *extra):
        import contextlib
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = report.main([
                '--project-dir', str(self.project_dir),
                '--project', 'probe',
                '--program', '/PROGRAM',
                '--output', str(self.output),
                *extra,
            ])
        return code, err.getvalue()

    def receipt(self):
        return json.loads(self.output.read_text(encoding='utf-8'))


class ValidationTests(Case):
    def test_a_request_without_a_mode_is_refused(self):
        code, err = self.run_main()
        self.assertEqual(code, report.EXIT_USAGE)
        receipt = self.receipt()
        self.assertEqual(receipt['outcome'], 'invalid_request')
        self.assertIn('at least one read or write mode', err)
        self.assertIn('attempt', receipt)
        self.assertEqual(len(receipt['attempt']['id']), 32)

    def test_impossible_limits_are_refused(self):
        for extra in (['--summary', '--limit', '0'],
                      ['--disassemble', 'F', '--max-instructions', '-1']):
            with self.subTest(extra=extra):
                code, _ = self.run_main(*extra)
                self.assertEqual(code, report.EXIT_USAGE)

    def test_text_output_needs_a_decompile(self):
        self.project()
        code, err = self.run_main('--summary', '--text-output', str(self.dir / 'x.c'))
        self.assertEqual(code, report.EXIT_USAGE)
        self.assertIn('--text-output needs --decompile', err)

    def test_annotation_modes_are_separate_invocations(self):
        self.project()
        code, err = self.run_main('--annotate', 'x', '--verify-annotation')
        self.assertEqual(code, report.EXIT_USAGE)
        self.assertIn('separate invocations', err)

    def test_the_recorded_request_names_every_mode(self):
        code, _ = self.run_main()
        modes = self.receipt()['requested']['modes']
        self.assertEqual(
            set(modes),
            {'summary', 'functions', 'symbols', 'xrefs', 'disassemble',
             'pcode', 'decompile', 'annotate', 'verify_annotation'},
        )
        self.assertFalse(any(modes.values()))


class ProjectOwnershipTests(Case):
    def test_a_missing_project_is_a_failure_and_is_not_created(self):
        code, _ = self.run_main('--summary')
        self.assertEqual(code, report.EXIT_NOT_FOUND)
        receipt = self.receipt()
        self.assertEqual(receipt['outcome'], 'project_missing')
        self.assertIn('never creates a project', receipt['error'])
        self.assertEqual(list(self.project_dir.iterdir()), [])

    def test_the_receipt_names_the_project_and_program(self):
        self.run_main('--summary')
        receipt = self.receipt()
        self.assertEqual(receipt['project']['name'], 'probe')
        self.assertEqual(receipt['requested']['program_path'], '/PROGRAM')
        self.assertEqual(receipt['schema'], report.RECEIPT_SCHEMA)


class PublicationTests(Case):
    def test_publication_is_atomic_and_leaves_no_temporary_file(self):
        payload = {'schema': 'probe', 'value': [1, 2, 3]}
        digest = report.publish_json(str(self.output), payload)
        self.assertTrue(self.output.is_file())
        self.assertEqual(
            report.json.loads(self.output.read_text(encoding='utf-8')), payload
        )
        self.assertEqual(
            digest,
            report.hashlib.sha256(
                self.output.read_bytes()
            ).hexdigest(),
        )
        self.assertEqual(
            [path.name for path in self.dir.iterdir() if '.tmp-' in path.name], []
        )

    def test_a_second_publication_replaces_the_first_completely(self):
        report.publish_json(str(self.output), {'a': 1, 'b': 2, 'c': 3})
        report.publish_json(str(self.output), {'a': 1})
        self.assertEqual(
            report.json.loads(self.output.read_text(encoding='utf-8')), {'a': 1}
        )

    def test_publication_to_stdout_returns_the_digest(self):
        buffer = io.StringIO()
        import contextlib
        with contextlib.redirect_stdout(buffer):
            digest = report.publish_json(None, {'a': 1})
        self.assertEqual(
            digest,
            report.hashlib.sha256(buffer.getvalue().encode('utf-8')).hexdigest(),
        )


class FingerprintTests(unittest.TestCase):
    """A report receipt has to name the bytes it describes."""

    def program(self, *blocks):
        return FakeProgram([FakeBlock(name, start, data, initialized)
                            for name, start, data, initialized in blocks])

    def test_the_same_bytes_and_geometry_hash_the_same(self):
        first = report._content_sha256(self.program(('CODE', 0x1000, b'\x90\x90', True)))
        second = report._content_sha256(self.program(('CODE', 0x1000, b'\x90\x90', True)))
        self.assertEqual(first, second)
        self.assertRegex(first, r'^[0-9a-f]{64}$')

    def test_one_differing_byte_changes_the_fingerprint(self):
        first = report._content_sha256(self.program(('CODE', 0x1000, b'\x90\x90', True)))
        second = report._content_sha256(self.program(('CODE', 0x1000, b'\x90\x91', True)))
        self.assertNotEqual(first, second)

    def test_block_geometry_is_part_of_the_fingerprint(self):
        first = report._content_sha256(self.program(('CODE', 0x1000, b'\x90', True)))
        second = report._content_sha256(self.program(('CODE', 0x2000, b'\x90', True)))
        self.assertNotEqual(first, second)

    def test_uninitialized_block_contents_are_not_hashed(self):
        # An uninitialized block has no stored bytes to describe, so only its
        # geometry counts; the same block in two projects must compare equal.
        first = report._content_sha256(
            self.program(('BSS', 0x2000, b'\x00\x00', False))
        )
        second = report._content_sha256(
            self.program(('BSS', 0x2000, b'\xff\xff', False))
        )
        self.assertEqual(first, second)


class FakeBlock:
    def __init__(self, name, start, data, initialized=True):
        self.name = name
        self.start = start
        self.data = data
        self.initialized = initialized
        self.size = len(data)

    def getName(self):
        return self.name

    def getStart(self):
        return self.start

    def getEnd(self):
        return self.start + self.size - 1

    def getSize(self):
        return self.size

    def isInitialized(self):
        return self.initialized


class FakeMemory:
    def __init__(self, blocks):
        self.blocks = blocks

    def getBlocks(self):
        return list(self.blocks)

    def getBytes(self, start, buffer):
        for block in self.blocks:
            if block.start == start:
                buffer[:] = block.data
                return len(block.data)
        raise KeyError(start)


class FakeProgram:
    def __init__(self, blocks):
        self.memory = FakeMemory(blocks)

    def getMemory(self):
        return self.memory


class ParserTests(unittest.TestCase):
    def test_exit_codes_are_distinct(self):
        codes = [report.EXIT_OK, report.EXIT_USAGE, report.EXIT_NOT_FOUND,
                 report.EXIT_OPEN_FAILED, report.EXIT_OPERATION_FAILED,
                 report.EXIT_NOT_PERSISTED]
        self.assertEqual(len(set(codes)), len(codes))

    def test_help_needs_no_ghidra_installation(self):
        import contextlib
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            with self.assertRaises(SystemExit) as raised:
                report.main(['--help'])
        self.assertEqual(raised.exception.code, 0)
        self.assertIn('--pcode', buffer.getvalue())


if __name__ == '__main__':
    unittest.main()
