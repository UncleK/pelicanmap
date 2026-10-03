"""Public original posts, distinct work units and preserved motion behaviour."""
import hashlib,json,unittest
from pathlib import Path
from PIL import Image,ImageStat
from bs4 import BeautifulSoup
from archival_test_assertions import user_requested_context_change, reviewed_video_context_change

ROOT=Path(__file__).resolve().parents[1]
DIR=ROOT/'pelican-archive/research/2026-10-02-x-september-continuation'
A=json.loads((DIR/'import-audit.json').read_text(encoding='utf8'))
CAT=json.loads((ROOT/'public-site/data/catalog.json').read_text(encoding='utf8'))
BY={x['id']:x for x in CAT['items']}

class XSeptemberContinuationTests(unittest.TestCase):
    def test_reviewed_originals_and_dates(self):
        self.assertEqual(len(A['added']),3)
        self.assertGreaterEqual(CAT['counts']['cases'],937)
        self.assertGreaterEqual(CAT['counts']['timeline'],614)
        self.assertEqual(CAT['counts']['referenceRecords'],138)
        self.assertFalse(any(x['sourceUrl']==A['duplicateSource'] for x in CAT['items']))
        for ident in A['added']:
            item=BY[ident]
            self.assertEqual(item['date'],'2026-09-28')
            self.assertEqual(len(item['modelNames']),1)
            self.assertTrue(item['caseVisible'] and item['timelineVisible'])
            self.assertFalse(item.get('referenceOnly') or item.get('interactive') or item.get('demoUrl'))
            self.assertTrue(item['generationConditions']['generationDateUnknown'])
        manifest=json.loads((DIR/'approved-manifest.json').read_text(encoding='utf8'))
        self.assertTrue(all(x['unitType']=='single-model-output' and x['modelToMediaVerified'] for x in manifest['cases']))
        self.assertEqual(BY[A['added'][1]]['originalLevel'],'Max')
        self.assertTrue(BY[A['added'][2]]['generationConditions']['previewOnly'])

    def test_original_bytes_and_nonblank_posters(self):
        self.assertEqual(len(A['newOriginals']),5)
        for asset in A['newOriginals']:
            path=ROOT/'public-site'/asset['src'].lstrip('/')
            self.assertEqual(path.stat().st_size,asset['bytes'])
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),asset['sha256'])
            if path.suffix!='.mp4':
                with Image.open(path) as image:
                    image.load()
                    self.assertGreater(min(image.size),500)
                    self.assertGreater(max(ImageStat.Stat(image.convert('RGB')).stddev),10)

    def test_bilingual_motion_first_and_still_only(self):
        for ident in A['added']:
            item=BY[ident]
            for prefix in ['', 'en/']:
                doc=BeautifulSoup((ROOT/'public-site'/prefix/item['path'].lstrip('/')/'index.html').read_text(encoding='utf8'),'html.parser')
                self.assertIsNotNone(doc.find('a',href=item['sourceUrl']))
                self.assertIsNotNone(doc.select_one('.detail-provenance:not([open])'))
                if ident in A['added'][:2]:
                    video=doc.select_one('.detail-motion video[data-motion-kind]')
                    self.assertIsNotNone(video)
                    self.assertEqual(video['data-motion-src'],item['media'][0]['src'])
                    for attr in ['autoplay','muted','loop','playsinline','controls']:self.assertTrue(video.has_attr(attr))
                    self.assertEqual(item['motionPreview']['type'],'video')
                    self.assertFalse(doc.select_one('[data-preview-only]'))
                else:
                    self.assertFalse(item.get('motionPreview'))
                    self.assertFalse(doc.select_one('video[data-motion-kind]'))
                    self.assertEqual(doc.select_one('.detail-layout figure')['data-media-src'],item['media'][0]['src'])
                    self.assertIn('motion is not invented' if prefix else '不把截图伪装成可动原件',doc.get_text())
                self.assertFalse(doc.select_one('iframe[data-local-demo]'))

    def test_old_records_and_additions_are_preserved(self):
        for item in json.loads((DIR/'before-catalog.json').read_text(encoding='utf8'))['items']:
            for key,value in item.items():
                if user_requested_context_change(self,item,BY[item['id']],key):continue
                if reviewed_video_context_change(self,item,BY[item['id']],key,BY):continue
                if key!='caseNumber':self.assertEqual(BY[item['id']][key],value,(item['id'],key))
        additions={x['id']:x for x in json.loads((ROOT/'site/additions.json').read_text(encoding='utf8'))}
        for item in json.loads((DIR/'before-additions.json').read_text(encoding='utf8')):
            self.assertEqual(additions[item['id']],item)

if __name__=='__main__':unittest.main()
