import copy
import hashlib
import json
import unittest
from pathlib import Path
from bs4 import BeautifulSoup
from PIL import Image
from model_chronology import apply_model_chronology,ordered_timeline,timeline_year
from detail_frames import apply_detail_frames
from historical_context import HISTORY_ID

ROOT=Path(__file__).resolve().parents[1]
CAT=json.loads((ROOT/'site/catalog.json').read_text(encoding='utf8'))

class ModelChronologyTests(unittest.TestCase):
    def test_desktop_title_spacing_preserves_mobile_rules(self):
        css=(ROOT/'site/assets/site.css').read_text(encoding='utf8')
        self.assertIn('@media(min-width:721px){\n  .page-top{padding-bottom:10px}',css)
        self.assertIn('.page-top h1{margin-bottom:8px}',css)
        self.assertIn('main:has([data-browser])>.page-top{padding-right:45%}',css)
        self.assertIn('main:has([data-browser]) .page-top h1{font-size:25px;line-height:1.3;margin:0}',css)
    def test_release_order_does_not_rewrite_dates_or_model_claims(self):
        rows=[{'id':'old','date':'2026-10-02','model':'gemini-3.8-flash','modelNames':['gemini-3.8-flash']},
              {'id':'new','date':'2026-09-29','model':'gpt-6.1-sol','modelNames':['gpt-6.1-sol']},
              {'id':'unknown','date':'2026-10-02','model':'Gemini mystery','modelNames':['Gemini mystery']}]
        before=copy.deepcopy(rows)
        apply_model_chronology(rows)
        self.assertEqual([x['id'] for x in ordered_timeline(rows)],['unknown','new','old'])
        self.assertEqual([x['id'] for x in ordered_timeline(rows,'oldest')],['old','new','unknown'])
        self.assertEqual([{k:v for k,v in x.items() if k!='modelTimeline'} for x in rows],before)
        self.assertEqual(timeline_year(rows[2]),'2026')
        self.assertNotIn('releaseDate',rows[2]['modelTimeline'])
        self.assertEqual(rows[2]['modelTimeline']['status'],'inferred-position')
        self.assertEqual(rows[2]['modelTimeline']['sortDate'],'2026-10')
        self.assertEqual(apply_model_chronology(copy.deepcopy(rows)),rows)
    def test_original_record_fields_and_additions_unchanged(self):
        before=json.loads((ROOT/'pelican-archive/research/2026-10-02-model-release-order/catalog-before.json').read_text(encoding='utf8'))
        strip=lambda x:{k:v for k,v in x.items() if k not in {'modelTimeline','detailFrames'}}
        old={x['id']:x for x in before['items']}
        self.assertEqual(set(old),{x['id'] for x in CAT['items']})
        for item in CAT['items']:
            previous=old[item['id']]
            if item['id']!=HISTORY_ID:
                self.assertEqual(strip(item),strip(previous),item['id'])
                continue
            allowed={'recordRepair'}
            self.assertEqual({k:v for k,v in strip(item).items() if k not in allowed},{k:v for k,v in strip(previous).items() if k not in allowed})
            self.assertEqual(len(item['media']),len(previous['media']))
            for media,prior_media in zip(item['media'],previous['media']):
                for key in ['src','source','poster']:self.assertEqual(media[key],prior_media[key])
                self.assertEqual(media,prior_media)
                self.assertEqual(hashlib.sha256((ROOT/'pelican-web'/media['src'].lstrip('/')).read_bytes()).hexdigest(),item['recordRepair']['mediaSha256'])
            self.assertEqual(item['recordRepair']['originalTitle'],previous['title'])
            self.assertEqual(item['recordRepair']['originalNotes'],previous['notes'])
        self.assertEqual(CAT['counts'],before['counts'])
        self.assertEqual(json.loads((ROOT/'site/additions.json').read_text(encoding='utf8')),json.loads((ROOT/'pelican-archive/research/2026-10-02-model-release-order/additions-before.json').read_text(encoding='utf8')))
    def test_release_conflict_and_explicit_snapshots_are_not_guessed(self):
        rows=[{'id':'pre','date':'2025-04-17','model':'Gemini 2.5 Flash','modelNames':['Gemini 2.5 Flash']},
              {'id':'snapshot','date':'2025-04-17','model':'gemini-2.5-flash-preview-04-17','modelNames':['gemini-2.5-flash-preview-04-17']},
              {'id':'unspecified','date':'2026-09-02','model':'Gemini 3.8','modelNames':['Gemini 3.8']}]
        apply_model_chronology(rows)
        self.assertNotIn('releaseDate',rows[0]['modelTimeline'])
        self.assertTrue(rows[0]['modelTimeline']['sourceDatePredatesRelease'])
        self.assertEqual(rows[1]['modelTimeline']['releaseDate'],'2025-04-17')
        self.assertNotIn('releaseDate',rows[2]['modelTimeline'])
        self.assertEqual(rows[2]['modelTimeline']['label'],'Gemini 3.8')

    def test_provisional_positions_use_first_counted_source_not_ingestion_or_reposts(self):
        rows=[{'id':'late','date':'2026-10-02','updated':'2026-10-02','sourceUrl':'https://example.com/late','model':'Fable mystery','modelNames':['Fable mystery'],'caseVisible':True},
              {'id':'early','date':'2026-09-20','sourceUrl':'https://example.com/early','model':'Fable mystery','modelNames':['Fable mystery'],'caseVisible':True},
              {'id':'context','date':'2024-01-01','sourceUrl':'https://example.com/context','model':'Fable mystery','modelNames':['Fable mystery'],'caseVisible':False},
              {'id':'reference','date':'2023-01-01','model':'Fable mystery','modelNames':['Fable mystery'],'referenceOnly':True}]
        before=copy.deepcopy(rows)
        apply_model_chronology(rows)
        for item in rows[:3]:
            self.assertEqual(item['modelTimeline']['sortDate'],'2026-09')
            self.assertNotIn('releaseDate',item['modelTimeline'])
            self.assertEqual(item['modelTimeline']['estimatedFrom']['id'],'early')
            self.assertEqual(item['modelTimeline']['estimatedFrom']['sourceUrl'],'https://example.com/early')
        self.assertNotIn('modelTimeline',rows[3])
        self.assertEqual([{k:v for k,v in x.items() if k!='modelTimeline'} for x in rows],before)
        self.assertEqual(apply_model_chronology(copy.deepcopy(rows)),rows)
        self.assertTrue(all(x.get('modelTimeline',{}).get('sortDate') for x in CAT['items'] if x.get('caseVisible') and not x.get('referenceOnly')))
    def test_genuine_frames_have_original_hashes_and_local_pixels(self):
        manifest=json.loads((ROOT/'site/detail-frames.json').read_text(encoding='utf8'))
        self.assertGreaterEqual(len(manifest['videos']),59)
        for src,row in manifest['videos'].items():
            self.assertEqual(hashlib.sha256((ROOT/'pelican-web'/src.lstrip('/')).read_bytes()).hexdigest(),row['sourceSha256'])
            self.assertEqual(len({f['second'] for f in row['frames']}),len(row['frames']))
            for f in row['frames']:
                local=ROOT/'pelican-web'/f['src'].lstrip('/')
                self.assertEqual(hashlib.sha256(local.read_bytes()).hexdigest(),f['sha256'])
                with Image.open(local) as im:
                    self.assertEqual(im.size,(row['width'],row['height']))
                    self.assertEqual(hashlib.sha256(im.convert('RGB').tobytes()).hexdigest(),f['pixelSha256'])
                self.assertTrue(0<f['second']<row['duration'])
        self.assertGreaterEqual(len(manifest['animations']),41)
        for src,row in manifest['animations'].items():
            original=ROOT/'pelican-web'/src.lstrip('/')
            self.assertEqual(hashlib.sha256(original.read_bytes()).hexdigest(),row['sourceSha256'])
            with Image.open(original) as source:
                self.assertGreater(source.n_frames,1)
                for f in row['frames']:
                    source.seek(f['frameIndex'])
                    local=ROOT/'pelican-web'/f['src'].lstrip('/')
                    self.assertEqual(hashlib.sha256(local.read_bytes()).hexdigest(),f['sha256'])
                    with Image.open(local) as frame:
                        self.assertEqual(frame.size,source.size)
                        self.assertEqual(frame.convert('RGBA').tobytes(),source.convert('RGBA').tobytes())
                        self.assertEqual(hashlib.sha256(frame.convert('RGB').tobytes()).hexdigest(),f['pixelSha256'])
        self.assertEqual(apply_detail_frames(copy.deepcopy(CAT['items']),ROOT/'public-site'),CAT['items'])
    def test_bilingual_timeline_and_detail_gallery(self):
        timeline=[x for x in CAT['items'] if x.get('timelineVisible') and not x.get('referenceOnly')]
        for prefix in ['', 'en/']:
            soup=BeautifulSoup((ROOT/'public-site'/prefix/'timeline/index.html').read_text(encoding='utf8'),'html.parser')
            self.assertFalse(soup.select_one('[data-model-collapse]').has_attr('checked'))
            expected=[x['path'] for x in ordered_timeline(timeline)[:24]]
            actual=[a['href'].removeprefix('/en') for a in soup.select('[data-results] .card-cover')]
            self.assertEqual(actual,expected)
            for item in CAT['items']:
                if not item.get('detailFrames'):continue
                page=BeautifulSoup((ROOT/'public-site'/prefix/item['path'].lstrip('/')/'index.html').read_text(encoding='utf8'),'html.parser')
                self.assertTrue(page.select_one('.detail-layout [data-detail-carousel]'),item['id'])
                self.assertTrue(page.select_one('.detail-layout > .facts'),item['id'])
                for frame in item['detailFrames']:
                    self.assertTrue(page.select_one('.detail-layout img[src="'+frame['src']+'"]'),item['id'])
                    self.assertIn(str(frame['second'])+' s' if 'second' in frame else str(frame['frameIndex']),page.select_one('.detail-layout').get_text())
    def test_all_works_matches_release_order_and_month_headings_are_date_only(self):
        works=[x for x in CAT['items'] if x.get('caseVisible') and not x.get('referenceOnly')]
        for prefix in ['', 'en/']:
            page=BeautifulSoup((ROOT/'public-site'/prefix/'specimens/index.html').read_text(encoding='utf8'),'html.parser')
            actual=[a['href'].removeprefix('/en') for a in page.select('[data-results] .card-cover')]
            self.assertEqual(actual,[x['path'] for x in ordered_timeline(works)[:24]])
            timeline=BeautifulSoup((ROOT/'public-site'/prefix/'timeline/index.html').read_text(encoding='utf8'),'html.parser')
            for section in timeline.select('[data-release-month]'):
                if section['data-release-month']!='unknown':
                    self.assertEqual(section.select_one('.month-title h2').get_text(),section['data-release-month'])
            self.assertFalse(timeline.select('[data-year="unknown"]'))
            self.assertFalse(timeline.select('[data-release-month="unknown"]'))
            self.assertNotIn('Release date unverified' if prefix else '发布时间待核',timeline.select_one('[data-browser]').get_text())
        self.assertEqual(CAT['worksSortBasis'],'model-release')

if __name__=='__main__':unittest.main()
