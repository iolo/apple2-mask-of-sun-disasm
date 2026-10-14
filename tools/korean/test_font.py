import base64
import unittest

from font import decode_bitmap, hgr_glyph, load_font, subset


class FontTests(unittest.TestCase):
    def test_run_kinds(self):
        # 1x7: zero, white, repeated intermediate value, literal white/zero.
        data = bytes([1, 7, 1, 0x42, 0x82, 17, 0xc2, 255, 0])
        self.assertEqual(decode_bitmap(base64.b64encode(data).decode()),
                         (7, 1, bytes([0, 255, 255, 17, 17, 255, 0])))

    def test_truncation_rejected(self):
        for data in [bytes([1]), bytes([1, 2, 0xc2, 255]), bytes([1, 1, 0x42])]:
            with self.assertRaises(ValueError):
                decode_bitmap(base64.b64encode(data).decode())

    def test_hgr_bit_order_and_clipping(self):
        g = {'width': 2, 'height': 1, 'x': 5, 'y': 8, 'pixels': bytes([255, 255])}
        self.assertEqual(hgr_glyph(g), bytes([0x60, 0, 0, 0, 0, 0, 0, 0]))
        g['x'] = 6
        with self.assertRaises(ValueError):
            hgr_glyph(g)

    def test_pinned_font_subset(self):
        g = load_font()
        chars, data = subset('한글 ABC\n한글', g)
        self.assertEqual(chars, sorted(set('한글 ABC')))
        self.assertEqual(len(data), 8 * len(chars))
        self.assertTrue(all(b < 128 for b in data))
        with self.assertRaises(ValueError):
            subset('\U0010ffff', g)


if __name__ == '__main__':
    unittest.main()
