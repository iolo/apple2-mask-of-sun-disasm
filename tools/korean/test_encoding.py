"""Boundary/collision and source-preservation checks for candidate encoding."""
import struct
import unittest

from encoding import allocation_plan, decode, encode, pool, reference, referenced_script, resident_set


class EncodingTests(unittest.TestCase):
    def test_residency_aliases_do_not_merge_review_entries(self):
        messages = [dict(id='lib', ko='A', kind='script_text', references=[dict(file='LIBRARY', path='lib')]),
                    dict(id='one', ko='B', kind='script_text', references=[dict(file='ROOM 1', path='one')]),
                    dict(id='two', ko='B', kind='script_text', references=[dict(file='ROOM 2', path='two')]),
                    dict(id='three', ko='A', kind='script_text', references=[dict(file='ROOM 3', path='three')])]
        resident, lookup, promoted = resident_set(messages, {}, 10)
        self.assertEqual(len(messages), 4)
        self.assertEqual(len(resident), 2)
        self.assertEqual(lookup['one'], lookup['two'])
        self.assertEqual(lookup['lib'], lookup['three'])
        self.assertEqual(len(promoted), 1)
        with self.assertRaises(ValueError):
            resident_set(messages, {}, 5)
        self.assertEqual(len(resident_set(messages, {}, 6)[0]), 1)

    def test_allocation_uses_only_freed_data_and_vtoc_free_sectors(self):
        disk = dict(files=[dict(path='room', sectors=[[1,0]], ts_lists=[[2,0]]),
                           dict(path='picture', sectors=[[1,2]], ts_lists=[[2,1]])],
                    catalog_sectors=[[17,15]])
        vtoc = bytearray(256)
        vtoc[0x3c:0x3e] = (1 << 1).to_bytes(2, 'big')
        packages = [dict(source='room', package_sectors=2)]
        plan = allocation_plan(disk, packages, vtoc)
        self.assertTrue(plan['fits'])
        self.assertEqual(plan['allocations'][0]['data_sectors'], [(1,0),(1,1)])
        packages[0]['package_sectors'] = 3
        self.assertFalse(allocation_plan(disk, packages, vtoc)['fits'])

    def test_low_bytes_may_equal_controls_and_ascii(self):
        chars = [chr(0xac00+i) for i in range(1024)]
        ids = {c:i for i,c in enumerate(chars)}
        # IDs with low-byte EOF, LF, CR, quote, semicolon and 8D must not terminate.
        text = 'A;~0000\n' + ''.join(chars[i] for i in (0,10,13,34,59,141,255,256,511,1023))
        encoded = encode(text, ids)
        self.assertEqual(decode(encoded, chars), text)
        self.assertIn(b'\x81\x00', encoded)
        self.assertEqual(encode('', ids), b'\0')

    def test_malformed_streams_rejected(self):
        for data in (b'', b'A', b'\x80', b'\x80\0\0', b'\xc0\0', b'\r\0', b'\0junk'):
            with self.subTest(data=data), self.assertRaises(ValueError):
                decode(data, [])
        with self.assertRaises(ValueError):
            encode('A\rB', {})
        with self.assertRaises(ValueError):
            encode('가', {'가':0x4000})
        with self.assertRaises(ValueError):
            encode('\u1100\u1161', {})

    def test_deduplicated_pool_offsets_are_absolute(self):
        chars = ['가']; ids = {'가':0}
        messages = [{'ko':s} for s in ['가', '', 'ASCII', '가']]
        data, unique = pool(messages, ids)
        count, = struct.unpack_from('<H', data)
        offsets = struct.unpack_from('<4H', data, 2)
        self.assertEqual(count, 4)
        self.assertEqual(unique, 3)
        self.assertEqual(offsets[0], 10)
        self.assertEqual(offsets[0], offsets[3])
        for m, offset in zip(messages, offsets):
            expected = encode(m['ko'], ids)
            self.assertEqual(data[offset:offset+len(expected)], expected)
            self.assertEqual(decode(expected, chars), m['ko'])

    def test_script_references_preserve_control_flow_and_low_bits(self):
        raw = bytes(ord(c)|128 for c in '.T P "one;\r.J +2\r.P "two\r') + b'\0\xff\x8d'
        # A low-bit space is legal in the original display literal.
        raw = raw.replace(b'\xef\xee\xe5', b'\xef \xe5')
        first = raw.index(b'\xef \xe5'); second = raw.index(b'\xf4\xf7\xef')
        refs = [(dict(offset=p, length=3, original_hex=raw[p:p+3].hex()), i)
                for p,i in [(first,0x8000),(second,0)]]
        result = referenced_script(raw, refs)
        self.assertEqual(result, raw[:first]+reference(0x8000)+raw[first+3:second]+reference(0)+raw[second+3:raw.index(0)+1])
        self.assertEqual(result.count(b'\x8d'), 3)
        with self.assertRaises(ValueError):
            referenced_script(raw, refs+refs[:1])
        refs[0][0]['original_hex'] = '000000'
        with self.assertRaises(ValueError):
            referenced_script(raw, refs)


if __name__ == '__main__':
    unittest.main()
