import json
import unittest
from pathlib import Path
from bs4 import BeautifulSoup
from experiment_batches import group_records, case_counts
from case_policy import in_timeline
from historical_context import historical_display

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'public-site'
EXPECTED=631+len(json.loads((ROOT/'site/additions.json').read_text(encoding='utf8')) if (ROOT/'site/additions.json').exists() else [])

class PublicSiteTests(unittest.TestCase):
    def test_reviewed_video_posters_are_shared_across_languages(self):
        overrides=json.loads((ROOT/'site/thumbnail-overrides.json').read_text(encoding='utf8'))
        self.assertGreaterEqual(len(overrides),9)
        for prefix in ['', 'en/']:
            catalog=json.loads((OUT/prefix/'data/catalog.json').read_text(encoding='utf8'))
            for item in catalog['items']:
                if item['originalId'] not in overrides:continue
                override=overrides[item['originalId']]
                self.assertEqual(item['thumbnail'],override['poster'])
                kind=override.get('type','source-video-frame')
                self.assertEqual(item['thumbnailProvenance']['type'],kind)
                src=override['poster'] if kind=='archived-source-image' else override['sourceSvg'] if kind=='svg-render' else override['video']
                media=next(m for m in item['media'] if m['src']==src)
                self.assertEqual(media['source'],override['source'])
                soup=BeautifulSoup((OUT/item['path'].lstrip('/')/'index.html').read_text(encoding='utf8'),'html.parser')
                if kind=='source-video-frame':
                    self.assertGreater(item['thumbnailProvenance']['timestampSeconds'],0)
                    self.assertEqual(media['poster'],override['poster'])
                    self.assertEqual(soup.select_one('video')['poster'],override['poster'])
                elif kind=='archived-source-image':
                    self.assertNotEqual(soup.select_one('video')['poster'],override['poster'])
                else:
                    self.assertEqual(media['preview'],override['poster'])
                    self.assertIsNotNone(soup.find('img',src=override['poster']))
                    self.assertIsNotNone(soup.find('a',href=override['sourceSvg']))
                self.assertTrue((OUT/override['poster'].lstrip('/')).is_file())

    def test_licensed_outputs_have_public_notices_in_both_languages(self):
        catalog=json.loads((OUT/'data/catalog.json').read_text(encoding='utf8'))
        for item in catalog['items']:
            if not item.get('licenseUrl'):continue
            for url in [item['licenseUrl'],*item.get('licenseFiles',[])]:
                self.assertTrue((OUT/url.lstrip('/')).is_file(),url)
                self.assertGreater((OUT/url.lstrip('/')).stat().st_size,100)
                for prefix in ['', 'en/']:
                    soup=BeautifulSoup((OUT/prefix/item['path'].lstrip('/')/'index.html').read_text(encoding='utf8'),'html.parser')
                    self.assertIsNotNone(soup.find('a',href=url),prefix+item['id'])

    def test_browsing_controls_and_compact_pagination_in_both_languages(self):
        for prefix in ['', 'en/']:
            for path in ['timeline/', 'specimens/', 'play/']:
                soup = BeautifulSoup((OUT/prefix/path/'index.html').read_text(encoding='utf8'), 'html.parser')
                self.assertIsNotNone(soup.select_one('[data-sort-toggle]'), prefix+path)
                self.assertIsNotNone(soup.select_one('[data-density-toggle]'), prefix+path)
                self.assertIsNotNone(soup.select_one('select[name=year]'), prefix+path)
                self.assertIsNotNone(soup.select_one('[data-page-jump]'), prefix+path)
                self.assertLessEqual(len(soup.select('[data-pagination] a')), 2)
                self.assertLessEqual(len(soup.select('[data-results] .card')), 24)
            self.assertTrue((OUT/prefix/'timeline/page/2/index.html').exists())

    def test_additions_are_counted_and_in_timeline(self):
        additions = json.loads((ROOT/'site/additions.json').read_text(encoding='utf8'))
        catalog = json.loads((OUT/'data/catalog.json').read_text(encoding='utf8'))
        self.assertEqual(catalog['counts']['timeline'], case_counts(catalog['items'])['timeline'])
        for prefix in ['', 'en/']:
            home = BeautifulSoup((OUT/prefix/'index.html').read_text(encoding='utf8'), 'html.parser')
            self.assertEqual(home.select_one('[data-total-records]').get_text(), str(catalog['counts']['cases']))
            timeline_html = ''.join(f.read_text(encoding='utf8') for f in (OUT/prefix/'timeline').rglob('index.html'))
            for item in additions:
                public = next(x for x in catalog['items'] if x['id'] == item['id'])
                if public.get('referenceOnly'):
                    self.assertNotIn(item['id'], timeline_html)
                    self.assertNotIn('/collections/'+public['batch']['id']+'/',timeline_html)
                elif public.get('batch'):
                    self.assertIn('/collections/'+public['batch']['id']+'/', timeline_html)
                    batch_html=(OUT/prefix/'collections'/public['batch']['id']/'index.html').read_text(encoding='utf8')
                    self.assertIn(item['id'],batch_html)
                elif in_timeline(public):
                    self.assertIn(item['id'], timeline_html)
                else:
                    self.assertNotIn('href="/'+prefix+'specimens/'+item['id']+'/',timeline_html)

    def test_benchmark_is_separate_with_collapsed_local_samples(self):
        catalog=json.loads((OUT/'data/catalog.json').read_text(encoding='utf8'))
        samples=[x for x in catalog['items'] if x.get('batch')]
        self.assertEqual(len(samples),138)
        self.assertEqual(len(group_records(samples)),0)
        self.assertEqual(len(group_records(samples,True)),1)
        self.assertEqual(catalog['counts']['cases'],len(group_records(catalog['items'])))
        self.assertEqual(catalog['counts']['samples'],0)
        self.assertEqual(catalog['counts']['referenceRecords'],138)
        self.assertTrue(all(x['caseNumber'] is None and x['kind']=='reference' for x in samples))
        for prefix in ['', 'en/']:
            path=OUT/prefix/'collections/openenv-2026-07-29/index.html'
            soup=BeautifulSoup(path.read_text(encoding='utf8'),'html.parser')
            self.assertEqual(len(soup.select('.batch-model')),7)
            self.assertEqual(len(soup.select('.batch-model[open]')),0)
            self.assertEqual(len(soup.select('[data-batch-sample]')),139)
            self.assertIsNotNone(soup.select_one('[data-batch-expand]'))
            self.assertTrue((path.parent/'index.md').exists())
            for sample in samples:
                expected='/'+prefix+sample['path'].lstrip('/')
                self.assertIsNotNone(soup.find('a',href=expected),sample['id'])
                detail=BeautifulSoup((OUT/expected.lstrip('/')/'index.html').read_text(encoding='utf8'),'html.parser')
                self.assertIsNotNone(detail.select_one('.batch-parent a'))
            for listing in ['specimens','timeline']:
                cards=[]
                for file in [OUT/prefix/listing/'index.html',*(OUT/prefix/listing/'page').glob('*/index.html')]:
                    document=BeautifulSoup(file.read_text(encoding='utf8'),'html.parser')
                    if document.select_one('meta[name=robots]')['content'].startswith('noindex'):continue
                    cards+=document.select('[data-batch-card]')
                    self.assertNotIn('href="/'+prefix+'specimens/hf-openenv-',str(document.select_one('[data-results]')))
                self.assertEqual(len(cards),0,prefix+listing)
            index=BeautifulSoup((OUT/prefix/'tags/benchmark/index.html').read_text(encoding='utf8'),'html.parser')
            self.assertEqual(len(index.select('[data-benchmark-collection]')),1)
            self.assertFalse(index.select('.page-top p,.callout.benchmark-disclaimer'))
            self.assertIsNotNone(index.select_one('nav.nav a[aria-current=page]'))

    def test_play_contains_only_local_interactions_and_embeds_them(self):
        catalog = json.loads((OUT/'data/catalog.json').read_text(encoding='utf8'))
        for prefix in ['', 'en/']:
            soup = BeautifulSoup((OUT/prefix/'play/index.html').read_text(encoding='utf8'), 'html.parser')
            for card in soup.select('[data-results] .card'):
                href = card.select_one('.card-cover')['href']
                item = next(x for x in catalog['items'] if href.endswith(x['path']))
                self.assertTrue(item.get('interactive'), item['id'])
                self.assertTrue(item['demoUrl'].startswith('https://pelicanmap-demos.aveniqa.com/'))
                detail = BeautifulSoup((OUT/href.strip('/')/'index.html').read_text(encoding='utf8'), 'html.parser')
                frame = detail.select_one('iframe[data-local-demo]')
                self.assertIsNotNone(frame, item['id'])
                self.assertEqual(frame['src'], item['demoUrl'])
            self.assertNotIn('github-openvglab-opus55', str(soup))

    def test_chronological_case_numbers_and_model_only_footers(self):
        from card_metadata import model_names
        self.assertEqual(model_names('GPT-3.5 → GPT-6 montage'),['GPT-3.5','GPT-6'])
        self.assertEqual(model_names('GPT-5.3 Codex Spark vs Codex'),['GPT-5.3 Codex Spark','Codex'])
        self.assertEqual(model_names('unspecified agent'),[])
        catalogs=[json.loads((OUT/p/'data/catalog.json').read_text(encoding='utf8')) for p in ['', 'en']]
        cases=sorted(group_records(catalogs[0]['items']),key=lambda x:(x['date'],x['id']))
        self.assertEqual([x['caseNumber'] for x in cases],list(range(1,len(cases)+1)))
        self.assertEqual({x['id']:x['caseNumber'] for x in catalogs[0]['items']},{x['id']:x['caseNumber'] for x in catalogs[1]['items']})
        samples=[x for x in catalogs[0]['items'] if x.get('batch')]
        self.assertEqual(len({x['caseNumber'] for x in samples}),1)
        self.assertEqual(len(group_records(samples,True)[0]['modelNames']),7)
        example=next(x for x in catalogs[0]['items'] if x['originalId']=='reddit-bellno9522-bicycle-riding-pelican-2026-09-30')
        self.assertEqual(example['modelNames'],['GPT-5.6 Sol','GPT-6 Sol','GPT-6 Astra','Seedance 2.0 mini'])
        for prefix in ['', 'en/']:
            for listing in ['timeline/','specimens/','play/']:
                soup=BeautifulSoup((OUT/prefix/listing/'index.html').read_text(encoding='utf8'),'html.parser')
                for card in soup.select('.specimen-card'):
                    self.assertEqual([x['class'][0] for x in card.find_all(recursive=False)],['card-cover','card-body','card-foot'])
                    self.assertEqual(card.select_one('.card-body')['tabindex'],'0')
                    number=card.select_one('.case-number').get_text()
                    if number not in {'来源存档','Source archive'}:self.assertRegex(number,r'^#\d+$')
                    else:self.assertEqual(listing,'play/')
                    self.assertTrue(card.select('.model-name'))
                    self.assertNotIn('查看标本',card.select_one('.card-foot').get_text())
                    self.assertNotIn('View record',card.select_one('.card-foot').get_text())

    def test_real_pages_and_machine_readable_records(self):
        self.assertTrue((OUT / 'data/catalog.json').exists(), 'Public catalog has not been built')
        catalog = json.loads((OUT / 'data/catalog.json').read_text(encoding='utf-8'))
        self.assertEqual(len(catalog['items']), EXPECTED)
        self.assertEqual(len({x['id'] for x in catalog['items']}), EXPECTED)
        for item in catalog['items']:
            file = OUT / item['path'].strip('/') / 'index.html'
            self.assertTrue(file.exists(), str(file))
            soup = BeautifulSoup(file.read_text(encoding='utf-8'), 'html.parser')
            self.assertEqual(soup.h1.get_text(), historical_display(item)['title'])
            self.assertEqual(soup.select_one('link[rel=canonical]')['href'], item['url'])
            self.assertTrue(soup.select_one('meta[name=description]')['content'])
            self.assertTrue((OUT / item['markdown'].lstrip('/')).exists())

    def test_publication_boundary_and_crawlable_navigation(self):
        self.assertTrue((OUT / 'index.html').exists(), 'Public homepage has not been built')
        soup = BeautifulSoup((OUT / 'index.html').read_text(encoding='utf-8'), 'html.parser')
        self.assertGreaterEqual(len(soup.select('a[href^="/specimens/"]')), 6)
        self.assertFalse((OUT / 'pelican-archive').exists())
        for f in OUT.rglob('*.html'):
            html = f.read_text(encoding='utf-8')
            self.assertNotIn('../pelican-archive', html, str(f))
            self.assertNotIn('file:///', html, str(f))
        for name in ['robots.txt', 'sitemap.xml', 'llms.txt', '404.html', 'openapi.json']:
            self.assertTrue((OUT / name).exists(), name)

    def test_catalog_preserves_sources_and_status(self):
        self.assertTrue((OUT / 'data/catalog.json').exists(), 'Public catalog has not been built')
        items = json.loads((OUT / 'data/catalog.json').read_text(encoding='utf-8'))['items']
        self.assertFalse(any(x['mediaStatus'] == 'source-deleted' for x in items))
        for item in items:
            self.assertTrue(item['thumbnail'],item['id'])
            self.assertTrue(item['media'],item['id'])
            self.assertTrue(item['sourceUrl'].startswith('https://'), item['id'])
            self.assertIn('promptStatus', item)
            self.assertNotIn('audit/', json.dumps(item))

    def test_removed_records_leave_no_public_pages_or_index_entries(self):
        removed=json.loads((ROOT/'site/publication-exclusions.json').read_text(encoding='utf-8'))
        for entry in removed:
            for prefix in ['', 'en/']:
                for name in ['index.html','index.md']:
                    self.assertFalse((OUT/prefix/'specimens'/entry['id']/name).exists(),entry['id'])
            for relative in ['sitemap.xml','feed.xml','en/feed.xml','data/catalog.json','en/data/catalog.json']:
                self.assertNotIn(entry['id'],(OUT/relative).read_text(encoding='utf-8'))

if __name__ == '__main__':
    unittest.main()
