"""Information-loss checks for the native renderer's wrapping and CR behavior."""
import unittest

from layout_preview import Screen, part


class LayoutPreviewTests(unittest.TestCase):
    def test_last_row_clamps_and_overwrites_instead_of_scrolling(self):
        screen = Screen(row=15, col=39)
        screen.text('AB', False, 'overflow')
        screen.text('\nC', False, 'next-line')
        result = screen.result()
        self.assertEqual((result['end_row'], result['end_column']), (15, 1))
        self.assertEqual(result['rows'][3][0], 'C')
        self.assertEqual(result['overwrites'][0]['old']['char'], 'B')
        self.assertTrue(result['body_on_prompt_row'])

    def test_full_row_wrap_followed_by_native_cr_skips_another_row(self):
        screen = Screen()
        screen.text('A' * 40, True, 'full-row')
        self.assertEqual((screen.row, screen.col), (14, 0))
        screen.text('B', False, 'next-message')
        self.assertEqual(screen.result()['rows'][2][0], 'B')

    def test_semicolon_join_and_numeric_newline_preserve_unit_position(self):
        screen = Screen()
        screen.text('약병에 남은 알약 수(개): ', False, 'prefix')
        screen.text('255', True, 'native-number')
        screen.text('생명을 지켜 줄 약입니다!', True, 'suffix')
        result = screen.result()
        self.assertEqual(result['rows'][0].rstrip(), '약병에 남은 알약 수(개): 255')
        self.assertEqual(result['rows'][1].rstrip(), '생명을 지켜 줄 약입니다!')
        self.assertFalse(result['overwrites'])
        self.assertFalse(result['body_on_prompt_row'])

    def test_prompt_role_does_not_hide_body_collision(self):
        screen = Screen(row=15)
        screen.text('OK>', False, 'prompt', 'prompt')
        self.assertTrue(screen.result()['prompt_row_used'])
        self.assertFalse(screen.result()['body_on_prompt_row'])
        screen.text('본문', False, 'body')
        self.assertTrue(screen.result()['body_on_prompt_row'])

    def test_exclusion_and_empty_translation_have_distinct_meanings(self):
        message = dict(id='blank', source='pills remaining!', ko='',
                       status='draft', layout=dict(newline=True))
        self.assertEqual(part(message)['text'], '')
        message.update(status='excluded', source='OK>^')
        self.assertEqual(part(message)['text'], 'OK>^')
        self.assertEqual(part(message)['role'], 'prompt')


if __name__ == '__main__':
    unittest.main()
