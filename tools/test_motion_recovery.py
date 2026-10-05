"""Lossless animated work units and licensed ordinary on-site previews."""
import hashlib,json,unittest
from pathlib import Path
from PIL import Image
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
DIR=ROOT/'pelican-archive/research/2026-10-02-motion-recovery'
A=json.loads((DIR/'import-audit.json').read_text())
CAT=json.loads((ROOT/'public-site/data/catalog.json').read_text())
BY={x['id']:x for x in CAT['items']}
class MotionRecoveryTests(unittest.TestCase):
    def test_counts_and_reviewed_representatives(self):
        self.assertEqual(len(A['added']),5)
        self.assertGreaterEqual(CAT['counts']['cases'],A['expectedCases'])
        self.assertGreaterEqual(CAT['counts']['timeline'],A['expectedTimeline'])
        self.assertFalse(BY[A['parentId']]['caseVisible'])
        group=[BY[x] for x in A['added'] if 'kylmawurr-opus55-' in x]
        self.assertEqual(len(group),4)
        self.assertEqual([x['originalLevel'] for x in group if x['timelineVisible']],['medium'])
        self.assertTrue(all(len(x['comparisonIds'])==4 and x['comparisonType']=='settings-and-iterations' for x in group))
        self.assertTrue(next(x for x in group if 'refined' in x['id'])['generationConditions']['visualIteration'])
        self.assertEqual(CAT['counts']['referenceRecords'],138)
    def test_exact_originals_and_crops(self):
        for a in A['newOriginals']:
            p=ROOT/'public-site'/a['src'].lstrip('/')
            self.assertEqual(p.stat().st_size,a['bytes']);self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),a['sha256'])
            if p.suffix!='.webm':
                with Image.open(p) as image:image.load();self.assertGreater(min(image.size),100)
        rows=json.loads((DIR/'kylma-derived.json').read_text())['rows']
        self.assertTrue(all(x['decodedFrameHashesMatch'] and x['frames']==180 for x in rows))
        for x in [BY[x] for x in A['added']]:
            self.assertTrue(all(m.get('detailOnly') for m in x['media'][1:]))
            self.assertEqual(len(x['modelNames']),1)
        d=BY['x-olddonkey-fable55-max-2026-10-02'];c=d['cropProvenance']
        with Image.open(ROOT/'public-site'/c['original'].lstrip('/')) as original,Image.open(ROOT/'public-site'/c['crop'].lstrip('/')) as crop:
            self.assertEqual(original.convert('RGB').crop(c['box']).tobytes(),crop.convert('RGB').tobytes())
        self.assertTrue(d['generationConditions']['sourceReportedRoutingUnverified'])
    def test_bilingual_media_order_and_not_play(self):
        for ident in A['added']:
            x=BY[ident]
            for prefix in ['', 'en/']:
                html=(ROOT/'public-site'/prefix/x['path'].lstrip('/')/'index.html').read_text(encoding='utf8');doc=BeautifulSoup(html,'html.parser')
                if 'kylmawurr-opus55-' in ident:
                    self.assertEqual(doc.select_one('.detail-motion video')['data-motion-src'],x['media'][0]['src'])
                    self.assertEqual(len(doc.select('[data-setting-comparison] figure')),4)
                    self.assertIn('later refinement' if prefix else '后续细化对照',html)
                    self.assertLess(html.index('class="detail-motion'),html.index('data-setting-comparison'))
                else:self.assertIsNotNone(doc.select_one('[data-preview-only]'))
                self.assertIsNotNone(doc.select_one('.detail-attachments:not([open])'))
        for a in A['augmented']:
            x=BY[a['id']];self.assertFalse(x['interactive']);self.assertEqual(x['previewUrl'],a['previewUrl']);self.assertFalse(x.get('demoUrl'))
            p=ROOT/'public-demos/demos/variora-motion-recovery'/x['id']/'index.html'
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),a['sha256'])
            self.assertIn('Copyright (c) 2026 scarletkc',(p.parent/'LICENSE.txt').read_text())
            for prefix in ['', 'en/']:
                doc=BeautifulSoup((ROOT/'public-site'/prefix/x['path'].lstrip('/')/'index.html').read_text(encoding='utf8'),'html.parser')
                self.assertEqual(doc.select_one('iframe[data-local-demo]')['src'],a['previewUrl'])
                self.assertFalse(doc.select_one('[data-preview-only]'))
        reviews=json.loads((ROOT/'site/demo-reviews.json').read_text())
        self.assertEqual(len(reviews),6)
        restored='variora-gemini-3-8-flash-2026-09-20'
        self.assertTrue(BY[restored]['interactive'])
        self.assertEqual(reviews[restored]['sourceSha256'],'f3f600e77d2963ce8027bca5a30af929585e9f7333393859d7bae626fe7abd6a')
        self.assertEqual(len(reviews[restored]['verifiedActions']),4)
    def test_prior_media_and_dates_preserved(self):
        for old in json.loads((DIR/'before-catalog.json').read_text())['items']:
            for key in ['id','model','date','author','sourceUrl','updated','media']:
                self.assertEqual(BY[old['id']][key],old[key])
if __name__=='__main__':unittest.main()
