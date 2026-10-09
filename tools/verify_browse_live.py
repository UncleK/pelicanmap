"""Read-only checks for pagination, local embeds and newly archived original media."""
import concurrent.futures
import hashlib
import json
import urllib.request
import urllib.error
import time
from pathlib import Path
from live_http import live_urlopen
from urllib.parse import urlsplit
from bs4 import BeautifulSoup
from experiment_batches import group_records

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://pelicanmap.aveniqa.com'


def get(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'PelicanMap-Verifier/1.0'})
    for attempt in range(3):
        try:
            with live_urlopen(request, timeout=40) as response:
                assert response.status == 200
                return response.read(), dict(response.headers)
        except urllib.error.HTTPError:
            raise
        except (urllib.error.URLError, TimeoutError, OSError):
            if attempt == 2:
                raise
            time.sleep(attempt + 1)


catalog = json.loads(get(BASE+'/data/catalog.json')[0])
local = json.loads((ROOT/'site/catalog.json').read_text(encoding='utf8'))
assert {x['id'] for x in catalog['items']} == {x['id'] for x in local['items']}
ordered=sorted(group_records(catalog['items']),key=lambda x:(x['date'],x['id']))
assert [x['caseNumber'] for x in ordered]==list(range(1,catalog['counts']['cases']+1))
assert len({x['caseNumber'] for x in catalog['items'] if x.get('batch')})==1
play_ids = set()
for prefix in ['', '/en']:
    for path in ['/timeline/', '/specimens/', '/play/']:
        content, headers = get(BASE+prefix+path)
        page = BeautifulSoup(content, 'html.parser')
        assert page.select_one('[data-sort-toggle]') and page.select_one('[data-density-toggle]')
        assert page.select_one('select[name=year]') and page.select_one('[data-page-jump]')
        assert len(page.select('[data-pagination] a')) <= 2
        assert len(page.select('[data-results] .card')) <= 24
        for card in page.select('[data-results] .specimen-card'):
            assert [child['class'][0] for child in card.find_all(recursive=False)]==['card-cover','card-body','card-foot']
            assert card.select_one('.card-body')['tabindex']=='0'
            assert card.select_one('.case-number').get_text().startswith('#') or path=='/play/'
            assert card.select('.model-name') and not card.select('.card-foot a')
        if path == '/play/':
            for card in page.select('[data-results] .card'):
                href = card.select_one('.card-cover')['href']
                item = next(x for x in catalog['items'] if href.endswith(x['path']))
                assert item['interactive'] and urlsplit(item['demoUrl']).netloc == 'pelicanmap-demos.aveniqa.com'
                detail = BeautifulSoup(get(BASE+href)[0], 'html.parser')
                assert detail.select_one('iframe[data-local-demo]')['src'] == item['demoUrl']
                assert detail.select_one('a[href="#demo"]')
                play_ids.add(item['id'])
    home = BeautifulSoup(get(BASE+prefix+'/')[0], 'html.parser')
    assert int(home.select_one('[data-total-records]').get_text()) == catalog['counts']['cases']
english=json.loads(get(BASE+'/en/data/catalog.json')[0])
assert {x['id']:x['caseNumber'] for x in english['items']}=={x['id']:x['caseNumber'] for x in catalog['items']}

for prefix in ['', '/en']:
    batch=BeautifulSoup(get(BASE+prefix+'/collections/openenv-2026-07-29/')[0],'html.parser')
    assert len(batch.select('.batch-model'))==7 and not batch.select('.batch-model[open]')
    assert len(batch.select('[data-batch-sample]'))==139
    parent=json.loads(get(BASE+'/api/v1/specimens/batch-openenv-2026-07-29?lang='+('en' if prefix else 'zh'))[0])
    assert parent['isBatch'] and parent['batch']['total']==138 and parent['path']==prefix+'/collections/openenv-2026-07-29/'
    query='lang=en&q=OpenEnv%20independent%20sample' if prefix else 'lang=zh&q=OpenEnv%20%E7%8B%AC%E7%AB%8B%E6%A0%B7%E6%9C%AC'
    data=json.loads(get(BASE+'/api/v1/specimens?'+query)[0])
    assert data['total']==0 and data['rawRecords']==0
    index=BeautifulSoup(get(BASE+prefix+'/tags/benchmark/')[0],'html.parser')
    assert len(index.select('[data-benchmark-collection]'))==1
    # The user removed explanatory copy from the collection directory only.
    # The actual scored collection and model pages still disclose upstream scores.
    assert not index.select_one('.page-top p')
    assert not index.select_one('.benchmark-disclaimer')
    assert batch.select_one('.benchmark-disclaimer')
    disclaimer='Upstream outputs, not a Pelican Map ranking' if prefix else '上游输出，非本馆排名'
    assert disclaimer in batch.select_one('.benchmark-disclaimer').get_text()
    assert all(x.get('caseNumber') is None for x in catalog['items'] if x.get('referenceOnly'))
    assert parent['referenceOnly']
    assert catalog['counts']['referenceRecords']==138
    assert catalog['counts']['mainRecords']==catalog['counts']['cases']+catalog['counts']['contextRecords']

additions = json.loads((ROOT/'site/additions.json').read_text(encoding='utf8'))
media = {m['src'] for x in additions for m in x['media'] if m['src'].startswith('/media/')}
reference=json.loads(get(BASE+'/data/benchmark.json')[0])
assert reference==json.loads((ROOT/'site/benchmarks/openenv-2026-07-29.json').read_text(encoding='utf8'))
assert len(reference['rows'])==169
media.update(x[key] for x in reference['rows'] for key in ['localSvg','localPng'] if x.get(key))
overrides=json.loads((ROOT/'site/thumbnail-overrides.json').read_text(encoding='utf8'))
for language_catalog,prefix in [(catalog,''),(english,'/en')]:
    for original_id,override in overrides.items():
        item=next(x for x in language_catalog['items'] if x['originalId']==original_id)
        assert item['thumbnail']==override['poster']
        detail=BeautifulSoup(get(BASE+item['path'])[0],'html.parser')
        if override.get('type','source-video-frame')=='source-video-frame':
            assert detail.select_one('video')['poster']==override['poster']
        elif override.get('type')=='svg-render':
            assert detail.find('img',src=override['poster']) and detail.find('a',href=override['sourceSvg'])
        media.add(override['poster'])
from benchmark_reference import model_path
for prefix in ['', '/en']:
    for model in {x['model'] for x in reference['rows'] if x['config']=='default'}:
        page=BeautifulSoup(get(BASE+prefix+model_path(model))[0],'html.parser')
        assert len(page.select('.benchmark-representatives .benchmark-sample'))==2
        assert page.select_one('.benchmark-disclaimer')
        disclaimer='Upstream outputs, not a Pelican Map ranking' if prefix else '上游输出，非本馆排名'
        assert disclaimer in page.select_one('.benchmark-disclaimer').get_text()


def check_media(path):
    content, _ = get(BASE+path)
    original = (ROOT/'pelican-web'/path.lstrip('/')).read_bytes()
    assert hashlib.sha256(content).digest() == hashlib.sha256(original).digest(), path


with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
    list(pool.map(check_media, media))
for url in {x['demoUrl'] for x in catalog['items'] if x.get('interactive')}:
    content, _ = get(url)
    assert b'<html' in content.lower()
assert len(play_ids)==5,'Four legacy demos plus one verified restored interactive work'
assert 'variora-gemini-3-8-flash-2026-09-20' in play_ids
print(json.dumps({'cases': catalog['counts']['cases'], 'raw_records': len(catalog['items']), 'reference_records': catalog['counts']['referenceRecords'], 'benchmark_rows': len(reference['rows']), 'timeline': catalog['counts']['timeline'], 'playable_demos': len(play_ids), 'archived_media_byte_identical': len(media), 'bilingual_browse_and_local_iframes': 'passed', 'chronological_numbers_and_card_regions': 'passed'}))
