"""Independent format specimens assembled from documented constants.

No lab file is opened and no production parser/writer is imported. Unknown header
bytes deliberately differ from archival files. This is test scaffolding, not a
supported database creator or an application compatibility fixture.
"""
import struct

DBCOLS = [('cname',80,'C'),('owner',80,'C'),('pos',4,'N'),
          ('len',4,'N'),('type',1,'C'),('uniq',1,'N')]
PERSONAL = [('Date',3,'C'),('DayOfWeek',1,'C'),('Duration',1,'C'),
            ('StartTime',1,'C'),('EndTime',1,'C'),('Protected',1,'C'),('Description',120,'K')]

def row(ident,fields):
    return bytes((128,ident))+b'\x01'.join(fields)+b'\x01\x02'

def event(ident,description,day=b'\x90lb',weekday=b'c',start=b'\xa5',end=b'\xa9'):
    return row(ident,[day,weekday,b'',start,end,b'1',description.encode('ascii')])

def build(kind='one'):
    if kind not in ('empty','one','two','five'):raise ValueError(kind)
    d=bytearray(6144);d[:4]=b'\x03FIL'
    marker=b'INDEPENDENT SYNTHETIC TEST';d[64:64+len(marker)]=marker
    internal=row(16,[b'  \xff',b'',b'',b'',b'',b'0',b'ie'+b'a'*12+b'@PaSsWoRd@='])
    rows=[(16,internal)]
    if kind!='empty':rows.append((17,event(17,'LPHa124')))
    if kind in ('two','five'):rows.append((18,event(18,'BETA456',start=b'\xac',end=b'\xb0')))
    if kind=='five':
        rows.extend([(19,event(19,'EARLY26',b'\x8fkx',b'g',b'\xa4',b'\xa8')),
                     (20,event(20,'MID2026',b'\x8flb',b'b',b'\xa8',b'\xac')),
                     (21,event(21,'LATEOCT',b'\x8fky',b'h'))])
    metadata=[[b'T',b'DBCOLS',b'2',b'06',b'00013',b'000',b'00029',b'3',b'2',b'3'],
              [b'T',b'PERSONAL',b'4',b'07',f'{len(rows):05d}'.encode(),b'000',
               f'{max(i for i,_ in rows)+1:05d}'.encode(),b'5',b'1',b'2',b'4',b'5',b'7']]
    m=b''.join(b'\x01'.join(tokens)+b'\x01\x02' for tokens in metadata)+b'\x03'
    d[1024:1024+len(m)]=m
    header=(b'\xff'*9+b'\x00')*4
    d[3072:3112]=header;d[5120:5160]=header
    cursor=2048;slot=3112;ident=16
    for owner,columns in (('DBCOLS',DBCOLS),('PERSONAL',PERSONAL)):
        for pos,(name,length,kindcode) in enumerate(columns,1):
            value=row(ident,[name.encode(),owner.encode(),str(pos).encode(),str(length).encode(),kindcode.encode(),b'0'])
            d[cursor:cursor+len(value)]=value
            struct.pack_into('<HHH',d,slot,2,cursor-2048,ident)
            cursor+=len(value);slot+=6;ident+=1
    d[cursor]=3
    cursor=4096;locations={}
    for ident,value in rows:
        locations[ident]=cursor;d[cursor:cursor+len(value)]=value;cursor+=len(value)
    d[cursor]=3
    order=[16,19,21,20,17,18] if kind=='five' else [i for i,_ in rows]
    for n,ident in enumerate(order):struct.pack_into('<HHH',d,5160+6*n,4,locations[ident]-4096,ident)
    return bytes(d)
