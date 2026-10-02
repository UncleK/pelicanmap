"""Reviewed all-date community units, faithful media and preserved source context."""
import hashlib,json,unittest
from pathlib import Path
from PIL import Image
from bs4 import BeautifulSoup
from archival_test_assertions import USER_REMOVED, user_requested_context_change
ROOT=Path(__file__).resolve().parents[1]
DIR=ROOT/'pelican-archive/research/2026-10-02-reddit-x-history'
AUDIT=json.loads((DIR/'import-audit.json').read_text())
CAT=json.loads((ROOT/'public-site/data/catalog.json').read_text())
BY={x['id']:x for x in CAT['items']}
NEW=[BY[x] for x in AUDIT['added']]

class RedditXHistoryTests(unittest.TestCase):
    def test_units_counts_and_source_boundaries(self):
        self.assertEqual(len(NEW),19)
        self.assertEqual(sum(x['timelineVisible'] for x in NEW),13)
        self.assertEqual(sum(x['date'].startswith('2025') for x in NEW),2)
        self.assertGreaterEqual(CAT['counts']['cases'],AUDIT['oldCases']+18)
        self.assertGreaterEqual(CAT['counts']['timeline'],AUDIT['oldTimeline']+13)
        self.assertEqual(sum(x['caseVisible'] for x in NEW),18)
        self.assertTrue(all(x['caseVisible'] and len(x['modelNames'])==1 and not x.get('referenceOnly') for x in NEW if x['id']!=USER_REMOVED))
        previous=json.loads((ROOT/'pelican-archive/research/2026-10-02-collapsed-search/before-catalog.json').read_text(encoding='utf8'))
        original=next(x for x in previous['items'] if x['id']==USER_REMOVED)
        self.assertTrue(user_requested_context_change(self,original,BY[USER_REMOVED],'caseVisible'))
        self.assertEqual(CAT['counts']['referenceRecords'],138)
        self.assertEqual(len(AUDIT['newOriginals']),34)
        self.assertFalse(any('jurly' in x['id'] or 'sahil' in x['id'] for x in NEW))
        for x in NEW:self.assertEqual(x['sourcePublicationDate'],x['date'])

    def test_real_files_and_lossless_crops(self):
        for a in AUDIT['newOriginals']:
            p=ROOT/'public-site'/a['src'].lstrip('/')
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),a['sha256'])
        movies=0
        for x in NEW:
            if x['media'][0]['src'].endswith(('.mp4','.webm')):movies+=1
            with Image.open(ROOT/'public-site'/x['thumbnail'].lstrip('/')) as image:
                image.load();self.assertGreater(min(image.size),10)
                expected={'.png':'PNG','.jpg':'JPEG','.jpeg':'JPEG','.webp':'WEBP'}
                self.assertEqual(image.format,expected[Path(x['thumbnail']).suffix])
            if x.get('cropProvenance'):
                c=x['cropProvenance']
                with Image.open(ROOT/'public-site'/c['original'].lstrip('/')) as source,Image.open(ROOT/'public-site'/c['crop'].lstrip('/')) as crop:
                    self.assertEqual(source.convert('RGB').crop(c['box']).tobytes(),crop.convert('RGB').tobytes())
            if x.get('videoCropProvenance'):
                c=x['videoCropProvenance'];self.assertTrue(c['decodedFrameHashesMatch'])
                self.assertIn(c['frames'],[96,300]);self.assertEqual(c['method'],'decoded-pixel-crop-lossless-vp9')
            self.assertTrue(all(m.get('detailOnly') for m in x['media'][1:]))
        self.assertEqual(movies,7)

    def test_bilingual_details_fold_whole_movies_and_label_actual_conditions(self):
        for x in NEW:
            for prefix in ['', 'en/']:
                html=(ROOT/'public-site'/prefix/x['path'].lstrip('/')/'index.html').read_text(encoding='utf8')
                doc=BeautifulSoup(html,'html.parser')
                figure=doc.select_one('.detail-motion figure') or doc.select_one('.detail-layout figure')
                self.assertEqual(figure['data-media-src'],x['media'][0]['src'])
                self.assertIn(x['sourceUrl'],html);self.assertIsNone(doc.select_one('[data-local-demo]'))
                for m in x['media'][1:]:
                    self.assertIsNotNone(doc.select_one('.detail-attachments:not([open]) [data-media-src="'+m['src']+'"]'))
                if 'x-chase-' in x['id']:
                    self.assertFalse(x['timelineVisible'])
                    self.assertEqual(len(x['comparisonIds']),4)
                    self.assertIn('access and prompt conditions' if prefix else '账号与题面条件对照',html)
                if x['media'][0]['src'].endswith(('.mp4','.webm')):
                    self.assertEqual(len(doc.select('.detail-motion video')),1)
        for old in json.loads((DIR/'before-catalog.json').read_text())['items']:
            for k in ['id','model','date','author','sourceUrl','updated','media']:self.assertEqual(BY[old['id']][k],old[k])

if __name__=='__main__':unittest.main()
