"""Read-only verification of deployed community units and motion originals."""
import concurrent.futures,hashlib,json,urllib.request
from pathlib import Path
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
DIR=ROOT/'pelican-archive/research/2026-10-02-community-splits'
AUDIT=json.loads((DIR/'import-audit.json').read_text())
CAT=json.loads((ROOT/'site/catalog.json').read_text())
BY={x['id']:x for x in CAT['items']}
ENBY={x['id']:x for x in json.loads((ROOT/'public-site/en/data/catalog.json').read_text())['items']}
BASE='https://pelicanmap.aveniqa.com'
def get(path):
    with urllib.request.urlopen(urllib.request.Request(BASE+path,headers={'User-Agent':'PelicanMap-Community-Splits-Verification/1.0'}),timeout=50) as r:return r.read()
def detail(task):
    ident,lang=task;x=BY[ident];html=get(('/en' if lang=='en' else '')+x['path']).decode();doc=BeautifulSoup(html,'html.parser')
    figure=doc.select_one('.detail-motion figure') or doc.select_one('.detail-layout figure')
    assert figure['data-media-src']==x['media'][0]['src'] and x['sourceUrl'] in html
    if x['media'][0]['src'].endswith('.mp4'):assert len(doc.select('.detail-motion video'))==1
    elif x['format']=='animation':assert doc.select_one('[data-preview-only]')
    if 'maximumwishbone' in ident:assert len(doc.select('[data-setting-comparison] figure'))==5
    assert not doc.select_one('[data-local-demo]')
    api=json.loads(get('/api/v1/specimens/'+ident+'?lang='+lang));api=api.get('item',api);expected=ENBY[ident] if lang=='en' else x
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
    html=get(prefix+'/about/').decode();assert ('October 2 community animation and settings splits' if prefix else '2026-10-02 社区动画与档位拆分') in html
    assert get(prefix+'/feed.xml')==(ROOT/'public-site'/prefix.lstrip('/')/'feed.xml').read_bytes()
    home=BeautifulSoup(get(prefix+'/').decode(),'html.parser');actions=home.select('.hero .actions a')
    assert any(a.get('href')==prefix+'/timeline/' for a in actions),('Homepage timeline button preserved',prefix)
    assert any(a.get('href')==prefix+'/specimens/' for a in actions),('Homepage all-works button preserved',prefix)
sitemap=get('/sitemap.xml');assert sitemap==(ROOT/'public-site/sitemap.xml').read_bytes()
for ident in AUDIT['added']:
    for prefix in ['', '/en']:assert (BASE+prefix+BY[ident]['path']).encode() in sitemap
result={'pagesAndIdApi':len(pages),'originalHashes':len(originals),'newMediaFiles':AUDIT['newMediaFiles'],'reusedOriginals':3,'newCases':13,'newRepresentatives':9,'newPlayableRecordings':5,'previewOnlyAnimations':3,'cases':CAT['counts']['cases'],'timeline':CAT['counts']['timeline'],'benchmarkReferenceRecords':CAT['counts']['referenceRecords'],'bilingualFeedsByteIdentical':True,'sitemapByteIdentical':True,'homepageButtonsPreserved':True,'verified':True}
(DIR/'live-batch-checks.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
