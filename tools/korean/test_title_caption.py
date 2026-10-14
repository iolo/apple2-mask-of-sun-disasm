"""The generated title must not move relative-jump targets within INITIAL."""
import unittest

from catalog import ROOT
from title_caption import high, insert_caption


class TitleTests(unittest.TestCase):
    def original(self):
        raw=(ROOT/'assets/raw/a/files/initial.bin').read_bytes()
        raw=raw[:raw.index(0)+1]
        first=raw.index(high('.P "'))+4;end=raw.index(b'\x8d',first)
        return raw[:first]+high('~8001')+raw[end:]

    def test_caption_keeps_original_prefix_tail_and_relative_jump_body(self):
        original=self.original()
        updated,meta=insert_caption(original,0x8002,0x8001,6)
        at=meta['insertion_offset'];size=meta['inserted_bytes']
        self.assertEqual(updated[:at]+updated[at+size:],original)
        self.assertEqual(updated[at:at+size],high('.V 1\r.H 17\r.P "~8002\r'))
        self.assertEqual(updated.count(high('.T J -8\r')),original.count(high('.T J -8\r')))
        self.assertEqual(updated[meta['reference_offset']:meta['reference_offset']+5],high('~8002'))
        self.assertLessEqual(len(updated),2048)

    def test_changed_hook_reinsertion_and_script_overflow_reject(self):
        original=self.original();updated,_=insert_caption(original,0x8002,0x8001,6)
        for raw in [b'x'+original[1:],updated,original[:-1]+b'X'*(2048-len(original))+b'\0']:
            with self.assertRaises(ValueError):insert_caption(raw,0x8002,0x8001,6)

    def test_room_ids_and_wrapping_titles_reject(self):
        for title,credit,cells in [(0,0x8001,6),(0x8002,0,6),(0x10000,0x8001,6),
                                  (0x8002,0x8001,0),(0x8002,0x8001,39)]:
            with self.assertRaises(ValueError):insert_caption(self.original(),title,credit,cells)


if __name__=='__main__':unittest.main()
