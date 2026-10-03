"""Reviewed model panels, faithful crops, motion and immutable old records."""
import hashlib,json,unittest
from pathlib import Path
from PIL import Image,ImageStat
from bs4 import BeautifulSoup
from archival_test_assertions import user_requested_context_change, reviewed_video_context_change
ROOT=Path(__file__).resolve().parents[1]
DIR=ROOT/'pelican-archive/research/2026-10-02-x-forum-continuation'
A=json.loads((DIR/'import-audit.json').read_text(encoding='utf8'))
CAT=json.loads((ROOT/'public-site/data/catalog.json').read_text(encoding='utf8'))
BY={x['id']:x for x in CAT['items']}

class XForumContinuationTests(unittest.TestCase):
    def test_independent_source_reported_units(self):
        self.assertEqual(len(A['added']),6)
        self.assertGreaterEqual(CAT['counts']['cases'],A['expectedCases'])
        self.assertGreaterEqual(CAT['counts']['timeline'],A['expectedTimeline'])
        self.assertEqual(CAT['counts']['referenceRecords'],138)
        for index,ident in enumerate(A['added']):
            x=BY[ident]
            self.assertEqual(x['date'],'2026-09-27' if index<2 else '2026-09-28')
            self.assertEqual(len(x['modelNames']),1)
            self.assertTrue(x['caseVisible'] and x['timelineVisible'])
            self.assertFalse(x.get('referenceOnly') or x.get('demoUrl') or x.get('interactive'))
            self.assertTrue(x['generationConditions']['generationDateUnknown'])
            self.assertEqual(x['modelClaimStatus'],'source-reported-not-independently-authenticated')
            self.assertTrue(x['media'][1]['detailOnly'])
            self.assertNotEqual(x['thumbnail'],x['media'][1]['src'])
        manifest=json.loads((DIR/'approved-manifest.json').read_text(encoding='utf8'))
        self.assertTrue(manifest['reviewed'])
        self.assertTrue(all(x['modelToMediaVerified'] and x['unitType']=='single-model-output' for x in manifest['cases']))

    def test_exact_media_and_faithful_crops(self):
        self.assertEqual(len(A['newOriginals']),10)
        for asset in A['newOriginals']:
            p=ROOT/'public-site'/asset['src'].lstrip('/')
            self.assertEqual(p.stat().st_size,asset['bytes'])
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),asset['sha256'])
            if p.suffix not in {'.mp4','.webm'}:
                with Image.open(p) as image:
                    image.load()
                    self.assertGreater(min(image.size),500)
                    self.assertGreater(max(ImageStat.Stat(image.convert('RGB')).stddev),10)
        derived=json.loads((DIR/'derived.json').read_text(encoding='utf8'))['rows']
        for index,ident in enumerate(A['added']):
            x=BY[ident];row=derived[index]
            provenance=x['videoCropProvenance'] if index<2 else x['cropProvenance']
            self.assertEqual(provenance['box'],row['box'])
            self.assertEqual(provenance['sourceSha256'],row['original']['sha256'])
            self.assertEqual(provenance['cropSha256'],row['sha256'])
            if index<2:
                self.assertEqual(provenance['frames'],150)
                self.assertTrue(provenance['decodedFrameHashesMatch'])
            else:
                with Image.open(ROOT/'public-site'/provenance['original'].lstrip('/')) as original,Image.open(ROOT/'public-site'/provenance['crop'].lstrip('/')) as crop:
                    self.assertEqual(original.convert('RGB').crop(provenance['box']).tobytes(),crop.convert('RGB').tobytes())

    def test_bilingual_media_first_with_folded_original(self):
        for index,ident in enumerate(A['added']):
            x=BY[ident]
            for prefix in ['', 'en/']:
                doc=BeautifulSoup((ROOT/'public-site'/prefix/x['path'].lstrip('/')/'index.html').read_text(encoding='utf8'),'html.parser')
                self.assertIsNotNone(doc.find('a',href=x['sourceUrl']))
                self.assertIsNotNone(doc.select_one('.detail-provenance:not([open])'))
                attachment=doc.select_one('.detail-attachments:not([open])')
                self.assertIsNotNone(attachment)
                self.assertIn(x['media'][1]['src'],str(attachment))
                if index<2:
                    video=doc.select_one('.detail-motion video[data-motion-kind]')
                    self.assertEqual(video['data-motion-src'],x['media'][0]['src'])
                    for attr in ['autoplay','muted','loop','playsinline','controls']:self.assertTrue(video.has_attr(attr))
                    self.assertEqual(x['motionPreview']['type'],'video')
                else:
                    self.assertFalse(x.get('motionPreview'))
                    self.assertFalse(doc.select_one('.detail-motion'))
                    self.assertEqual(doc.select_one('.detail-layout figure')['data-media-src'],x['media'][0]['src'])
                self.assertFalse(doc.select_one('iframe[data-local-demo]'))

    def test_all_previous_records_preserved(self):
        before=json.loads((DIR/'before-catalog.json').read_text(encoding='utf8'))
        for x in before['items']:
            for key,value in x.items():
                if user_requested_context_change(self,x,BY[x['id']],key):continue
                if reviewed_video_context_change(self,x,BY[x['id']],key,BY):continue
                if key!='caseNumber':self.assertEqual(BY[x['id']][key],value,(x['id'],key))
        additions={x['id']:x for x in json.loads((ROOT/'site/additions.json').read_text(encoding='utf8'))}
        for x in json.loads((DIR/'before-additions.json').read_text(encoding='utf8')):
            self.assertEqual(additions[x['id']],x)

if __name__=='__main__':unittest.main()
