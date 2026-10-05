"""Verify artwork units independently of archival rows and timeline selection."""
import hashlib
import copy
import json
import unittest
from pathlib import Path
from bs4 import BeautifulSoup
from PIL import Image
from case_policy import apply_case_policy, is_case, in_timeline, timeline_media
from card_metadata import apply_card_metadata

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'public-site'
CAT=json.loads((OUT/'data/catalog.json').read_text(encoding='utf8'))
ITEMS=CAT['items']
BY={x['id']:x for x in ITEMS}

class CaseUnitTests(unittest.TestCase):
    def test_all_dates_and_media_can_be_timeline_representatives(self):
        cover=next(x['thumbnail'] for x in ITEMS if x['thumbnail'].endswith('.webp'))
        outputs=[]
        for n,medium in enumerate(['svg','image','animation','3d','game','video','audio','other']):
            sample=copy.deepcopy(BY['simon-gemini-flash-default-2025-04-17'])
            for key in ['modelRunGroup','representativeOf','parentId','canonicalId','cropProvenance']:
                sample.pop(key,None)
            sample.update(id='all-media-fixture-'+str(n),date='2024' if n==0 else '2026-09-30',format=medium,originalForm=medium,originalLevel='',thumbnail=cover,representativeMedia=cover,media=[{'src':cover}])
            outputs.append(sample)
        reviewed=apply_case_policy(outputs,OUT,reviews={})
        self.assertTrue(all(in_timeline(x) for x in reviewed))
        self.assertEqual([x['format'] for x in reviewed],['svg','image','animation','3d','game','video','audio','other'])
        reference={**outputs[0],'id':'reference-fixture','referenceOnly':True}
        self.assertFalse(in_timeline(apply_case_policy([reference],OUT,reviews={})[0]))

    def test_preserves_every_original_and_attachment(self):
        before=json.loads((ROOT/'pelican-archive/research/2026-10-01-case-units/before-catalog.json').read_text(encoding='utf8'))['items']
        for old in before:
            self.assertIn(old['id'],BY)
            current=BY[old['id']]
            self.assertEqual(current['sourceUrl'],old['sourceUrl'])
            self.assertTrue({m['src'] for m in old['media']}<={m['src'] for m in current['media']})
            self.assertTrue((OUT/current['path'].lstrip('/')/'index.html').is_file())

    def test_35_cases_seven_timeline_representatives(self):
        parent='reddit-emu001-codex-pelican-matrix-2026-09-26'
        samples=[x for x in ITEMS if x.get('parentId')==parent]
        self.assertEqual(len(samples),35)
        self.assertTrue(all(is_case(x) for x in samples))
        self.assertEqual(sum(in_timeline(x) for x in samples),7)
        self.assertEqual({x['originalLevel'] for x in samples if in_timeline(x)},{'medium'})
        self.assertEqual(len({x['caseNumber'] for x in samples}),35)
        self.assertFalse(is_case(BY[parent]))
        for sample in samples:
            self.assertEqual(len(sample['comparisonIds']),5)
            for prefix in ['', 'en/']:
                doc=(OUT/prefix/sample['path'].lstrip('/')/'index.html').read_text(encoding='utf8')
                soup=BeautifulSoup(doc,'html.parser')
                comparison=soup.select_one('[data-setting-comparison]')
                self.assertEqual(len(comparison.select('figure')),5)
                self.assertLess(doc.index('data-setting-comparison'),doc.index('class="detail-gallery"'))
                self.assertIsNotNone(soup.find('img',src=sample['cropProvenance']['original']))

    def test_source_crops_are_original_pixels(self):
        for x in ITEMS:
            p=x.get('cropProvenance')
            if not p:continue
            original=OUT/p['original'].lstrip('/');crop=OUT/p['crop'].lstrip('/')
            self.assertEqual(hashlib.sha256(original.read_bytes()).hexdigest(),p['sourceSha256'])
            self.assertEqual(hashlib.sha256(crop.read_bytes()).hexdigest(),p['cropSha256'])
            with Image.open(original) as a,Image.open(crop) as b:
                self.assertEqual(a.crop(p['box']).convert('RGBA').tobytes(),b.convert('RGBA').tobytes())
            self.assertNotEqual(x['thumbnail'],p['original'])
            self.assertEqual(x['thumbnail'],p['crop'])

    def test_counts_numbering_and_benchmark_exclusion(self):
        cases=[x for x in ITEMS if is_case(x)]
        self.assertTrue(all(len(x['modelNames'])==1 for x in cases))
        self.assertEqual(len(cases),CAT['counts']['cases'])
        self.assertEqual(sum(in_timeline(x) for x in ITEMS),CAT['counts']['timeline'])
        ordered=sorted(cases,key=lambda x:(x['date'],x['id']))
        self.assertEqual([x['caseNumber'] for x in ordered],list(range(1,len(cases)+1)))
        for x in ITEMS:
            if not is_case(x):self.assertIsNone(x['caseNumber'])
            if in_timeline(x):
                self.assertEqual(len(x['modelNames']),1)
                self.assertTrue(timeline_media(x,OUT))
                self.assertFalse(x.get('representativeOf'))
        for lang in ['', 'en/']:
            soup=BeautifulSoup((OUT/lang/'timeline/index.html').read_text(encoding='utf8'),'html.parser')
            self.assertIsNotNone(soup.select_one('select[name=family]'))
            for card in soup.select('.timeline-card'):
                self.assertEqual(len(card.select('img')),1)
                self.assertFalse(card.select('.note, .media-label, .card-body'))
                path=card.select_one('.card-cover')['href']
                item=next(x for x in ITEMS if path.endswith(x['path']))
                self.assertEqual(card.select_one('.case-number').get_text(),'#'+str(item['caseNumber']))

    def test_june_source_is_split_not_replaced(self):
        panels=[x for x in ITEMS if x['id'].startswith('simon-june-slides-')]
        self.assertEqual(len(panels),22)
        self.assertTrue(all(x['datePrecision']=='month' for x in panels))
        for panel in panels:
            self.assertTrue(is_case(panel) or is_case(BY[panel['canonicalId']]))
        self.assertEqual({x['sourceUrl'] for x in panels},{'https://simonwillison.net/2025/Jun/6/six-months-in-llms/'})
        self.assertFalse(is_case(next(x for x in ITEMS if x['originalId']=='elo-june-2025')))

    def test_old_source_posts_are_individual_outputs(self):
        for original,expected,representatives in [
            ('x-1887198978334482514',3,3),('x-1902509366244471291',2,1),
            ('x-1989123523206578351',2,1),('x-2024544280451350689',2,1),
            ('x-simon-qwen36-2026-04-22',2,1)]:
            parent=next(x for x in ITEMS if x['originalId']==original)
            children=[BY[k] for k in parent['linkedCaseIds']]
            self.assertFalse(is_case(parent))
            self.assertEqual(len(children),expected)
            self.assertTrue(all(is_case(x) for x in children))
            self.assertEqual(sum(in_timeline(x) for x in children),representatives)
        alias=BY['simon-june-slides-o1-pro-2025-03']
        self.assertFalse(is_case(alias))
        self.assertEqual(BY[alias['canonicalId']]['date'],'2025-03-19')
        self.assertEqual(BY['simon-source-1989123523206578351-gpt-5-1-none']['date'],'2025-11-13')

    def test_policy_is_idempotent_for_server_rebuilds(self):
        again=apply_card_metadata(apply_case_policy(ITEMS,OUT))
        self.assertEqual(ITEMS,again)

    def test_old_play_entries_and_same_day_prompt_alternative_are_preserved(self):
        from catalog_policy import playable_records
        self.assertEqual(len(playable_records(ITEMS)),5)
        self.assertTrue(BY['variora-gemini-3-8-flash-2026-09-20']['interactive'])
        for lang in ['', 'en/']:
            page=BeautifulSoup((OUT/lang/'play/index.html').read_text(encoding='utf8'),'html.parser')
            self.assertEqual(len(page.select('[data-results] .card')),5)
            self.assertNotIn('#None',str(page))
        runs=[x for x in ITEMS if x.get('modelRunGroup')=='simon-gemini3-classic-2025-11-18']
        self.assertEqual(len(runs),3)
        self.assertEqual([x['originalLevel'] for x in runs if in_timeline(x)],['high'])

    def test_existing_named_efforts_follow_the_same_rule(self):
        runs=[x for x in ITEMS if x['id'].startswith('simon-gpt61-sol-')]
        self.assertEqual(len(runs),5)
        self.assertEqual([x['originalLevel'] for x in runs if in_timeline(x)],['medium'])
        for run in runs:self.assertEqual(len(run['comparisonIds']),5)

    def test_requoted_grid_panels_do_not_create_new_works(self):
        for stem,expected in [('claude-fable-5-1',5),('claude-opus-5-5',4)]:
            aliases=[x for x in ITEMS if x['id'].startswith('simon-grid-2026-09-22-'+stem+'-')]
            self.assertEqual(len(aliases),expected)
            for alias in aliases:
                self.assertFalse(is_case(alias))
                canonical=BY[alias['canonicalId']]
                self.assertTrue(is_case(canonical))
                self.assertEqual(len(canonical['comparisonIds']),expected)
                self.assertEqual(alias['comparisonIds'],canonical['comparisonIds'])
                self.assertIn(alias['media'][-1]['src'],{m['src'] for m in canonical['media']})

if __name__=='__main__':unittest.main()
