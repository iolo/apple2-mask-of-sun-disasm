"""Fixed native UI slots must not move code or reference evictable room text."""
import unittest

from native_ui import replace


class NativeUITests(unittest.TestCase):
    def message(self, newline=True):
        return {'id':'native:test','source':'PROMPT TEXT','status':'draft',
                'layout':{'newline':newline}}

    def test_fixed_slot_preserves_surrounding_code_and_semicolon(self):
        for newline in (True,False):
            message=self.message(newline)
            original=bytes(ord(c)|128 for c in 'PROMPT TEXT'+('' if newline else ';')+'\r')
            before=b'\xa9\x80'+original+b'\x60\xea'
            after,record=replace(before,2,original,message,{'native:test':0x809a})
            expected=bytes(ord(c)|128 for c in '~809A'+('' if newline else ';')+'\r')
            self.assertEqual(len(before),len(after))
            self.assertEqual(after[:2],before[:2]);self.assertEqual(after[-2:],before[-2:])
            self.assertEqual(after[2:2+len(expected)],expected)
            self.assertEqual(after[2+len(expected):-2],bytes(len(original)-len(expected)))
            self.assertEqual(record['message_id'],0x809a)

    def test_stale_or_small_slots_reject_before_a_patch_can_escape(self):
        message=self.message();original=bytes(ord(c)|128 for c in 'PROMPT TEXT\r')
        for damaged in (b'x'+original[1:],original[:-1],b'\x8d'+original[1:]):
            with self.subTest(damaged=damaged),self.assertRaises(ValueError):
                replace(damaged,0,original,message,{'native:test':0x8000})
        short=dict(message,source='A')
        with self.assertRaises(ValueError):replace(b'\xc1\x8d',0,b'\xc1\x8d',short,{'native:test':0x8000})
        changed=dict(message,layout={'newline':False})
        with self.assertRaises(ValueError):replace(original,0,original,changed,{'native:test':0x8000})

    def test_room_ids_missing_ids_and_exclusions_are_never_packed(self):
        message=self.message();original=bytes(ord(c)|128 for c in 'PROMPT TEXT\r')
        for aliases in ({},{'native:test':0},{'native:test':0x10000}):
            with self.assertRaises(ValueError):replace(original,0,original,message,aliases)
        message['status']='excluded'
        with self.assertRaises(ValueError):replace(original,0,original,message,{'native:test':0x8000})


if __name__=='__main__':unittest.main()
