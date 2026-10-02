"""Public source mappings, complete video, faithful crops and immutable prior intake."""
import hashlib,json,unittest
from pathlib import Path
from PIL import Image,ImageStat
from bs4 import BeautifulSoup
from archival_test_assertions import user_requested_context_change
ROOT=Path(__file__).resolve().parents[1]
DIR=ROOT/'pelican-archive/research/2026-10-02-x-earlier-review'
A=json.loads((DIR/'import-audit.json').read_text(encoding='utf8'))
CAT=json.loads((ROOT/'public-site/data/catalog.json').read_text(encoding='utf8'))
BY={x['id']:x for x in CAT['items']}

class XEarlierReviewTests(unittest.TestCase):
    def test_reviewed_source_reported_units(self):
        self.assertEqual(len(A['added']),5)
        self.assertGreaterEqual(CAT['counts']['cases'],A['expectedCases']-1)
        self.assertGreaterEqual(CAT['counts']['timeline'],A['expectedTimeline']-1)
        self.assertEqual(CAT['counts']['referenceRecords'],138)
        manifest=json.loads((DIR/'approved-manifest.json').read_text(encoding='utf8'))
        self.assertTrue(manifest['reviewed'])
        for c in manifest['cases']:
            x=BY[c['id']]
            self.assertTrue(c['modelToMediaVerified'] and x['caseVisible'] and x['timelineVisible'])
            self.assertEqual(c['unitType'],'single-model-output')
            self.assertEqual(len(x['modelNames']),1)
            self.assertEqual(x['date'],c['date'])
            self.assertTrue(x['generationConditions']['generationDateUnknown'])
            self.assertFalse(x.get('referenceOnly') or x.get('demoUrl') or x.get('interactive'))
            self.assertEqual(x['modelClaimStatus'],'source-reported-not-independently-authenticated')
        for ident in A['added'][2:4]:
            self.assertEqual(BY[ident]['model'],'Space Bunny Alpha')
            self.assertTrue(BY[ident]['generationConditions']['anonymousOrRoutingLabelUnresolved'])

    def test_exact_media_and_faithful_crop_pixels(self):
        self.assertEqual(len(A['newOriginals']),7)
        for asset in A['newOriginals']:
            p=ROOT/'public-site'/asset['src'].lstrip('/')
            self.assertEqual(p.stat().st_size,asset['bytes'])
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),asset['sha256'])
            if p.suffix!='.mp4':
                with Image.open(p) as im:
                    im.load();self.assertGreater(min(im.size),120)
                    self.assertGreater(max(ImageStat.Stat(im.convert('RGB')).stddev),10)
        for ident in A['added'][:2]:
            x=BY[ident];p=x['cropProvenance']
            with Image.open(ROOT/'public-site'/p['original'].lstrip('/')) as im,Image.open(ROOT/'public-site'/p['crop'].lstrip('/')) as crop:
                self.assertEqual(im.convert('RGB').crop(p['box']).tobytes(),crop.convert('RGB').tobytes())
            self.assertTrue(x['media'][1]['detailOnly'])
            self.assertNotEqual(x['thumbnail'],x['media'][1]['src'])
        motion=next(x for x in json.loads((DIR/'derived.json').read_text(encoding='utf8'))['rows'] if x['key']=='orca-saq2')
        self.assertTrue(motion['fullDecode'])
        self.assertEqual(motion['frames'],395)
        self.assertEqual(motion['distinctDecodedFrames'],395)

    def test_bilingual_actual_media_first(self):
        for ident in A['added']:
            x=BY[ident]
            for prefix in ['', 'en/']:
                doc=BeautifulSoup((ROOT/'public-site'/prefix/x['path'].lstrip('/')/'index.html').read_text(encoding='utf8'),'html.parser')
                self.assertIsNotNone(doc.find('a',href=x['sourceUrl']))
                self.assertIsNotNone(doc.select_one('.detail-provenance:not([open])'))
                if ident==A['added'][-1]:
                    v=doc.select_one('.detail-motion video[data-motion-kind]')
                    self.assertEqual(v['data-motion-src'],x['media'][0]['src'])
                    for attr in ['autoplay','muted','loop','playsinline','controls']:self.assertTrue(v.has_attr(attr))
                    self.assertEqual(x['motionPreview']['type'],'video')
                else:
                    self.assertFalse(x.get('motionPreview'))
                    self.assertFalse(doc.select_one('.detail-motion'))
                    self.assertEqual(doc.select_one('.detail-layout figure')['data-media-src'],x['media'][0]['src'])
                if len(x['media'])>1:
                    attachment=doc.select_one('.detail-attachments:not([open])')
                    self.assertIsNotNone(attachment)
                    self.assertIn(x['media'][1]['src'],str(attachment))
                self.assertFalse(doc.select_one('iframe[data-local-demo]'))

    def test_all_previous_records_preserved(self):
        before=json.loads((DIR/'before-catalog.json').read_text(encoding='utf8'))
        for x in before['items']:
            for key,value in x.items():
                if user_requested_context_change(self,x,BY[x['id']],key):continue
                if key!='caseNumber':self.assertEqual(BY[x['id']][key],value,(x['id'],key))
        additions={x['id']:x for x in json.loads((ROOT/'site/additions.json').read_text(encoding='utf8'))}
        for x in json.loads((DIR/'before-additions.json').read_text(encoding='utf8')):self.assertEqual(additions[x['id']],x)

if __name__=='__main__':unittest.main()
