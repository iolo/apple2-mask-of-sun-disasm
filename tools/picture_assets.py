#!/usr/bin/env python3
"""Decode native ULTRA pictures into constrained SVG geometry and encode edits.

SVG stores named native layers, orthogonal directional geometry, fill seeds and
header parameters. Native previews are separate: SVG fills only approximate the
Apple II scan-fill and artifact colors. No native packed vector payload is kept
in SVG metadata. See docs/pictures.md for supported edits and storage limits.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SVG = 'http://www.w3.org/2000/svg'
ET.register_namespace('', SVG)
PALETTE = ['#b93cda', '#42b941', '#286de0', '#df7927', '#000000', '#ffffff']
EXCLUDED = {'ADVEN INTERP.OBJ', 'CHAR GEN', 'INTRIN.OBJ', 'PARMS.OBJ'}
DELTA = [(0, -1), (1, 0), (-1, 0), (0, 1)]


def integer(value, label, minimum=0, maximum=255):
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValueError(f'{label}: expected integer')
    if str(number) != str(value) or not minimum <= number <= maximum:
        raise ValueError(f'{label}: expected integer {minimum}..{maximum}')
    return number


def unpack_vector(data):
    commands = []
    for byte in data:
        commands.extend([byte & 7, (byte >> 3) & 7])
        if byte >> 6:
            commands.append(byte >> 6)
    return commands


def pack_vector(commands, packing=None):
    if not commands:
        raise ValueError('a vector layer needs at least one step')
    if len(commands) == 1:
        commands = commands + [4]  # final unplotted move, coordinates unused afterwards
    if packing and sum(packing) == len(commands):
        result, index = bytearray(), 0
        for width in packing:
            if width not in (2, 3):
                raise ValueError('packing groups must have two or three steps')
            group = commands[index:index+width]
            if width == 3 and not 1 <= group[2] <= 3:
                break  # geometry edit no longer fits the old grouping
            result.append(group[0] | (group[1] << 3) | ((group[2] << 6) if width == 3 else 0))
            index += width
        else:
            if len(result)>65536:raise ValueError('vector exceeds sixteen-bit packed length')
            return bytes(result)
    result = bytearray()
    index = 0
    while index < len(commands):
        first = commands[index]
        if index + 1 == len(commands):
            second = 4
        else:
            second = commands[index + 1]
        index += 2
        third = 0
        if index < len(commands) and 1 <= commands[index] <= 3:
            third = commands[index]
            index += 1
        result.append(first | (second << 3) | (third << 6))
    if len(result) > 65536:
        raise ValueError('vector exceeds sixteen-bit packed length')
    return bytes(result)


def decode_records(data):
    records, offset = [], 0
    while offset < len(data):
        if offset + 13 > len(data):
            raise ValueError(f'truncated record header at {offset}')
        name_bytes = data[offset:offset+5]
        if any(not 0xa0 <= value <= 0xfe for value in name_bytes):
            raise ValueError(f'invalid high-bit name at {offset}')
        length = int.from_bytes(data[offset+5:offset+7], 'little')
        count = data[offset+12]
        if not 1 <= count <= 64 or length < 13 + count or offset + length > len(data):
            raise ValueError(f'invalid length/layer count at {offset}')
        position, layers = offset + 13 + count, []
        for color in data[offset+13:position]:
            if position + 2 > offset + length:
                raise ValueError('truncated layer origin/seed')
            x, y = data[position:position+2]
            if color & 128:
                layers.append({'kind':'seed','color':color,'origin':[x,y]})
                position += 2
            else:
                if position + 4 > offset + length:
                    raise ValueError('truncated vector length')
                size = int.from_bytes(data[position+2:position+4], 'little') + 1
                if position + 4 + size > offset + length:
                    raise ValueError('vector crosses record boundary')
                packed = data[position+4:position+4+size]
                commands = unpack_vector(packed)
                layers.append({'kind':'vector','color':color,'origin':[x,y],'commands':commands,
                    'packing':[3 if byte >> 6 else 2 for byte in packed]})
                position += 4 + size
        records.append({'name':bytes(value&127 for value in name_bytes).decode('ascii'),
            'parameters':list(data[offset+7:offset+12]), 'layers':layers,
            'padding':data[position:offset+length], 'native_offset':offset,
            'native_size':length, 'native_sha256':hashlib.sha256(data[offset:offset+length]).hexdigest()})
        offset += length
    return records


def svg_path(layer):
    x, y = layer['origin']
    parts = [f'M {x} {y}']
    for command in layer['commands']:
        dx, dy = DELTA[command & 3]
        x += dx
        y += dy
        parts.append(f'{"M" if command & 4 else "L"} {x} {y}')
    return ' '.join(parts)


def save_svg(record, path):
    root = ET.Element(f'{{{SVG}}}svg', {'width':'280','height':'192','viewBox':'0 0 140 192',
        'preserveAspectRatio':'none','data-mask-format':'1','data-name':record['name'],
        'data-origin-x':str(record['parameters'][0]),'data-origin-y':str(record['parameters'][1]),
        'data-scale-x':str(record['parameters'][2]),'data-scale-y':str(record['parameters'][3]),
        'data-options':str(record['parameters'][4])})
    ET.SubElement(root,f'{{{SVG}}}title').text = record['name'].strip() + ' — native ULTRA vector geometry'
    ET.SubElement(root,f'{{{SVG}}}desc').text = ('Editing geometry: native scan-fill and artifact colors are shown in the companion PNG. '
        'Layers retain order; M moves without drawing, L plots before moving. Units are orthogonal native steps.')
    metadata = ET.SubElement(root,f'{{{SVG}}}metadata')
    metadata.text = json.dumps({'native_offset':record['native_offset'],'native_size':record['native_size'],
        'native_sha256':record['native_sha256'],'padding':base64.b64encode(record['padding']).decode('ascii')}, separators=(',',':'))
    ET.SubElement(root,f'{{{SVG}}}rect', {'width':'140','height':'192','fill':'white','data-role':'background'})
    ox,oy=record['parameters'][:2]
    ox=ox-256 if ox>=128 else ox;oy=oy-256 if oy>=128 else oy
    group = ET.SubElement(root,f'{{{SVG}}}g',{'data-role':'layers','transform':f'translate({ox} {oy})',
        'stroke-linecap':'square','stroke-linejoin':'miter','stroke-width':'0.35'})
    for index,layer in enumerate(record['layers']):
        color=layer['color']&127
        attributes={'id':f'layer-{index:02d}','data-color':str(layer['color']),'data-kind':layer['kind']}
        if layer['kind']=='seed':
            attributes.update({'cx':str(layer['origin'][0]),'cy':str(layer['origin'][1]),'r':'1.5',
                'fill':PALETTE[color] if color<6 else '#777777','stroke':'#ff0066'})
            ET.SubElement(group,f'{{{SVG}}}circle',attributes)
        else:
            attributes.update({'d':svg_path(layer),'data-packing':''.join(map(str,layer['packing'])),
                'fill':'none' if color==127 else PALETTE[color] if color<6 else '#aaaaaa',
                'stroke':'#000000'})
            ET.SubElement(group,f'{{{SVG}}}path',attributes)
    ET.indent(root,space='  ')
    path.parent.mkdir(parents=True,exist_ok=True)
    ET.ElementTree(root).write(path,encoding='utf-8',xml_declaration=True)


def read_svg(path):
    root=ET.parse(path).getroot()
    if root.tag!=f'{{{SVG}}}svg' or root.get('data-mask-format')!='1':
        raise ValueError(f'{path}: expected native picture SVG format1')
    if root.get('viewBox')!='0 0 140 192' or root.get('width')!='280' or root.get('height')!='192':
        raise ValueError(f'{path}: dimensions/viewBox must stay 280x192 / 0 0 140 192')
    if root.get('transform') or root.get('preserveAspectRatio')!='none':
        raise ValueError(f'{path}: root transforms/aspect changes are unsupported')
    allowed={f'{{{SVG}}}{tag}' for tag in ('title','desc','metadata','rect','g')}
    for child in root:
        if child.tag not in allowed or (child.tag==f'{{{SVG}}}rect' and child.get('data-role')!='background') or (child.tag==f'{{{SVG}}}g' and child.get('data-role')!='layers'):
            raise ValueError(f'{path}: unsupported SVG element outside native layers')
    name=root.get('data-name','')
    if len(name)!=5 or any(not 32<=ord(c)<=126 for c in name):
        raise ValueError(f'{path}: native picture name must be five ASCII characters')
    parameters=[integer(root.get(key),key) for key in ('data-origin-x','data-origin-y','data-scale-x','data-scale-y','data-options')]
    if parameters[4]&~0x2f:
        raise ValueError(f'{path}: unsupported drawing-option bits')
    metadata=root.find(f'{{{SVG}}}metadata')
    if metadata is None:raise ValueError(f'{path}: missing padding/provenance metadata')
    info=json.loads(metadata.text)
    padding=base64.b64decode(info['padding'],validate=True)
    groups=[g for g in root.findall(f'{{{SVG}}}g') if g.get('data-role')=='layers']
    if len(groups)!=1:raise ValueError(f'{path}: expected one layers group')
    group=groups[0]
    ox,oy=parameters[:2];ox=ox-256 if ox>=128 else ox;oy=oy-256 if oy>=128 else oy
    if group.get('transform')!=f'translate({ox} {oy})':
        raise ValueError(f'{path}: translate must match native origin attributes')
    layers=[]
    for element in group:
        if element.get('transform') or len(element):
            raise ValueError(f'{path}: per-layer transforms/nested elements are unsupported')
        color=integer(element.get('data-color'),'layer color')
        kind=element.get('data-kind')
        if kind=='seed' and color&128 and element.tag==f'{{{SVG}}}circle':
            layers.append({'kind':kind,'color':color,'origin':[integer(element.get('cx'),'seed x'),integer(element.get('cy'),'seed y')]})
        elif kind=='vector' and not color&128 and element.tag==f'{{{SVG}}}path':
            tokens=re.findall(r'[ML]|-?\d+',element.get('d',''))
            if re.sub(r'[ML]|-?\d+|[\s,]','',element.get('d','')) or len(tokens)%3:
                raise ValueError(f'{path}: paths support absolute integer M/L commands only')
            if len(tokens)<6 or tokens[0]!='M':
                raise ValueError(f'{path}: vector needs origin M and at least one step')
            x=integer(tokens[1],'vector origin x');y=integer(tokens[2],'vector origin y')
            origin=[x,y];commands=[]
            for index in range(3,len(tokens),3):
                mode=tokens[index]
                if mode not in ('M','L'):raise ValueError('unsupported path command')
                nx=integer(tokens[index+1],'path x',-256,511);ny=integer(tokens[index+2],'path y',-256,511)
                dx,dy=nx-x,ny-y
                if bool(dx)==bool(dy):raise ValueError(f'{path}: segments must be nonzero orthogonal moves')
                direction=1 if dx>0 else 2 if dx<0 else 3 if dy>0 else 0
                commands.extend([direction+(4 if mode=='M' else 0)]*(abs(dx)+abs(dy)))
                if len(commands)>196608:raise ValueError(f'{path}: too many vector steps')
                x,y=nx,ny
            packing=element.get('data-packing','')
            if any(c not in '23' for c in packing):raise ValueError(f'{path}: packing groups must be 2/3')
            layers.append({'kind':kind,'color':color,'origin':origin,'commands':commands,
                'packing':list(map(int,packing))})
        else:raise ValueError(f'{path}: layer tag/kind/color disagree')
    if not 1<=len(layers)<=64:raise ValueError(f'{path}: layer count must be 1..64')
    return {'name':name,'parameters':parameters,'layers':layers,'padding':padding}


def encode_record(record,padding=b''):
    payload=bytearray()
    for layer in record['layers']:
        payload.extend(layer['origin'])
        if layer['kind']=='vector':
            packed=pack_vector(layer['commands'],layer.get('packing'))
            payload.extend((len(packed)-1).to_bytes(2,'little'));payload.extend(packed)
    length=13+len(record['layers'])+len(payload)+len(padding)
    if length>65535:raise ValueError('picture record exceeds sixteen-bit size')
    return bytes(ord(c)|128 for c in record['name'])+length.to_bytes(2,'little')+bytes(record['parameters'])+bytes([len(record['layers'])])+bytes(layer['color'] for layer in record['layers'])+payload+padding


def encode_collection(entry, directory):
    records=[read_svg(directory/name) for name in entry['pictures']]
    if not records:raise ValueError('empty picture collection')
    bodies=[encode_record(record,record['padding'] if index+1<len(records) else b'') for index,record in enumerate(records)]
    remaining=entry['allocated_bytes']-sum(map(len,bodies))
    if remaining<0:raise ValueError(f'{entry["name"]}: edits exceed allocated {entry["allocated_bytes"]} bytes by {-remaining}')
    # Final record absorbs allocation slack. Its unused residue is not image code.
    padding=records[-1]['padding'][:remaining].ljust(remaining,b'\0')
    bodies[-1]=encode_record(records[-1],padding)
    return b''.join(bodies)


def decode_all(directory):
    if directory.exists():raise ValueError('decode output already exists')
    manifest=json.loads((ROOT/'assets/raw/manifest.json').read_text());entries=[]
    for disk in manifest['disks']:
        for file in disk['files']:
            if file['type']!=4 or file['name'] in EXCLUDED:continue
            records=decode_records((ROOT/file['path']).read_bytes())
            folder=Path(disk['side'])/Path(file['path']).stem
            pictures=[]
            for index,record in enumerate(records):
                slug=re.sub('[^a-z0-9]+','-',record['name'].lower()).strip('-')
                name=str(folder/f'{index:03d}-{slug}.svg');save_svg(record,directory/name);pictures.append(name)
            entries.append({'side':disk['side'],'name':file['name'],'asset':file['path'],
                'allocated_bytes':file['allocated_bytes'],'pictures':pictures})
    (directory/'manifest.json').write_text(json.dumps({'format':1,'collections':entries},indent=2)+'\n')
    return entries


def encode_all(directory):
    manifest=json.loads((directory/'manifest.json').read_text())
    if manifest.get('format')!=1:raise ValueError('unsupported picture manifest format')
    raw_manifest=json.loads((ROOT/'assets/raw/manifest.json').read_text())
    expected={file['path']:file['allocated_bytes'] for disk in raw_manifest['disks']
              for file in disk['files'] if file['type']==4 and file['name'] not in EXCLUDED}
    replacements={}
    for entry in manifest['collections']:
        if entry['asset'] in replacements:raise ValueError('duplicate picture asset mapping')
        if not re.fullmatch(r'assets/raw/[ab]/files/[a-z0-9-]+\.bin',entry['asset']):
            raise ValueError('invalid native picture asset path')
        for name in entry['pictures']:
            if Path(name).is_absolute() or '..' in Path(name).parts or Path(name).suffix!='.svg':
                raise ValueError('picture paths must be relative SVG files within the asset directory')
        if entry['asset'] not in expected or entry['allocated_bytes']!=expected[entry['asset']]:
            raise ValueError('picture collection allocation does not match disk manifest')
        replacements[entry['asset']]=encode_collection(entry,directory)
    if set(replacements)!=set(expected):raise ValueError('missing native picture collection mapping')
    return replacements


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    decoder=sub.add_parser('decode');decoder.add_argument('--output',type=Path,required=True)
    encoder=sub.add_parser('encode');encoder.add_argument('directory',type=Path);encoder.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.command=='decode':
        entries=decode_all(args.output);print(f'Decoded {sum(len(e["pictures"]) for e in entries)} pictures from {len(entries)} collections')
    else:
        replacements=encode_all(args.directory)
        for asset,data in replacements.items():
            path=args.output/Path(asset).relative_to('assets/raw');path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        print(f'Encoded {len(replacements)} picture collections')


if __name__=='__main__':
    try:main()
    except (OSError,ValueError,ET.ParseError) as error:sys.exit(str(error))
