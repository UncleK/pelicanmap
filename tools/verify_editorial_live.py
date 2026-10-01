"""Verify published bilingual selection, SEO, counting exports and MCP guidance."""
import csv
import io
import json
import urllib.request
from pathlib import Path
from bs4 import BeautifulSoup
from editorial_content import FEATURED_IDS, CATALOG_VERSION, CSV_FIELDS, scope_sections

ROOT=Path(__file__).resolve().parents[1]
BASE='https://pelicanmap.aveniqa.com'
checks=0


def request(path,payload=None):
    global checks
    headers={'User-Agent':'PelicanMap-EditorialVerifier/1.3'}
    if payload is not None:headers.update({'Content-Type':'application/json','Accept':'application/json, text/event-stream'})
    req=urllib.request.Request(BASE+path,headers=headers,data=json.dumps(payload).encode() if payload is not None else None)
    with urllib.request.urlopen(req,timeout=40) as response:
        assert response.status==200,path
        checks+=1
        return response.read()


def rpc(method,params):
    return json.loads(request('/mcp',{'jsonrpc':'2.0','id':1,'method':method,'params':params}))['result']


for lang in ['zh','en']:
    prefix='/en' if lang=='en' else ''
    local=json.loads((ROOT/'public-site'/prefix.lstrip('/')/'data/catalog.json').read_text(encoding='utf8'))
    catalog=json.loads(request(prefix+'/data/catalog.json?editorial=20261001-v1'))
    assert catalog==local
    assert catalog['version']==CATALOG_VERSION
    by={x['id']:x for x in catalog['items']}
    home=BeautifulSoup(request(prefix+'/'),'html.parser')
    cards=home.select('#featured .specimen-card')
    assert len(cards)==6 and not home.select('#featured .source-archive-link')
    assert [x.select_one('.card-cover')['href'] for x in cards]==[by[key]['path'] for key in FEATURED_IDS]
    for card,key in zip(cards,FEATURED_IDS):
        assert card.select_one('img')['src']==by[key]['thumbnail']
        assert by[key]['caseVisible'] and by[key]['timelineVisible'] and by[key]['format']=='svg'
    schema=json.loads(home.select_one('script[type="application/ld+json"]').string)
    assert schema['mainEntity']['numberOfItems']==6
    assert int(home.select_one('[data-total-records]').get_text())==catalog['counts']['cases']
    for relative in ['about/','developers/','timeline/','specimens/','play/','sources/','collections/origins/','collections/beyond-svg/','collections/reading-the-test/','tags/benchmark/','timeline/1988/']:
        path=prefix+'/'+relative
        page=BeautifulSoup(request(path),'html.parser')
        assert page.html['lang']==('en' if lang=='en' else 'zh-CN'),path
        assert page.select_one('link[rel=canonical]')['href']==BASE+path,path
        assert {x['hreflang'] for x in page.select('link[hreflang]')}=={'zh-CN','en','x-default'}
        assert page.select_one('meta[property="og:image:alt"]'),path
        assert page.select_one('meta[name="twitter:image:alt"]'),path
        for stale in ['实验批次计 1 个','one per experiment batch','目录版本 1.1','Catalog version 1.1','counts are not a total of unique works']:
            assert stale not in page.get_text(),path
        if relative in ['about/','developers/']:
            for _,text in scope_sections(catalog['counts'],lang):assert text in page.get_text(' ',strip=True),path
        if relative=='timeline/1988/':
            assert page.select_one('meta[name=robots]')['content'].startswith('noindex')
            assert not page.select('[data-results] .card')
        if relative=='timeline/':
            for card in page.select('[data-results] .timeline-card'):
                row=card.select_one('.timeline-meta')
                assert [x['class'][0] for x in row.find_all(recursive=False)]==['case-number','timeline-model','timeline-date']
                assert row.select_one('time')['datetime']==row.select_one('time').get_text()
    for key in FEATURED_IDS:
        item=by[key]
        page=BeautifulSoup(request(item['path']),'html.parser')
        schema=json.loads(page.select_one('script[type="application/ld+json"]').string)
        assert schema['identifier']==key and schema['isBasedOn']==item['sourceUrl']
        assert schema['temporalCoverage']==item['date']
        assert not any(field in schema for field in ['dateCreated','datePublished','aggregateRating','additionalProperty'])
    guide_bytes=request(prefix+'/llms.txt')
    assert guide_bytes==(ROOT/'public-site'/prefix.lstrip('/')/'llms.txt').read_bytes(), 'Published Agent guide bytes differ'
    guide=guide_bytes.decode()
    assert 'caseVisible' in guide and 'referenceOnly' in guide and 'datePrecision' in guide
    raw_csv=request(prefix+'/data/catalog.csv').decode()
    reader=csv.DictReader(io.StringIO(raw_csv));rows=list(reader)
    assert reader.fieldnames==CSV_FIELDS and len(rows)==catalog['counts']['records']
    assert sum(x['caseVisible']=='true' and x['referenceOnly']!='true' for x in rows)==catalog['counts']['cases']
    assert sum(x['timelineVisible']=='true' for x in rows)==catalog['counts']['timeline']
    for endpoint,count in [('specimens',catalog['counts']['cases']),('timeline',catalog['counts']['timeline'])]:
        value=json.loads(request('/api/v1/'+endpoint+'?lang='+lang+'&limit=1'))
        assert value['version']==CATALOG_VERSION and value['total']==count

api=json.loads(request('/openapi.json'))
assert api==json.loads((ROOT/'public-site/openapi.json').read_text(encoding='utf8'))
assert api['info']['version']==CATALOG_VERSION
sitemap=request('/sitemap.xml').decode()
assert '/timeline/1988/' not in sitemap
init=rpc('initialize',{'protocolVersion':'2025-03-26','capabilities':{},'clientInfo':{'name':'editorial-live-check','version':'1'}})
assert init['serverInfo']['version']==CATALOG_VERSION
assert all(text in init['instructions'] for text in ['counts.cases','counts.timeline','datePrecision','referenceOnly','not independently authenticated'])
resources=rpc('resources/list',{})['resources']
assert {x['uri'] for x in resources}=={BASE+'/llms.txt',BASE+'/en/llms.txt'}
for resource in resources:
    guide=rpc('resources/read',{'uri':resource['uri']})['contents'][0]['text']
    assert str(catalog['counts']['cases'])+' independent works' in guide and str(catalog['counts']['timeline'])+' timeline representatives across media, a subset' in guide
    assert 'referenceOnly' in guide and 'Records overlap' not in guide
print(json.dumps({'published_editorial_checks':checks,'bilingual_selection':6,'catalog_version':CATALOG_VERSION,
                  'case_count':catalog['counts']['cases'],'timeline_subset':catalog['counts']['timeline'],'seo_language_schema':True,'csv_counting_flags':True,'llms_and_mcp_scope':True,'legacy_1988_stale_cards':0}))
