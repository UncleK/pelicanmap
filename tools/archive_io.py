"""Small cached HTTP helpers shared by archive maintenance scripts."""
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlsplit
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import mimetypes

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'pelican-web'
AUDIT = ROOT / 'pelican-archive/audit/2026-09-27'
MANIFEST = AUDIT / 'retrieval.json'

def records():
    return {x['url']: x for x in json.loads(MANIFEST.read_text(encoding='utf-8'))}

def fetch_batch(jobs, kind='source', media=False):
    known = records()
    existing_media = {}
    if media:
        for p in (WEB / 'media').rglob('*'):
            if p.is_file():
                existing_media.setdefault(hashlib.sha256(p.read_bytes()).hexdigest(), p)
    def get(url):
        old = known.get(url)
        if old and old.get('status') == 200 and (ROOT / old['file']).exists() and (not media or old.get('kind') == 'media'):
            return old
        result = {'url': url, 'kind': 'media' if media else kind}
        try:
            with urlopen(Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=30) as res:
                payload = res.read(100 * 1024 * 1024 + 1)
                if len(payload) > 100 * 1024 * 1024:
                    raise ValueError('Response exceeds the 100 MiB per-file limit')
                ctype = res.headers.get_content_type()
                if media and not (ctype.startswith(('image/', 'video/')) or payload.lstrip().startswith((b'<svg', b'<?xml'))):
                    raise ValueError('Expected image/video, received ' + ctype)
                ext = {'text/html': '.html', 'application/json': '.json', 'image/jpeg': '.jpg', 'image/svg+xml': '.svg', 'video/mp4': '.mp4'}.get(ctype)
                if not ext:
                    ext = mimetypes.guess_extension(ctype) or Path(urlsplit(url).path).suffix or '.bin'
                folder = WEB / 'media/recovered' if media else AUDIT / 'sources'
                folder.mkdir(parents=True, exist_ok=True)
                digest = hashlib.sha256(payload).hexdigest()
                path = existing_media.get(digest) if media else None
                if path is None:
                    path = folder / (hashlib.sha256(url.encode()).hexdigest()[:20] + ext)
                    path.write_bytes(payload)
                result.update(status=res.status, content_type=ctype, bytes=len(payload), final_url=res.url, file=path.relative_to(ROOT).as_posix(), sha256=digest)
        except Exception as exc:
            result.update(status=getattr(exc, 'code', None), error=str(exc))
        return result
    urls = list(dict.fromkeys(jobs))
    output = {}
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(get, u) for u in urls]
        for n, future in enumerate(as_completed(futures), 1):
            result = future.result()
            output[result['url']] = result
            known[result['url']] = result
            if n % 20 == 0 or result.get('error'):
                print(f'{kind}: {n}/{len(urls)} {result["url"]}: {result.get("error") or result["status"]}', flush=True)
    latest = records()
    latest.update(output)
    MANIFEST.write_text(json.dumps(list(latest.values()), ensure_ascii=False, indent=2), encoding='utf-8')
    return output

def text_for(url):
    row = records().get(url)
    return (ROOT / row['file']).read_text(encoding='utf-8', errors='replace') if row and row.get('file') else ''
