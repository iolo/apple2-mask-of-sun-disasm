"""Reclaim native B data sectors without inheriting stale TS-list headers."""
import unittest

from startup_disk import Disk, dos_disk, file_bytes, offset, SAVE_SECTORS


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

    def test_save_reservation_survives_allocation_and_raw_snapshot_writes(self):
        files=[(f'FILE{i}',0,bytes([i+1])*110*256) for i in range(3)]
        image,report=dos_disk(self.seed(),files,reserved_sectors=SAVE_SECTORS)
        disk=Disk(image);catalog=disk.catalog();vtoc=disk.sector(17,0)
        self.assertEqual(len(SAVE_SECTORS),145)
        self.assertFalse(SAVE_SECTORS.intersection(disk.owners))
        self.assertTrue(any(t>=32 for t,s in disk.owners))
        self.assertEqual(report['free_sectors'],18)
        saved=bytearray(image)
        for t,s in SAVE_SECTORS:
            self.assertFalse(int.from_bytes(vtoc[0x38+4*t:0x3a+4*t],'big')&(1<<s))
            self.assertEqual(disk.sector(t,s),bytes(256))
            saved[offset(t,s):offset(t,s)+256]=b'\xa5'*256
        self.assertEqual(Disk(bytes(saved)).catalog(),catalog)
        for spec,file in zip(files,catalog['files']):
            self.assertEqual(file_bytes(saved,file),spec[2])
        with self.assertRaisesRegex(ValueError,'allocation overflow'):
            dos_disk(self.seed(),[(f'FILE{i}',0,b'x'*117*256) for i in range(3)],
                     reserved_sectors=SAVE_SECTORS)


if __name__ == '__main__':
    unittest.main()
