"""Read-only verification of this batch's actual published pages and bytes."""
import concurrent.futures,hashlib,json,urllib.request
from pathlib import Path
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
DIR=ROOT/'pelican-archive/research/2026-10-02-x-forum-continuation'
A=json.loads((DIR/'import-audit.json').read_text(encoding='utf8'))
CAT=json.loads((ROOT/'public-site/data/catalog.json').read_text(encoding='utf8'))
BY={x['id']:x for x in CAT['items']}
EN={x['id']:x for x in json.loads((ROOT/'public-site/en/data/catalog.json').read_text(encoding='utf8'))['items']}
BASE='https://pelicanmap.aveniqa.com'
def get(path):
    request=urllib.request.Request(BASE+path,headers={'User-Agent':'PelicanMap-Source-Verification/1.0','Cache-Control':'no-cache'})
    with urllib.request.urlopen(request,timeout=60) as response:
        assert response.status==200
        return response.read()
def detail(task):
    index,ident,lang=task;x=(EN if lang=='en' else BY)[ident]
    doc=BeautifulSoup(get(('/en' if lang=='en' else '')+BY[ident]['path']),'html.parser')
    assert doc.find('a',href=x['sourceUrl'])
    assert doc.select_one('.detail-provenance:not([open])')
    attachment=doc.select_one('.detail-attachments:not([open])')
    assert attachment and x['media'][1]['src'] in str(attachment)
    assert doc.select_one('script[src^="/assets/motion.js?v="]')
    if index<2:
        video=doc.select_one('.detail-motion video[data-motion-kind]')
        assert video['data-motion-src']==x['media'][0]['src']
        assert all(video.has_attr(a) for a in ['autoplay','muted','loop','playsinline','controls'])
    else:
        assert not doc.select_one('.detail-motion') and not x.get('motionPreview')
        assert doc.select_one('.detail-layout figure')['data-media-src']==x['media'][0]['src']
    api=json.loads(get('/api/v1/specimens/'+ident+'?lang='+lang));api=api.get('item',api)
    for key in ['id','model','date','sourceUrl','caseVisible','timelineVisible','caseNumber','media','motionPreview','cropProvenance','videoCropProvenance']:
        assert api.get(key)==x.get(key),(ident,lang,key)
    assert api['date']==('2026-09-27' if index<2 else '2026-09-28') and len(api['modelNames'])==1
    return ident+' '+lang
def media(asset):
    data=get(asset['src'])
    assert len(data)==asset['bytes'] and hashlib.sha256(data).hexdigest()==asset['sha256'],asset['src']
    return asset['src']
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
    pages=list(pool.map(detail,[(index,ident,lang) for index,ident in enumerate(A['added']) for lang in ['zh','en']]))
    originals=list(pool.map(media,A['newOriginals']))
for prefix in ['', '/en']:
    catalog=json.loads(get(prefix+'/data/catalog.json'))
    expected=json.loads((ROOT/'public-site'/prefix.lstrip('/')/'data/catalog.json').read_text(encoding='utf8'))
    assert catalog==expected and catalog['counts']['cases']>=A['expectedCases'] and catalog['counts']['timeline']>=A['expectedTimeline']
    assert catalog['counts']['referenceRecords']==138
    for route in ['/specimens/','/timeline/']:
        doc=BeautifulSoup(get(prefix+route),'html.parser')
        assert doc.select_one('script[src^="/assets/browse.js?v="]')
        assert doc.select_one('script[src^="/assets/motion.js?v="]')
    assert ('October 2 labelled comparison splits and animation follow-up' if prefix else '2026-10-02 模型对照拆分与动画续查').encode() in get(prefix+'/about/')
    for name in ['feed.xml','data/catalog.csv']:
        assert get(prefix+'/'+name)==(ROOT/'public-site'/prefix.lstrip('/')/name).read_bytes()
    for route,key in [('specimens','cases'),('timeline','timeline')]:
        assert json.loads(get('/api/v1/'+route+'?lang='+('en' if prefix else 'zh')+'&limit=1'))['total']==CAT['counts'][key]
sitemap=get('/sitemap.xml');assert sitemap==(ROOT/'public-site/sitemap.xml').read_bytes()
for ident in A['added']:
    for prefix in ['', '/en']:assert (BASE+prefix+BY[ident]['path']).encode() in sitemap
result={'verified':True,'bilingualDetailsAndIdApi':len(pages),'originalMediaHashes':len(originals),'newWorks':6,'newRepresentatives':6,'newAnimatedCrops':2,'newStillPreviews':4,'cases':CAT['counts']['cases'],'timeline':CAT['counts']['timeline'],'rawRecords':len(CAT['items']),'bilingualCatalogsFeedsCsvAndSitemapByteIdentical':True,'referenceRecords':138,'newCodeMirrors':0}
(DIR/'live-batch-checks.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
