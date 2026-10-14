"""Synthetic fixtures preserve layout/byte cost while removing draft bodies."""
import struct
import unittest

from encoding import encode, decode, pool
from synthetic import mask_pool


class SyntheticTests(unittest.TestCase):
    def test_mask_keeps_indices_aliases_token_widths_and_control_low_bytes(self):
        chars=[chr(0xac00+i) for i in range(300)]
        ids={c:i for i,c in enumerate(chars)}
        texts=['A '+chars[0]+chars[10]+chars[141]+'\nB', '', 'DUP', 'DUP']
        original,_=pool([{'ko':s} for s in texts],ids)
        masked=mask_pool(original,chars,256)
        self.assertEqual(len(masked),len(original))
        self.assertEqual(masked[:10],original[:10])
        offsets=struct.unpack_from('<4H',masked,2)
        self.assertEqual(offsets[2],offsets[3])
        for text,start in zip(texts,offsets):
            expected=''.join(c if c in ' \n' else chars[256] if ord(c)>=128 else 'X' for c in text)
            size=len(encode(text,ids))
            self.assertEqual(decode(masked[start:start+size],chars),expected)

    def test_invalid_pool_cannot_leave_unmasked_tail_or_index_into_header(self):
        data,_=pool([{'ko':'ABC'}],{})
        for damaged in (data[:-1], data+b'x', data[:2]+b'\x01\0'+data[4:], b'\0\0x'):
            with self.subTest(damaged=damaged),self.assertRaises(ValueError):
                mask_pool(damaged,['가'])
        self.assertEqual(mask_pool(b'',[]),b'')


if __name__=='__main__':unittest.main()
