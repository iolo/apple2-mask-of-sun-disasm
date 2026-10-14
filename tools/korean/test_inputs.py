"""English spelling audit must obey five-character word cells, not substrings."""
import unittest

from audit_inputs import normalized_words, vocabulary_matches


class InputAuditTests(unittest.TestCase):
    def test_long_words_truncate_but_short_words_do_not_match_longer_ones(self):
        self.assertEqual(normalized_words('SILVER KEY'), 'SILVEKEY  ')
        self.assertTrue(vocabulary_matches('SHOVEL', [{'pattern':'SHOVE'}]))
        self.assertFalse(vocabulary_matches('GO', [{'pattern':'GOLD KEY  '}]))
        self.assertFalse(vocabulary_matches('N', [{'pattern':'NORTH'}]))

    def test_scenery_word_may_be_later_in_a_room_specific_pattern(self):
        patterns = [{'pattern':'DROP URN  RIGHTPEDES'}]
        self.assertTrue(vocabulary_matches('PEDESTAL', patterns))
        self.assertTrue(vocabulary_matches('RIGHT PEDESTAL', patterns))
        self.assertFalse(vocabulary_matches('PEDESTAL RIGHT', patterns))


if __name__ == '__main__':
    unittest.main()
