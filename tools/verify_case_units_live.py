"""Read-only published artwork-unit and evolution-axis acceptance checks."""
import concurrent.futures
import json
import urllib.request
from pathlib import Path
from live_http import live_urlopen
from bs4 import BeautifulSoup
from model_chronology import ordered_timeline

ROOT=Path(__file__).resolve().parents[1]
BASE='https://pelicanmap.aveniqa.com'
LOCAL=json.loads((ROOT/'site/catalog.json').read_text(encoding='utf8'))


def get(path):
    req=urllib.request.Request(BASE+path,headers={'User-Agent':'PelicanMap-CaseUnitVerifier/1.0'})
    with live_urlopen(req,timeout=40) as response:
        assert response.status==200,path
        return response.read()


def data(path):
    return json.loads(get(path))


catalog=data('/data/catalog.json?case-units=20261001')
assert catalog==LOCAL,'Published catalog differs from the approved local build'
by={x['id']:x for x in catalog['items']}
parent='reddit-emu001-codex-pelican-matrix-2026-09-26'
members=[x for x in catalog['items'] if x.get('parentId')==parent]
assert len(members)==35 and sum(x['timelineVisible'] for x in members)==7
assert all(x['caseVisible'] and x['caseNumber'] for x in members)


def detail_check(pair):
    item,lang=pair
    prefix='/en' if lang=='en' else ''
    page=BeautifulSoup(get(prefix+item['path']),'html.parser')
    comparison=page.select_one('[data-setting-comparison]')
    assert len(comparison.select('figure'))==5,item['id']
    assert len(page.select('.detail-gallery img'))>=2,item['id']
    assert page.find('img',src=item['cropProvenance']['original']),item['id']
    api=data('/api/v1/specimens/'+item['id']+'?lang='+lang)
    assert api['id']==item['id'] and api['caseNumber']==item['caseNumber']
    assert api['timelineVisible']==item['timelineVisible']
    return item['id']+':'+lang


with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
    verified=list(pool.map(detail_check,[(x,lang) for x in members for lang in ['zh','en']]))

for lang in ['zh','en']:
    prefix='/en' if lang=='en' else ''
    all_cases=data('/api/v1/specimens?lang='+lang+'&limit=1')
    assert all_cases['total']==catalog['counts']['cases']
    timeline=data('/api/v1/timeline?lang='+lang+'&limit=1')
    assert timeline['total']==catalog['counts']['timeline']
    family=data('/api/v1/timeline?lang='+lang+'&family=Gemini&sort=oldest&limit=50')
    assert family['items'] and all(x['modelNames'] and len(x['modelNames'])==1 for x in family['items'])
    assert all('Gemini' in x['modelFamilies'] and x['timelineVisible'] for x in family['items'])
    assert family['items']==ordered_timeline(family['items'],'oldest')
    assert family['sortBasis']=='model-release'
    elo=data('/api/v1/specimens/elo-june-2025-3ea5a875?lang='+lang)
    assert not elo['caseVisible'] and elo['caseNumber'] is None and len(elo['childIds'])==22
    page=BeautifulSoup(get(prefix+'/specimens/elo-june-2025-3ea5a875/'),'html.parser')
    assert len(page.select('.detail-gallery img'))==15
    assert all(page.find('a',href=prefix+by[ident]['path']) for ident in elo['childIds'])
    timeline_page=BeautifulSoup(get(prefix+'/timeline/'),'html.parser')
    assert timeline_page.select_one('select[name=family]')
    for card in timeline_page.select('[data-results] .timeline-card'):
        assert len(card.select('img'))==1 and not card.select('.card-body,.media-label')
        path=card.select_one('.card-cover')['href']
        item=next(x for x in catalog['items'] if path.endswith(x['path']))
        assert card.select_one('.case-number').get_text()=='#'+str(item['caseNumber'])
    context=BeautifulSoup(get(prefix+'/collections/source-records/'),'html.parser')
    assert context.find('a',href=prefix+'/specimens/elo-june-2025-3ea5a875/')

assert data('/data/collecting-policy.json')==json.loads((ROOT/'site/collecting-policy.json').read_text(encoding='utf8'))
print(json.dumps({'cases':catalog['counts']['cases'],'timeline':catalog['counts']['timeline'],
                  'raw_records':catalog['counts']['records'],'matrix_cases':35,'matrix_timeline':7,
                  'bilingual_matrix_details_and_id_api':len(verified),'june_model_panels':22,
                  'family_chronology_reference_exclusion':'passed','published_catalog':'byte-content identical'}))
