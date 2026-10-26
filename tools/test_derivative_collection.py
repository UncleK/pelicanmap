"""The new collection must keep attribution, old URLs and existing browse behavior."""
import csv
import copy
import io
import json
import unittest
from pathlib import Path
from bs4 import BeautifulSoup
from case_policy import apply_case_policy,in_timeline,is_case,is_derivative

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'public-site'

class DerivativeCollectionTests(unittest.TestCase):
    def test_missing_default_and_legacy_review_do_not_exclude_classic_runs(self):
        catalog=json.loads((OUT/'data/catalog.json').read_text(encoding='utf8'))
        base=next(x for x in catalog['items'] if is_case(x) and in_timeline(x) and not is_derivative(x))
        rows=[];reviews={}
        for level in ['low','max']:
            row=copy.deepcopy(base)
            for key in ['representativeOf','parentId','canonicalId','cropProvenance','authorDefault']:
                row.pop(key,None)
            row.update(id='classic-run-'+level,modelRunGroup='explicit-source-run',originalLevel=level)
            rows.append(row)
            reviews[row['id']]={'sourceUrl':row['sourceUrl'],'role':'case','timelineVisible':False}
        result=apply_case_policy(rows,OUT,reviews)
        self.assertTrue(all(in_timeline(x) for x in result))
        self.assertTrue(all(not x.get('representativeOf') for x in result))
        self.assertEqual([x['media'] for x in result],[x['media'] for x in rows])

    def test_derivatives_cannot_reenter_the_timeline_via_old_task_or_review(self):
        catalog=json.loads((OUT/'data/catalog.json').read_text(encoding='utf8'))
        base=next(x for x in catalog['items'] if is_case(x) and in_timeline(x) and not is_derivative(x))
        for classification in [{'topicTags':['derivative']}, {'promptCategory':'saturn-rings'}, {'task':'derived'}]:
            sample=copy.deepcopy(base)
            for key in ['modelRunGroup','representativeOf','parentId','canonicalId','cropProvenance']:
                sample.pop(key,None)
            sample.update(id='reviewed-derivative-fixture',task='pelican_bicycle',originalLevel='')
            sample.update(classification)
            review={sample['id']:{'sourceUrl':sample['sourceUrl'],'role':'case','timelineVisible':True}}
            result=apply_case_policy([sample],OUT,review)[0]
            self.assertTrue(is_case(result))
            self.assertTrue(is_derivative(result))
            self.assertFalse(in_timeline(result))
            self.assertEqual(result['media'],sample['media'])

    def test_classic_3d_style_alone_stays_eligible(self):
        catalog=json.loads((OUT/'data/catalog.json').read_text(encoding='utf8'))
        sample=copy.deepcopy(next(x for x in catalog['items'] if is_case(x) and in_timeline(x) and not is_derivative(x)))
        for key in ['modelRunGroup','representativeOf','parentId','canonicalId','cropProvenance']:
            sample.pop(key,None)
        sample.update(id='classic-3d-fixture',task='pelican_bicycle',promptCategory='classic',topicTags=[],originalLevel='',format='3d')
        self.assertTrue(in_timeline(apply_case_policy([sample],OUT,{})[0]))

    def test_published_timeline_and_derivatives_are_disjoint(self):
        for prefix in ['', 'en/']:
            catalog=json.loads((OUT/prefix/'data/catalog.json').read_text(encoding='utf8'))
            self.assertFalse([x['id'] for x in catalog['items'] if in_timeline(x) and is_derivative(x)])

    def test_explicit_prompt_categories_are_used_instead_of_style_guesses(self):
        for category in ['derived','derivative','pelican_bicycle_derivative','saturn-rings']:
            self.assertTrue(is_derivative({'promptCategory':category}))
        self.assertTrue(is_derivative({'task':'derived'}))
        self.assertFalse(is_derivative({'title':'tower-shaped bicycle','promptCategory':'classic'}))

    def test_bilingual_collection_and_original_towers(self):
        for prefix,label in [('', '衍生作品'),('en/','Derivative works')]:
            cat=json.loads((OUT/prefix/'data/catalog.json').read_text(encoding='utf8'))
            selected=[x for x in cat['items'] if is_case(x) and 'derivative' in x.get('topicTags',[])]
            ids={x['id'] for x in selected}
            for key in ['x-binkg-fable-55-pelican-tower-animation-2026-10-17','x-harshith-gemini4-argon-high-twelve-layer-tower-2026-10-18','x-thungdick-deepseek-v41-flash-1017-recursive-2026-10-19']:
                self.assertIn(key,ids)
            self.assertNotIn('x-moblacksoil-deepseek-v41-flash-1017-whale-animation-2026-10-17',ids)
            self.assertTrue(all(not x.get('referenceOnly') for x in selected))
            soup=BeautifulSoup((OUT/prefix/'derivatives/index.html').read_text(encoding='utf8'),'html.parser')
            nav=soup.select('.nav a');labels=[a.text for a in nav]
            self.assertEqual(labels[3],label)
            self.assertEqual(nav[3]['aria-current'],'page')
            self.assertEqual(soup.select_one('[data-browser]')['data-scope'],'derivative')
            for selector in ['[data-search]','[data-sort-toggle]','[data-density-toggle]','[data-pagination]']:
                self.assertIsNotNone(soup.select_one(selector))
            self.assertEqual(len(soup.select('[data-results] article.card')),min(24,len(selected)))
            rows=list(csv.DictReader(io.StringIO((OUT/prefix/'data/catalog.csv').read_text(encoding='utf8'))))
            self.assertEqual({x['id'] for x in rows if 'derivative' in x.get('topicTags','').split(',') and x['caseVisible']=='true' and x['referenceOnly']=='false'},ids)

if __name__=='__main__':unittest.main()
