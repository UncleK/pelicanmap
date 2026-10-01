"""Archive a pinned public HF scoring reference. Never execute upstream code."""
import concurrent.futures
import hashlib
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
REVISION = '548f58a232c4aadf05f4798c2d69b8bd95e4b502'
DATASET = 'https://huggingface.co/datasets/sergiopaniego/pelican-svg-drawings'
ARCHIVE = ROOT/'pelican-archive/research/2026-10-01-source-backfill'
MEDIA = ROOT/'pelican-web/media/benchmark/openenv-2026-07-29'


def fetch(relative):
    assert re.fullmatch(r'[\w./-]+', relative) and '..' not in relative
    url = DATASET+'/resolve/'+REVISION+'/'+relative
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'PelicanMap-ReferenceArchiver/1.0'}), timeout=60) as response:
        return response.read()


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        assert path.read_bytes() == data, 'Pinned source changed: '+str(path)
    else:
        path.write_bytes(data)


def validate_svg(data):
    assert b'<!DOCTYPE' not in data.upper() and b'<!ENTITY' not in data.upper()
    root = ET.fromstring(data)
    assert root.tag == '{http://www.w3.org/2000/svg}svg'
    animated = False
    for element in root.iter():
        tag = element.tag.split('}')[-1].lower()
        assert tag not in {'script', 'foreignobject'}
        animated |= tag in {'animate', 'animatetransform', 'animatemotion', 'set'}
        for key, value in element.attrib.items():
            assert not key.lower().startswith('on')
            if key.split('}')[-1].lower() == 'href':
                assert value.startswith('#'), 'Non-local SVG dependency'
            assert not re.search(r'url\(\s*[\'"]?(?!#)[^\s]', value, re.I), 'External SVG dependency'
    return not animated


def main():
    additions_path = ROOT/'site/additions.json'
    additions = json.loads(additions_path.read_text(encoding='utf8'))
    existing = {x['datasetSample']['id']: x for x in additions if x['id'].startswith('hf-openenv-')}
    raw = fetch('data.jsonl')
    assert raw == (ARCHIVE/'hf-data.jsonl').read_bytes(), 'Review upstream revision before import'
    coverage = fetch('coverage.jsonl')
    save(ARCHIVE/'hf-coverage.jsonl', coverage)
    rows = [dict(json.loads(line), config=config) for config, contents in [('default', raw), ('coverage', coverage)] for line in contents.decode().splitlines() if line.strip()]
    assert len(rows) == 169 and sum(x['config'] == 'default' for x in rows) == 139
    assert len({x['id'] for x in rows}) == len(rows)

    def archive(row):
        required = ['model', 'access', 'provider', 'task', 'sample', 'reward', 'structure_score', 'semantic_score', 'gate_passed', 'violations', 'judge_model', 'judge_blind_caption', 'svg', 'png']
        row['missingSourceFields'] = [key for key in required if key not in row]
        for key in required:
            row.setdefault(key, None)
        row['sourceUrl'] = DATASET+'/blob/'+REVISION+'/'+row['svg']
        row['localSvg'] = row['localPng'] = None
        row['latency'] = row.get('latency_s')
        row['tags'] = ['benchmark']+(['benchmark-catalogue'] if row['task'] != 'pelican_bicycle' else [])
        if not row.get('png'):
            assert row['gate_passed'] is False and 'truncated_svg' in row['violations']
            row['mediaStatus'] = 'unrenderable'
            return row
        local_svg = ARCHIVE/'hf-original-svg'/Path(row['svg']).name
        prior_svg = MEDIA/Path(row['svg']).name
        svg = local_svg.read_bytes() if row['config'] == 'default' else prior_svg.read_bytes() if prior_svg.exists() else fetch(row['svg'])
        static_svg = validate_svg(svg)
        svg_target = MEDIA/Path(row['svg']).name
        if static_svg:
            save(svg_target, svg)
            row['localSvg'] = '/'+svg_target.relative_to(ROOT/'pelican-web').as_posix()
        else:
            row['svgDeferredReason'] = 'SVG contains SMIL animation; only the upstream static PNG is displayed for scoring reference.'
        if row['id'] in existing:
            png_path = ROOT/'pelican-web'/existing[row['id']]['media'][0]['src'].lstrip('/')
            row['recordId'] = existing[row['id']]['id']
            row['recordPath'] = existing[row['id']]['path']
        else:
            png_path = MEDIA/Path(row['png']).name
            if not png_path.exists():
                save(png_path, fetch(row['png']))
        with Image.open(png_path) as image:
            image.verify()
        row['localPng'] = '/'+png_path.relative_to(ROOT/'pelican-web').as_posix()
        row['sha256'] = {'svg': hashlib.sha256(svg).hexdigest(), 'png': hashlib.sha256(png_path.read_bytes()).hexdigest()}
        row['mediaStatus'] = 'local'
        return row

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        rows = list(pool.map(archive, rows))
    payload = {'id': 'openenv-2026-07-29', 'referenceOnly': True,
               'sourceUrl': DATASET, 'revision': REVISION,
               'author': 'Sergio Paniego (@sergiopaniego)', 'publicationDate': '2026-07-29',
               'runDate': None, 'runDateNote': 'Not separately published; dataset publication is not a run timestamp.',
               'prompt': 'generate an SVG of a pelican riding a bicycle', 'license': 'Apache-2.0',
               'licenseUrl': '/media/collected/2026-10-01-source-backfill/apache-2.0.txt',
               'attributionUrl': '/media/collected/2026-10-01-source-backfill/ATTRIBUTION.txt',
               'envUrl': 'https://huggingface.co/spaces/sergiopaniego/pelican-svg-env',
               'repositoryUrl': 'https://github.com/huggingface/OpenEnv/tree/main/envs/pelican_svg_env',
               'disclaimer': {'zh': '上游输出，非本馆排名', 'en': 'Upstream outputs, not a Pelican Map ranking'}, 'rows': rows}
    target = ROOT/'site/benchmarks/openenv-2026-07-29.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf8')
    deferred = ROOT/'deferred.md'
    prior = deferred.read_text(encoding='utf8') if deferred.exists() else '# 暂缓媒体\n\n'
    for row in rows:
        if row.get('svgDeferredReason') and row['sourceUrl'] not in prior:
            prior += '- '+row['sourceUrl']+' — SVG 含 SMIL 动画，不镜像 SVG；独立评分参考区仅保留上游静态 PNG 和原评分元数据。\n'
    deferred.write_text(prior, encoding='utf8')
    by_id = {x['id']: x for x in rows if x['config'] == 'default'}
    for item in existing.values():
        row = by_id[item['datasetSample']['id']]
        item.update(kind='reference', referenceOnly=True, tags=['benchmark'])
        item['datasetSample'].update({k: row.get(k) for k in ['model', 'access', 'provider', 'task', 'sample', 'reward', 'structure_score', 'semantic_score', 'gate_passed', 'violations', 'judge_model', 'judge_blind_caption', 'latency', 'latency_s', 'svg', 'png']})
        item['benchmarkMedia'] = {'svg': row['localSvg'], 'png': row['localPng']}
    additions_path.write_text(json.dumps(additions, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps({'reference_rows': len(rows), 'main_task_rows': 139, 'viewable_main_samples': 138, 'coverage_rows': 30, 'main_cases_added': 0}))


if __name__ == '__main__':
    main()
