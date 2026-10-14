"""Checks for source preservation and fail-closed review editing."""
import copy
from pathlib import Path
import tempfile
import unittest

from catalog import directive, entry, export_review, import_review, literal_bytes, merge, python_text_constant, review_hash, script_lines, validate


class CatalogTests(unittest.TestCase):
    def test_generated_notice_is_read_without_executing_python(self):
        source='raise RuntimeError("must not run")\nNOTICE = "PRINT; \\\"A\\\""\n'
        self.assertEqual(python_text_constant(source,'NOTICE'),'PRINT; "A"')
        for bad in ('NOTICE = make_text()', 'NOTICE = "A"\nNOTICE = "B"', 'NOTICE = 3', 'other = "A"'):
            with self.subTest(bad=bad),self.assertRaises(ValueError):python_text_constant(bad,'NOTICE')

    def test_required_input_spelling_survives_korean_particles(self):
        c = self.sample(); m = c['messages'][0]
        m.update(ko='RETURN을 누르세요. SAY XOTZIL', protected_tokens=['RETURN', 'XOTZIL'])
        validate(c)
        for text in ('return을 누르세요. SAY XOTZIL', 'RETURNED SAY XOTZIL', 'RETURN SAY XOTZI'):
            m['ko'] = text
            with self.subTest(text=text), self.assertRaises(ValueError):
                validate(c)

    def test_literal_notice_preserves_controls_and_string_punctuation(self):
        source = 'notice: .byte 13,"A,B;C",$8D ; comment\n .byte 0\nnext: .byte 99\n'
        self.assertEqual(literal_bytes(source, 'notice'), b'\rA,B;C\x8d\0')

    def test_literal_notice_rejects_assembly_expressions_and_ambiguous_labels(self):
        for source in ('notice: .byte symbol', 'notice: .byte $80+1',
                       'notice: .byte 256', 'notice: .byte 1,',
                       'notice: .byte 1\nnotice: .byte 2', 'other: .byte 1'):
            with self.subTest(source=source), self.assertRaises(ValueError):
                literal_bytes(source, 'notice')

    def sample(self):
        m = entry('room:0042', 'A | "B"; C', {'path': 'fixture', 'offset': 66},
                  'script_text', {'before': ['.I N:1'], 'after': []}, newline=False)
        return {'schema_version': 1, 'messages': [m]}

    def test_condition_and_literal_boundaries(self):
        self.assertEqual(directive('.T E P "quoted .P ";'), ('P', 7, ['T', 'E']))
        self.assertEqual(directive('.P N;'), ('P', 3, []))
        self.assertIsNone(directive('SAY .P "literal'))

    def test_roundtrip_keeps_low_bits_and_padding(self):
        raw = b'\xae\xd0\xa0\xa2\xc1 \xc2\xbb\x8d\0\xff\x8d\x01'
        lines = script_lines(raw)
        self.assertEqual(lines[0]['raw'], raw[:8])
        self.assertTrue(lines[0]['cr'])
        with self.assertRaises(ValueError):
            script_lines(b'no terminator')

    def test_review_roundtrip_and_edit_revokes_approval(self):
        c = self.sample()
        m = c['messages'][0]
        m.update(ko='한글 | "인용"\n둘째 줄', status='approved', reviewer='fixture', reviewed_at='2026-10-13')
        m['reviewed_hash'] = review_hash(m)
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'review.md'
            export_review(c, p)
            saved = copy.deepcopy(c)
            import_review(c, p)
            self.assertEqual(c, saved)
            p.write_text(p.read_text().replace('둘째 줄', '수정한 줄'))
            import_review(c, p)
            self.assertEqual(m['status'], 'draft')
            self.assertIsNone(m['reviewed_hash'])
            with self.assertRaises(ValueError):
                validate(c, approved=True)

    def test_missing_duplicate_and_stale_review_rejected(self):
        for mode in ['missing', 'duplicate', 'stale']:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                c = self.sample()
                p = Path(tmp) / 'review.md'
                export_review(c, p)
                rows = p.read_text().splitlines()
                if mode == 'missing':
                    rows = rows[:-1]
                elif mode == 'duplicate':
                    rows.append(rows[-1])
                else:
                    rows[-1] = rows[-1].replace(c['messages'][0]['source_hash'], 'stale')
                p.write_text('\n'.join(rows))
                with self.assertRaises(ValueError):
                    import_review(c, p)

    def test_source_change_archived_and_not_approved(self):
        old = self.sample()
        old['messages'][0]['ko'] = '원래 번역'
        fresh = self.sample()
        fresh['messages'][0] = entry('room:0042', 'Changed', {}, 'script_text', {})
        result = merge(old, fresh)
        self.assertIsNone(result['messages'][0]['ko'])
        self.assertEqual(result['orphaned'][0]['ko'], '원래 번역')
        with self.assertRaises(ValueError):
            validate(result, approved=True)


if __name__ == '__main__':
    unittest.main()
