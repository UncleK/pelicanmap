"""Reviewed restoration guards must not allow unrelated identity or media edits."""
import copy,json,unittest
from pathlib import Path
from archival_test_assertions import reviewed_swe_addition_restoration
ROOT=Path(__file__).resolve().parents[1]
IDENT='variora-step-5-2026-09-20'
class ReviewedMotionGuardTests(unittest.TestCase):
    def setUp(self):
        earlier=json.loads((ROOT/'pelican-archive/research/2026-10-02-model-release-order/additions-before.json').read_text(encoding='utf8'))
        current=json.loads((ROOT/'site/additions.json').read_text(encoding='utf8'))
        self.previous=next(x for x in earlier if x['id']==IDENT)
        self.current=next(x for x in current if x['id']==IDENT)
    def test_exact_review_is_ordinary_motion_only(self):
        self.assertTrue(reviewed_swe_addition_restoration(self,self.previous,self.current))
        self.assertFalse(self.current['interactive'] or self.current.get('demoUrl'))
        reviews=json.loads((ROOT/'site/demo-reviews.json').read_text(encoding='utf8'))
        self.assertNotIn(IDENT,reviews)
        changed=copy.deepcopy(self.current);changed['interactive']=True
        with self.assertRaises(AssertionError):reviewed_swe_addition_restoration(self,self.previous,changed)
    def test_identity_media_and_unrelated_records_are_frozen(self):
        for field,value in [('date','2026-10-06'),('model','invented version'),('sourceUrl','https://invalid.example/'),('media',[])]:
            with self.subTest(field=field):
                changed=copy.deepcopy(self.current);changed[field]=value
                with self.assertRaises(AssertionError):reviewed_swe_addition_restoration(self,self.previous,changed)
        old=copy.deepcopy(self.previous);old['id']='unreviewed-original'
        self.assertFalse(reviewed_swe_addition_restoration(self,old,self.current))
if __name__=='__main__':unittest.main()
