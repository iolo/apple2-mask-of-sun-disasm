"""Add one resident title reference in INITIAL's empty row below the credit."""
import json

from catalog import digest, write_json
from encoding import refresh_allocation
from packages import package, split


def high(text):return bytes(ord(c)|128 for c in text)


def insert_caption(script, title_id, credit_id, cells):
    if not 0x8000<=title_id<=0xffff or not 0x8000<=credit_id<=0xffff:
        raise ValueError('title and credit must be resident messages')
    if not 1<=cells<=38:raise ValueError('title must fit the isolated row without wrapping')
    # Before this point the two unchanged native logo records have been drawn.
    # The hook precedes all INITIAL branches/relative jumps and variable setup.
    prefix=high('.C 0,2,0\r.$ 2\r.C 1,1,0\r.L L,LOGO\r.B LOGO1\r.S V=1\r.D \r'
                '.B LOGO2\r.S V=1\r.D \r.$ 1\r._ 1\r.M 1\r.V 0\r'+f'.P "~{credit_id:04X}\r')
    if not script.startswith(prefix+high('.V 13\r')):
        raise ValueError('INITIAL title hook changed or already inserted')
    column=(40-cells)//2
    position=high(f'.V 1\r.H {column}\r.P "')
    insertion=position+high(f'~{title_id:04X}\r')
    updated=script[:len(prefix)]+insertion+script[len(prefix):]
    if len(updated)>2048:raise ValueError('caption exceeds INITIAL script RAM')
    return updated,dict(row=1,column=column,cells=cells,message_id=title_id,
                        insertion_offset=len(prefix),inserted_bytes=len(insertion),
                        reference_offset=len(prefix)+len(position),
                        insertion_hex=insertion.hex(),original_script_sha256=digest(script))


def add_caption(report, output, catalog):
    messages={m['id']:m for m in catalog['messages']}
    title=messages['picture:title']
    if title['status']=='excluded' or not title['ko'] or '\n' in title['ko'] or not title['layout']['newline']:
        raise ValueError('title requires a one-line active caption')
    aliases=json.loads((output/'resident-aliases.json').read_text())
    initial=next(f for f in report['files'] if f['side']=='a' and f['name']=='INITIAL')
    path=output/initial['package'];old=path.read_bytes();script,pool=split(old)
    script,record=insert_caption(script,aliases['picture:title'],aliases['a:INITIAL:0061'],len(title['ko']))
    framed=package(script,pool,identity=old[8:20],sides=old[20])
    path.write_bytes(framed)
    initial.update(script_bytes=len(script),script_fits=True,sha256=digest(framed),
                   package_bytes=len(framed),package_sectors=(len(framed)+255)//256,
                   generated_caption=True)
    report['title_caption']=dict(record,id='picture:title',package=initial['package'],
                                 generated_only_reference=True)
    refresh_allocation(report,output)
    write_json(output/'encoding.json',report)
    return report['title_caption']
