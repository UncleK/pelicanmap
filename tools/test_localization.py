import json,unittest
from pathlib import Path
from bs4 import BeautifulSoup
from localization import LOCALES,statistics,localized_catalog,artwork_year_range
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'public-site'
class LocalizationTests(unittest.TestCase):
 def test_year_range_follows_new_work_years_and_excludes_historical_context(self):
  self.assertEqual(artwork_year_range([{'date':'1988-01','caseVisible':False},{'date':'2024-10'},{'date':'2028-02'},{'date':'2030-01','referenceOnly':True}]),'2024—2028')
  self.assertEqual(artwork_year_range([{'date':'2028-02'}]),'2028')
 @classmethod
 def setUpClass(cls):
  cls.en=json.loads((OUT/'en/data/catalog.json').read_text(encoding='utf8'))
 def test_shared_counts_source_and_archival_fields(self):
  for lang in ('ru','pt-BR'):
   data=json.loads((OUT/lang/'data/catalog.json').read_text(encoding='utf8'))
   self.assertEqual(data,localized_catalog(self.en,lang))
   for before,after in zip(self.en['items'],data['items']):
    for key in ('id','caseNumber','sourceUrl','date','model','prompt','notes','media','motionPreview','thumbnail','demoUrl'):
     self.assertEqual(before.get(key),after.get(key),(lang,before['id'],key))
    self.assertTrue((OUT/after['path'].lstrip('/')/'index.html').is_file())
    self.assertTrue((OUT/after['markdown'].lstrip('/')).is_file())
 def test_real_translated_navigation_controls_and_reciprocal_links(self):
  for lang in LOCALES:
   for path in ('','timeline/','specimens/','derivatives/','about/','rights/','developers/'):
    file=OUT/LOCALES[lang]['prefix'].lstrip('/')/path/'index.html'
    soup=BeautifulSoup(file.read_text(encoding='utf8'),'html.parser')
    self.assertEqual(soup.html['lang'],LOCALES[lang]['tag'])
    self.assertEqual({x['hreflang'] for x in soup.select('link[hreflang]')},{x['tag'] for x in LOCALES.values()}|{'x-default'})
    self.assertEqual(len(soup.select('.language-menu')),1)
    scripts=[x.get('src') for x in soup.select('script[src]')]
    locale_script=next((s for s in scripts if '/locale-data.js?' in s),None)
    self.assertIsNotNone(locale_script,(lang,path,'missing dynamic locale dictionary'))
    self.assertLess(scripts.index(locale_script),next(i for i,s in enumerate(scripts) if '/site.js?' in s))
    if lang in ('ru','pt-BR'):
     self.assertIn(LOCALES[lang]['strings']['Home'],soup.select_one('.nav').get_text())
     self.assertTrue(soup.select_one('[data-translation-scope=interface]'))
     if path=='timeline/':
      self.assertTrue(soup.select_one('[data-model-collapse]').has_attr('checked'))
      self.assertIn(LOCALES[lang]['strings']['Search'],soup.select_one('[data-search-toggle]').get_text())
 def test_atomic_stats_match_catalog_and_home_bindings(self):
  stats=json.loads((OUT/'data/stats.json').read_text(encoding='utf8'))
  self.assertEqual(stats,statistics(self.en))
  self.assertEqual(stats['works'],stats['timeline']+stats['derivatives'])
  for rows in (stats['years'],stats['sources']):self.assertEqual(sum(x['total'] for x in rows),stats['works'])
  for item in LOCALES.values():
   home=BeautifulSoup((OUT/item['prefix'].lstrip('/')/'index.html').read_text(encoding='utf8'),'html.parser')
   for key in ('cases','timeline','sourceIndex','benchmarkCollections'):
    self.assertEqual(int(home.select_one('[data-stat='+key+']').get_text()),self.en['counts'][key])
if __name__=='__main__':unittest.main()
