"""Validate data references, archive CRCs, images and video containers locally."""
from pathlib import Path
from urllib.parse import urlsplit, unquote
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
from zipfile import ZipFile
from bs4 import BeautifulSoup
from PIL import Image
import xml.etree.ElementTree as ET
import subprocess
import shutil
import json
import csv

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'pelican-web'
AUDIT = ROOT / 'pelican-archive/audit/2026-09-27'
data = json.loads((WEB / 'data.js').read_text(encoding='utf-8').split('=', 1)[1].strip().removesuffix(';'))
errors = []
external = []
refs = set()
for group in ['timeline', 'gallery', 'repos']:
    ids = [x['id'] for x in data[group]]
    if len(set(ids)) != len(ids):
        errors.append([group, 'duplicate IDs'])
    for item in data[group]:
        for key in ['media', 'zip', 'demo', 'sourceCode']:
            if item.get(key):
                refs.add((item['id'], item[key]))
        for media in item.get('mediaItems', []):
            refs.add((item['id'], media['src']))
            if media.get('poster'):
                refs.add((item['id'], media['poster']))
for item_id, value in refs:
    if value.startswith(('http:', 'https:')):
        errors.append([item_id, 'nonlocal data asset', value])
    elif not (WEB / unquote(urlsplit(value).path)).is_file():
        errors.append([item_id, 'missing data asset', value])

for page in WEB.rglob('*.html'):
    soup = BeautifulSoup(page.read_text(encoding='utf-8', errors='replace'), 'html.parser')
    for tag, attr in [('script', 'src'), ('img', 'src'), ('source', 'src'), ('video', 'src'), ('video', 'poster'), ('iframe', 'src'), ('object', 'data'), ('link', 'href'), ('a', 'href')]:
        for el in soup.find_all(tag):
            value = el.get(attr, '')
            if not value or value.startswith(('#', 'data:', 'blob:', 'mailto:', 'javascript:')) or '${' in value:
                continue
            parts = urlsplit(value)
            if parts.scheme or parts.netloc:
                if tag != 'a' and (tag != 'link' or set(el.get('rel') or []).intersection({'stylesheet', 'modulepreload', 'icon'})):
                    external.append([page.relative_to(WEB).as_posix(), value])
                continue
            target = WEB / unquote(parts.path.lstrip('/')) if parts.path.startswith('/') else page.parent / unquote(parts.path)
            if target.is_dir():
                target /= 'index.html'
            if not target.is_file():
                errors.append([page.relative_to(WEB).as_posix(), 'missing HTML reference', value])

archives = []
for path in (WEB / 'repos').glob('*.zip'):
    with ZipFile(path) as z:
        bad = z.testzip()
        if bad:
            errors.append([path.name, 'CRC mismatch', bad])
        archives.append(dict(file=path.name, files=sum(not i.is_dir() for i in z.infolist())))

media = [p for p in (WEB / 'media').rglob('*') if p.is_file()]
media += [p for p in (WEB / 'demos').rglob('*') if p.suffix.lower() in ['.svg', '.png', '.jpg', '.jpeg', '.webp', '.gif']]
images = 0
for path in media:
    try:
        if path.suffix.lower() == '.svg':
            ET.parse(path)
            images += 1
        elif path.suffix.lower() in ['.png', '.jpg', '.jpeg', '.webp', '.gif', '.avif']:
            with Image.open(path) as img:
                img.verify()
            images += 1
    except Exception as exc:
        errors.append([path.relative_to(WEB).as_posix(), 'image decode', str(exc)])

videos = [p for p in media if p.suffix.lower() in ['.mp4', '.webm']]
ffprobe = shutil.which('ffprobe')
def probe(path):
    result = subprocess.run([ffprobe, '-v', 'error', '-show_entries', 'format=duration', '-of', 'json', str(path)], capture_output=True, text=True)
    if result.returncode:
        return [path.relative_to(WEB).as_posix(), 'video probe', result.stderr]
    try:
        if float(json.loads(result.stdout)['format']['duration']) <= 0:
            raise ValueError('empty duration')
    except Exception as exc:
        return [path.relative_to(WEB).as_posix(), 'video duration', str(exc)]
if ffprobe:
    with ThreadPoolExecutor(max_workers=6) as pool:
        errors.extend(x for x in pool.map(probe, videos) if x)
else:
    errors.append(['ffprobe', 'not available'])

catalog = json.loads((ROOT / 'pelican-archive/normalized/catalog.json').read_text(encoding='utf-8'))
cases = json.loads((ROOT / 'pelican-archive/normalized/community-cases.json').read_text(encoding='utf-8'))
with (ROOT / 'pelican-archive/normalized/catalog.csv').open(encoding='utf-8-sig') as f:
    csv_rows = list(csv.DictReader(f))
if len(catalog) != len(csv_rows) or len(catalog) != data['stats']['catalog']:
    errors.append(['catalog', 'JSON, CSV and website count mismatch'])
if {x['id'] for x in cases} != {x['id'] for x in data['timeline']}:
    errors.append(['timeline', 'community cases mismatch'])
for row in catalog:
    if row.get('local_media') and not (ROOT / 'pelican-archive' / row['local_media']).is_file():
        errors.append([row['id'], 'catalog missing media', row['local_media']])
for group in ['timeline', 'gallery', 'simon', 'repos']:
    if len(data[group]) != data['stats'][group]:
        errors.append([group, 'stats mismatch'])
for x in data['simon']:
    if not (WEB / x['snapshot']).is_file():
        errors.append([x['url'], 'missing source snapshot'])

result = dict(errors=errors, counts=dict(timeline=len(data['timeline']), timeline_with_media=sum(bool(x.get('media')) for x in data['timeline']), timeline_statuses=dict(Counter(x.get('mediaStatus') for x in data['timeline'])), gallery=len(data['gallery']), gallery_with_media=sum(bool(x.get('media')) for x in data['gallery']), catalog=len(catalog), simon=len(data['simon']), zip_archives=len(archives), checked_images=images, checked_videos=len(videos), asset_references=len(refs)), archives=archives, external_resources=external, without_media=[dict(id=x['id'], model=x['model'], status=x.get('mediaStatus'), note=x.get('mediaNote', ''), demo=x.get('demo', ''), url=x['url']) for x in data['timeline'] if not x.get('media')])
(AUDIT / 'validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(result, ensure_ascii=False, indent=2))
raise SystemExit(bool(errors))
