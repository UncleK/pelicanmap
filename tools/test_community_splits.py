"""Public motion sources, source-labelled settings and reused collection originals."""
import hashlib,json,unittest
from pathlib import Path
from PIL import Image
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
DIR=ROOT/'pelican-archive/research/2026-10-02-community-splits'
AUDIT=json.loads((DIR/'import-audit.json').read_text())
CAT=json.loads((ROOT/'public-site/data/catalog.json').read_text())
BY={x['id']:x for x in CAT['items']}
NEW=[BY[x] for x in AUDIT['added']]
class CommunitySplitsTests(unittest.TestCase):
    def test_unit_counts_and_settings_representative(self):
        self.assertEqual(len(NEW),13)
        self.assertEqual(sum(x['timelineVisible'] for x in NEW),9)
        self.assertGreaterEqual(CAT['counts']['cases'],AUDIT['oldCases']+13)
        self.assertGreaterEqual(CAT['counts']['timeline'],AUDIT['oldTimeline']+9)
        self.assertEqual(CAT['counts']['referenceRecords'],138)
        self.assertTrue(all(x['caseVisible'] and len(x['modelNames'])==1 and not x.get('referenceOnly') for x in NEW))
        sweep=[x for x in NEW if 'maximumwishbone' in x['id']]
        self.assertEqual(len(sweep),5)
        self.assertEqual([x['originalLevel'] for x in sweep if x['timelineVisible']],['medium'])
        self.assertTrue(all(len(x['comparisonIds'])==5 for x in sweep))
        for x in NEW:self.assertEqual(x['sourcePublicationDate'],x['date'])
    def test_hashes_reuse_and_nonblank_covers(self):
        self.assertEqual(sum(not a['reused'] for a in AUDIT['newOriginals']),15)
        self.assertEqual(sum(a['reused'] for a in AUDIT['newOriginals']),3)
        for a in AUDIT['newOriginals']:
            p=ROOT/'public-site'/a['src'].lstrip('/')
            self.assertEqual(p.stat().st_size,a['bytes'])
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),a['sha256'])
            if p.suffix!='.mp4':
                with Image.open(p) as image:
                    image.load();self.assertGreater(min(image.size),10)
                    self.assertEqual(image.format,{'.png':'PNG','.jpg':'JPEG','.webp':'WEBP'}[p.suffix])
        luna=next(x for x in NEW if 'emu001-luna-' in x['id'])
        self.assertEqual(luna['media'][0]['posterProvenance']['frameTime'],6)
        self.assertFalse(BY['reddit-emu001-pelican-stick-meme-2026-09-30']['caseVisible'])
    def test_motion_first_and_preview_only_bilingual(self):
        self.assertEqual(sum(x['media'][0]['src'].endswith('.mp4') for x in NEW),5)
        for x in NEW:
            for prefix in ['', 'en/']:
                html=(ROOT/'public-site'/prefix/x['path'].lstrip('/')/'index.html').read_text(encoding='utf8')
                doc=BeautifulSoup(html,'html.parser')
                figure=doc.select_one('.detail-motion figure') or doc.select_one('.detail-layout figure')
                self.assertEqual(figure['data-media-src'],x['media'][0]['src'])
                self.assertIn(x['sourceUrl'],html);self.assertIsNone(doc.select_one('[data-local-demo]'))
                if x['media'][0]['src'].endswith('.mp4'):self.assertEqual(len(doc.select('.detail-motion video')),1)
                elif x['format']=='animation':self.assertIsNotNone(doc.select_one('[data-preview-only]'))
                if 'maximumwishbone' in x['id']:
                    comparison=doc.select_one('[data-setting-comparison]')
                    self.assertIsNotNone(comparison)
                    self.assertLess(html.index('data-setting-comparison'),html.index('class="detail-layout"'))
    def test_old_fields_stable_and_claims_not_certified(self):
        for old in json.loads((DIR/'before-catalog.json').read_text())['items']:
            for key in ['id','model','date','author','sourceUrl','updated','media']:self.assertEqual(BY[old['id']][key],old[key])
        claimed=next(x for x in NEW if 'ga-claim' in x['id'])
        self.assertTrue(claimed['generationConditions']['modelIdentityUnverified'])
        self.assertIn('作者声称',claimed['title'])
        self.assertTrue(all(not x.get('demoUrl') for x in NEW))
if __name__=='__main__':unittest.main()
