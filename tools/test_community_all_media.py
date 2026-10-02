"""Post-intake regression checks for the explicitly reviewed forum batch."""
import hashlib
import json
import unittest
from pathlib import Path
from bs4 import BeautifulSoup
from PIL import Image
from case_policy import apply_case_policy
from archival_test_assertions import reviewed_context_change

ROOT=Path(__file__).resolve().parents[1]
AUDIT=ROOT/'pelican-archive/research/2026-10-01-community-all-media'
MANIFEST=json.loads((AUDIT/'approved-manifest.json').read_text(encoding='utf8'))
CAT=json.loads((ROOT/'site/catalog.json').read_text(encoding='utf8'))
BY={x['id']:x for x in CAT['items']}

class CommunityMediaTests(unittest.TestCase):
    def test_twenty_six_outputs_and_eighteen_representatives(self):
        self.assertEqual(len(MANIFEST['cases']),26)
        entries=[BY[c['id']] for c in MANIFEST['cases']]
        self.assertEqual(sum(x['caseVisible'] for x in entries),26)
        self.assertEqual(sum(x['timelineVisible'] for x in entries),18)
        self.assertEqual(sum(x['format']=='3d' for x in entries),4)
        self.assertTrue(all(not x.get('referenceOnly') and not x['interactive'] for x in entries))
        for c,x in zip(MANIFEST['cases'],entries):
            self.assertEqual(x['modelNames'],[c['model']])
            self.assertEqual(x['date'],c['date'])
            self.assertEqual(x['sourceUrl'],c['sourceUrl'])
            self.assertGreater(x['caseNumber'],0)
            self.assertEqual(x['modelClaimStatus'],'source-reported-not-independently-authenticated')

    def test_all_original_bytes_and_real_animation(self):
        frames=0;assets=0
        for c in MANIFEST['cases']:
            x=BY[c['id']]
            for original,media in zip(c['media'],x['media']):
                data=(ROOT/'pelican-web'/media['src'].lstrip('/')).read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(),original['sha256'])
                with Image.open(ROOT/'pelican-web'/media['src'].lstrip('/')) as image:
                    self.assertGreater(min(image.size),10)
                    if getattr(image,'n_frames',1)>1:frames+=1
                    image.verify()
                assets+=1
        self.assertEqual(assets,36)
        self.assertEqual(frames,3)
        day=BY['linuxdo-ds41-day-night-2026-09-10']
        self.assertEqual(len(day['media']),6)
        self.assertTrue(all(m['detailOnly'] for m in day['media'][1:]))
        self.assertTrue(day['generationConditions']['iterative'])
        glm=BY['linuxdo-glm53f-three-2026-09-09']
        self.assertTrue(glm['generationConditions']['visualFeedback'])
        self.assertEqual(glm['model'],'glm-5.3-flash')

    def test_bilingual_comparisons_do_not_invent_default_runs(self):
        for c in MANIFEST['cases']:
            for prefix in ['', 'en/']:
                x=BY[c['id']]
                soup=BeautifulSoup((ROOT/'public-site'/prefix/x['path'].lstrip('/')/'index.html').read_text(encoding='utf8'),'html.parser')
                self.assertEqual(soup.html['lang'],'en' if prefix else 'zh-CN')
                self.assertIsNotNone(soup.find('a',href=c['sourceUrl']))
                self.assertTrue(soup.find('img',src=x['thumbnail']))
                if c.get('modelRunGroup'):
                    block=soup.select_one('[data-setting-comparison]')
                    self.assertIsNotNone(block)
                    self.assertIn('不擅自挑一张' if not prefix else 'no timeline representative is guessed',block.get_text())

    def test_old_records_and_reference_count_are_unchanged(self):
        before=json.loads((AUDIT/'before-catalog.json').read_text(encoding='utf8'))
        for previous in before['items']:
            now=BY[previous['id']]
            for key in ['date','model','author','sourceUrl','thumbnail','media','caseVisible','timelineVisible']:
                if reviewed_context_change(self,previous,now,key,BY):continue
                self.assertEqual(now.get(key),previous.get(key),(previous['id'],key))
        self.assertGreaterEqual(CAT['counts']['cases'],before['counts']['cases']+26)
        self.assertGreaterEqual(CAT['counts']['timeline'],before['counts']['timeline']+18)
        self.assertEqual(CAT['counts']['referenceRecords'],before['counts']['referenceRecords'])
        self.assertEqual(CAT['items'],apply_case_policy(CAT['items'],ROOT/'public-site'))

if __name__=='__main__':unittest.main()
