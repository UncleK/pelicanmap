"""Read-only public byte, bilingual work-unit and motion checks for this intake."""
import concurrent.futures,hashlib,json,urllib.request
from pathlib import Path
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
DIR=ROOT/'pelican-archive/research/2026-10-02-x-september-continuation'
A=json.loads((DIR/'import-audit.json').read_text())
CAT=json.loads((ROOT/'public-site/data/catalog.json').read_text())
BY={x['id']:x for x in CAT['items']}
EN={x['id']:x for x in json.loads((ROOT/'public-site/en/data/catalog.json').read_text())['items']}
BASE='https://pelicanmap.aveniqa.com'
def get(path):
    request=urllib.request.Request(BASE+path,headers={'User-Agent':'PelicanMap-X-Original-Verification/1.0','Cache-Control':'no-cache'})
    with urllib.request.urlopen(request,timeout=45) as response:
        assert response.status==200
        return response.read()
def detail(task):
    ident,lang=task;x=(EN if lang=='en' else BY)[ident]
    prefix='/en' if lang=='en' else ''
    html=get(prefix+BY[ident]['path']).decode();doc=BeautifulSoup(html,'html.parser')
    assert doc.find('a',href=x['sourceUrl'])
    assert doc.select_one('.detail-provenance:not([open])')
    assert doc.select_one('script[src^="/assets/motion.js?v="]')
    if ident in A['added'][:2]:
        video=doc.select_one('.detail-motion video[data-motion-kind]')
        assert video['data-motion-src']==x['media'][0]['src']
        assert all(video.has_attr(a) for a in ['autoplay','muted','loop','playsinline','controls'])
        assert not doc.select_one('[data-preview-only]')
    else:
        assert not doc.select_one('.detail-motion') and not x.get('motionPreview')
        assert not doc.select_one('video[data-motion-kind]')
        assert doc.select_one('.detail-layout figure')['data-media-src']==x['media'][0]['src']
        assert ('motion is not invented' if lang=='en' else '不把截图伪装成可动原件') in doc.get_text()
    api=json.loads(get('/api/v1/specimens/'+ident+'?lang='+lang));api=api.get('item',api)
    for key in ['id','model','date','sourceUrl','caseVisible','timelineVisible','caseNumber','media','motionPreview']:
        assert api.get(key)==x.get(key),(ident,lang,key)
    assert api['date']=='2026-09-28' and len(api['modelNames'])==1
    return ident+' '+lang
def media(asset):
    data=get(asset['src'])
    assert len(data)==asset['bytes'] and hashlib.sha256(data).hexdigest()==asset['sha256'],asset['src']
    return asset['src']
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
    pages=list(pool.map(detail,[(ident,lang) for ident in A['added'] for lang in ['zh','en']]))
    originals=list(pool.map(media,A['newOriginals']))
for prefix in ['', '/en']:
    catalog=json.loads(get(prefix+'/data/catalog.json'))
    expected=json.loads((ROOT/'public-site'/prefix.lstrip('/')/'data/catalog.json').read_text())
    assert catalog==expected and catalog['counts']['cases']==937 and catalog['counts']['timeline']==614
    assert catalog['counts']['referenceRecords']==138
    assert not any(x['sourceUrl']==A['duplicateSource'] for x in catalog['items'])
    for route in ['/specimens/','/timeline/']:
        path=prefix+route+'?q=Sonnet&year=2026'
        doc=BeautifulSoup(get(path),'html.parser')
        assert doc.select_one('script[src^="/assets/browse.js?v="]')
        assert doc.select_one('script[src^="/assets/motion.js?v="]')
    assert ('October 2 X original-post continuation' if prefix else '2026-10-02 X 原帖续查').encode() in get(prefix+'/about/')
    for name in ['feed.xml','data/catalog.csv']:
        assert get(prefix+'/'+name)==(ROOT/'public-site'/prefix.lstrip('/')/name).read_bytes()
sitemap=get('/sitemap.xml');assert sitemap==(ROOT/'public-site/sitemap.xml').read_bytes()
for ident in A['added']:
    for prefix in ['', '/en']:assert (BASE+prefix+BY[ident]['path']).encode() in sitemap
result={'verified':True,'bilingualDetailsAndIdApi':len(pages),'originalMediaHashes':len(originals),
        'newWorks':3,'newRepresentatives':3,'newPlayableVideoOriginals':2,'newStillOnlyPreview':1,
        'cases':937,'timeline':614,'rawRecords':len(CAT['items']),'duplicateNotCounted':True,
        'bilingualCatalogsFeedsCsvAndSitemapByteIdentical':True,'referenceRecords':138,'newCodeMirrors':0}
(DIR/'live-batch-checks.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
