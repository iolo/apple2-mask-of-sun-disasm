"""New/changed native output sites must not inherit a completeness claim."""
import copy
import unittest

from audit_outputs import call_sites, verify_policy


class OutputTests(unittest.TestCase):
    def test_output_calls_include_inline_labels_indirection_and_conditionals(self):
        source='one: jsr rom_cout\n.ifdef KO\n jsr ko_print_script_string\n.else\n jsr print_script_string\n.endif\n jmp (string_printer_vector)\n jsr unrelated\n jsr rom_cout\n'
        sites=call_sites(source,'fixture.s')
        self.assertEqual(len(sites),5)
        self.assertEqual(sites[-1]['id'],'fixture.s:one:jsr:rom_cout:2')
        self.assertEqual(sites[3]['target'],'(string_printer_vector)')

    def test_changed_source_new_site_or_missing_catalog_reference_rejects(self):
        sites=call_sites('label: jsr rom_cout','fixture.s')
        policy={'source_sha256':{'fixture.s':'hash'},'sites':{sites[0]['id']:'ui'},
                'categories':{'ui':{'treatment':'translate','reason':'fixture','catalog_ids':['message']}}}
        verify_policy(policy['source_sha256'],sites,policy,{'message'})
        for hashes,calls,ids in [({'fixture.s':'changed'},sites,{'message'}),
                                  (policy['source_sha256'],[],{'message'}),
                                  (policy['source_sha256'],sites,set())]:
            with self.assertRaises(ValueError):verify_policy(hashes,calls,policy,ids)
        for site,category in [('missing.py:generate','ui'),('fixture.s:generate','unknown')]:
            changed=copy.deepcopy(policy);changed['generated_outputs']={site:category}
            with self.assertRaises(ValueError):verify_policy(policy['source_sha256'],sites,changed,{'message'})


if __name__=='__main__':unittest.main()
