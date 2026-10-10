"""Inventory every counted work for faithful motion restoration, without decoding old video."""
import argparse
import datetime as dt
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def media_kind(src, output):
    path = output / unquote(urlsplit(src).path).lstrip('/')
    if urlsplit(src).netloc:
        return 'remote', False
    if not path.is_file():
        return 'missing', False
    suffix = path.suffix.lower()
    if suffix in {'.mp4', '.webm'}:
        return 'video', True
    if suffix == '.svg':
        source = path.read_text(encoding='utf8')
        if re.search(r'<(?:\w+:)?(?:animate\w*|set)\b|@(?:-webkit-)?keyframes\b', source, re.I):
            return 'svg-animation', True
        if re.search(r'<script\b', source, re.I):
            return 'svg-script-needs-document', False
        return 'static-svg', False
    if suffix in {'.gif', '.webp', '.png', '.jpg', '.jpeg'}:
        with Image.open(path) as image:
            return ('animated-image', True) if getattr(image, 'is_animated', False) else ('static-image', False)
    return suffix.lstrip('.'), False


def audit(catalog, output):
    checked = {}
    rows = []
    for item in catalog['items']:
        if not item.get('caseVisible', True) or item.get('referenceOnly'):
            continue
        media = []
        for value in item['media']:
            src = value['src']
            if src not in checked:
                try:
                    checked[src] = media_kind(src, output)
                except Exception as error:
                    checked[src] = ('inspection-error: ' + str(error), False)
            kind, moving = checked[src]
            media.append({'src': src, 'kind': kind, 'moving': moving,
                          'detailOnly': value.get('detailOnly', False), 'source': value.get('source', '')})
        if item.get('motionPreview'):
            status = 'dynamic-cover-present'
        elif any(x['moving'] for x in media):
            status = 'archived-motion-needs-primary-review'
        elif any(x['kind'] == 'svg-script-needs-document' for x in media):
            status = 'scripted-svg-needs-document'
        elif item.get('format') in {'animation', 'video', 'game', '3d'} or re.search(
                r'animation|animated|threejs|html|webgl', item.get('originalForm', ''), re.I):
            status = 'dynamic-source-recheck'
        else:
            status = 'static-media-no-motion-evidence'
        rows.append({'id': item['id'], 'title': item['title'], 'status': status,
                     'sourceUrl': item['sourceUrl'], 'sourceCodeUrl': item.get('sourceCodeUrl', ''),
                     'externalUrl': item.get('externalUrl', ''), 'format': item['format'],
                     'originalForm': item.get('originalForm', ''), 'notes': item.get('notes', ''),
                     'motionPreview': item.get('motionPreview'), 'media': media})
    summary = {}
    for row in rows:
        summary[row['status']] = summary.get(row['status'], 0) + 1
    return {'auditedAt': dt.datetime.now(dt.timezone.utc).isoformat(), 'counts': catalog['counts'],
            'worksAudited': len(rows), 'uniqueMediaInspected': len(checked), 'summary': summary,
            'limits': 'Original media headers and SVG code inspected once; source hints are candidates, not proof that every original has recoverable motion. Existing video decoding evidence is reused.',
            'works': rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog', type=Path, default=ROOT / 'site/catalog.json')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    value = audit(json.loads(args.catalog.read_text(encoding='utf8')), ROOT / 'public-site')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps({k: value[k] for k in ['worksAudited', 'uniqueMediaInspected', 'summary']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
