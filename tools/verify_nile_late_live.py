"""Check the approved 44-work batch against the actual bilingual deployment."""
import concurrent.futures,hashlib,json,urllib.request
from pathlib import Path
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
BASE='https://pelicanmap.aveniqa.com'
AUDIT=ROOT/'pelican-archive/research/2026-10-01-nile-late'
MANIFEST=json.loads((AUDIT/'approved-manifest.json').read_text(encoding='utf8'))['cases']
LOCAL=json.loads((ROOT/'site/catalog.json').read_text(encoding='utf8'))

def get(path):
 with urllib.request.urlopen(urllib.request.Request(BASE+path,headers={'User-Agent':'PelicanMap-OriginalSourceVerifier/1.0'}),timeout=45) as r:
  assert r.status==200,path
  return r.read()
def data(path):return json.loads(get(path))
live=data('/data/catalog.json?original-source-batch=20261001-nile-late')
assert live==LOCAL,'Live catalog differs from approved local build'
by={x['id']:x for x in live['items']}
entries=[by[c['id']] for c in MANIFEST]
assert len(entries)==44 and sum(x['caseVisible'] for x in entries)==44
assert sum(x['timelineVisible'] for x in entries)==32
assert not any(x.get('referenceOnly') or x['interactive'] for x in entries)
assets={m['src']:m['sha256'] for x in entries for m in x['media']}
assert len(assets)==58

def verify_asset(pair):
 src,expected=pair;original=get(src)
 assert original==(ROOT/'pelican-web'/src.lstrip('/')).read_bytes(),src
 assert hashlib.sha256(original).hexdigest()==expected,src
 return src
def verify_detail(pair):
 item,lang=pair;prefix='/en' if lang=='en' else ''
 soup=BeautifulSoup(get(prefix+item['path']),'html.parser')
 assert soup.html['lang']==('en' if lang=='en' else 'zh-CN')
 assert soup.find('a',href=item['sourceUrl'])
 assert soup.find('img',src=item['thumbnail'])
 assert not soup.select('iframe')
 api=data('/api/v1/specimens/'+item['id']+'?lang='+lang)
 for key in ['caseVisible','timelineVisible','caseNumber','model','date','dateBasis','generationConditions']:
  assert api[key]==item[key],(item['id'],lang,key)
 if item.get('modelRunGroup'):
  block=soup.select_one('[data-setting-comparison]')
  assert block
  if item['comparisonType']=='visual-iterations':
   assert ('visual-feedback iterations' if lang=='en' else '视觉反馈迭代') in block.get_text()
  if not any(by[k]['timelineVisible'] for k in item['comparisonIds']):
   assert ('no timeline representative is guessed' if lang=='en' else '不擅自挑一张') in block.get_text()
 return item['id']+':'+lang
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
 media=list(pool.map(verify_asset,assets.items()))
 details=list(pool.map(verify_detail,[(x,lang) for x in entries for lang in ['zh','en']]))
for lang in ['zh','en']:
 assert data('/api/v1/specimens?lang='+lang+'&limit=1')['total']==live['counts']['cases']
 assert data('/api/v1/timeline?lang='+lang+'&limit=1')['total']==live['counts']['timeline']
 prefix='/en' if lang=='en' else ''
 about=BeautifulSoup(get(prefix+'/about/'),'html.parser').get_text()
 assert ('Forty-four works' if lang=='en' else '共 44 件作品') in about
 timeline=data('/api/v1/timeline?year=2025&family=GPT&lang='+lang+'&limit=50&sort=oldest')
 assert all(x['timelineVisible'] and len(x['modelNames'])==1 for x in timeline['items'])
 assert [(x['date'],x['id']) for x in timeline['items']]==sorted((x['date'],x['id']) for x in timeline['items'])
assert live['counts']['referenceRecords']==138
result={'cases':live['counts']['cases'],'timeline':live['counts']['timeline'],'records':live['counts']['records'],
 'newWorks':44,'newRepresentatives':32,'localOriginalFilesVerified':len(media),'bilingualDetailsAndIdApis':len(details),'referenceRecordsUnchanged':138}
(AUDIT/'live-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps(result))
