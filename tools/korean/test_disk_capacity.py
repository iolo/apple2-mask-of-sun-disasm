"""Reclaim native B data sectors without inheriting stale TS-list headers."""
import unittest

from startup_disk import Disk, dos_disk, file_bytes, offset


class DiskCapacityTests(unittest.TestCase):
    def seed(self):
        data = bytearray(143360)
        # Native B file data may occupy tracks 1/2. The first new TS block must
        # clear its old contents, including the continuation and index fields.
        data[offset(1, 0):offset(1, 0)+256] = b'\xa5' * 256
        vtoc = offset(17, 0)
        data[vtoc+3] = 3
        data[vtoc+6] = 254
        data[vtoc+0x27] = 122
        return bytes(data)

    def test_early_reclaimed_sector_becomes_clean_ts_list(self):
        image, report = dos_disk(self.seed(), [('TEST', 0, b'payload')],
                                 reusable_sectors={(1, 0), (1, 1), (3, 0)})
        file = Disk(image).catalog()['files'][0]
        self.assertEqual(file['ts_lists'], [(1, 0)])
        self.assertEqual(file_bytes(image, file), b'payload'.ljust(256, b'\0'))
        self.assertEqual(report['free_sectors'], 1)
        self.assertEqual(image[offset(1, 0):offset(1, 0)+12], bytes(12))

    def test_reusable_set_cannot_overlap_loader_sentinel_or_catalog(self):
        for pair in ((0, 1), (17, 1), (35, 0), (1, 16)):
            with self.subTest(pair=pair), self.assertRaises(ValueError):
                dos_disk(self.seed(), [('TEST', 0, b'x')], reusable_sectors={pair})


if __name__ == '__main__':
    unittest.main()
