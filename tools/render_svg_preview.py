"""Archive a faithful raster preview for a reviewed browser-incompatible SVG.

Original bytes and artwork are not modified; this is a format/render derivative.
"""
import hashlib
import json
from pathlib import Path

import cairosvg

ROOT=Path(__file__).resolve().parents[1]
catalog=json.loads((ROOT/'public-site/data/catalog.json').read_text(encoding='utf8'))
item=next(x for x in catalog['items'] if x['originalId']=='origin-gemini-1.5-pro-001.svg')
media=next(x for x in item['media'] if x['src'].endswith('.svg'))
original=ROOT/'pelican-web'/media['src'].lstrip('/')
target=ROOT/'pelican-web/media/posters/2026-10-01/origin-gemini-1.5-pro-001-preview.png'
assert not target.exists(), 'Preserve archived preview'
target.parent.mkdir(parents=True,exist_ok=True)
cairosvg.svg2png(bytestring=original.read_bytes(),write_to=str(target),scale=2)
manifest=ROOT/'site/thumbnail-overrides.json'
overrides=json.loads(manifest.read_text(encoding='utf8'))
overrides[item['originalId']]={
    'type':'svg-render','poster':'/'+target.relative_to(ROOT/'pelican-web').as_posix(),
    'sourceSvg':media['src'],'source':media['source'],
    'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
    'sourceSha256':hashlib.sha256(original.read_bytes()).hexdigest(),
    'caption':'原始 SVG 的本地渲染预览；原代码缺少 SVG 命名空间，原文件保留未改动',
    'captionEn':'Local render of the original SVG, which lacks the SVG namespace. Original source bytes are preserved unchanged.',
    'reviewed':'2026-10-01',
}
manifest.write_text(json.dumps(overrides,ensure_ascii=False,indent=2),encoding='utf8')
print(target)
