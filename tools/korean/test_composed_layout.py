"""Detect inventory row-loss hazards beyond isolated message-width checks."""
import unittest

from audit_composed_layout import check, inventory_pages


def message(mid, text, newline=False, source='item'):
    return dict(id=mid, ko=text, source=source, status='draft', layout=dict(newline=newline))


class ComposedLayoutTests(unittest.TestCase):
    def setUp(self):
        self.heading=message('heading','주변에 보이는 것:',True)
        self.wait=message('wait','[ 아무 키나 누르세요 ]',True,'[ waiting ]')

    def test_nearby_heading_leaves_only_two_items_on_first_page(self):
        items=[message(str(n),'물건') for n in range(3)]
        pages=inventory_pages(items,self.heading,self.wait,True)
        self.assertEqual(len(pages),2)
        self.assertTrue(all(check(p) for p in pages))
        self.assertEqual(pages[0].cells[14,0]['source'],'1')
        self.assertEqual(pages[1].cells[12,0]['source'],'2')

    def test_item_expansion_cannot_silently_break_line_count_pagination(self):
        for text in ('가'*40,'한\n글'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                inventory_pages([message('expanded',text)],self.heading,self.wait,False)

    def test_multiline_heading_overflow_is_reported_even_if_each_line_fits(self):
        heading=message('heading','첫 줄\n둘째 줄',True)
        pages=inventory_pages([message('one','하나'),message('two','둘')],heading,self.wait,True)
        self.assertFalse(check(pages[0]))


if __name__=='__main__':
    unittest.main()
