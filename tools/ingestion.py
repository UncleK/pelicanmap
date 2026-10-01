"""Authenticated submissions and deterministic publication from trusted sources.

Remote HTML/JSON is data only. No submitted code, command or SVG is executed.
"""
import datetime as dt
import hashlib
import hmac
import http.client
import io
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
import ssl
import subprocess
import sys
import threading
import uuid
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit,urljoin
from PIL import Image,ImageStat
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
STATE=Path(os.environ.get('PELICAN_STATE','/srv/pelicanmap/state'))
CURRENT=Path(os.environ.get('PELICAN_CURRENT','/srv/pelicanmap/current'))
BASE='https://pelicanmap.aveniqa.com'
RAW='https://raw.githubusercontent.com/AzatJalilov/PelicanSdf/main/'
Image.MAX_IMAGE_PIXELS=32_000_000
SUBMISSION_LOCK=threading.Lock()

def atomic_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    os.chmod(temp,0o644)
    temp.replace(path)

def text(value,limit=1600):
    if not isinstance(value,str) or not value.strip() or len(value)>limit:raise ValueError('Missing or overlong text')
    if any(ord(c)<32 and c not in '\n\t' for c in value):raise ValueError('Control characters are not allowed')
    return value.strip()

def url(value):
    value=text(value,2000);p=urlsplit(value)
    if p.scheme!='https' or not p.hostname or p.username or p.password or p.port not in (None,443) or p.fragment:raise ValueError('Use a plain HTTPS URL without credentials or fragment')
    if p.hostname.lower() in {'localhost','localhost.localdomain'}:raise ValueError('Local addresses are not allowed')
    try:ipaddress.ip_address(p.hostname)
    except ValueError:pass
    else:raise ValueError('IP addresses are not allowed')
    if '\\' in value or re.search(r'%2f|%5c|%2e',p.path,re.I):raise ValueError('Encoded path separators are not allowed')
    return value

def validate(payload):
    keys={'sourceUrl','date','model','author','format','title','notes','media','prompt','unitType','modelToMediaVerified'}
    if not isinstance(payload,dict) or set(payload)-keys:raise ValueError('Unknown submission fields')
    p={k:payload.get(k) for k in keys}
    p['sourceUrl']=url(p['sourceUrl'])
    for k in ['model','author']:p[k]=text(p[k],180)
    for k in ['title','notes']:
        if not isinstance(p[k],dict) or set(p[k])!={'zh','en'}:raise ValueError(k+' requires zh and en')
        p[k]={lang:text(value,180 if k=='title' else 1600) for lang,value in p[k].items()}
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',text(p['date'],10)):raise ValueError('Date must use YYYY-MM-DD')
    day=dt.date.fromisoformat(p['date'])
    if day>dt.datetime.now(dt.timezone.utc).date() or day.year<1980:raise ValueError('Invalid or future source date')
    if p['format']!='svg':raise ValueError('This authenticated adapter supports static SVG previews only; other eligible media needs reviewed batch import or a verified source adapter')
    if p['unitType']!='single-model-output' or p['modelToMediaVerified'] is not True:raise ValueError('Explicit single-model output review is required')
    if not isinstance(p['media'],list) or len(p['media'])!=1:raise ValueError('One output per case; split compilations before submission')
    p['media']=[url(x) for x in p['media']]
    if len(set(p['media']))!=len(p['media']):raise ValueError('Duplicate images in submission')
    p['prompt']=text(p['prompt'],2000) if p['prompt'] else ''
    return p

def permitted(value):
    p=urlsplit(url(value))
    if p.hostname=='simonwillison.net' and re.fullmatch(r'/20\d\d/[A-Z][a-z]{2}/\d{1,2}/[a-z0-9-]+/',p.path) and not p.query:return
    if p.hostname=='static.simonwillison.net' and p.path.startswith('/static/') and not p.query:return
    if p.hostname=='raw.githubusercontent.com' and p.path.startswith('/AzatJalilov/PelicanSdf/main/') and not p.query:return
    raise ValueError('Source is outside the configured trust list')

class PinnedHTTPS(http.client.HTTPSConnection):
    def connect(self):
        addresses=socket.getaddrinfo(self.host,443,type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(x[4][0]).is_global for x in addresses):raise ValueError('Non-public source address')
        sock=socket.create_connection((addresses[0][4][0],443),self.timeout)
        self.sock=self._context.wrap_socket(sock,server_hostname=self.host)

def fetch(value,limit=4_000_000):
    for _ in range(4):
        permitted(value);p=urlsplit(value)
        conn=PinnedHTTPS(p.hostname,timeout=25,context=ssl.create_default_context())
        try:
            conn.request('GET',p.path+('?' + p.query if p.query else ''),headers={'User-Agent':'PelicanMap-Archive/1.0','Accept-Encoding':'identity'})
            response=conn.getresponse()
            if response.status in {301,302,303,307,308}:
                value=urljoin(value,response.getheader('Location',''));continue
            if response.status!=200:raise ValueError('Source returned HTTP '+str(response.status))
            length=response.getheader('Content-Length')
            if length and int(length)>limit:raise ValueError('Source exceeds size limit')
            content=response.read(limit+1)
            if len(content)>limit:raise ValueError('Source exceeds size limit')
            return content
        finally:conn.close()
    raise ValueError('Too many redirects')

def verify_source(p,fetcher=fetch):
    source=urlsplit(p['sourceUrl']);warning='';demo=''
    if source.hostname=='simonwillison.net':
        permitted(p['sourceUrl']);page=fetcher(p['sourceUrl']).decode('utf-8')
        expected=f'/{p["date"][:4]}/{dt.date.fromisoformat(p["date"]).strftime("%b")}/{int(p["date"][8:])}/'
        if not source.path.startswith(expected) or p['author']!='Simon Willison':raise ValueError('Source date or author does not match')
        soup=BeautifulSoup(page,'html.parser')
        if p['model'].casefold() not in soup.get_text(' ',strip=True).casefold():raise ValueError('Model label is not present in the original source')
        refs={urljoin(p['sourceUrl'],tag.get(attr,'')) for tag in soup.find_all(True) for attr in ['src','href'] if tag.get(attr)}
        if not set(p['media'])<=refs:raise ValueError('Preview is not linked by the original source')
        if any(urlsplit(u).hostname!='static.simonwillison.net' for u in p['media']):raise ValueError('Preview must be hosted by the source')
    elif source.hostname=='github.com':
        raise ValueError('DCC/SDF is eligible for the collection, but this source needs reviewed batch import or a verified adapter')
        match=re.fullmatch(r'/AzatJalilov/PelicanSdf/blob/main/data/results/([a-z0-9-]+)\.json',source.path)
        if not match or source.query:raise ValueError('Repository is outside the configured trust list')
        ident=match[1];record=json.loads(fetcher(RAW+'data/results/'+ident+'.json'))
        manifest=json.loads(fetcher(RAW+'data/manifest.json'))
        if 'results/'+ident+'.json' not in manifest:raise ValueError('Run is not in the published manifest')
        if record['id']!=ident or record['createdAt'][:10]!=p['date'] or record['model']!=p['model']:raise ValueError('Run identity, date or model does not match')
        if p['author']!='AzatJalilov / Pelican SDF' or p['format']!='3d':raise ValueError('Invalid repository attribution or format')
        if p['media']!=[RAW+'assets/thumbnails/'+ident+'.jpg']:raise ValueError('Preview does not belong to this run')
        warning='unverified' if record.get('status')=='unverified' else ''
        demo='https://pelican.vibe-overflow.com/result.html?id='+ident
    else:raise ValueError('Source is outside the configured trust list')
    return {'warning':warning,'demo':demo}

def verify_image(content):
    if len(content)>10_000_000:raise ValueError('Image exceeds 10 MB')
    with Image.open(io.BytesIO(content)) as im:
        if im.format not in {'PNG','JPEG','WEBP'} or getattr(im,'n_frames',1)!=1:raise ValueError('This source adapter decodes single-frame PNG/JPEG/WebP previews; other media uses reviewed import')
        im.verify()
    with Image.open(io.BytesIO(content)) as im:
        if min(im.size)<100 or max(im.size)>10000:raise ValueError('Preview dimensions are unsuitable')
        frame=im.convert('RGB');frame.thumbnail((1600,1200),Image.Resampling.LANCZOS)
        if max(ImageStat.Stat(frame).stddev)<3:raise ValueError('Blank image preview')
        return content

def make_record(p,provenance,images):
    ident='ingest-'+hashlib.sha256((p['sourceUrl']+'\n'+'\n'.join(sorted(p['media']))).encode()).hexdigest()[:16]
    path='/specimens/'+ident+'/'
    notes=dict(p['notes'])
    if provenance['warning']:
        notes['zh']+=' 原仓库标为 unverified，尚未独立复现。'
        notes['en']+=' The source marks this run unverified; it has not been independently reproduced.'
    labels={'svg':'静态 SVG','animation':'动画','3d':'三维作品','game':'游戏 / 交互','video':'视频'}
    media=[]
    for u,b in zip(p['media'],images):
        with Image.open(io.BytesIO(b)) as im:ext={'PNG':'.png','JPEG':'.jpg','WEBP':'.webp'}[im.format]
        media.append({'src':'/media/ingested/'+hashlib.sha256(b).hexdigest()+ext,'source':u,'caption':'原始来源预览','poster':''})
    return {'id':ident,'originalId':ident,'kind':'timeline','title':p['title']['zh'],'model':p['model'],'author':p['author'],'date':p['date'],'month':p['date'][:7],
      'notes':notes['zh'],'source':'community','sourceLabel':'社区记录','sourceUrl':p['sourceUrl'],'format':p['format'],'formatLabel':labels[p['format']],
      'originalForm':p['format'],'originalLevel':'','promptCategory':'','promptStatus':p['prompt'] or '原始逐条提示词未在目录中完整记录，请查看来源',
      'mediaStatus':'local','mediaNote':'','media':media,'thumbnail':media[0]['src'],'demoUrl':'','externalUrl':provenance['demo'],'sourceCodeUrl':'','interactive':False,
      'path':path,'url':BASE+path,'markdown':path+'index.md','updated':dt.datetime.now(dt.timezone.utc).date().isoformat(),'rights':'作品权利归原作者；本站收录不改变原作品许可。',
      'i18n':{'en':{'title':p['title']['en'],'notes':notes['en'],'promptStatus':p['prompt'] or 'The complete original prompt is not recorded here; consult the source.'}},
      'unitType':'single-model-output','reviewedModelNames':[p['model']],'modelClaimStatus':'source-reported-not-independently-authenticated',
      'ingestion':{'sourceChecked':True,'imagesChecked':True,'contentHashes':[hashlib.sha256(b).hexdigest() for b in images],'sourceVerification':provenance['warning'] or 'source-attributed'}}

def publish(p):
    import fcntl
    STATE.mkdir(parents=True,exist_ok=True)
    with (STATE/'publish.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        source=verify_source(p)
        images=[verify_image(fetch(u,10_000_000)) for u in p['media']]
        item=make_record(p,source,images)
        previous=CURRENT.resolve();catalog=json.loads((previous/'site/data/catalog.json').read_text(encoding='utf8'))
        if any(x['id']==item['id'] for x in catalog['items']):return {'status':'duplicate','recordUrl':item['url'],'recordId':item['id']}
        if any(x.get('sourceUrl')==item['sourceUrl'] and x.get('ingestion',{}).get('contentHashes')==item['ingestion']['contentHashes'] for x in catalog['items']):raise ValueError('Duplicate source and image content')
        release=previous.parent/(dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-auto')
        subprocess.run(['cp','-al',str(previous),str(release)],check=True)
        for m,image in zip(item['media'],images):
            dest=release/'site'/m['src'].lstrip('/');dest.parent.mkdir(parents=True,exist_ok=True)
            if not dest.exists():dest.write_bytes(image)
        os.environ['PELICAN_OUTPUT_DIR']=str(release/'site')
        import build_public_site as zh
        import build_english as en
        zh.OUT=release/'site';en.OUT=release/'site'
        zh.UPDATED=dt.datetime.now(dt.timezone.utc).date().isoformat();en.UPDATED=zh.UPDATED
        zh.build(items=catalog['items']+[item],prepare=False)
        en.build()
        for edition in ['', 'en/']:
            built=json.loads((release/'site'/edition/'data/catalog.json').read_text(encoding='utf8'))
            assert len(built['items'])==len(catalog['items'])+1
            assert (release/'site'/edition/item['path'].lstrip('/')/'index.html').exists()
            assert all(x['thumbnail'] for x in built['items'])
        # Generated files and media are read-only to the web services.
        subprocess.run(['chmod','-R','a+rX,go-w',str(release)],check=True)
        next_link=CURRENT.with_name('current.auto-next')
        next_link.symlink_to(release);next_link.replace(CURRENT)
        base_ids={zh.normalize(record,kind)['id'] for kind in ['gallery','timeline'] for record in zh.DATA[kind]}
        additions=[x for x in catalog['items']+[item] if x['id'] not in base_ids]
        atomic_json(STATE/'additions.json',additions)
        return {'status':'published','recordUrl':item['url'],'recordId':item['id'],'englishUrl':BASE+'/en'+item['path']}

def process_jobs():
    for marker in sorted((STATE/'pending').glob('*.job')):
        path=STATE/'jobs'/(marker.stem+'.json')
        job=json.loads(path.read_text(encoding='utf8'))
        if job['status'] not in {'queued','processing'}:
            marker.unlink(missing_ok=True);continue
        job['status']='processing';atomic_json(path,job)
        try:job.update(publish(validate(job['submission'])))
        except Exception as err:
            job.update(status='needs_review',error=str(err)[:250])
        job['finishedAt']=dt.datetime.now(dt.timezone.utc).isoformat();atomic_json(path,job)
        marker.unlink(missing_ok=True)
        print(json.dumps({'id':job['id'],'status':job['status']},ensure_ascii=False),flush=True)

class Handler(BaseHTTPRequestHandler):
    server_version='PelicanMap'
    def log_message(self,*args):pass
    def reply(self,status,data):
        encoded=json.dumps(data,ensure_ascii=False).encode()
        self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(encoded)));self.end_headers();self.wfile.write(encoded)
    def authorized(self):
        token=os.environ.get('PELICAN_INGEST_TOKEN','')
        return len(token)>=32 and hmac.compare_digest(self.headers.get('Authorization',''),'Bearer '+token)
    def do_GET(self):
        if not self.authorized():return self.reply(401,{'error':'Authentication required'})
        if self.path=='/api/v1/ingest/export':
            path=STATE/'additions.json';return self.reply(200,json.loads(path.read_text()) if path.exists() else [])
        match=re.fullmatch(r'/api/v1/ingest/([a-f0-9]{24})',self.path)
        if not match:return self.reply(404,{'error':'Unknown endpoint'})
        path=STATE/'jobs'/(match[1]+'.json')
        if not path.exists():return self.reply(404,{'error':'Unknown submission'})
        job=json.loads(path.read_text());job.pop('submission',None);self.reply(200,job)
    def do_POST(self):
        if not self.authorized():return self.reply(401,{'error':'Authentication required'})
        if self.path!='/api/v1/ingest':return self.reply(404,{'error':'Unknown endpoint'})
        if self.headers.get_content_type()!='application/json':return self.reply(415,{'error':'Use application/json'})
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=32768:return self.reply(413,{'error':'Request size must be 1–32768 bytes'})
            self.connection.settimeout(10)
            p=validate(json.loads(self.rfile.read(size)))
            ident=hashlib.sha256(json.dumps(p,sort_keys=True).encode()).hexdigest()[:24]
            path=STATE/'jobs'/(ident+'.json')
            with SUBMISSION_LOCK:
                if path.exists():job=json.loads(path.read_text())
                else:
                    if len(list((STATE/'jobs').glob('*.json')))>=10000:return self.reply(429,{'error':'Submission archive capacity reached'})
                    job={'id':ident,'status':'queued','receivedAt':dt.datetime.now(dt.timezone.utc).isoformat(),'submission':p};atomic_json(path,job)
                    (STATE/'pending'/(ident+'.job')).touch()
            return self.reply(202,{'id':ident,'status':job['status'],'statusUrl':'/api/v1/ingest/'+ident})
        except (ValueError,TypeError,KeyError) as err:return self.reply(400,{'error':str(err)[:200]})

if __name__=='__main__':
    if '--process' in sys.argv:process_jobs()
    else:
        (STATE/'jobs').mkdir(parents=True,exist_ok=True)
        (STATE/'pending').mkdir(parents=True,exist_ok=True)
        for path in (STATE/'jobs').glob('*.json'):
            if json.loads(path.read_text())['status'] in {'queued','processing'}:
                (STATE/'pending'/(path.stem+'.job')).touch()
        ThreadingHTTPServer(('127.0.0.1',48671),Handler).serve_forever()
