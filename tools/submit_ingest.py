"""Submit a bilingual JSON case; credentials stay in .private/ingest.env."""
import json
import sys
import urllib.request
from pathlib import Path
from sync_ingest import BASE,token
def submit(payload):
    request=urllib.request.Request(BASE+'/api/v1/ingest',data=json.dumps(payload,ensure_ascii=False).encode(),headers={'Authorization':'Bearer '+token(),'Content-Type':'application/json','User-Agent':'PelicanMap-Maintainer/1.0'},method='POST')
    with urllib.request.urlopen(request,timeout=45) as response:return json.load(response)
if __name__=='__main__':
    print(json.dumps(submit(json.loads(Path(sys.argv[1]).read_text(encoding='utf8'))),ensure_ascii=False))
