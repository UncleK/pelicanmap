"""Regression checks added after implementation; original archives are untouched."""
import copy
import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from PIL import Image
from bs4 import BeautifulSoup
from detail_presentation import apply_motion_previews, cover_media, motion_kind

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'public-site'

class MotionAutoplayTests(unittest.TestCase):
    def test_only_actual_original_motion_is_selected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'media').mkdir()
            Image.new('RGB',(10,10),'white').save(root/'media/still.gif')
            frames=[Image.new('RGB',(10,10),c) for c in ['red','blue']]
            frames[0].save(root/'media/moving.gif',save_all=True,append_images=frames[1:],duration=100,loop=0)
            (root/'media/real.webm').write_bytes(b'fixture-only')
            def item(src,**extra):return {'thumbnail':'/media/still.gif','media':[{'src':src}],**extra}
            records=[item('/media/still.gif',format='animation'),item('/media/moving.gif'),item('/media/real.webm'),item('/media/missing.webm'),item('/media/moving.gif',referenceOnly=True),item('/media/still.gif',previewUrl='https://example.com/unsafe')]
            apply_motion_previews(records,root)
            self.assertNotIn('motionPreview',records[0])
            self.assertEqual(records[1]['motionPreview']['type'],'image')
            self.assertEqual(records[2]['motionPreview']['type'],'video')
            for record in records[3:]:self.assertNotIn('motionPreview',record)
            original=copy.deepcopy(records)
            apply_motion_previews(records,root)
            self.assertEqual(records,original)
            folded=item('/media/still.gif');folded['media'].append({'src':'/media/real.webm','detailOnly':True})
            self.assertNotIn('motionPreview',apply_motion_previews([folded],root)[0])

    def test_publisher_resolves_the_current_release_demo_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'site').mkdir();(root/'demos/demos/example').mkdir(parents=True)
            frames=[Image.new('RGB',(10,10),c) for c in ['red','blue']]
            frames[0].save(root/'demos/demos/example/real.gif',save_all=True,append_images=frames[1:],duration=100,loop=0)
            url='https://pelicanmap-demos.aveniqa.com/demos/example/real.gif'
            records=[{'media':[{'src':url}],'thumbnail':url}]
            self.assertEqual(apply_motion_previews(records,root/'site')[0]['motionPreview'],{'type':'image','src':url})

    def test_generated_catalog_and_bilingual_cards_have_same_motion(self):
        zh=json.loads((OUT/'data/catalog.json').read_text(encoding='utf8'))
        en=json.loads((OUT/'en/data/catalog.json').read_text(encoding='utf8'))
        english={x['id']:x for x in en['items']}
        totals=Counter()
        for item in zh['items']:
            preview=item.get('motionPreview')
            self.assertEqual(preview,english[item['id']].get('motionPreview'))
            self.assertFalse(item.get('referenceOnly') and preview)
            if not preview:continue
            totals[preview['type']]+=1
            if preview['type']!='iframe':
                self.assertIn(motion_kind(preview['src'],str(OUT)),{'video','animation'})
                self.assertTrue(any(m['src']==preview['src'] and not m.get('detailOnly') for m in item['media']))
            for prefix in ['', 'en/']:
                page=BeautifulSoup((OUT/prefix/item['path'].lstrip('/')/'index.html').read_text(encoding='utf8'),'html.parser')
                self.assertTrue(page.select_one('script[src^="/assets/motion.js?v="]'))
                for video in page.select('video[data-motion-kind]'):
                    for attr in ['autoplay','muted','loop','playsinline']:self.assertTrue(video.has_attr(attr))
                    self.assertFalse(video.has_attr('src')) # only visible originals fetch/play
            card=BeautifulSoup(cover_media(item),'html.parser')
            self.assertEqual(card.select_one('[data-motion-kind]')['data-motion-src'],preview['src'])
            self.assertTrue(card.select_one('img[alt]'))
        self.assertGreater(totals['video'],10)
        self.assertGreater(totals['image'],20)
        self.assertGreaterEqual(totals['iframe'],3)
        self.assertNotIn('motionPreview',next(x for x in zh['items'] if x['id']=='x-olddonkey-fable55-max-2026-10-02'))

if __name__=='__main__':unittest.main()
