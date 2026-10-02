"""Post-implementation checks for bilingual editorial, SEO and Agent consistency."""
import csv
import json
import unittest
from pathlib import Path
from bs4 import BeautifulSoup
from editorial_content import FEATURED_IDS, CATALOG_VERSION, CSV_FIELDS, scope_sections, HOME_COPY
from historical_context import HISTORY_ID, historical_sections

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'public-site'


class EditorialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalogs = {lang:json.loads((OUT/('en/' if lang=='en' else '')/'data/catalog.json').read_text(encoding='utf8')) for lang in ['zh','en']}

    def soup(self, relative, lang):
        return BeautifulSoup((OUT/('en/' if lang=='en' else '')/relative).read_text(encoding='utf8'),'html.parser')

    def test_selection_is_same_reviewed_single_model_image_in_both_languages(self):
        for lang,catalog in self.catalogs.items():
            by = {x['id']:x for x in catalog['items']}
            home = self.soup('index.html',lang)
            cards = home.select('#featured .specimen-card')
            self.assertEqual(len(cards),6)
            self.assertFalse(home.select('#featured .source-archive-link'))
            self.assertEqual([x.select_one('.card-cover')['href'] for x in cards],[by[key]['path'] for key in FEATURED_IDS])
            for key,card in zip(FEATURED_IDS,cards):
                item=by[key]
                self.assertTrue(item['caseVisible'] and item['timelineVisible'])
                self.assertFalse(item.get('referenceOnly') or item.get('interactive'))
                self.assertEqual(item['format'],'svg')
                self.assertEqual(len(item['modelNames']),1)
                self.assertEqual(len(card.select('img')),1)
                self.assertEqual(card.select_one('img')['src'],item['thumbnail'])
                self.assertNotEqual(item['thumbnail'],item.get('cropProvenance',{}).get('original'))
            history=by[HISTORY_ID]
            self.assertEqual(home.select_one('[data-historical-hero] img')['src'],history['thumbnail'])
            self.assertEqual(home.select_one('[data-historical-hero] .hero-media')['href'],history['path'])
            self.assertEqual(home.select_one('[data-historical-hero] video')['data-motion-src'],history['media'][0]['src'])
            self.assertTrue(home.select_one('[data-historical-hero] video').has_attr('muted'))
            self.assertIn('1988',home.select_one('[data-historical-hero]').get_text())
            self.assertFalse(history['caseVisible'] or history['timelineVisible'])
            self.assertIsNone(history['caseNumber'])
            schema=json.loads(home.select_one('script[type="application/ld+json"]').string)
            self.assertEqual(schema['mainEntity']['numberOfItems'],6)
            self.assertEqual([x['url'] for x in schema['mainEntity']['itemListElement']],[by[key]['url'] for key in FEATURED_IDS])

    def test_home_uses_exact_user_supplied_bilingual_copy(self):
        for lang in ['zh','en']:
            home=self.soup('index.html',lang)
            title=home.select_one('.hero-title').get_text(' ',strip=True).replace(' ','')
            self.assertEqual(title,HOME_COPY[lang]['title'].replace(' ',''))
            self.assertEqual(home.select_one('.hero-question').get_text(),HOME_COPY[lang]['question'])
            self.assertEqual(home.select_one('.hero .intro').get_text(),HOME_COPY[lang]['description'])
            schema=json.loads(home.select_one('script[type="application/ld+json"]').string)
            self.assertEqual(schema['description'],HOME_COPY[lang]['description'])
            prefix='en/' if lang=='en' else ''
            markdown=(OUT/prefix/'index.md').read_text(encoding='utf8')
            self.assertIn(HOME_COPY[lang]['question'],markdown)
            self.assertIn(HOME_COPY[lang]['description'],markdown)
            self.assertEqual(home.select_one('link[type="text/markdown"]')['href'],'/'+prefix+'index.md')

    def test_historical_film_has_linked_bilingual_story_without_fabricated_ai_origin(self):
        for lang,catalog in self.catalogs.items():
            item=next(x for x in catalog['items'] if x['id']==HISTORY_ID)
            page=BeautifulSoup((OUT/item['path'].lstrip('/')/'index.html').read_text(encoding='utf8'),'html.parser')
            story=page.select_one('[data-historical-story]')
            self.assertEqual(len(story.select('section')),5)
            markdown=(OUT/item['markdown'].lstrip('/')).read_text(encoding='utf8')
            for title,text,url,_ in historical_sections(lang):
                self.assertIn(title,story.get_text())
                self.assertIn(text,story.get_text())
                self.assertTrue(story.find('a',href=url))
                self.assertIn(text,markdown)
                self.assertIn(url,markdown)
            self.assertIn('Dave Spafford',page.select_one('.facts').get_text())
            self.assertIn('not AI' if lang=='en' else '非 AI',page.select_one('.facts').get_text())
            schema=json.loads(page.select_one('script[type="application/ld+json"]').string)
            self.assertEqual(schema['about']['@type'],'Movie')

    def test_about_developers_markdown_and_llms_share_scope(self):
        for lang,catalog in self.catalogs.items():
            prefix='en/' if lang=='en' else ''
            for title,text in scope_sections(catalog['counts'],lang):
                for relative in ['about/index.html','developers/index.html']:
                    soup=self.soup(relative,lang)
                    self.assertIn(text,soup.select_one('main').get_text(' ',strip=True),prefix+relative)
                for relative in ['llms.txt','about/index.md','developers/index.md']:
                    self.assertIn(text,(OUT/prefix/relative).read_text(encoding='utf8'),prefix+relative)
            self.assertEqual(catalog['version'],CATALOG_VERSION)
            self.assertIn('1.3',self.soup('developers/index.html',lang).get_text())
            for relative in ['index.html','about/index.html','developers/index.html','timeline/index.html','play/index.html','sources/index.html']:
                text=self.soup(relative,lang).get_text(' ',strip=True)
                for stale in ['实验批次计 1 个','one per experiment batch','目录版本 1.1','Catalog version 1.1','counts are not a total of unique works','These are category counts']:
                    self.assertNotIn(stale,text,prefix+relative)
                for stale in ['普通新增仅限','异介质不进入静态','New ordinary intake is limited','outside the static timeline','当前不新增收录']:
                    self.assertNotIn(stale,text,prefix+relative)
            guide=(OUT/prefix/'llms.txt').read_text(encoding='utf8')
            self.assertIn('caseVisible',guide)
            self.assertIn('datePrecision',guide)
            self.assertIn('family',guide)
            self.assertIn('medium',guide)
            self.assertIn('all dates and media' if lang=='en' else '全时间段、全媒体',guide)
            self.assertTrue(any(x['timelineVisible'] and x['format']!='svg' for x in catalog['items']))

    def test_csv_exposes_same_counting_flags_and_provenance_as_json(self):
        for lang,catalog in self.catalogs.items():
            with (OUT/('en/' if lang=='en' else '')/'data/catalog.csv').open(encoding='utf8',newline='') as source:
                reader=csv.DictReader(source)
                self.assertEqual(reader.fieldnames,CSV_FIELDS)
                rows=list(reader)
            self.assertEqual(len(rows),catalog['counts']['records'])
            self.assertEqual(sum(x['caseVisible']=='true' and x['referenceOnly']!='true' for x in rows),catalog['counts']['cases'])
            self.assertEqual(sum(x['timelineVisible']=='true' for x in rows),catalog['counts']['timeline'])
            for row,item in zip(rows,catalog['items']):
                for key in ['id','date','sourceUrl','url','markdown','thumbnail']:
                    self.assertEqual(row[key],item[key])
                self.assertEqual(row['caseNumber'],str(item['caseNumber']) if item['caseNumber'] is not None else '')

    def test_all_generated_page_metadata_and_alternates(self):
        checked=0
        for path in OUT.rglob('*.html'):
            if 'index.html'!=path.name and path.name!='404.html':continue
            soup=BeautifulSoup(path.read_text(encoding='utf8'),'html.parser')
            if not soup.select_one('main#main'):continue
            checked+=1
            canonical=soup.select_one('link[rel=canonical]')['href']
            lang=soup.html['lang']
            self.assertTrue(soup.title.get_text(strip=True),str(path))
            self.assertTrue(soup.select_one('meta[name=description]')['content'],str(path))
            self.assertEqual(soup.select_one('meta[property="og:url"]')['content'],canonical)
            self.assertEqual({x['hreflang'] for x in soup.select('link[hreflang]')},{'zh-CN','en','x-default'})
            schema=json.loads(soup.select_one('script[type="application/ld+json"]').string)
            self.assertEqual(schema['url'],canonical)
            self.assertEqual(schema['inLanguage'],lang)
            self.assertNotIn('aggregateRating',schema)
            self.assertNotIn('additionalProperty',schema)
            self.assertTrue(soup.select_one('meta[property="og:image:alt"]')['content'])
            self.assertTrue(soup.select_one('meta[name="twitter:image:alt"]')['content'])
        self.assertGreater(checked,2000)

    def test_detail_schema_retains_source_precision_and_real_media(self):
        for lang,catalog in self.catalogs.items():
            for item in catalog['items']:
                soup=BeautifulSoup((OUT/item['path'].lstrip('/')/'index.html').read_text(encoding='utf8'),'html.parser')
                schema=json.loads(soup.select_one('script[type="application/ld+json"]').string)
                self.assertEqual(schema['isBasedOn'],item['sourceUrl'])
                self.assertEqual(schema['identifier'],item['id'])
                self.assertIn('not independently authenticated' if lang=='en' else '未独立认证',schema['abstract'])
                if item.get('date'):self.assertEqual(schema['temporalCoverage'],item['date'])
                self.assertNotIn('dateCreated',schema)
                self.assertNotIn('datePublished',schema)
                if item.get('author'):self.assertEqual(schema['creditText'],item['author'])
                expected='https://pelicanmap.aveniqa.com'+item['thumbnail'] if item['thumbnail'].startswith('/') else item['thumbnail']
                self.assertEqual(schema['image'],expected)
                social=soup.select_one('meta[property="og:image"]')['content']
                if item['thumbnail'].endswith(('.png','.jpg','.jpeg','.webp')):self.assertEqual(social,expected)
                else:self.assertTrue(social.endswith('og-cover-en.png' if lang=='en' else 'og-cover.png'))

    def test_openapi_matches_current_api_schema(self):
        api=json.loads((OUT/'openapi.json').read_text(encoding='utf8'))
        self.assertEqual(api['info']['version'],CATALOG_VERSION)
        params={x['name']:x['schema'] for x in api['paths']['/api/v1/specimens']['get']['parameters']}
        self.assertEqual(params['sort']['enum'],['newest','oldest'])
        self.assertEqual(params['lang']['enum'],['zh','en'])
        self.assertEqual(params['limit']['maximum'],50)
        self.assertEqual(params['offset']['maximum'],100000)
        self.assertIn('referenceOnly',api['components']['schemas']['Record']['properties'])
        self.assertIn('timelineVisible',api['components']['schemas']['Record']['properties'])

    def test_removed_year_route_has_no_stale_non_ai_card(self):
        sitemap=(OUT/'sitemap.xml').read_text(encoding='utf8')
        for lang in ['zh','en']:
            soup=self.soup('timeline/1988/index.html',lang)
            self.assertTrue(soup.select_one('meta[name=robots]')['content'].startswith('noindex'))
            self.assertFalse(soup.select('[data-results] .card'))
            self.assertIn('0',soup.select_one('[data-result-count]').get_text())
        self.assertNotIn('/timeline/1988/',sitemap)

    def test_timeline_footer_is_one_row_number_model_date_in_both_languages(self):
        for lang in ['zh','en']:
            soup=self.soup('timeline/index.html',lang)
            for card in soup.select('[data-results] .timeline-card'):
                row=card.select_one('.timeline-meta')
                self.assertIsNotNone(row)
                self.assertEqual([x['class'][0] for x in row.find_all(recursive=False)],['case-number','timeline-model','timeline-date'])
                date=row.select_one('time.timeline-date')
                self.assertEqual(date['datetime'],date.get_text())
                self.assertTrue(date.get('aria-label'))
                self.assertTrue(row.select_one('.timeline-model').get('title'))
        css=(ROOT/'site/assets/site.css').read_text(encoding='utf8')
        self.assertIn('.specimen-card>.card-foot,.timeline-meta{display:grid;grid-template-columns:74px minmax(0,1fr) 74px',css)


if __name__=='__main__':unittest.main()
