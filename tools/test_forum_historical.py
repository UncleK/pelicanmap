"""Historical public author replies, animation and nonduplicated comparison units."""
import hashlib,json,unittest
from pathlib import Path
from PIL import Image,ImageSequence
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
DIR=ROOT/'pelican-archive/research/2026-10-02-forum-historical'
AUDIT=json.loads((DIR/'import-audit.json').read_text())
CAT=json.loads((ROOT/'public-site/data/catalog.json').read_text())
BY={x['id']:x for x in CAT['items']}
NEW=[BY[x] for x in AUDIT['added']]

class ForumHistoricalTests(unittest.TestCase):
    def test_independent_units_and_reference_boundary(self):
        self.assertEqual(len(NEW),13)
        self.assertEqual(sum(x['timelineVisible'] for x in NEW),13)
        self.assertEqual(sum(x['date'].startswith('2025') for x in NEW),6)
        self.assertGreaterEqual(CAT['counts']['cases'],AUDIT['oldCases']+13)
        self.assertGreaterEqual(CAT['counts']['timeline'],AUDIT['oldTimeline']+13)
        self.assertTrue(all(x['caseVisible'] and len(x['modelNames'])==1 and not x.get('referenceOnly') for x in NEW))
        self.assertEqual(CAT['counts']['referenceRecords'],138)
        self.assertFalse(any('evolink' in x['id'] or 'deepthink' in x['id'] for x in NEW))
        for x in NEW:self.assertEqual(x['sourcePublicationDate'],x['date'])

    def test_original_hashes_actual_formats_and_lossless_crops(self):
        self.assertEqual(len(AUDIT['newOriginals']),17)
        for a in AUDIT['newOriginals']:
            p=ROOT/'public-site'/a['src'].lstrip('/')
            self.assertEqual(p.stat().st_size,a['bytes'])
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),a['sha256'])
            if p.suffix=='.mp4':continue
            with Image.open(p) as image:
                self.assertEqual(image.format,{'.png':'PNG','.jpg':'JPEG','.gif':'GIF'}[p.suffix])
                for frame in ImageSequence.Iterator(image):
                    frame.load();self.assertGreater(min(frame.size),10)
        crops=0
        for x in NEW:
            if x.get('cropProvenance'):
                crops+=1;c=x['cropProvenance']
                with Image.open(ROOT/'public-site'/c['original'].lstrip('/')) as source,Image.open(ROOT/'public-site'/c['crop'].lstrip('/')) as crop:
                    self.assertEqual(source.convert('RGB').crop(c['box']).tobytes(),crop.convert('RGB').tobytes())
            self.assertTrue(all(m.get('detailOnly') for m in x['media'][1:]))
        self.assertEqual(crops,2)

    def test_bilingual_motion_first_and_folded_context(self):
        self.assertEqual(sum(x['format']=='animation' for x in NEW),3)
        for x in NEW:
            for prefix in ['', 'en/']:
                html=(ROOT/'public-site'/prefix/x['path'].lstrip('/')/'index.html').read_text(encoding='utf8')
                doc=BeautifulSoup(html,'html.parser')
                figure=doc.select_one('.detail-motion figure') or doc.select_one('.detail-layout figure')
                self.assertEqual(figure['data-media-src'],x['media'][0]['src'])
                self.assertIn(x['sourceUrl'],html);self.assertIsNone(doc.select_one('[data-local-demo]'))
                for m in x['media'][1:]:
                    self.assertIsNotNone(doc.select_one('.detail-attachments:not([open]) [data-media-src="'+m['src']+'"]'))
                if x['format']=='animation':self.assertIsNotNone(doc.select_one('.detail-motion figure'))
                if x['media'][0]['src'].endswith('.mp4'):self.assertEqual(len(doc.select('.detail-motion video')),1)
        gif=next(x for x in NEW if x['media'][0]['src'].endswith('.gif'))
        with Image.open(ROOT/'public-site'/gif['media'][0]['src'].lstrip('/')) as image:
            self.assertTrue(image.is_animated);self.assertGreater(image.n_frames,1)

    def test_old_units_remain_and_reused_panels_not_redated(self):
        for old in json.loads((DIR/'before-catalog.json').read_text())['items']:
            for key in ['id','model','date','author','sourceUrl','updated','media']:self.assertEqual(BY[old['id']][key],old[key])
        fc=[x for x in NEW if 'reddit-fc6808-' in x['id']]
        self.assertEqual(sorted((x['model'],x['date']) for x in fc),[('Opus 4.5','2026-02-06'),('Opus 4.6','2026-02-06'),('Opus 4.7','2026-04-16')])
        self.assertTrue(all(not x.get('prompt') for x in NEW if 'reddit-ivampirepapi' in x['id']))

if __name__=='__main__':unittest.main()
