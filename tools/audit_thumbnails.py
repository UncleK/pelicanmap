"""Decode every catalog thumbnail and flag low-information images for human review.

This is an audit, not an image-quality judge: sparse/bad model outputs remain intact.
No artwork is altered and no candidate is automatically replaced.
"""
import argparse
import concurrent.futures
import io
import html
import json
import math
import urllib.parse
import urllib.request
from pathlib import Path
from xml.etree import ElementTree

import cairosvg
from PIL import Image, ImageDraw, ImageOps, ImageStat

ROOT = Path(__file__).resolve().parents[1]


def image_metrics(image):
    rgba = image.convert('RGBA')
    background = Image.new('RGBA', rgba.size, 'white')
    background.alpha_composite(rgba)
    image = background.convert('RGB')
    image.thumbnail((240, 180), Image.Resampling.LANCZOS)
    gray = ImageOps.grayscale(image)
    stats = ImageStat.Stat(gray)
    hist = gray.histogram()
    total = sum(hist)
    occupied = [i for i, count in enumerate(hist) if count]
    return {
        'width': rgba.width, 'height': rgba.height,
        'stddev': round(stats.stddev[0], 3),
        'range': max(occupied) - min(occupied),
        'darkFraction': round(sum(hist[:220]) / total, 5),
        'dominantFraction': round(max(hist) / total, 5),
    }


def check_path(url, site):
    result = {'thumbnail': url}
    try:
        if not url:
            raise ValueError('Missing thumbnail')
        if url.startswith('https://'):
            data = urllib.request.urlopen(urllib.request.Request(url, headers={
                'User-Agent': 'PelicanMap-ThumbnailAudit/1.0'}), timeout=30).read()
            suffix = Path(urllib.parse.urlsplit(url).path).suffix.lower()
        else:
            path = (site / urllib.parse.unquote(url.lstrip('/').split('?')[0])).resolve()
            assert path.is_relative_to(site.resolve()), 'Path outside public site'
            data = path.read_bytes()
            suffix = path.suffix.lower()
        if suffix == '.svg':
            tree = ElementTree.fromstring(data)
            # Do not fetch remote resources or execute embedded code during audit.
            for node in tree.iter():
                for key, value in node.attrib.items():
                    if key.rsplit('}', 1)[-1] == 'href' and not value.startswith(('#', 'data:')):
                        raise ValueError('SVG external resource requires browser review')
            data = cairosvg.svg2png(bytestring=data, output_width=360, output_height=240)
        with Image.open(io.BytesIO(data)) as image:
            image.load()
            result.update(image_metrics(image))
        result['needsReview'] = result['stddev'] < 8 or result['darkFraction'] < .005
    except Exception as exc:
        result.update(error=str(exc), needsReview=True)
    return result


def contact_sheet(rows, site, target):
    if not rows:
        return
    cols, cell_w, cell_h = 4, 300, 230
    sheet = Image.new('RGB', (cols * cell_w, math.ceil(len(rows) / cols) * cell_h), '#dddace')
    draw = ImageDraw.Draw(sheet)
    for index, row in enumerate(rows):
        x, y = (index % cols) * cell_w, (index // cols) * cell_h
        try:
            path = site / urllib.parse.unquote(row['thumbnail'].lstrip('/'))
            data = path.read_bytes()
            if path.suffix.lower() == '.svg':
                data = cairosvg.svg2png(bytestring=data, output_width=280, output_height=185)
            with Image.open(io.BytesIO(data)) as image:
                image = ImageOps.contain(image.convert('RGB'), (280, 185))
                sheet.paste(image, (x + (cell_w - image.width) // 2, y + 5))
        except Exception:
            draw.text((x + 10, y + 10), row.get('error', 'Unavailable')[:38], fill='red')
        draw.text((x + 8, y + 194), row['id'][:42], fill='black')
        draw.text((x + 8, y + 209), f"sd={row.get('stddev')} dark={row.get('darkFraction')}", fill='black')
    sheet.save(target)


def live_checks(rows, origin):
    def fetch(row):
        url = row['thumbnail']
        if not url.startswith('https://'):
            url = origin.rstrip('/') + url
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={
                    'User-Agent': 'PelicanMap-ThumbnailAudit/1.0'}), timeout=40) as response:
                data = response.read()
                if not data:
                    raise ValueError('Empty response')
                return {'thumbnail': row['thumbnail'], 'status': response.status, 'bytes': len(data)}
        except Exception as exc:
            return {'thumbnail': row['thumbnail'], 'error': str(exc)}
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        return list(pool.map(fetch, rows))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--site', type=Path, default=ROOT / 'public-site')
    parser.add_argument('--output', type=Path, default=ROOT / 'deploy-build/thumbnail-audit')
    parser.add_argument('--live', action='store_true')
    args = parser.parse_args()
    catalog = json.loads((args.site / 'data/catalog.json').read_text(encoding='utf8'))
    grouped = {}
    for item in catalog['items']:
        grouped.setdefault(item['thumbnail'], []).append(item)
    # Cairo's Windows font backend is not thread safe; keep decode/render serial.
    # Remote HTTP checks below still run concurrently.
    checked = [check_path(url,args.site) for url in grouped]
    rows = []
    for row in checked:
        row['records'] = [item['id'] for item in grouped[row['thumbnail']]]
        row['id'] = row['records'][0]
        row['formats'] = sorted({item['format'] for item in grouped[row['thumbnail']]})
        row['hasVideo'] = any(media['src'].endswith(('.mp4','.webm')) for item in grouped[row['thumbnail']] for media in item['media'])
        rows.append(row)
    args.output.mkdir(parents=True, exist_ok=True)
    candidates = sorted([row for row in rows if row['needsReview']], key=lambda r: r.get('stddev', -1))
    videos = [row for row in rows if row['hasVideo'] or 'video' in row['formats']]
    for name, items in [('candidates', candidates), ('video-covers', videos)]:
        # Keep sheets bounded and readable.
        for start in range(0, len(items), 40):
            contact_sheet(items[start:start + 40], args.site, args.output / f'{name}-{start // 40 + 1}.jpg')
    result = {'records': len(catalog['items']), 'uniqueThumbnails': len(rows),
              'decodeErrors': [row for row in rows if 'error' in row],
              'reviewCandidates': candidates, 'rows': rows}
    if args.live:
        result['live'] = live_checks(rows, catalog['site'])
        result['liveErrors'] = [row for row in result['live'] if 'error' in row]
    (args.output / 'audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf8')
    for start in range(0,len(rows),200):
        chunk=rows[start:start+200]
        content='<!doctype html><meta charset="utf-8"><title>Thumbnail browser audit</title><style>body{font:12px system-ui}.grid{display:grid;grid-template-columns:repeat(5,1fr);gap:12px}img{width:100%;height:130px;object-fit:contain}figure{margin:0}</style><h1>Thumbnail audit '+str(start+1)+'–'+str(start+len(chunk))+'</h1><div class="grid">'
        for row in chunk:
            url=row['thumbnail'] if row['thumbnail'].startswith('https://') else catalog['site']+row['thumbnail']
            content+='<figure><img loading="eager" data-record="'+html.escape(row['id'],quote=True)+'" src="'+html.escape(url,quote=True)+'"><figcaption>'+html.escape(row['id'])+'</figcaption></figure>'
        (args.output / f'browser-{start//200+1}.html').write_text(content+'</div>',encoding='utf8')
    print(json.dumps({key: result[key] for key in ('records', 'uniqueThumbnails')}, ensure_ascii=False))
    print('Decode errors:', len(result['decodeErrors']), 'Review candidates:', len(candidates))
    for row in candidates:
        print(row['id'], row.get('stddev'), row.get('darkFraction'), row.get('error', ''))
    if args.live:
        print('Live errors:', len(result['liveErrors']))
        if result['liveErrors']:
            raise SystemExit(1)


if __name__ == '__main__':
    main()
