import importlib.util
import unittest
from pathlib import Path

spec=importlib.util.spec_from_file_location('release_state',Path(__file__).resolve().parents[1]/'site/deploy/sync-additions-state.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ReleaseStateTests(unittest.TestCase):
    def test_full_release_preserves_previous_exported_records(self):
        additions=[{'id':'old','notes':'preserved'},{'id':'new'}]
        result=module.validate({'items':[{'id':'base'},*additions]},additions,[{'id':'old'}])
        self.assertEqual(result,additions)

    def test_stale_full_release_cannot_drop_live_additions(self):
        with self.assertRaises(ValueError):
            module.validate({'items':[{'id':'old'},{'id':'new'}]},[{'id':'old'}],[{'id':'old'},{'id':'new'}])

    def test_export_cannot_contain_unpublished_or_duplicate_records(self):
        for incoming in [[{'id':'missing'}],[{'id':'old'},{'id':'old'}]]:
            with self.assertRaises(ValueError):
                module.validate({'items':[{'id':'old'}]},incoming,[])


if __name__=='__main__':unittest.main()
