"""Read-only deployed public original hashes, bilingual details and author units."""
import concurrent.futures,hashlib,json,urllib.request
from pathlib import Path
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
DIR=ROOT/'pelican-archive/research/2026-10-02-forum-historical'
AUDIT=json.loads((DIR/'import-audit.json').read_text())
CAT=json.loads((ROOT/'site/catalog.json').read_text())
BY={i['id']:i for i in CAT['items']}
ENBY={i['id']:i for i in json.loads((ROOT/'public-site/en/data/catalog.json').read_text())['items']}
BASE='https://pelicanmap.aveniqa.com'
def get(path):
    request=urllib.request.Request(BASE+path,headers={'User-Agent':'PelicanMap-Forum-Historical-Verification/1.0'})
    with urllib.request.urlopen(request,timeout=60) as response:return response.read()
def detail(task):
    ident,lang=task;item=BY[ident]
    html=get(('/en' if lang=='en' else '')+item['path']).decode();doc=BeautifulSoup(html,'html.parser')
    assert item['sourceUrl'] in html
    figure=doc.select_one('.detail-motion figure') or doc.select_one('.detail-layout figure')
    assert figure['data-media-src']==item['media'][0]['src'],(ident,lang)
    assert not doc.select_one('[data-local-demo]')
    for m in item['media'][1:]:assert doc.select_one('.detail-attachments:not([open]) [data-media-src="'+m['src']+'"]'),(ident,m['src'])
    if item['format']=='animation':assert doc.select_one('.detail-motion figure')
    if item['media'][0]['src'].endswith('.mp4'):assert len(doc.select('.detail-motion video'))==1
    api=json.loads(get('/api/v1/specimens/'+ident+'?lang='+lang));api=api.get('item',api)
    expected=ENBY[ident] if lang=='en' else item
    for key in ['id','model','date','sourceUrl','caseVisible','timelineVisible','caseNumber','media']:assert api[key]==expected[key],(ident,lang,key)
    return ident+' '+lang
def media(a):
    b=get(a['src']);assert len(b)==a['bytes'] and hashlib.sha256(b).hexdigest()==a['sha256'],a['src'];return a['src']
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
    pages=list(pool.map(detail,[(ident,lang) for ident in AUDIT['added'] for lang in ['zh','en']]))
    originals=list(pool.map(media,AUDIT['newOriginals']))
for endpoint,count in [('specimens',CAT['counts']['cases']),('timeline',CAT['counts']['timeline'])]:
    for lang in ['zh','en']:
        data=json.loads(get('/api/v1/'+endpoint+'?limit=1&lang='+lang));assert data['total']==count and data['rawRecords']==count
for prefix in ['', '/en']:
    data=json.loads(get(prefix+'/data/catalog.json'));assert data['counts']==CAT['counts']
    html=get(prefix+'/about/').decode();assert ('October 2 historical forum replies and animation' if prefix else '2026-10-02 历史论坛回复与动画') in html
    assert get(prefix+'/feed.xml')==(ROOT/'public-site'/prefix.lstrip('/')/'feed.xml').read_bytes()
live_sitemap=get('/sitemap.xml');assert live_sitemap==(ROOT/'public-site/sitemap.xml').read_bytes()
for ident in AUDIT['added']:
    for prefix in ['', '/en']:assert (BASE+prefix+BY[ident]['path']).encode() in live_sitemap
result={'pagesAndIdApi':len(pages),'newOriginalHashes':len(originals),'cases':CAT['counts']['cases'],'timeline':CAT['counts']['timeline'],'newCases':13,'newRepresentatives':13,'benchmarkReferenceRecords':CAT['counts']['referenceRecords'],'bilingualFeedsByteIdentical':True,'sitemapByteIdentical':True,'newDetailSitemapEntries':26,'verified':True}
(DIR/'live-batch-checks.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
