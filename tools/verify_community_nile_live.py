"""Verify published batch pages, original bytes and read-only API units."""
import concurrent.futures,hashlib,json,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DIR=ROOT/'pelican-archive/research/2026-10-01-evening-discovery'
AUDIT=json.loads((DIR/'import-audit.json').read_text())
CAT=json.loads((ROOT/'site/catalog.json').read_text())
BY={x['id']:x for x in CAT['items']}
BASE='https://pelicanmap.aveniqa.com'
def get(path):
    request=urllib.request.Request(BASE+path,headers={'User-Agent':'PelicanMap-Source-Batch-Verification/1.0'})
    with urllib.request.urlopen(request,timeout=60) as response:return response.read()
def detail(task):
    ident,language=task;x=BY[ident];prefix='/en' if language=='en' else ''
    html=get(prefix+x['path']).decode()
    assert x['sourceUrl'] in html and x['media'][0]['src'] in html,(ident,language,'missing original')
    item=json.loads(get('/api/v1/specimens/'+ident+'?lang='+language))
    if 'item' in item:item=item['item']
    assert item['id']==ident and item['caseVisible'] and item['timelineVisible']==x['timelineVisible'],(ident,language,'API unit')
    if ident.startswith('linuxdo-2891201-'):assert 'data-detail-primary="media"' in html and not item['timelineVisible']
    return ident+' '+language
def media(asset):
    assert hashlib.sha256(get(asset['src'])).hexdigest()==asset['sha256'],asset['src']
    return asset['src']
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
    pages=list(pool.map(detail,[(x,lang) for x in AUDIT['added'] for lang in ['zh','en']]))
    media_checks=list(pool.map(media,AUDIT['newOriginals']))
for name,expected in [('specimens',CAT['counts']['cases']),('timeline',CAT['counts']['timeline'])]:
    for lang in ['zh','en']:
        response=json.loads(get('/api/v1/'+name+'?limit=1&lang='+lang))
        assert response['total']==expected and response['rawRecords']==expected,(name,lang)
for prefix in ['', '/en']:
    html=get(prefix+'/about/').decode()
    assert ('2026-10-02 社区动画与原文拆分' if not prefix else 'October 2 community animation and source splitting') in html
audit={'pagesAndIdApi':len(pages),'newOriginalHashes':len(media_checks),'cases':CAT['counts']['cases'],'timeline':CAT['counts']['timeline'],'newCases':45,'newRepresentatives':15,'benchmarkReferenceRecords':CAT['counts']['referenceRecords'],'verified':True}
(DIR/'live-batch-checks.json').write_text(json.dumps(audit,indent=2)+'\n')
print(json.dumps(audit))
