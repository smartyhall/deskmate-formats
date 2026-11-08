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

def event(ident,description,day=b'\x90lb',weekday=b'c',start=b'\xa5',end=b'\xa9',
          *,duration=b'',protected=b'1'):
    return row(ident,[day,weekday,duration,start,end,protected,description.encode('ascii')])

INTERNAL = row(16, [b'  \xff', b'', b'', b'', b'', b'0', b'ie'+b'a'*12+b'@PaSsWoRd@='])

def allocation(data, chains=()):
    """Independent bitstring model of the documented small-file page map."""
    count = len(data) // 1024
    links = [4088] * count + [4095]
    for chain in chains:
        for previous, following in zip(chain, chain[1:]):
            links[previous] = following
    bits = ''.join(f'{link:012b}' for link in links)
    bits += '0' * (-len(bits) % 8)
    data[32:32 + len(bits) // 8] = int(bits, 2).to_bytes(len(bits) // 8, 'big')

def build(kind='one'):
    if kind not in ('empty','one','two','five'):raise ValueError(kind)
    rows=[(16,INTERNAL)]
    if kind!='empty':rows.append((17,event(17,'LPHa124')))
    if kind in ('two','five'):rows.append((18,event(18,'BETA456',start=b'\xac',end=b'\xb0')))
    if kind=='five':
        rows.extend([(19,event(19,'EARLY26',b'\x8fkx',b'g',b'\xa4',b'\xa8')),
                     (20,event(20,'MID2026',b'\x8flb',b'b',b'\xa8',b'\xac')),
                     (21,event(21,'LATEOCT',b'\x8fky',b'h'))])
    order=[16,19,21,20,17,18] if kind=='five' else [i for i,_ in rows]
    return assemble(rows, order)

def assemble(rows, order, *, page_map=True):
    """Assemble physical rows and a separate index order."""
    d=bytearray(6144);d[:4]=b'\x03FIL'
    marker=b'INDEPENDENT SYNTHETIC TEST'
    at = 384 if page_map else 64
    d[at:at+len(marker)]=marker
    if page_map:
        allocation(d)
        d[0x15] = 1
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
    if cursor >= 5120:
        raise ValueError('synthetic rows exceed the PERSONAL data page')
    d[cursor]=3
    for n,ident in enumerate(order):struct.pack_into('<HHH',d,5160+6*n,4,locations[ident]-4096,ident)
    return bytes(d)
