import json
import unittest
from pathlib import Path
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'public-site'

class BilingualTests(unittest.TestCase):
    def test_every_record_has_localized_page_and_source(self):
        en=json.loads((OUT/'en/data/catalog.json').read_text(encoding='utf-8'))
        zh=json.loads((OUT/'data/catalog.json').read_text(encoding='utf8'))
        self.assertEqual({x['id'] for x in en['items']},{x['id'] for x in zh['items']})
        for item in en['items']:
            soup=BeautifulSoup((OUT/item['path'].lstrip('/')/'index.html').read_text(encoding='utf-8'),'html.parser')
            self.assertEqual(soup.html['lang'],'en')
            self.assertEqual(soup.select_one('link[rel=canonical]')['href'],item['url'])
            self.assertTrue(soup.select_one('link[hreflang=zh-CN]'))
            self.assertTrue(soup.select_one('a[data-language]'))
            self.assertTrue((OUT/item['markdown'].lstrip('/')).exists())
            self.assertTrue(item['sourceUrl'].startswith('https://'))
    def test_interactive_records_have_actual_preview(self):
        catalog=json.loads((OUT/'data/catalog.json').read_text(encoding='utf-8'))
        for item in catalog['items']:
            if item['demoUrl']:
                self.assertTrue(item['thumbnail'],item['id'])
                self.assertTrue(item['media'],item['id'])
    def test_language_switches_match_current_page(self):
        for rel in ['index.html','timeline/index.html','play/index.html','sources/index.html','developers/index.html']:
            for prefix in ['','en/']:
                soup=BeautifulSoup((OUT/(prefix+rel)).read_text(encoding='utf-8'),'html.parser')
                alternates={x['hreflang']:x['href'] for x in soup.select('link[hreflang]')}
                self.assertEqual(set(alternates),{'zh-CN','en','x-default'})
                self.assertIn('/en/',alternates['en'])
                self.assertEqual(soup.select_one('a[data-language]')['href'],('/'+rel.removesuffix('index.html')) if prefix else '/en/'+rel.removesuffix('index.html'))

if __name__=='__main__': unittest.main()
