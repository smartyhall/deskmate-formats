from datetime import date
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from contextlib import redirect_stderr
import io
import json
import tempfile
import unittest
from deskmate_formats.calendar.personal import parse_bytes
from deskmate_formats.calendar.writer import Appointment,TARGET,append_appointment,capacity,write_new,main
from test_calendar_personal import fixture_path

SAMPLE=[TARGET,Appointment(date(2026,10,23),540,600,'EARLY26'),
        Appointment(date(2026,11,1),600,660,'MID2026'),
        Appointment(date(2026,10,24),555,615,'LATEOCT')]

class MultiWriterTests(unittest.TestCase):
    def generate(self):
        data=fixture_path('E07_date_20271101').read_bytes()
        for event in SAMPLE:data=append_appointment(data,event)
        return data

    def test_multiple_nonchronological_appends_and_index_enumeration(self):
        db=parse_bytes(self.generate())
        self.assertEqual([r.description for r in db.appointments],['EARLY26','LATEOCT','MID2026','LPHa124','BETA456'])
        self.assertEqual([r.description for r in sorted(db.appointments,key=lambda r:r.offset)],['LPHa124','BETA456','EARLY26','MID2026','LATEOCT'])
        self.assertEqual([r.record_id for r in sorted(db.records,key=lambda r:r.offset)],list(range(0x10,0x16)))
        self.assertEqual(db.metadata['tables']['PERSONAL']['record_count'],6)
        self.assertEqual(db.metadata['tables']['PERSONAL']['next_id_candidate'],22)

    def test_sample_fields_and_physical_preservation(self):
        source=fixture_path('E07_date_20271101').read_bytes();data=source
        for event in SAMPLE:
            old=parse_bytes(data);data=append_appointment(data,event);new=parse_bytes(data)
            for prior in old.records:
                current=next(r for r in new.records if r.record_id==prior.record_id)
                self.assertEqual((current.offset,current.raw_hex),(prior.offset,prior.raw_hex))
            row=next(r for r in new.appointments if r.description==event.description)
            self.assertEqual(row.date,event.day.isoformat())
            self.assertEqual(row.start_time,f'{event.start_minutes//60:02d}:{event.start_minutes%60:02d}')
            self.assertEqual(row.end_time,f'{event.end_minutes//60:02d}:{event.end_minutes%60:02d}')
        self.assertEqual(len(data),len(source))

    def test_capacity_arithmetic_without_generating_near_full_database(self):
        free=capacity(self.generate())
        self.assertEqual((free['data_bytes'],free['index_entries']),(864,157))
        self.assertEqual(min(free['data_bytes']//24,free['index_entries'],free['low_ids_remaining']),36)

    def test_both_capacity_guards_reject_before_output(self):
        source=fixture_path('E07_date_20271101').read_bytes()
        for free in ({'data_bytes':23,'index_entries':1},{'data_bytes':100,'index_entries':0}):
            with self.subTest(free=free),patch('deskmate_formats.calendar.writer.capacity',return_value=free):
                with self.assertRaisesRegex(ValueError,'additional.*page'):append_appointment(source)

    def test_unsupported_characters_dates_times_and_opaque_fields(self):
        source=fixture_path('E07_date_20271101').read_bytes()
        changes=[{'description':s} for s in ('','A'*121,'BAD\x00','BAD\x01','BAD\x02','BAD\x03','BAD\n','caf\u00e9')]
        changes += [{'day':date(2028,11,1)},{'start_minutes':True},{'start_minutes':675},
                    {'end_minutes':600},{'duration_raw':b'Q'},{'protected_raw':b'0'}]
        for change in changes:
            with self.subTest(change=change),self.assertRaises(ValueError):append_appointment(source,replace(TARGET,**change))

    def test_same_date_earlier_time_insertion(self):
        source=fixture_path('E07_date_20271101').read_bytes()
        generated=append_appointment(source,Appointment(date(2027,11,1),540,555,'FIRST09'))
        db=parse_bytes(generated)
        self.assertEqual([r.description for r in db.appointments],['FIRST09','LPHa124'])
        self.assertGreater(db.appointments[0].offset,db.appointments[1].offset)

    def test_atomic_new_output_and_failure_cleanup(self):
        data=self.generate()
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'new.cln';write_new(out,data)
            self.assertEqual(out.read_bytes(),data)
            with self.assertRaises(FileExistsError):write_new(out,data)
            with patch('deskmate_formats.calendar.writer.os.link',side_effect=OSError('test publication failure')):
                with self.assertRaises(OSError):write_new(Path(tmp)/'failed.cln',data)
            self.assertEqual([p.name for p in Path(tmp).iterdir()],['new.cln'])

    def test_preserved_application_roundtrip_matches_generation(self):
        base=fixture_path('E07_date_20271101').parents[4]/'PHASE3A/multi_record'
        # fixture path parents[4] is EXPERIMENTS; no fixture is rewritten.
        expected=self.generate()
        self.assertEqual((base/'generated_PERSONAL.CLN').read_bytes(),expected)
        self.assertEqual((base/'after/files/DESKMATE/PERSONAL.CLN').read_bytes(),expected)

    def test_e15_fixed_length_plan_without_generating_it(self):
        free=capacity(self.generate())
        self.assertEqual(free['data_bytes']//(17+60),11)
        self.assertEqual(free['data_bytes']-11*(17+60),17)
        # Four measured dates and five usable start values allow20 unique keys.
        self.assertGreaterEqual(20-5,11+1)

    def test_independent_e10_reconstruction(self):
        source=fixture_path('E07_date_20271101').read_bytes()
        generated=append_appointment(source,replace(TARGET,description='GAMMA45'))
        self.assertEqual(generated,fixture_path('E10_reuse_gamma45').read_bytes())

    def test_cli_batch_and_failed_batch_leave_no_partial_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source.cln';batch=root/'batch.json';out=root/'result.cln'
            original=fixture_path('E07_date_20271101').read_bytes();source.write_bytes(original)
            items=[{'date':e.day.isoformat(),'start_minutes':e.start_minutes,'end_minutes':e.end_minutes,'description':e.description} for e in SAMPLE]
            batch.write_text(json.dumps(items),encoding='utf-8')
            self.assertEqual(main([str(source),str(out),'--appointments',str(batch)]),0)
            self.assertEqual(out.read_bytes(),self.generate())
            items[-1]['description']='BAD\x01';batch.write_text(json.dumps(items),encoding='utf-8')
            failed=root/'failed.cln'
            with redirect_stderr(io.StringIO()):
                self.assertEqual(main([str(source),str(failed),'--appointments',str(batch)]),2)
            self.assertFalse(failed.exists());self.assertEqual(source.read_bytes(),original)

if __name__=='__main__':unittest.main()
