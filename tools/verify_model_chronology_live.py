"""Read-only release-axis, faithful supplementary gallery and export checks."""
import concurrent.futures
import csv
import hashlib
import io
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from live_http import live_urlopen
from bs4 import BeautifulSoup
from model_chronology import ordered_timeline, timeline_year

ROOT=Path(__file__).resolve().parents[1]
BASE='https://pelicanmap.aveniqa.com'
CAT=json.loads((ROOT/'site/catalog.json').read_text(encoding='utf8'))

def get(path,payload=None):
    headers={'User-Agent':'PelicanMap-ReleaseAxisVerifier/1.3'}
    if payload is not None:headers.update({'Content-Type':'application/json','Accept':'application/json, text/event-stream'})
    req=urllib.request.Request(BASE+path,headers=headers,data=json.dumps(payload).encode() if payload is not None else None)
    for attempt in range(3):
        try:
            with live_urlopen(req,timeout=40) as response:
                assert response.status==200,path
                return response.read()
        except urllib.error.HTTPError:raise
        except urllib.error.URLError:
            if attempt==2:raise
            time.sleep(attempt+1)

def data(path):return json.loads(get(path))

def main():
    timeline=[x for x in CAT['items'] if x.get('timelineVisible') and not x.get('referenceOnly')]
    assert data('/data/catalog.json?release-axis=20261002')==CAT
    assert data('/data/model-releases.json')==json.loads((ROOT/'site/model-releases.json').read_text(encoding='utf8'))
    for language,prefix in [('zh',''),('en','/en')]:
        localized=json.loads((ROOT/'public-site'/prefix.lstrip('/')/'data/catalog.json').read_text(encoding='utf8'))
        assert data(prefix+'/data/catalog.json?release-axis=20261002')==localized
        by={x['id']:x for x in localized['items']}
        for family in ['', 'Gemini','GPT']:
            for sort in ['oldest','newest']:
                for year in ['', '2025','2026','unknown']:
                    query=urllib.parse.urlencode({'lang':language,'family':family,'sort':sort,'year':year,'limit':50})
                    expected=[x for x in timeline if (not family or family in x['modelFamilies']) and (not year or (not x.get('modelTimeline',{}).get('releaseDate') if year=='unknown' else timeline_year(x)==year))]
                    actual=data('/api/v1/timeline?'+query)
                    assert actual['sortBasis']=='model-release'
                    assert actual['total']==len(expected),(language,family,sort,year)
                    assert actual['items']==[by[x['id']] for x in ordered_timeline(expected,sort)[:50]]
        for path in ['/timeline/','/timeline/2025/','/timeline/unknown/']:
            page=BeautifulSoup(get(prefix+path),'html.parser')
            assert not page.select_one('[data-model-collapse]').has_attr('checked')
            for asset in page.select('script[src]'):
                src=asset['src'].split('?')[0]
                if src.startswith('/assets/'):
                    assert get(asset['src'])==(ROOT/'public-site'/src.lstrip('/')).read_bytes()
            css=page.select_one('link[rel=stylesheet]')['href']
            assert get(css)==(ROOT/'public-site'/css.split('?')[0].lstrip('/')).read_bytes()
            assert 'Mobile page totals sit beside the listing title' in get(css).decode()
        for row in csv.DictReader(io.StringIO(get(prefix+'/data/catalog.csv').decode())):
            item=by[row['id']]
            assert row['date']==item['date']
            assert row['modelReleaseDate']==item.get('modelTimeline',{}).get('releaseDate','')
        for path in ['/llms.txt','/index.md','/feed.xml']:
            assert get(prefix+path)==(ROOT/'public-site'/prefix.lstrip('/')/path.lstrip('/')).read_bytes()
    for path in ['/openapi.json','/sitemap.xml']:
        assert get(path)==(ROOT/'public-site'/path.lstrip('/')).read_bytes()
    payload={'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':'get_timeline','arguments':{'family':'Gemini','sort':'oldest','limit':50}}}
    rpc=data('/api/v1/timeline?family=Gemini&sort=oldest&limit=50')
    result=json.loads(get('/mcp',payload))['result']
    structured=result.get('structuredContent') or json.loads(result['content'][0]['text'])
    assert structured==rpc
    frames={f['src']:f['sha256'] for x in CAT['items'] for f in x.get('detailFrames',[])}
    def frame_check(pair):
        src,sha=pair
        assert hashlib.sha256(get(src)).hexdigest()==sha,src
        return src
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        verified=list(pool.map(frame_check,frames.items()))
    detail_items=[x for x in CAT['items'] if x.get('detailFrames')]
    def detail_check(pair):
        item,prefix=pair
        page=BeautifulSoup(get(prefix+item['path']),'html.parser')
        gallery=page.select_one('.detail-layout [data-detail-carousel]')
        assert gallery and page.select_one('.detail-layout > .facts'),item['id']
        assert page.select_one('.detail-notes') if item.get('notes') else True
        for frame in item['detailFrames']:
            assert gallery.find('img',src=frame['src']),item['id']
            assert gallery.find('a',href=frame['sourceMedia']),item['id']
        if page.select_one('.detail-attachments'):
            assert not page.select_one('.detail-attachments').has_attr('open')
        assert page.find('a',href=item['sourceUrl'])
        return item['id']+prefix
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        details=list(pool.map(detail_check,[(x,p) for x in detail_items for p in ['','/en']]))
    print(json.dumps({'cases':CAT['counts']['cases'],'timeline':len(timeline),
                      'verified_release_timeline':sum(bool(x.get('modelTimeline',{}).get('releaseDate')) for x in timeline),
                      'pending_release_timeline':sum(not x.get('modelTimeline',{}).get('releaseDate') for x in timeline),
                      'supplemental_frame_hashes':len(verified),'bilingual_frame_galleries':len(details),
                      'api_mcp_release_axis_original_dates_exports':'passed'},ensure_ascii=False))

if __name__=='__main__':main()
