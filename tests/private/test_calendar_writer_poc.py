"""E08 is an independent oracle; the writer never receives its bytes."""
from contextlib import redirect_stderr
from dataclasses import replace
import io
import tempfile
from pathlib import Path
import unittest

from deskmate_formats.calendar.personal import parse_bytes
from deskmate_formats.calendar.writer import TARGET, append_appointment, main
from test_calendar_personal import fixture_path


class WriterProofTests(unittest.TestCase):
    def test_complete_binary_equivalence(self):
        source = fixture_path('E07_date_20271101').read_bytes()
        generated = append_appointment(source)
        # Oracle consulted only after construction.
        self.assertEqual(generated, fixture_path('E08_two_events').read_bytes())

    def test_parse_values_and_preserve_existing_records(self):
        source = fixture_path('E07_date_20271101').read_bytes()
        old, new = parse_bytes(source), parse_bytes(append_appointment(source))
        rows = {r.description:r for r in new.appointments}
        row = rows['BETA456']
        self.assertEqual((row.date,row.day_of_week,row.start_time,row.end_time),
                         ('2027-11-01','Monday','11:00','12:00'))
        self.assertEqual(row.record_id, max(r.record_id for r in old.records)+1)
        self.assertEqual(row.offset, max(r.offset+r.length for r in old.records))
        self.assertEqual(rows['LPHa124'].raw_hex,old.appointments[0].raw_hex)
        self.assertEqual(new.internal_records[0].raw_hex,old.internal_records[0].raw_hex)

    def test_input_buffer_not_modified(self):
        source=bytearray(fixture_path('E07_date_20271101').read_bytes())
        before=bytes(source)
        append_appointment(source)
        self.assertEqual(bytes(source),before)

    def test_unsupported_event_and_tied_repeat_rejected(self):
        source=fixture_path('E07_date_20271101').read_bytes()
        for change in ({'description':'BAD\x01TEXT'},{'start_minutes':675},{'protected_raw':b'0'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                append_appointment(source,replace(TARGET,**change))
        with self.assertRaises(ValueError):append_appointment(append_appointment(source))

    def test_malformed_and_additional_pages_rejected(self):
        source=fixture_path('E07_date_20271101').read_bytes()
        for invalid in (source[:-1],source+bytes(1024),b'BAD!'+source[4:]):
            with self.subTest(size=len(invalid)),self.assertRaises(ValueError):
                append_appointment(invalid)

    def test_cli_creates_new_file_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);source=root/'source.cln';output=root/'generated.cln'
            original=fixture_path('E07_date_20271101').read_bytes()
            source.write_bytes(original)
            self.assertEqual(main([str(source),str(output)]),0)
            self.assertEqual(output.read_bytes(),append_appointment(original))
            with redirect_stderr(io.StringIO()):
                self.assertEqual(main([str(source),str(output)]),2)
                self.assertEqual(main([str(source),str(source)]),2)
            self.assertEqual(source.read_bytes(),original)
            self.assertEqual(output.read_bytes(),append_appointment(original))


if __name__ == '__main__':unittest.main()
