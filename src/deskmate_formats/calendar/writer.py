"""Bounded experimental append-only writer for the observed six-page profile."""
from dataclasses import dataclass
from datetime import date
from pathlib import Path
import argparse
import json
import os
import struct
import sys
import tempfile
from .personal import (FILE_SIZE, PAGE_SIZE, INDEX_HEADER_SIZE,
                               OBSERVED_DATES, OBSERVED_TIMES, parse_bytes)

@dataclass(frozen=True)
class Appointment:
    day: date
    start_minutes: int
    end_minutes: int
    description: str
    duration_raw: bytes = b''
    protected_raw: bytes = b'1'

TARGET = Appointment(date(2027,11,1),660,720,'BETA456')

def _validate(event):
    if not isinstance(event,Appointment) or type(event.day) is not date:
        raise ValueError('expected Appointment with date value')
    if (event.day.year,event.day.month,event.day.day) not in OBSERVED_DATES:
        raise ValueError('date outside experimentally measured mappings')
    for minutes in (event.start_minutes,event.end_minutes):
        if type(minutes) is not int or minutes % 15 or 0x80+minutes//15 not in OBSERVED_TIMES:
            raise ValueError('time outside experimentally measured mappings')
    if event.start_minutes >= event.end_minutes:
        raise ValueError('nonpositive or overnight duration unsupported')
    if (type(event.description) is not str or not 1 <= len(event.description) <= 120
            or any(not 0x20 <= ord(c) < 0x7F for c in event.description)):
        raise ValueError('description requires 1..120 printable ASCII characters')
    if event.duration_raw != b'' or event.protected_raw != b'1':
        raise ValueError('only observed opaque Duration/Protected values accepted')

def capacity(source):
    """Available new row bytes exclude required list marker; reserve index sentinel."""
    db=parse_bytes(source);t=db.metadata['tables']['PERSONAL']
    end=max(r.offset+r.length for r in db.records)
    index=t['index_page']*PAGE_SIZE+INDEX_HEADER_SIZE
    return {'data_bytes':(t['data_page']+1)*PAGE_SIZE-end-1,
            'index_entries':((t['index_page']+1)*PAGE_SIZE-index)//6-1-len(db.records),
            'next_id':t['next_id_candidate'],'low_ids_remaining':0x80-t['next_id_candidate']}

def append_appointment(source, event=TARGET):
    _validate(event)
    data=bytes(source);db=parse_bytes(data);t=db.metadata['tables']['PERSONAL']
    # Sorting is deliberately restricted to fully understood, non-tied keys.
    keys=[]
    for r in db.appointments:
        if (None in (r.date,r.start_time,r.end_time,r.description) or
                r.undecoded_fields != {'Duration':'','Protected':'31'}):
            raise ValueError('existing event has unsupported/undecoded fields')
        keys.append((r.date,r.start_time))
    key=(event.day.isoformat(),f'{event.start_minutes//60:02d}:{event.start_minutes%60:02d}')
    if len(keys)!=len(set(keys)) or key in keys:
        raise ValueError('tied date/start index keys unsupported')
    ident=t['next_id_candidate']
    if ident>=0x80:raise ValueError('long record ID unsupported')
    weekday=(event.day.weekday()+1)%7+1
    fields=[bytes((0x61+event.day.year-1980,0x61+event.day.month,0x61+event.day.day)),
            bytes((0x61+weekday,)),event.duration_raw,bytes((0x80+event.start_minutes//15,)),
            bytes((0x80+event.end_minutes//15,)),event.protected_raw,event.description.encode('ascii')]
    row=bytes((0x80,ident))+b'\x01'.join(fields)+b'\x01\x02'
    free=capacity(data)
    if len(row)>free['data_bytes'] or free['index_entries']<1:
        raise ValueError('additional data/index page required; unsupported')
    address=max(r.offset+r.length for r in db.records)
    index_base=t['index_page']*PAGE_SIZE+INDEX_HEADER_SIZE
    # Preserve physical rows. Only chronological index triples are inserted/reordered.
    entries=[(k,r.offset,r.record_id) for k,r in zip(keys,db.appointments)]+[(key,address,ident)]
    entries.sort(key=lambda x:x[0])
    ordered=[(r.offset,r.record_id) for r in db.internal_records]+[(a,i) for _,a,i in entries]
    output=bytearray(data)
    output[address:address+len(row)+1]=row+b'\x03'
    for n,(a,i) in enumerate(ordered):
        struct.pack_into('<HHH',output,index_base+6*n,t['data_page'],a-t['data_page']*PAGE_SIZE,i)
    cursor=PAGE_SIZE
    while True:
        end=data.index(b'\x01\x02',cursor,2*PAGE_SIZE);tokens=data[cursor:end].split(b'\x01')
        if tokens[1]==b'PERSONAL':break
        cursor=end+2
    for n,value in ((4,t['record_count']+1),(6,ident+1)):
        p=cursor+sum(len(v)+1 for v in tokens[:n]);output[p:p+5]=f'{value:05d}'.encode('ascii')
    result=bytes(output);parsed=parse_bytes(result)
    if len(result)!=len(data) or len(parsed.records)!=len(db.records)+1:
        raise ValueError('append postcondition failed')
    by_id={r.record_id:r for r in parsed.records}
    if any(by_id[r.record_id].raw_hex!=r.raw_hex or by_id[r.record_id].offset!=r.offset for r in db.records):
        raise ValueError('append modified an existing physical record')
    return result

def write_new(path,data):
    """Publish complete validated file atomically, fail if destination exists.

    Same-directory temporary file + flushed hard-link publication; no overwrite
    fallback on filesystems without hard-link support. Directory durability is
    filesystem dependent. The temporary link is removed in all cases.
    """
    parse_bytes(data);path=Path(path)
    fd,temp=tempfile.mkstemp(prefix='.calendar-',suffix='.tmp',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as handle:
            handle.write(data);handle.flush();os.fsync(handle.fileno())
        os.link(temp,path)
    finally:
        os.unlink(temp)

def main(argv=None):
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('source',type=Path);cli.add_argument('output',type=Path)
    cli.add_argument('--appointments',type=Path,help='JSON array: date,start_minutes,end_minutes,description')
    args=cli.parse_args(argv)
    try:
        if args.source.resolve()==args.output.resolve():raise ValueError('source and output must differ')
        events=[TARGET]
        if args.appointments:
            items=json.loads(args.appointments.read_text(encoding='utf-8'))
            if not isinstance(items,list) or not 1<=len(items)<=100:raise ValueError('expected 1..100 appointment objects')
            events=[]
            for item in items:
                if not isinstance(item,dict) or set(item)!={'date','start_minutes','end_minutes','description'}:
                    raise ValueError('unexpected appointment keys')
                events.append(Appointment(date.fromisoformat(item['date']),item['start_minutes'],item['end_minutes'],item['description']))
        with args.source.open('rb') as handle:data=handle.read(FILE_SIZE+1)
        for event in events:data=append_appointment(data,event)
        write_new(args.output,data)
    except (OSError,ValueError,TypeError) as exc:
        print(str(exc),file=sys.stderr);return 2
    return 0

if __name__=='__main__':raise SystemExit(main())
