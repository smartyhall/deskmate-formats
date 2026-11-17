"""Exact generated/native bytes; no live application or self-agreeing parser."""
from pathlib import Path
from hashlib import sha256
import unittest

from deskmate_formats.calendar.maintenance import replace_description

FIXTURES = Path(__file__).resolve().parents[1] / 'fixtures/application-generated/calendar'


class WriterAcceptanceTests(unittest.TestCase):
    def test_generated_candidate_matches_independent_native_page_and_ascii_edit(self):
        source = (FIXTURES / 'sdk-30-days-allocator-tool-generated.cln').read_bytes()
        candidate = (FIXTURES / 'writer-normalized-check-tool-generated.cln').read_bytes()
        native_page_source = (FIXTURES / 'native-30-day-open-close-20261117.cln').read_bytes()
        self.assertEqual(candidate, native_page_source.replace(b'Plan 01 / allocator trial',
                                                               b'Plan 01 / allocator check'))
        self.assertEqual(candidate, replace_description(source, 77, 'Plan 01 / allocator check',
                                                        normalize=True, experimental=True))
        self.assertEqual(len(candidate), 8192)
        self.assertEqual(sha256(candidate).hexdigest(),
                         'b0db0f9a8978f37f9996ace0b4d1d2179941d3982ba76fd6c6faf1019cf73402')

    def test_native_save_only_changes_declared_five_ascii_bytes(self):
        candidate = (FIXTURES / 'writer-normalized-check-tool-generated.cln').read_bytes()
        saved = (FIXTURES / 'native-writer-normalized-final-20261117.cln').read_bytes()
        self.assertEqual(saved, candidate.replace(b'Plan 01 / allocator check',
                                                 b'Plan 01 / allocator final'))
        self.assertEqual(sum(a != b for a, b in zip(candidate, saved)), 5)
        self.assertEqual(saved, replace_description(candidate, 77, 'Plan 01 / allocator final',
                                                    experimental=True))
        self.assertEqual(sha256(saved).hexdigest(),
                         '093c8ff83805b658c9b2c71748d85be2b487256db964dfb50a85e818781c915a')
