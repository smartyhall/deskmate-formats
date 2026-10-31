"""Synthetic retained-deleted-row profiles remain outside production support."""
from pathlib import Path
import tempfile,unittest
from deskmate_formats.calendar.personal import CalendarParseError,parse_bytes,parse_file
from deskmate_formats.calendar.writer import append_appointment
from synthetic import build,event


def retained_page():
    # Invented data only. This constructs a test input, not a deletion operation.
    data=bytearray(build('five'))
    marker=b'00006\x01000\x0100022'
    replacement=b'00006\x01001\x0100023'
    assert data.count(marker)==1
    at=data.index(marker);data[at:at+len(marker)]=replacement
    dead=event(0x16,'RETIRED_SYNTH')
    page=b'D'+dead[1:]+b'\x03'
    return bytes(data)+page+bytes(1024-len(page))


class RetainedPageScopeTests(unittest.TestCase):
    def test_inactive_extra_page_is_not_silently_accepted_or_rewritten(self):
        data=bytearray(retained_page());before=bytes(data)
        self.assertEqual(len(data),7168)
        self.assertEqual(data[6144],0x44)
        for operation in (parse_bytes,append_appointment):
            with self.subTest(operation=operation.__name__),self.assertRaises(CalendarParseError) as caught:
                operation(data)
            self.assertEqual(caught.exception.code,'unsupported_layout')
            self.assertEqual(data,before)

    def test_file_reader_preserves_evidence_and_nonzero_descriptor_is_unsupported(self):
        data=retained_page()
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'synthetic.cln';path.write_bytes(data);mtime=path.stat().st_mtime_ns
            with self.assertRaises(CalendarParseError) as caught:parse_file(path)
            self.assertEqual(caught.exception.code,'unsupported_layout')
            self.assertEqual(path.read_bytes(),data)
            self.assertEqual(path.stat().st_mtime_ns,mtime)
        # Discarding a retained page would not restore the measured six-page profile.
        with self.assertRaises(CalendarParseError) as caught:parse_bytes(data[:6144])
        self.assertEqual(caught.exception.code,'unsupported_layout')
