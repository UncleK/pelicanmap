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
from generation_scope import DIRECT_VIDEO_IDS
from archival_test_assertions import reviewed_video_context_change, reviewed_swe_motion_restoration, reviewed_swe_addition_restoration

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
        # Historical intake may renumber the public display index. Archive IDs,
        # original facts and media still have to match the pre-chronology snapshot.
        strip=lambda x:{k:v for k,v in x.items() if k not in {'modelTimeline','detailFrames','caseNumber'}}
        old={x['id']:x for x in before['items']}
        additions=json.loads((ROOT/'site/additions.json').read_text(encoding='utf8'))
        prior_additions=json.loads((ROOT/'pelican-archive/research/2026-10-02-model-release-order/additions-before.json').read_text(encoding='utf8'))
        current_additions={x['id']:x for x in additions}
        previous_additions={x['id']:x for x in prior_additions}
        self.assertEqual(len(current_additions),len(additions))
        self.assertLessEqual(set(previous_additions),set(current_additions))
        for key,previous in previous_additions.items():
            if not reviewed_swe_addition_restoration(self,previous,current_additions[key]):self.assertEqual(current_additions[key],previous,key)
        newly_reviewed=set(current_additions)-set(previous_additions)
        self.assertEqual({x['id'] for x in CAT['items']},set(old)|newly_reviewed)
        for item in CAT['items']:
            if item['id'] in newly_reviewed:
                raw=current_additions[item['id']]
                self.assertEqual(raw['unitType'],'single-model-output')
                self.assertTrue(raw['ingestion']['sourceChecked'])
                self.assertTrue(raw['ingestion']['imagesChecked'])
                self.assertTrue(raw['ingestion']['evidence'])
                self.assertEqual(len(raw['reviewedModelNames']),1)
                for key in ['id','model','author','date','sourceUrl','media','rights']:
                    self.assertEqual(item[key],raw[key],(item['id'],key))
                continue
            previous=old[item['id']]
            if item['id'] in DIRECT_VIDEO_IDS:
                for key,value in previous.items():
                    if key in {'modelTimeline','detailFrames','caseNumber'}:continue
                    if reviewed_video_context_change(self,previous,item,key,{x['id']:x for x in CAT['items']}):continue
                    self.assertEqual(item[key],value,(item['id'],key))
                continue
            if item['id']!=HISTORY_ID:
                for key,value in strip(previous).items():
                    if not reviewed_swe_motion_restoration(self,previous,item,key):self.assertEqual(item[key],value,(item['id'],key))
                self.assertEqual(set(strip(item))-set(strip(previous)), {'motionPreview','generationConditions'} if item['id'] in {'variora-swe-2-2026-09-22','variora-mimo-v2-6-flash-free-2026-09-22','variora-grok-4-7-2026-09-22','variora-gemini-3-8-flash-2026-09-20','variora-step-5-2026-09-20'} else set())
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
        current={x['id']:x for x in CAT['items']}
        self.assertEqual(CAT['counts']['records'],before['counts']['records']+len(newly_reviewed))
        for ident in DIRECT_VIDEO_IDS:
            self.assertTrue(old[ident]['caseVisible'] and old[ident]['timelineVisible'])
            self.assertFalse(current[ident]['caseVisible'] or current[ident]['timelineVisible'])
        self.assertEqual(CAT['counts']['cases'],before['counts']['cases']-4+sum(bool(current[key].get('caseVisible')) for key in newly_reviewed))
        self.assertEqual(CAT['counts']['timeline'],before['counts']['timeline']-4+sum(bool(current[key].get('timelineVisible')) for key in newly_reviewed))
        self.assertEqual(CAT['counts']['referenceRecords'],before['counts']['referenceRecords'])
        for key,previous in old.items():
            if key in DIRECT_VIDEO_IDS:
                continue  # Original facts and exact user-requested role checked above.
            self.assertEqual(current[key].get('caseVisible'),previous.get('caseVisible'),key)
            self.assertEqual(current[key].get('timelineVisible'),previous.get('timelineVisible'),key)
        numbered=sorted([x for x in CAT['items'] if x.get('caseVisible') and not x.get('referenceOnly')],key=lambda x:(x['date'],x['id']))
        self.assertEqual([x['caseNumber'] for x in numbered],list(range(1,len(numbered)+1)))
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

    def test_new_gist_label_uses_primary_release_without_changing_artwork_facts(self):
        rows=[{'id':'preview','date':'2026-06-10','model':'DiffusionGemma','modelNames':['DiffusionGemma']},
              {'id':'arena','date':'2026-05-01','model':'grok 4.3','modelNames':['grok 4.3']}]
        before=copy.deepcopy(rows)
        apply_model_chronology(rows)
        self.assertEqual(rows[0]['modelTimeline']['releaseDate'],'2026-06-10')
        self.assertEqual(rows[0]['modelTimeline']['sortBasis'],'documented-release')
        self.assertTrue(rows[0]['modelTimeline']['sourceUrl'].startswith('https://blog.google/'))
        # Later Bedrock availability is not Grok's first public release.
        self.assertNotIn('releaseDate',rows[1]['modelTimeline'])
        self.assertEqual(rows[1]['modelTimeline']['sortDate'],'2026-05')
        self.assertEqual(rows[1]['modelTimeline']['sortBasis'],'earliest-source-work')
        self.assertEqual([{k:v for k,v in x.items() if k!='modelTimeline'} for x in rows],before)

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
