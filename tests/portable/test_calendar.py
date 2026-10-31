from contextlib import redirect_stdout,redirect_stderr
from dataclasses import replace
from datetime import date
from pathlib import Path
from unittest.mock import patch
import io,json,tempfile,unittest
from deskmate_formats.calendar.personal import parse_bytes,parse_file,CalendarParseError
from deskmate_formats.calendar.cli import main as read_main
from deskmate_formats.calendar.writer import Appointment,TARGET,append_appointment,capacity,write_new,main
from synthetic import build

SAMPLE=[TARGET,Appointment(date(2026,10,23),540,600,'EARLY26'),
        Appointment(date(2026,11,1),600,660,'MID2026'),Appointment(date(2026,10,24),555,615,'LATEOCT')]

class PortableCalendarTests(unittest.TestCase):
    def test_synthetic_profiles_and_internal_exclusion(self):
        for kind,count in [('empty',0),('one',1),('two',2),('five',5)]:
            with self.subTest(kind=kind):
                db=parse_bytes(build(kind));self.assertEqual(len(db.appointments),count)
                self.assertEqual(len(db.internal_records),1)
                self.assertEqual(db.metadata['tables']['PERSONAL']['record_count'],count+1)

    def test_independent_synthetic_append_oracle(self):
        self.assertEqual(append_appointment(build('one')),build('two'))

    def test_multiple_appends_against_independently_assembled_five(self):
        data=build('one')
        for event in SAMPLE:
            old=parse_bytes(data);data=append_appointment(data,event);new=parse_bytes(data)
            for prior in old.records:
                r=next(r for r in new.records if r.record_id==prior.record_id)
                self.assertEqual((r.offset,r.raw_hex),(prior.offset,prior.raw_hex))
        self.assertEqual(data,build('five'))
        db=parse_bytes(data)
        self.assertEqual([r.description for r in db.appointments],['EARLY26','LATEOCT','MID2026','LPHa124','BETA456'])
        self.assertEqual([r.description for r in sorted(db.appointments,key=lambda r:r.offset)],['LPHa124','BETA456','EARLY26','MID2026','LATEOCT'])

    def test_same_day_nonchronological_insertion(self):
        db=parse_bytes(append_appointment(build(),Appointment(date(2027,11,1),540,555,'FIRST09')))
        self.assertEqual([r.description for r in db.appointments],['FIRST09','LPHa124'])
        self.assertGreater(db.appointments[0].offset,db.appointments[1].offset)

    def test_capacity_without_large_fixture(self):
        c=capacity(build('five'))
        self.assertEqual((c['data_bytes'],c['index_entries']),(864,157))
        for free in ({'data_bytes':23,'index_entries':1},{'data_bytes':100,'index_entries':0}):
            with patch('deskmate_formats.calendar.writer.capacity',return_value=free):
                with self.assertRaisesRegex(ValueError,'additional.*page'):append_appointment(build())

    def test_reject_unsupported_values_and_ties(self):
        changes=[{'description':v} for v in ('','A'*121,'BAD\n','BAD\x01','bad\u00e9')]
        changes += [{'day':date(2028,11,1)},{'start_minutes':675},{'start_minutes':True},{'protected_raw':b'0'}]
        for change in changes:
            with self.subTest(change=change),self.assertRaises(ValueError):append_appointment(build(),replace(TARGET,**change))
        with self.assertRaises(ValueError):append_appointment(build('two'))

    def test_immutable_source_and_file_reader(self):
        data=bytearray(build());old=bytes(data);append_appointment(data);self.assertEqual(data,old)
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'sample.cln';p.write_bytes(old);stat=p.stat()
            self.assertEqual(len(parse_file(p).appointments),1)
            self.assertEqual(p.read_bytes(),old);self.assertEqual(p.stat().st_mtime_ns,stat.st_mtime_ns)

    def test_atomic_publication_and_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'output.cln';write_new(out,build())
            with self.assertRaises(FileExistsError):write_new(out,build())
            with patch('deskmate_formats.calendar.writer.os.link',side_effect=OSError('simulated failure')):
                with self.assertRaises(OSError):write_new(Path(tmp)/'failed.cln',build())
            self.assertEqual([p.name for p in Path(tmp).iterdir()],['output.cln'])

    def test_cli_batch_read_and_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'input.cln';out=root/'output.cln';batch=root/'events.json'
            source.write_bytes(build())
            items=[{'date':e.day.isoformat(),'start_minutes':e.start_minutes,'end_minutes':e.end_minutes,'description':e.description} for e in SAMPLE]
            batch.write_text(json.dumps(items),encoding='utf-8')
            self.assertEqual(main([str(source),str(out),'--appointments',str(batch)]),0)
            self.assertEqual(out.read_bytes(),build('five'))
            for flags in ([],['--json']):
                text=io.StringIO()
                with redirect_stdout(text):self.assertEqual(read_main([str(out)]+flags),0)
                self.assertIn('EARLY26',text.getvalue())
                if flags:self.assertEqual(json.loads(text.getvalue())['appointment_count'],5)
            with redirect_stderr(io.StringIO()):
                self.assertEqual(main([str(source),str(out)]),2)
                self.assertEqual(main([str(source),str(source)]),2)

    def test_cli_failure_has_no_partial_file_or_listing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'input.cln';out=root/'output.cln';batch=root/'bad.json'
            source.write_bytes(build());batch.write_text('[{}]',encoding='utf-8')
            with redirect_stderr(io.StringIO()):self.assertEqual(main([str(source),str(out),'--appointments',str(batch)]),2)
            self.assertFalse(out.exists())
            text=io.StringIO()
            with patch('deskmate_formats.calendar.cli.parse_file',side_effect=CalendarParseError('truncated_file','test')),redirect_stdout(text),redirect_stderr(io.StringIO()):
                self.assertEqual(read_main(['missing','--json']),2)
            self.assertEqual(text.getvalue(),'')
