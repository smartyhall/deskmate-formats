"""Independent synthetic checks for the measured E15 pre-boundary profile."""
from datetime import date
import unittest
from deskmate_formats.calendar.personal import parse_bytes
from deskmate_formats.calendar.writer import Appointment, append_appointment, capacity
from synthetic import build


def additions():
    keys = [(date(2026,10,23),s,e) for s,e in [(555,615),(600,660),(615,660),(660,720)]]
    keys += [(date(2026,10,24),s,e) for s,e in [(540,600),(600,660),(615,660),(660,720)]]
    keys += [(date(2026,11,1),s,e) for s,e in [(540,600),(555,615),(615,660)]]
    return [Appointment(d,s,e,f'FILL{n:03d}'+'X'*53) for n,(d,s,e) in enumerate(keys,1)]


def near_capacity():
    data = build('five')
    for event in additions():
        data = append_appointment(data,event)
    return data


class PreBoundaryTests(unittest.TestCase):
    def test_long_records_and_capacity(self):
        data = near_capacity()
        db = parse_bytes(data)
        self.assertEqual(len(data),6144)
        self.assertEqual((len(db.records),len(db.appointments)),(17,16))
        self.assertEqual(capacity(data),dict(data_bytes=17,index_entries=146,next_id=33,low_ids_remaining=95))
        table = db.metadata['tables']['PERSONAL']
        self.assertEqual((table['record_count'],table['next_id_candidate']),(17,33))
        for n,event in enumerate(additions(),0x16):
            r = next(r for r in db.appointments if r.description==event.description)
            self.assertEqual((r.record_id,r.length,len(r.description)),(n,77,60))
            self.assertEqual(r.date,event.day.isoformat())
            self.assertEqual((r.start_time,r.end_time),(f'{event.start_minutes//60:02d}:{event.start_minutes%60:02d}',f'{event.end_minutes//60:02d}:{event.end_minutes%60:02d}'))
        self.assertEqual([(r.date,r.start_time) for r in db.appointments],sorted((r.date,r.start_time) for r in db.appointments))

    def test_old_records_and_real_capacity_guard(self):
        source = build('five')
        data = near_capacity()
        old,new = parse_bytes(source),parse_bytes(data)
        for prior in old.records:
            r = next(r for r in new.records if r.record_id==prior.record_id)
            self.assertEqual((r.offset,r.raw_hex),(prior.offset,prior.raw_hex))
        marker = max(r.offset+r.length for r in new.records)
        self.assertEqual(data[marker],3)
        self.assertEqual(data[marker+1:5120],bytes(17))
        mutable = bytearray(data)
        for description in ('BOUND12','BOUND12'+'X'*53):
            event = Appointment(date(2026,11,1),660,720,description)
            with self.subTest(length=len(description)),self.assertRaisesRegex(ValueError,'additional.*page'):
                append_appointment(mutable,event)
            self.assertEqual(mutable,data)
