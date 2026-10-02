"""Read-only release checks; browser playback evidence is saved separately."""
import concurrent.futures
import hashlib
import json
import urllib.request
from collections import Counter
from pathlib import Path
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
DIR=ROOT/'pelican-archive/research/2026-10-02-motion-autoplay'
BASE='https://pelicanmap.aveniqa.com'
LOCAL=json.loads((ROOT/'public-site/data/catalog.json').read_text(encoding='utf8'))
EN={x['id']:x for x in json.loads((ROOT/'public-site/en/data/catalog.json').read_text(encoding='utf8'))['items']}

def get(path):
    request=urllib.request.Request(BASE+path,headers={'User-Agent':'PelicanMap-Autoplay-Verifier/1.0','Cache-Control':'no-cache'})
    with urllib.request.urlopen(request,timeout=45) as r:
        assert r.status==200
        return r.read()

def detail(task):
    prefix,item=task
    page=BeautifulSoup(get(prefix+item['path']),'html.parser')
    script=page.select_one('script[src^="/assets/motion.js?v="]')
    assert script,item['id']
    for video in page.select('figure[data-media-src] > video[data-motion-kind]'):
        assert video['data-motion-src'] in {m['src'] for m in item['media']}
        assert all(video.has_attr(key) for key in ['autoplay','muted','loop','playsinline','controls'])
        assert not video.has_attr('src')
    assert page.find('a',href=item['sourceUrl'])
    assert page.select_one('.detail-provenance:not([open])')
    if item['motionPreview']['type']=='iframe':
        frame=page.select_one('iframe[data-local-demo]')
        assert frame['src']==item['motionPreview']['src']
        assert 'allow-top-navigation' not in frame['sandbox']
    api=json.loads(get('/api/v1/specimens/'+item['id']+'?lang='+('en' if prefix else 'zh')))
    api=api.get('item',api)
    assert api['motionPreview']==item['motionPreview']
    assert api['media']==(EN[item['id']]['media'] if prefix else item['media'])
    return prefix+item['id']

def main():
    before=json.loads((DIR/'before-catalog.json').read_text(encoding='utf8'))
    # Reviewed intake may append works and renumber chronological display labels,
    # but must preserve the originals verified at the autoplay release.
    for key in ['cases','timeline']:
        assert LOCAL['counts'][key]>=before['counts'][key]
    assert LOCAL['counts']['referenceRecords']==before['counts']['referenceRecords']
    old={x['id']:x for x in before['items']}
    current={x['id']:x for x in LOCAL['items']}
    assert set(old)<=set(current)
    for ident,item in old.items():
        for key,value in item.items():
            if ident=='x-keth-space-bunny-alpha-animation-2026-09-30' and key in {'caseRole','caseVisible','timelineVisible','caseReview'}:
                reviewed=current[ident]
                assert reviewed['caseRole']=='context' and not reviewed['caseVisible'] and not reviewed['timelineVisible']
                assert "user's direct request on 2026-10-02" in reviewed['caseReview']['reason']
                continue
            if key!='caseNumber':assert current[ident][key]==value,(ident,key)
    prior_additions=json.loads((DIR/'before-additions.json').read_text())
    additions={x['id']:x for x in json.loads((ROOT/'site/additions.json').read_text())}
    for item in prior_additions:assert additions.get(item['id'])==item,item['id']
    for prefix in ['', '/en']:
        expected=json.loads((ROOT/'public-site'/prefix.lstrip('/')/'data/catalog.json').read_text(encoding='utf8'))
        live=json.loads(get(prefix+'/data/catalog.json'))
        assert live==expected
        for endpoint,count in [('specimens',LOCAL['counts']['cases']),('timeline',LOCAL['counts']['timeline'])]:
            api=json.loads(get('/api/v1/'+endpoint+'?limit=1&lang='+('en' if prefix else 'zh')))
            assert api['total']==count and api['rawRecords']==count
        for route in ['/specimens/','/timeline/','/play/']:
            page=BeautifulSoup(get(prefix+route),'html.parser')
            assert page.select_one('script[src^="/assets/motion.js?v="]')
        assert get(prefix+'/feed.xml')==(ROOT/'public-site'/prefix.lstrip('/')/'feed.xml').read_bytes()
        assert get(prefix+'/data/catalog.csv')==(ROOT/'public-site'/prefix.lstrip('/')/'data/catalog.csv').read_bytes()
        assert ('automatic motion previews' if prefix else '动态预览自动播放').encode() in get(prefix+'/about/')
    for name in ['site.css','site.js','browse.js','motion.js']:
        source=(ROOT/'site/assets'/name).read_bytes()
        version=hashlib.sha256(source).hexdigest()[:12]
        assert get('/assets/'+name+'?v='+version)==source,name
    assert get('/sitemap.xml')==(ROOT/'public-site/sitemap.xml').read_bytes()
    selected=[x for x in LOCAL['items'] if x.get('caseVisible') and x.get('motionPreview') and not x.get('referenceOnly')]
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        checked=list(pool.map(detail,[(prefix,x) for prefix in ['', '/en'] for x in selected]))
    coverage=dict(Counter(x['motionPreview']['type'] for x in selected))
    result={'verified':True,'cases':LOCAL['counts']['cases'],'timeline':LOCAL['counts']['timeline'],
            'rawRecords':len(LOCAL['items']),'movingCoverTypes':coverage,'bilingualDetailsAndIdApi':len(checked),
            'existingFieldsPreservedExceptChronologicalNumbers':True,'existingAdditionsPreserved':True,
            'originalMediaUnchanged':True,'additionalRecordsSinceAutoplayRelease':len(current)-len(old),
            'sharedAssetsByteIdentical':4}
    (DIR/'live-autoplay-checks.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))

if __name__=='__main__':main()
