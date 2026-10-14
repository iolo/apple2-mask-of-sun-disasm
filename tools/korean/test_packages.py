"""Package identity covers payloads, side policy and external build assets."""
import copy
from pathlib import Path
import tempfile
import unittest

from packages import package, split, identify, seal


class PackageTests(unittest.TestCase):
    def test_framing_rejects_truncation_trailing_data_and_unknown_flags(self):
        data=package(b'script\0', b'pool\0', identity=b'x'*12, sides=3)
        self.assertEqual(split(data),(b'script\0',b'pool\0'))
        for damaged in (data[:-1], data+b'x', b'KOR1'+data[4:],
                        data[:20]+b'\0'+data[21:], data[:21]+b'\1'+data[22:]):
            with self.subTest(damaged=damaged), self.assertRaises(ValueError):
                split(damaged)

    def test_identity_is_repeatable_and_changes_with_each_dependency(self):
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)
            path=output/'room.bin'
            original=package(b'script\0',b'pool\0')
            path.write_bytes(original)
            report={'files':[{'side':'a','name':'ROOM 1.0','package':path.name}]}
            assets=[('font',b'font'),('runtime',b'code')]
            identity=identify(report,output,assets)
            seal(report,output,identity)
            self.assertEqual(path.read_bytes()[8:20],identity)
            self.assertEqual(identify(report,output,list(reversed(assets))),identity)
            self.assertNotEqual(identify(report,output,[('font',b'FONT'),assets[1]]),identity)
            changed=copy.deepcopy(report)
            changed['files'][0]['side']='b'
            self.assertNotEqual(identify(changed,output,assets),identity)
            for other in (package(b'SCRIPT\0',b'pool\0'), package(b'script\0',b'POOL\0'),
                          package(b'script\0',b'pool\0',sides=2)):
                path.write_bytes(other)
                self.assertNotEqual(identify(report,output,assets),identity)
            with self.assertRaises(ValueError):
                seal(report,output,bytes(12))


if __name__=='__main__':
    unittest.main()
