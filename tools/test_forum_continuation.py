"""Source-reviewed all-media follow-up: units, genuine files and bilingual presentation."""
import hashlib,json,unittest
from pathlib import Path
from PIL import Image
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
DIR=ROOT/'pelican-archive/research/2026-10-02-forum-continuation'
AUDIT=json.loads((DIR/'import-audit.json').read_text())
CAT=json.loads((ROOT/'public-site/data/catalog.json').read_text())
BY={x['id']:x for x in CAT['items']}
NEW=[BY[x] for x in AUDIT['added']]

class ForumContinuationTests(unittest.TestCase):
    def test_works_representatives_and_reference_boundary(self):
        self.assertEqual(len(NEW),16)
        self.assertEqual(sum(x['timelineVisible'] for x in NEW),16)
        self.assertGreaterEqual(CAT['counts']['cases'],AUDIT['oldCases']+16)
        self.assertGreaterEqual(CAT['counts']['timeline'],AUDIT['oldTimeline']+16)
        self.assertTrue(all(x['caseVisible'] and len(x['modelNames'])==1 and not x.get('referenceOnly') for x in NEW))
        self.assertEqual(sum(x['task']=='derived' for x in NEW),2)
        self.assertEqual(CAT['counts']['referenceRecords'],138)
        self.assertEqual(len(AUDIT['newOriginals']),19)

    def test_originals_decode_and_primary_media_is_first(self):
        animations=0
        for asset in AUDIT['newOriginals']:
            file=ROOT/'public-site'/asset['src'].lstrip('/')
            self.assertEqual(hashlib.sha256(file.read_bytes()).hexdigest(),asset['sha256'])
        for x in NEW:
            src=x['media'][0]['src']
            if src.endswith(('.gif','.webp')):
                with Image.open(ROOT/'public-site'/src.lstrip('/')) as image:
                    self.assertTrue(image.is_animated);animations+=1
                    self.assertEqual(image.n_frames,x['generationConditions']['frames'])
                    for k in range(image.n_frames):image.seek(k);image.load()
            for prefix in ['', 'en/']:
                html=(ROOT/'public-site'/prefix/x['path'].lstrip('/')/'index.html').read_text(encoding='utf8')
                doc=BeautifulSoup(html,'html.parser')
                self.assertIn(x['sourceUrl'],html)
                primary=doc.select_one('[data-detail-primary]')
                if x['generationConditions']['previewOnly']:
                    self.assertIsNone(primary)
                    self.assertIsNotNone(doc.select_one('[data-preview-only]'))
                else:
                    self.assertEqual(primary['data-detail-primary'],'media')
                self.assertIsNone(doc.select_one('[data-local-demo]'))
                self.assertEqual(doc.select_one('main figure')['data-media-src'],src)
                self.assertTrue(all(m.get('detailOnly') for m in x['media'][1:]))
        self.assertEqual(animations,5)

    def test_views_edits_and_unverified_labels_are_not_extra_works(self):
        lily=next(x for x in NEW if x['author']=='lilianS')
        grok=next(x for x in NEW if x['author']=='JOJO2')
        self.assertEqual(lily['model'],'6pro');self.assertEqual(len(lily['media']),2)
        self.assertEqual(grok['model'],'grok4.6');self.assertEqual(len(grok['media']),2)
        self.assertFalse(grok['generationConditions']['oneShot'])
        minimax=next(x for x in NEW if x['author']=='veigar')
        self.assertTrue(minimax['generationConditions']['visualIteration'])
        self.assertEqual(minimax['generationConditions']['completion'],'author-reported-interrupted')
        longcat=next(x for x in NEW if x['author']=='asyu9912')
        self.assertEqual(longcat['originalLevel'],'')
        self.assertTrue(longcat['generationConditions']['settingMappingUnverified'])
        jae=BY['x-jaebird-glm53-flash-exl3-2026-10-01']
        self.assertEqual(jae['format'],'video')
        self.assertEqual(jae['media'][0]['posterProvenance']['frameTime'],1)
        self.assertEqual(jae['date'],'2026-10-01')
        for old in json.loads((DIR/'before-catalog.json').read_text())['items']:
            for key in ['id','model','date','author','sourceUrl','updated','media']:
                self.assertEqual(BY[old['id']][key],old[key])

if __name__=='__main__':unittest.main()
