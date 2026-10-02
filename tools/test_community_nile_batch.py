"""Regression checks for agent-reviewed, all-media intake; not a scraper."""
import hashlib,json,unittest
from pathlib import Path
from PIL import Image
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
DIR=ROOT/'pelican-archive/research/2026-10-01-evening-discovery'
AUDIT=json.loads((DIR/'import-audit.json').read_text())
CAT=json.loads((ROOT/'public-site/data/catalog.json').read_text())
BY={x['id']:x for x in CAT['items']}
NEW=[BY[x] for x in AUDIT['added']]

class CommunityNileTests(unittest.TestCase):
    def test_independent_units_and_representative_subset(self):
        self.assertEqual(len(NEW),45)
        self.assertEqual(sum(x['timelineVisible'] for x in NEW),15)
        self.assertGreaterEqual(CAT['counts']['cases'],AUDIT['oldCases']+45)
        self.assertGreaterEqual(CAT['counts']['timeline'],AUDIT['oldTimeline']+15)
        self.assertTrue(all(x['caseVisible'] and len(x['modelNames'])==1 and not x.get('referenceOnly') for x in NEW))
        runs=[x for x in NEW if x.get('modelRunGroup')=='linuxdo-qwen38-repeated-2026-09-11']
        self.assertEqual(len(runs),29)
        self.assertTrue(all(not x['timelineVisible'] and len(x['comparisonIds'])==29 for x in runs))
        self.assertEqual({x['generationConditions']['sourceSetting'] for x in runs},{'low','medium','xhigh'})
        self.assertTrue(all(x['generationConditions']['settingMappingUnverified'] for x in runs))

    def test_local_originals_motion_and_bilingual_details(self):
        self.assertEqual(len(AUDIT['newOriginals']),43)
        for asset in AUDIT['newOriginals']:
            file=ROOT/'public-site'/asset['src'].lstrip('/')
            self.assertEqual(hashlib.sha256(file.read_bytes()).hexdigest(),asset['sha256'])
        for x in NEW:
            animated=x['id'].startswith('linuxdo-2891201-')
            if animated:
                with Image.open(ROOT/'public-site'/x['media'][0]['src'].lstrip('/')) as image:
                    self.assertTrue(image.is_animated)
                    self.assertEqual(image.n_frames,x['generationConditions']['frames'])
                    for k in [0,image.n_frames//2,image.n_frames-1]:image.seek(k);image.load()
            for prefix in ['', 'en/']:
                text=(ROOT/'public-site'/prefix/x['path'].lstrip('/')/'index.html').read_text(encoding='utf8')
                doc=BeautifulSoup(text,'html.parser')
                self.assertIn(x['sourceUrl'],text)
                self.assertIsNone(doc.select_one('[data-local-demo]'))
                if animated:self.assertEqual(doc.select_one('[data-detail-primary]')['data-detail-primary'],'media')
                if x.get('cropProvenance'):self.assertIsNotNone(doc.find('img',src=x['cropProvenance']['original']))

    def test_archive_splits_reuse_originals_and_keep_old_ids(self):
        before=json.loads((DIR/'before-catalog.json').read_text())['items']
        for old in before:
            now=BY[old['id']]
            for key in ['id','date','model','author','sourceUrl','updated']:
                self.assertEqual(now[key],old[key])
            self.assertTrue({m['src'] for m in old['media']}<={m['src'] for m in now['media']})
        for x in NEW:
            if x.get('parentId'):
                self.assertFalse(BY[x['parentId']]['caseVisible'])
                self.assertIn(x['media'][0]['src'],[m['src'] for m in BY[x['parentId']]['media']])
        enhanced=BY['simon-gemini3-deepthink-enhanced-2026-02-12']
        self.assertFalse(enhanced['timelineVisible'])
        self.assertEqual(enhanced['comparisonType'],'prompt')
        self.assertEqual(len(enhanced['comparisonIds']),2)
        self.assertEqual(CAT['counts']['referenceRecords'],138)

if __name__=='__main__':unittest.main()
