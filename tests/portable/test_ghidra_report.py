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

    def write_json(self, payload, name='annotate.json'):
        path = self.dir / name
        path.write_text(json.dumps(payload), encoding='utf-8')
        return path


def annotate_receipt(project_dir, *, attempt_id='a' * 32, text='note',
                     project='probe', program='/PROGRAM', address='1000:0000'):
    """An annotate receipt as the tool publishes one."""
    plate = report.ANNOTATION_PLATE % (attempt_id, text)
    return {
        'schema': report.RECEIPT_SCHEMA,
        'tool': 'tools/ghidra/ghidra_program_report.py',
        'attempt': {'id': attempt_id, 'started_utc': '2026-11-27T00:00:00Z'},
        'requested': {
            'project': project,
            'project_dir': str(project_dir),
            'program_path': program,
            'modes': {'annotate': True},
        },
        'project': {'name': project, 'dir': str(project_dir)},
        'outcome': 'succeeded',
        'annotation': {
            'program': program,
            'address': address,
            'plate': plate,
            'bookmark': {
                'type': report.ANNOTATION_BOOKMARK_TYPE,
                'category': report.ANNOTATION_BOOKMARK_CATEGORY,
                'comment': plate,
            },
            'label': report.ANNOTATION_LABEL,
            'committed': True,
            'saved': True,
            'persisted': True,
        },
    }


class AnnotationCase(Case):
    def expected(self):
        path = self.write_json(annotate_receipt(self.project_dir))
        expected, problems = report._annotation_expectations(
            str(path), 'probe', self.project_dir, '/PROGRAM'
        )
        self.assertEqual(problems, [])
        return expected


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


class ModeSelectionTests(Case):
    """Each advertised mode is a complete request, not an unset one.

    A single-mode run has to reach the project, so a missing project proves the
    mode was accepted: the project check comes after validation and before any
    JVM. `--symbols` was missing from the mode list this replaces.
    """

    SINGLE = {
        'summary': ['--summary'],
        'functions': ['--functions'],
        'symbols': ['--symbols'],
        'xrefs': ['--xrefs', '1000:0000'],
        'disassemble': ['--disassemble', 'F'],
        'pcode': ['--pcode', 'F'],
        'decompile': ['--decompile', 'F'],
        'annotate': ['--annotate', 'note'],
    }

    def test_every_single_mode_is_accepted(self):
        for mode, argv in self.SINGLE.items():
            with self.subTest(mode=mode):
                code, err = self.run_main(*argv)
                self.assertEqual(code, report.EXIT_NOT_FOUND, err)
                self.assertEqual(self.receipt()['outcome'], 'project_missing')
                self.assertNotIn('at least one read or write mode', err)

    def test_a_symbols_only_request_is_accepted(self):
        code, err = self.run_main('--symbols')
        self.assertEqual(code, report.EXIT_NOT_FOUND, err)
        modes = self.receipt()['requested']['modes']
        self.assertTrue(modes['symbols'])
        self.assertEqual([name for name, set_ in modes.items() if set_], ['symbols'])


class VerificationRequestTests(Case):
    """Verification names what it expects, and refuses before it looks."""

    def test_verification_without_an_annotate_receipt_is_refused(self):
        self.project()
        code, err = self.run_main('--verify-annotation')
        self.assertEqual(code, report.EXIT_USAGE)
        self.assertIn('--annotation-receipt', err)

    def test_a_missing_receipt_is_refused_before_the_project_is_opened(self):
        code, err = self.run_main(
            '--verify-annotation',
            '--annotation-receipt', str(self.dir / 'missing.json'),
        )
        self.assertEqual(code, report.EXIT_USAGE)
        self.assertEqual(self.receipt()['outcome'], 'invalid_request')
        self.assertIn('unreadable', err)

    def test_a_receipt_for_another_project_is_refused(self):
        path = self.write_json(annotate_receipt(self.project_dir, project='other'))
        code, err = self.run_main('--verify-annotation', '--annotation-receipt', str(path))
        self.assertEqual(code, report.EXIT_USAGE)
        self.assertIn("'other'", err)

    def test_a_receipt_is_useless_without_verification(self):
        self.project()
        code, err = self.run_main(
            '--summary', '--annotation-receipt', str(self.dir / 'x.json')
        )
        self.assertEqual(code, report.EXIT_USAGE)
        self.assertIn('only read with --verify-annotation', err)


class AnnotationExpectationTests(AnnotationCase):
    """A verify run has to be told which annotation it is looking for."""

    def expectations(self, payload=None, *, project='probe', program='/PROGRAM'):
        path = self.write_json(
            payload if payload is not None else annotate_receipt(self.project_dir)
        )
        return report._annotation_expectations(
            str(path), project, self.project_dir, program
        )

    def test_a_receipt_from_the_annotate_run_is_accepted(self):
        expected = self.expected()
        self.assertEqual(expected['attempt_id'], 'a' * 32)
        self.assertEqual(expected['address'], '1000:0000')
        self.assertEqual(expected['plate'], 'campaign probe (%s): note' % ('a' * 32))
        self.assertEqual(expected['bookmark']['category'], 'campaign-probe')
        self.assertEqual(expected['label'], 'probe_label')
        self.assertRegex(expected['receipt_sha256'], r'^[0-9a-f]{64}$')

    def test_an_unreadable_receipt_is_refused(self):
        expected, problems = report._annotation_expectations(
            str(self.dir / 'missing.json'), 'probe', self.project_dir, '/PROGRAM'
        )
        self.assertIsNone(expected)
        self.assertIn('unreadable', problems[0])

    def test_a_receipt_that_is_not_an_object_is_refused(self):
        expected, problems = self.expectations([1, 2, 3])
        self.assertIsNone(expected)
        self.assertIn('not a JSON object', problems[0])

    def test_each_broken_part_of_a_receipt_is_named(self):
        def foreign_project(payload):
            payload['requested']['project'] = 'other'

        def foreign_program(payload):
            payload['requested']['program_path'] = '/OTHER.EXE'

        def foreign_directory(payload):
            payload['requested']['project_dir'] = 'C:/elsewhere'

        def unsaved(payload):
            payload['outcome'] = 'not_persisted'

        def not_persisted(payload):
            payload['annotation']['persisted'] = False

        def persisted_as_text(payload):
            payload['annotation']['persisted'] = 'true'

        def no_attempt(payload):
            payload['attempt']['id'] = ''

        def no_address(payload):
            payload['annotation']['address'] = ''

        def no_plate(payload):
            payload['annotation']['plate'] = ''

        def plate_without_the_attempt(payload):
            payload['annotation']['plate'] = 'campaign probe: note'

        def no_bookmark(payload):
            del payload['annotation']['bookmark']

        def other_bookmark_type(payload):
            payload['annotation']['bookmark']['type'] = 'Info'

        def other_bookmark_category(payload):
            payload['annotation']['bookmark']['category'] = 'other'

        def bookmark_of_another_text(payload):
            payload['annotation']['bookmark']['comment'] = 'other'

        def other_label(payload):
            payload['annotation']['label'] = 'other_label'

        cases = {
            'foreign project': foreign_project,
            'foreign program': foreign_program,
            'foreign directory': foreign_directory,
            'unsaved': unsaved,
            'not persisted': not_persisted,
            'persisted as text': persisted_as_text,
            'no attempt': no_attempt,
            'no address': no_address,
            'no plate': no_plate,
            'stale plate': plate_without_the_attempt,
            'no bookmark': no_bookmark,
            'other bookmark type': other_bookmark_type,
            'other bookmark category': other_bookmark_category,
            'bookmark of another text': bookmark_of_another_text,
            'other label': other_label,
        }
        for name, change in cases.items():
            with self.subTest(case=name):
                payload = annotate_receipt(self.project_dir)
                change(payload)
                expected, problems = self.expectations(payload)
                self.assertIsNone(expected, name)
                self.assertTrue(problems, name)

    def test_a_receipt_naming_another_program_is_refused(self):
        expected, problems = self.expectations(program='/OTHER.EXE')
        self.assertIsNone(expected)
        self.assertTrue(any('program' in problem for problem in problems))


class AnnotationComparisonTests(AnnotationCase):
    """Persistence is the conjunction of the four verified components."""

    def observed(self, **changes):
        expected = self.expected()
        observed = {
            'address': '1000:0000',
            'plate_comment': expected['plate'],
            'bookmarks': [dict(expected['bookmark'])],
            'symbols': [report.ANNOTATION_LABEL],
        }
        observed.update(changes)
        return expected, observed

    def test_the_positive_control_persists(self):
        expected, observed = self.observed()
        result = report._compare_annotation(expected, observed)
        self.assertTrue(result['persisted'])
        self.assertEqual(
            set(result['checks']),
            {'address', 'plate_comment', 'bookmark', 'label'},
        )
        self.assertTrue(all(check['ok'] for check in result['checks'].values()))

    def test_a_missing_component_prevents_persistence(self):
        cases = {
            'plate': ({'plate_comment': None}, 'plate_comment'),
            'bookmark': ({'bookmarks': []}, 'bookmark'),
            'label': ({'symbols': []}, 'label'),
            'address': ({'address': None}, 'address'),
            'everything': ({
                'address': None, 'plate_comment': None,
                'bookmarks': [], 'symbols': [],
            }, 'plate_comment'),
        }
        for name, (changes, component) in cases.items():
            with self.subTest(missing=name):
                expected, observed = self.observed(**changes)
                result = report._compare_annotation(expected, observed)
                self.assertFalse(result['persisted'], name)
                self.assertFalse(result['checks'][component]['ok'], name)

    def test_a_stale_or_mismatched_component_prevents_persistence(self):
        expected, base = self.observed()
        cases = {
            'stale plate': {'plate_comment': 'campaign probe: earlier note'},
            'plate of another attempt': {
                'plate_comment': report.ANNOTATION_PLATE % ('b' * 32, 'note')
            },
            'bookmark of another text': {
                'bookmarks': [dict(expected['bookmark'], comment='other')]
            },
            'bookmark of another category': {
                'bookmarks': [dict(expected['bookmark'], category='other')]
            },
            'bookmark of another type': {
                'bookmarks': [dict(expected['bookmark'], type='Info')]
            },
            'label of another probe': {'symbols': ['other_label']},
            'annotation at another address': {'address': '2000:0000'},
        }
        for name, changes in cases.items():
            with self.subTest(case=name):
                result = report._compare_annotation(expected, dict(base, **changes))
                self.assertFalse(result['persisted'], name)

    def test_an_unrelated_bookmark_does_not_hide_the_expected_one(self):
        expected, observed = self.observed()
        observed['bookmarks'] = [
            {'type': 'Info', 'category': 'other', 'comment': 'x'},
            dict(expected['bookmark']),
        ]
        self.assertTrue(report._compare_annotation(expected, observed)['persisted'])


class FakeCommentType:
    PLATE = 'plate'


class fake_ghidra_modules:
    """Provide only the module the adapter imports, and leave sys.modules as it was.

    The real import is a Ghidra class that needs a JVM; the adapter's contract,
    which is what the test is about, is the program it reads and the comment
    type it asks for.
    """

    NAMES = ('ghidra', 'ghidra.program', 'ghidra.program.model',
             'ghidra.program.model.listing')

    def __enter__(self):
        import types
        self.previous = {}
        for name in self.NAMES:
            self.previous[name] = sys.modules.get(name)
            module = types.ModuleType(name)
            module.__path__ = []
            sys.modules[name] = module
        sys.modules['ghidra'].program = sys.modules['ghidra.program']
        sys.modules['ghidra.program'].model = sys.modules['ghidra.program.model']
        sys.modules['ghidra.program.model'].listing = \
            sys.modules['ghidra.program.model.listing']
        sys.modules['ghidra.program.model.listing'].CommentType = FakeCommentType
        return self

    def __exit__(self, *exception):
        for name, module in self.previous.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module
        return False


class FakeAnnotationProgram:
    """The read surface _verify_annotation uses, and nothing else."""

    def __init__(self, *, address='1000:0000', plate=None, bookmarks=(),
                 symbols=()):
        self.address = address
        self.plate = plate
        self.bookmarks = list(bookmarks)
        self.symbols = list(symbols)

    def getAddressFactory(self):
        return self

    def getAddress(self, text):
        return text if text == self.address else None

    def getListing(self):
        return self

    def getComment(self, kind, at):
        return self.plate

    def getBookmarkManager(self):
        return self

    def getBookmarks(self, at):
        return [FakeBookmark(*row) for row in self.bookmarks]

    def getSymbolTable(self):
        return self

    def getSymbols(self, at):
        return [FakeSymbol(name) for name in self.symbols]

    def __enter__(self):
        return self

    def __exit__(self, *exception):
        return False


class FakeBookmark:
    def __init__(self, type_string, category, comment):
        self.type_string = type_string
        self.category = category
        self.comment = comment

    def getTypeString(self):
        return self.type_string

    def getCategory(self):
        return self.category

    def getComment(self):
        return self.comment


class FakeSymbol:
    def __init__(self, name):
        self.name = name

    def getName(self):
        return self.name


class FakeProject:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class AnnotationVerifyTests(AnnotationCase):
    """The adapter reads the named annotation, not whatever is at the address."""

    def verify(self, program):
        project = FakeProject()
        original = report._open_readonly

        def fake_open(*args, **kwargs):
            return program, project

        report._open_readonly = fake_open
        try:
            with fake_ghidra_modules():
                record = report._verify_annotation(
                    self.project_dir, 'probe', '/PROGRAM', self.expected()
                )
        finally:
            report._open_readonly = original
        self.assertTrue(project.closed)
        return record

    def matching(self, expected):
        return FakeAnnotationProgram(
            plate=expected['plate'],
            bookmarks=[(
                expected['bookmark']['type'],
                expected['bookmark']['category'],
                expected['bookmark']['comment'],
            )],
            symbols=[report.ANNOTATION_LABEL, 'FUN_1000_0000'],
        )

    def test_a_matching_annotation_is_persisted(self):
        expected = self.expected()
        record = self.verify(self.matching(expected))
        self.assertTrue(record['persisted'])
        self.assertEqual(record['address'], '1000:0000')
        self.assertEqual(record['observed']['plate_comment'], expected['plate'])

    def test_a_stale_plate_fails_although_the_bookmark_and_label_match(self):
        expected = self.expected()
        program = self.matching(expected)
        program.plate = 'campaign probe: earlier note'
        record = self.verify(program)
        self.assertFalse(record['persisted'])
        self.assertFalse(record['checks']['plate_comment']['ok'])
        self.assertTrue(record['checks']['bookmark']['ok'])
        self.assertTrue(record['checks']['label']['ok'])
        self.assertTrue(record['checks']['address']['ok'])

    def test_an_annotation_from_another_attempt_is_not_persisted(self):
        other = report.ANNOTATION_PLATE % ('b' * 32, 'note')
        record = self.verify(FakeAnnotationProgram(
            plate=other,
            bookmarks=[(report.ANNOTATION_BOOKMARK_TYPE,
                        report.ANNOTATION_BOOKMARK_CATEGORY, other)],
            symbols=[report.ANNOTATION_LABEL],
        ))
        self.assertFalse(record['persisted'])
        self.assertFalse(record['checks']['plate_comment']['ok'])
        self.assertFalse(record['checks']['bookmark']['ok'])
        self.assertTrue(record['checks']['label']['ok'])

    def test_a_missing_bookmark_is_not_persisted(self):
        expected = self.expected()
        record = self.verify(FakeAnnotationProgram(
            plate=expected['plate'], symbols=[report.ANNOTATION_LABEL]
        ))
        self.assertFalse(record['persisted'])
        self.assertFalse(record['checks']['bookmark']['ok'])
        self.assertTrue(record['checks']['plate_comment']['ok'])

    def test_a_missing_label_is_not_persisted(self):
        expected = self.expected()
        pattern = self.matching(expected)
        pattern.symbols = ['FUN_1000_0000']
        record = self.verify(pattern)
        self.assertFalse(record['persisted'])
        self.assertFalse(record['checks']['label']['ok'])

    def test_an_unresolvable_address_is_not_persisted(self):
        record = self.verify(FakeAnnotationProgram(address='2000:0000'))
        self.assertIsNone(record['address'])
        self.assertFalse(record['persisted'])
        self.assertFalse(record['checks']['address']['ok'])


if __name__ == '__main__':
    unittest.main()
