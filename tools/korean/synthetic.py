"""Replace draft pool bodies with test characters without changing allocation.

This operates on host encoding outputs before any disk is made. Original
indices, body boundaries, spaces, newlines and token widths remain unchanged.
"""
import struct

from catalog import digest, write_json
from encoding import decode
from packages import package, split


def mask_pool(data, glyphs, test_glyph=0):
    if not data:
        return data
    if len(data)<2 or not 0<=test_glyph<len(glyphs):
        raise ValueError('invalid synthetic pool or test glyph')
    count=struct.unpack_from('<H',data)[0]
    first=2+2*count
    if first>len(data):
        raise ValueError('truncated pool index')
    offsets=sorted(set(struct.unpack_from(f'<{count}H',data,2)))
    if not offsets:
        if len(data)!=2:raise ValueError('unindexed pool bytes')
        return data
    if offsets[0]!=first or offsets[-1]>=len(data):
        raise ValueError('invalid pool body offsets')
    result=bytearray(data)
    for begin,end in zip(offsets,offsets[1:]+[len(data)]):
        decode(data[begin:end],glyphs)  # includes exact terminator/boundary check
        pos=begin
        while pos<end:
            value=data[pos]
            if 0x80<=value<=0xbf:
                result[pos:pos+2]=bytes([0x80|(test_glyph>>8),test_glyph&255])
                pos+=2
            else:
                if value not in (0,10,32):result[pos]=ord('X')
                pos+=1
    assert len(result)==len(data) and result[:first]==data[:first]
    return bytes(result)


def mask_encoding(report, output, glyphs):
    test_glyph=glyphs.index('가') if '가' in glyphs else 0
    records=[]
    resident=output/'resident-pool.bin'
    before=resident.read_bytes()
    after=mask_pool(before,glyphs,test_glyph)
    resident.write_bytes(after)
    records.append({'name':'resident','bytes':len(after),
                    'shape_source_sha256':digest(before),'synthetic_sha256':digest(after)})
    for f in report['files']:
        path=output/f['package']
        before=path.read_bytes()
        script,pool=split(before)
        after=package(script,mask_pool(pool,glyphs,test_glyph),
                      identity=before[8:20],sides=before[20])
        assert len(before)==len(after) and split(after)[0]==script
        path.write_bytes(after)
        f['sha256']=digest(after)
        records.append({'side':f['side'],'name':f['name'],'bytes':len(after),
                        'script_sha256':digest(script),'script_unchanged':True,
                        'shape_source_sha256':digest(before),'synthetic_sha256':digest(after)})
    report.update(kind='complete synthetic draft-shaped encoding; no draft message bodies',
                  synthetic_body_policy='ASCII X, preserved spaces/LF/terminators, one repeated Hangul glyph; no index deduplication after masking',
                  synthetic_test_glyph=glyphs[test_glyph],synthetic_test_glyph_id=test_glyph)
    write_json(output/'synthetic-shape.json',{'stage':'masked bodies before final media identity binding',
               'policy':report['synthetic_body_policy'],
               'test_glyph':glyphs[test_glyph],'test_glyph_id':test_glyph,
               'catalog_sha256':report['catalog_sha256'],'files':records})
