import json
import re
from pathlib import Path
from urllib.parse import unquote, urlparse
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'public-site'
DEMO=ROOT/'public-demos'
downloads=json.loads((ROOT/'site/downloads.json').read_text(encoding='utf-8'))
missing=set()
links=0
for file in OUT.rglob('*.html'):
    soup=BeautifulSoup(file.read_text(encoding='utf-8'),'html.parser')
    for tag in soup.select('[href], [src], [poster]'):
        for attr in ['href','src','poster']:
            value=tag.get(attr)
            if not value or value.startswith(('#','data:','mailto:')):
                continue
            url=urlparse(value)
            if url.netloc=='pelicanmap-demos.aveniqa.com':
                base=DEMO
            elif url.netloc in ['','pelicanmap.aveniqa.com']:
                base=OUT
            else:
                continue
            path=unquote(url.path)
            if path in ['/mcp'] or path in downloads:
                continue
            target=base/path.lstrip('/') if path.startswith('/') else file.parent/path
            if path.endswith('/'):
                target=target/'index.html'
            links+=1
            if not target.is_file():
                missing.add((str(file.relative_to(OUT)),value))
print(json.dumps({'checked':links,'missing':sorted(missing)},ensure_ascii=False,indent=2))
if missing:
    raise SystemExit(1)
