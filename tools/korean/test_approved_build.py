"""Production media must reject missing/stale approval before creating output."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import startup_disk
from catalog import entry, review_hash


class ApprovedBuildTests(unittest.TestCase):
    def test_unapproved_or_changed_translation_fails_before_output(self):
        message=entry('test','English',{},'script_text',{})
        message.update(ko='한국어',status='approved',reviewer='fixture',reviewed_at='2026-10-14')
        message['reviewed_hash']=review_hash(message)
        for change in ({'status':'draft'},{'ko':'변경'},{'context':{'changed':True}}):
            with self.subTest(change=change),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);path=root/'assets/korean/messages.json'
                path.parent.mkdir(parents=True)
                candidate=copy.deepcopy(message);candidate.update(change)
                path.write_text(json.dumps({'messages':[candidate]}))
                output=root/'output'
                with patch.object(startup_disk,'ROOT',root),patch('sys.argv',['startup_disk.py','--approved','--output',str(output)]):
                    with self.assertRaisesRegex(ValueError,'missing or stale human approval'):
                        startup_disk.main()
                self.assertFalse(output.exists())


if __name__=='__main__':unittest.main()
