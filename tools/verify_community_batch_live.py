"""Verify both new source-reviewed batches against the actual public release."""
import concurrent.futures,hashlib,json,urllib.request
from pathlib import Path
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
BASE='https://pelicanmap.aveniqa.com'
AUDIT=ROOT/'pelican-archive/research/2026-10-01-community-all-media'
X_AUDIT=ROOT/'pelican-archive/research/2026-10-01-x-browser-batch'
LOCAL=json.loads((ROOT/'site/catalog.json').read_text(encoding='utf8'))
manifest=json.loads((AUDIT/'approved-manifest.json').read_text(encoding='utf8'))['cases']+json.loads((X_AUDIT/'approved-manifest.json').read_text(encoding='utf8'))['cases']

def get(path):
 with urllib.request.urlopen(urllib.request.Request(BASE+path,headers={'User-Agent':'PelicanMap-CommunityVerifier/1.0'}),timeout=40) as r:
  assert r.status==200,path
  return r.read()
def data(path):return json.loads(get(path))
catalog=data('/data/catalog.json?community-batch=20261001')
assert catalog==LOCAL,'Live catalog not the approved build'
by={x['id']:x for x in catalog['items']}
entries=[by[c['id']] for c in manifest]
assert len(entries)==31 and sum(x['caseVisible'] for x in entries)==31
assert sum(x['timelineVisible'] for x in entries)==23
assert not any(x.get('referenceOnly') or x['interactive'] for x in entries)
assets={m['src']:m['sha256'] for x in entries for m in x['media']}
assert len(assets)==44
def verify_asset(pair):
 src,expected=pair
 live=get(src);local=(ROOT/'pelican-web'/src.lstrip('/')).read_bytes()
 assert live==local and hashlib.sha256(live).hexdigest()==expected,src
 return src
def verify_detail(pair):
 item,lang=pair;prefix='/en' if lang=='en' else ''
 soup=BeautifulSoup(get(prefix+item['path']),'html.parser')
 assert soup.html['lang']==('en' if lang=='en' else 'zh-CN')
 assert soup.find('a',href=item['sourceUrl'])
 assert soup.find('img',src=item['thumbnail'])
 api=data('/api/v1/specimens/'+item['id']+'?lang='+lang)
 assert api['caseVisible'] and api['timelineVisible']==item['timelineVisible']
 assert api['caseNumber']==item['caseNumber']
 if item.get('cropProvenance'):assert soup.find('img',src=item['cropProvenance']['original'])
 if item.get('modelRunGroup'):
  comparison=soup.select_one('[data-setting-comparison]')
  assert comparison and ('no timeline representative is guessed' if lang=='en' else '不擅自挑一张') in comparison.get_text()
 return item['id']+':'+lang
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
 media=list(pool.map(verify_asset,assets.items()))
 details=list(pool.map(verify_detail,[(x,lang) for x in entries for lang in ['zh','en']]))
for lang in ['zh','en']:
 assert data('/api/v1/specimens?lang='+lang+'&limit=1')['total']==catalog['counts']['cases']
 assert data('/api/v1/timeline?lang='+lang+'&limit=1')['total']==catalog['counts']['timeline']
 prefix='/en' if lang=='en' else ''
 about=BeautifulSoup(get(prefix+'/about/'),'html.parser').get_text()
 assert ('Public X originals' if lang=='en' else '2 个 X 公开原帖') in about
assert catalog['counts']['referenceRecords']==138
result={'cases':catalog['counts']['cases'],'timeline':catalog['counts']['timeline'],'records':catalog['counts']['records'],
 'newWorks':31,'newRepresentatives':23,'localOriginalAndCropFilesVerified':len(media),'bilingualDetailsAndIdApis':len(details),'referenceRecordsUnchanged':138}
(AUDIT/'live-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps(result))
