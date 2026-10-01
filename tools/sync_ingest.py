"""Preserve automatically published additions before a manual site build."""
import json
import urllib.request
from pathlib import Path
from catalog_policy import merge_additions
ROOT=Path(__file__).resolve().parents[1]
BASE='https://pelicanmap.aveniqa.com'
def token():
    return dict(line.split('=',1) for line in (ROOT/'.private/ingest.env').read_text().splitlines() if '=' in line)['PELICAN_INGEST_TOKEN']
def request(path,authenticated=False):
    headers={'User-Agent':'PelicanMap-Maintainer/1.0'}
    if authenticated:headers['Authorization']='Bearer '+token()
    return urllib.request.urlopen(urllib.request.Request(BASE+path,headers=headers),timeout=45).read()
def sync():
    remote=json.loads(request('/api/v1/ingest/export',True))
    path=ROOT/'site/additions.json'
    local=json.loads(path.read_text(encoding='utf8')) if path.exists() else []
    items=merge_additions(local,remote)
    for x in items:
        for media in x['media']:
            if not media['src'].startswith('/media/ingested/'):continue
            target=(ROOT/'pelican-web'/media['src'].lstrip('/')).resolve()
            assert target.is_relative_to((ROOT/'pelican-web/media/ingested').resolve())
            if not target.exists():
                target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(request(media['src']))
    (ROOT/'site/additions.json').write_text(json.dumps(items,ensure_ascii=False,indent=2),encoding='utf8')
    print('Synced additions:',len(items))
if __name__=='__main__':sync()
