"""Focused release checks: changed bytes/media, bilingual counts and affected links."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
from urllib.parse import unquote, urljoin, urlsplit
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup
from PIL import Image
from release_delta import MANIFEST, metadata
from case_policy import is_case, in_timeline

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://pelicanmap.aveniqa.com'
# Nginx injects this exact, first-party traffic script into served HTML.
TRAFFIC_SCRIPT = b'<script defer src="/_traffic/client.js" data-config="/_traffic/config" data-media="true"></script>'


def check_live_bytes(name, data, expected):
    if name.endswith('.html') and data.count(TRAFFIC_SCRIPT) == 1:
        data = data.replace(TRAFFIC_SCRIPT, b'', 1)
    if hashlib.sha256(data).hexdigest() != expected['sha256']:
        raise ValueError('Changed live file hash mismatch: '+name)


def fetch(url):
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers={'User-Agent':'PelicanMap-Delta-Verify/1.0'})
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read()
        except urllib.error.HTTPError:
            raise
        except (urllib.error.URLError, TimeoutError, OSError):
            if attempt == 2:
                raise


def check_api_record(expected, actual):
    if actual != expected:
        fields = sorted(key for key in set(expected) | set(actual) if expected.get(key) != actual.get(key))
        raise ValueError('Affected API record differs from the new catalog: '+expected['id']+' / '+', '.join(fields[:8]))


def check(archive_path, root=ROOT, live=False):
    root = Path(root)
    with tarfile.open(archive_path) as archive:
        manifest = json.load(archive.extractfile(MANIFEST))
        payloads = {}
        for name, row in manifest['changed'].items():
            data = archive.extractfile(name).read()
            if len(data) != row['bytes'] or hashlib.sha256(data).hexdigest() != row['sha256']:
                raise ValueError('Changed file hash mismatch: ' + name)
            payloads[name] = data
    catalogs = [json.loads((root/'public-site'/prefix/'data/catalog.json').read_text(encoding='utf8')) for prefix in ('', 'en')]
    for catalog in catalogs:
        assert catalog['counts']['cases'] == sum(is_case(x) for x in catalog['items'])
        assert catalog['counts']['timeline'] == sum(in_timeline(x) for x in catalog['items'])
    assert {x['id'] for x in catalogs[0]['items']} == {x['id'] for x in catalogs[1]['items']}
    assert catalogs[0]['counts'] == catalogs[1]['counts']
    changed_media = {x for x in payloads if x.startswith('site/media/')}
    affected = [x for x in catalogs[0]['items'] if x['id'] in manifest['affectedRecords'] or
                any('site'+m['src'] in changed_media or 'site'+m.get('poster','') in changed_media for m in x['media'])]
    affected_pages = set()
    for record in affected:
        for prefix in ('', 'en/'):
            affected_pages.update({'site/'+prefix+record['path'].lstrip('/')+'index.html',
                                   'site/'+prefix+record['markdown'].lstrip('/')})
    entry_pages = {'site/'+prefix+path for prefix in ('', 'en/') for path in
                   ('index.html', 'specimens/index.html', 'timeline/index.html',
                    'data/catalog.json', 'data/catalog.csv', 'llms.txt', 'feed.xml', 'sitemap.xml')}
    checked_links = 0
    checked_pages = 0
    for name, data in payloads.items():
        if name.startswith('site/') and name.endswith('.html') and (
                name in affected_pages | entry_pages or name not in manifest['baseline']['files']):
            checked_pages += 1
            soup = BeautifulSoup(data, 'html.parser')
            page_url = BASE+'/'+name.removeprefix('site/').removesuffix('index.html')
            for node in soup.select('[href], [src], [poster]'):
                for attribute in ('href', 'src', 'poster'):
                    value = node.get(attribute)
                    if not value or value.startswith(('data:', '#', 'mailto:', 'javascript:')):
                        continue
                    url = urlsplit(urljoin(page_url, value))
                    if url.netloc != urlsplit(BASE).netloc or url.path.startswith(('/api/', '/mcp')):
                        continue
                    relative = 'site/'+unquote(url.path).lstrip('/')
                    if relative.endswith('/'):
                        relative += 'index.html'
                    if relative not in manifest['files']:
                        raise ValueError('Affected page has a missing local link: '+name+' -> '+relative)
                    checked_links += 1
        if name in changed_media:
            path = root/'public-site'/name.removeprefix('site/')
            assert metadata(path) == manifest['changed'][name]
            suffix = path.suffix.lower()
            if suffix == '.svg':
                ET.fromstring(data)
            elif suffix in {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.avif'}:
                with Image.open(path) as image:
                    for frame in range(getattr(image, 'n_frames', 1)):
                        image.seek(frame)
                        image.load()
            elif suffix in {'.mp4', '.webm'}:
                ffmpeg = os.environ.get('PELICAN_FFMPEG') or shutil.which('ffmpeg')
                if not ffmpeg and os.environ.get('LOCALAPPDATA'):
                    ffmpeg = next((str(p) for p in Path(os.environ['LOCALAPPDATA']).glob('Microsoft/WinGet/Packages/Gyan.FFmpeg*/**/ffmpeg.exe')), None)
                if not ffmpeg:
                    raise ValueError('FFmpeg is required to check changed video')
                subprocess.run([ffmpeg, '-v', 'error', '-xerror', '-i', str(path), '-f', 'null', '-'],
                               check=True, capture_output=True, timeout=180)
    requests = 0
    if live:
        for name in payloads:
            if not name.startswith('site/') or name.startswith('site/downloads/'):
                continue
            if name.endswith(('.html', '.md')) and name not in affected_pages | entry_pages:
                continue
            # Affected records, changed media/assets and changed data entry points.
            url = BASE+'/'+name.removeprefix('site/')+'?v='+manifest['changed'][name]['sha256'][:12]
            check_live_bytes(name, fetch(url), manifest['changed'][name])
            requests += 1
        for record in affected:
            for lang in ('zh', 'en'):
                result = json.loads(fetch(BASE+'/api/v1/specimens/'+record['id']+'?lang='+lang))
                expected = next(item for item in catalogs[0 if lang == 'zh' else 1]['items'] if item['id'] == record['id'])
                check_api_record(expected, result)
                requests += 1
    return {'changedFiles':len(payloads), 'changedMedia':len(changed_media),
            'affectedRecords':[x['id'] for x in affected], 'checkedLinks':checked_links, 'checkedHtmlPages':checked_pages,
            'counts':catalogs[0]['counts'], 'liveRequests':requests}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--live', action='store_true')
    args = parser.parse_args()
    print(json.dumps(check(args.archive, args.root, args.live), ensure_ascii=False, indent=2))
