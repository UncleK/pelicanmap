"""Reviewed source units, lossless original animation panels and immutable prior intake."""
import hashlib,json,unittest
from pathlib import Path
from PIL import Image,ImageStat
from bs4 import BeautifulSoup
from archival_test_assertions import reviewed_video_context_change
ROOT=Path(__file__).resolve().parents[1]
DIR=ROOT/'pelican-archive/research/2026-10-02-github-dynamic-continuation'
A=json.loads((DIR/'import-audit.json').read_text(encoding='utf8'))
CAT=json.loads((ROOT/'public-site/data/catalog.json').read_text(encoding='utf8'))
BY={x['id']:x for x in CAT['items']}

class GithubDynamicContinuationTests(unittest.TestCase):
    def test_reviewed_source_units_not_six_claimed_runs(self):
        self.assertEqual(len(A['added']),4)
        # Four preserved direct-video records left main counts under the user's code-generation scope.
        self.assertGreaterEqual(CAT['counts']['cases'],951-4)
        self.assertGreaterEqual(CAT['counts']['timeline'],626-4)
        self.assertEqual(CAT['counts']['referenceRecords'],138)
        manifest=json.loads((DIR/'approved-manifest.json').read_text(encoding='utf8'))
        self.assertTrue(manifest['reviewed'])
        for c in manifest['cases']:
            x=BY[c['id']]
            self.assertTrue(c['modelToMediaVerified'] and x['caseVisible'])
            self.assertEqual(c['unitType'],'single-model-output')
            self.assertEqual(len(x['modelNames']),1)
            self.assertEqual(x['date'],c['date'])
            self.assertTrue(x['generationConditions']['generationDateUnknown'])
            self.assertFalse(x.get('referenceOnly') or x.get('demoUrl') or x.get('interactive'))
            self.assertEqual(x['modelClaimStatus'],'source-reported-not-independently-authenticated')
        self.assertEqual(sum(BY[i]['timelineVisible'] for i in A['added']),2)
        for ident in [A['added'][1],A['added'][3]]:
            x=BY[ident]
            self.assertEqual(x['model'],'grok-4.6')
            self.assertEqual(x['modelRunGroup'],'cat-grok46-high-2026-10-02')
            self.assertEqual(x['comparisonType'],'repeat-runs')
            self.assertFalse(x['timelineVisible'] or x.get('authorDefault'))

    def test_media_and_decoded_pixel_evidence(self):
        self.assertEqual(len(A['newOriginals']),8)
        for asset in A['newOriginals']:
            p=ROOT/'public-site'/asset['src'].lstrip('/')
            self.assertEqual(p.stat().st_size,asset['bytes'])
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),asset['sha256'])
            if p.suffix=='.png':
                with Image.open(p) as im:
                    im.load();self.assertGreater(min(im.size),120)
                    self.assertGreater(max(ImageStat.Stat(im.convert('RGB')).stddev),10)
        rows=json.loads((DIR/'derived.json').read_text(encoding='utf8'))['rows']
        moving=[r for r in rows if r.get('allFramesDecoded')]
        self.assertEqual(len(moving),3)
        for r in moving:
            self.assertTrue(r['decodedPixelsMatch'])
            self.assertEqual((r['frames'],r['uniqueFrames'],r['duration']),(300,300,12))
        for ident in A['added'][:3]:
            x=BY[ident];p=x['videoCropProvenance']
            self.assertTrue(p['decodedFrameHashesMatch'])
            self.assertEqual(p['frames'],300)
            self.assertEqual(p['method'],'decoded-pixel-crop-lossless-vp9')
            self.assertTrue(x['media'][1]['detailOnly'])
            self.assertNotEqual(x['thumbnail'],x['media'][1]['src'])

    def test_bilingual_dynamic_first_still_is_not_fake_video(self):
        for ident in A['added']:
            x=BY[ident]
            for prefix in ['', 'en/']:
                doc=BeautifulSoup((ROOT/'public-site'/prefix/x['path'].lstrip('/')/'index.html').read_text(encoding='utf8'),'html.parser')
                self.assertIsNotNone(doc.find('a',href=x['sourceUrl']))
                self.assertIsNotNone(doc.select_one('.detail-provenance:not([open])'))
                if ident!=A['added'][-1]:
                    v=doc.select_one('.detail-motion video[data-motion-kind]')
                    self.assertEqual(v['data-motion-src'],x['media'][0]['src'])
                    for attr in ['autoplay','muted','loop','playsinline','controls']:self.assertTrue(v.has_attr(attr))
                    self.assertEqual(x['motionPreview']['type'],'video')
                    attachment=doc.select_one('.detail-attachments:not([open])')
                    self.assertIsNotNone(attachment)
                    self.assertIn(x['media'][1]['src'],str(attachment))
                else:
                    self.assertFalse(x.get('motionPreview'))
                    self.assertFalse(doc.select_one('.detail-motion'))
                    self.assertEqual(doc.select_one('.detail-layout figure')['data-media-src'],x['media'][0]['src'])
                if 'grok46' in ident:
                    self.assertIsNotNone(doc.select_one('[data-setting-comparison]'))
                self.assertFalse(doc.select_one('iframe[data-local-demo]'))

    def test_all_prior_records_and_user_retraction_preserved(self):
        before=json.loads((DIR/'before-catalog.json').read_text(encoding='utf8'))
        for x in before['items']:
            for key,value in x.items():
                if reviewed_video_context_change(self,x,BY[x['id']],key,BY):continue
                if key!='caseNumber':self.assertEqual(BY[x['id']][key],value,(x['id'],key))
        additions={x['id']:x for x in json.loads((ROOT/'site/additions.json').read_text(encoding='utf8'))}
        for x in json.loads((DIR/'before-additions.json').read_text(encoding='utf8')):self.assertEqual(additions[x['id']],x)
        self.assertFalse(BY['x-keth-space-bunny-alpha-animation-2026-09-30']['caseVisible'])

if __name__=='__main__':unittest.main()
