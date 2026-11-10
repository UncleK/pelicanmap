"""The user-approved Tihu move preserves originals while separating references."""
import hashlib
import json
import unittest
from unittest.mock import patch
from collections import Counter
from pathlib import Path
from bs4 import BeautifulSoup
from case_policy import apply_case_policy, is_case, in_timeline
from card_metadata import apply_card_metadata
from tihu_benchmark import load, pages, record_details, PATH

ROOT=Path(__file__).resolve().parents[1]
BATCH=ROOT/'pelican-archive/research/2026-11-02-tihu-benchmark'
BEFORE=json.loads((BATCH/'catalog-local-before.json').read_text(encoding='utf8'))


class TihuCoreTests(unittest.TestCase):
    def test_exact_original_outputs_and_sources_are_preserved(self):
        rows=load()['rows'];previous={x['id']:x for x in BEFORE['items']}
        self.assertEqual(len(rows),90)
        self.assertEqual(len({row['id'] for row in rows}),90)
        self.assertEqual(len({row['model'] for row in rows}),10)
        settings=Counter((row['model'],row['effort']) for row in rows)
        self.assertEqual(len(settings),30)
        self.assertEqual(set(settings.values()),{3})
        for row in rows:
            old=previous[row['id']]
            self.assertEqual(row['specimenPath'],old['path'])
            self.assertEqual(row['sourceUrl'],old['sourceUrl'])
            self.assertEqual(row['originalCaseNumber'],old['caseNumber'])
            self.assertEqual(row['localSvg'],old['media'][0]['src'])
            self.assertEqual(row['svgSha256'],old['media'][0]['sha256'])
            original=ROOT/'pelican-web'/row['localSvg'].lstrip('/')
            self.assertEqual(hashlib.sha256(original.read_bytes()).hexdigest(),row['svgSha256'])

    def test_classification_changes_only_the_reviewed_samples(self):
        ids={row['id'] for row in load()['rows']}
        original={x['id']:x for x in BEFORE['items']}
        reviews=json.loads((ROOT/'site/case-reviews.json').read_text(encoding='utf8'))
        reviews={key: value for key, value in reviews.items() if key in original}
        controls=apply_case_policy(BEFORE['items'],ROOT/'pelican-web',
                                   reviews={key: value for key, value in reviews.items() if key not in ids})
        old={x['id']:x for x in controls}
        result=apply_case_policy(BEFORE['items'],ROOT/'pelican-web',reviews=reviews)
        apply_card_metadata(result,BEFORE)
        self.assertEqual(len(result),len(old))
        for item in result:
            if item['id'] not in ids:
                for key in ['date','model','sourceUrl','media','thumbnail','referenceOnly','caseVisible','timelineVisible']:
                    self.assertEqual(item.get(key),old[item['id']].get(key),(item['id'],key))
                continue
            self.assertTrue(item['referenceOnly'])
            self.assertFalse(is_case(item));self.assertFalse(in_timeline(item))
            self.assertIsNone(item['caseNumber'])
            self.assertEqual(item['archivedCaseNumber'],original[item['id']]['caseNumber'])
            for key in ['id','path','date','model','sourceUrl','media','thumbnail','rights']:
                self.assertEqual(item[key],old[item['id']][key],key)
            self.assertIn('Open Tihu Benchmark',record_details(item,'en'))

    def test_grouped_source_cards_keep_effort_run_score_and_old_links(self):
        items=apply_case_policy(BEFORE['items'],ROOT/'pelican-web')
        for lang in ['zh','en']:
            local=[dict(item,path=('/en'+item['path']) if lang=='en' else item['path']) for item in items]
            with patch('tihu_benchmark.collections',return_value=['tihu-2026-11-01']):
                path,title,description,body=next(pages(local,lang))
            self.assertEqual(path,PATH)
            soup=BeautifulSoup(body,'html.parser')
            self.assertEqual(len(soup.select('.batch-model')),10)
            self.assertEqual(len(soup.select('[data-batch-sample]')),90)
            self.assertIsNotNone(soup.select_one('[data-reference-only=true]'))
            self.assertFalse(soup.select('.batch-model[open]'))
            for row in load()['rows']:
                self.assertIn(('/en' if lang=='en' else '')+row['specimenPath'],body)
                self.assertIn('#'+str(row['originalCaseNumber']),body)
                self.assertIn(row['upstreamScoreText'],soup.get_text())
            self.assertIn('low',body);self.assertIn('medium',body);self.assertIn('max',body)
            self.assertIsNotNone(soup.select_one('script[src^="/assets/tihu-benchmark.js?v="][defer]'))

    def test_server_only_translations_do_not_change_browser_asset(self):
        import localization
        asset=ROOT/'site/assets/locale-data.js';before=asset.read_bytes()
        localization.write_runtime()
        self.assertEqual(asset.read_bytes(),before)
        for lang in ['ru','pt-BR']:
            self.assertNotEqual(localization.translate('Former archive number',lang),'Former archive number')
            self.assertNotEqual(localization.translate('Former archive number #123',lang),'Former archive number #123')
            self.assertNotEqual(localization.translate('Source AI reference score: 8.90 ± 0.20',lang),'Source AI reference score: 8.90 ± 0.20')
            self.assertNotEqual(localization.translate('10 model labels · 30 effort groups · 90 samples',lang),'10 model labels · 30 effort groups · 90 samples')
            self.assertNotEqual(localization.translate('medium · Sample 2/3',lang),'medium · Sample 2/3')

    def test_benchmark_generator_includes_new_and_existing_collections(self):
        from benchmark_reference import pages as benchmark_pages
        items=apply_case_policy(BEFORE['items'],ROOT/'pelican-web')
        with patch('tihu_benchmark.collections',return_value=['tihu-2026-11-01']):
            rendered=list(benchmark_pages(items,'en'))
        paths=[row[0] for row in rendered]
        for path in [PATH,'/collections/openenv-2026-07-29/','/collections/pelicanbenchmark-2026-09-28/']:
            self.assertEqual(paths.count(path),1)


class TihuRenderedTests(unittest.TestCase):
    def test_real_four_language_pages_and_current_stats(self):
        root=ROOT/'public-site'
        data=json.loads((root/'data/catalog.json').read_text(encoding='utf8'))
        self.assertEqual(data['counts']['cases'],BEFORE['counts']['cases']-90)
        self.assertEqual(data['counts']['timeline'],BEFORE['counts']['timeline']-90)
        self.assertEqual(data['counts']['records'],BEFORE['counts']['records'])
        self.assertEqual(data['counts']['benchmarkCollections'],3)
        self.assertEqual(data['counts']['referenceRecords'],BEFORE['counts']['referenceRecords']+90)
        for prefix in ['', 'en/', 'ru/', 'pt-BR/']:
            index=BeautifulSoup((root/prefix/'tags/benchmark/index.html').read_text(encoding='utf8'),'html.parser')
            self.assertEqual(len(index.select('[data-benchmark-collection]')),3)
            card=index.select_one('[data-benchmark-collection=tihu-2026-11-01]')
            self.assertIsNotNone(card)
            self.assertEqual(card.select_one('a')['href'],'/'+prefix+PATH.lstrip('/'))
            page=BeautifulSoup((root/prefix/PATH.lstrip('/')/'index.html').read_text(encoding='utf8'),'html.parser')
            self.assertEqual(len(page.select('[data-batch-sample]')),90)
            self.assertEqual(len(page.select('.batch-model')),10)
            first=load()['rows'][0]
            detail=BeautifulSoup((root/prefix/first['specimenPath'].lstrip('/')/'index.html').read_text(encoding='utf8'),'html.parser')
            self.assertIsNotNone(detail.select_one('[data-tihu-reference]'))
            self.assertIn('#'+str(first['originalCaseNumber']),detail.get_text())
            if prefix in ['ru/','pt-BR/']:
                self.assertNotIn('Former archive number',page.get_text())
                self.assertNotIn('Scores come from Tihu AI judges.',page.get_text())
        current={i['id']:i for i in data['items']}
        for row in load()['rows']:
            self.assertTrue(current[row['id']]['referenceOnly'])
            self.assertFalse(current[row['id']]['timelineVisible'])
            self.assertFalse(current[row['id']]['caseVisible'])


if __name__=='__main__':unittest.main()
