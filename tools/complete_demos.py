from archive_io import ROOT, WEB, AUDIT, records, text_for, fetch_batch
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlsplit, quote
from zipfile import ZipFile, ZIP_DEFLATED
from pathlib import Path
import hashlib
import html
import json
import re
import shutil
import os

def save(path, content):
    path = WEB / path
    if path.exists():
        backup = AUDIT / 'demo-before' / path.relative_to(WEB)
        if not backup.exists():
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, backup)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')

pages = {
    'https://tihuqiche.com/offline.html': 'demos/tihuqiche/index.html',
    'https://claude-opus-5-5.riba2534.cn/': 'demos/riba-opus-coast.html',
    'https://pelican-ride.workspace-754454.chatgpt.site/': 'demos/pelican-ride-lab/index.html',
    'https://case.ccvibe.top': 'demos/sites/parrot-ccvibe.html',
}
for model in ['luna', 'sol', 'astra']:
    for level in ['low', 'medium', 'high', 'xhigh', 'max']:
        pages[f'https://pelican-ride.workspace-754454.chatgpt.site/{model}-{level}.html'] = f'demos/pelican-ride-lab/{model}-{level}.html'
rust_source = 'https://en.rustfisher.com/ai/pelican-bike-demo202609-gpt6astra-gemini3-8flash-deepseek4-1flash/'
rust = BeautifulSoup((WEB / 'demos/sites/rustfisher-compare.html').read_text(encoding='utf-8'), 'html.parser')
rust_pages = [x['src'] for x in rust.select('iframe[src]') if x['src'].startswith('https://')]
# Allow repeat runs after the comparison page has been replaced with local links.
if not rust_pages:
    original = AUDIT / 'demo-before/demos/sites/rustfisher-compare.html'
    rust_pages = [x['src'] for x in BeautifulSoup(original.read_text(encoding='utf-8'), 'html.parser').select('iframe[src]')]
for u in rust_pages:
    pages[u] = 'demos/rustfisher/' + urlsplit(u).path.strip('/').split('/')[-1] + '.html'
baiguangru_source = 'https://baiguangru.vip/2026/09/09/pelican-bike-model-regression-check.html'
baiguangru_pages = [urljoin(baiguangru_source, x['src']) for x in BeautifulSoup(text_for(baiguangru_source), 'html.parser').select('iframe[src]')]
for i, u in enumerate(baiguangru_pages):
    pages[u] = f'demos/baiguangru/{i+1}.html'
fetch_batch(list(pages) + ['https://github.com/staypzy/prab', 'https://demobench.janekm.com/previews/data.js', 'https://demobench.janekm.com/audio-player.js', 'https://demobench.janekm.com/machine-worker.js'], kind='offline-demo')

# Keep downloaded dependencies beside the demo, with all import paths rewritten.
assets = {}
problems = []
def asset_url(base, ref):
    if not ref or ref.startswith(('data:', 'blob:', '#')) or '${' in ref:
        return None
    if any(k in ref for k in ['cloudflareinsights', 'googletagmanager', 'challenge-platform']):
        return None
    u = urljoin(base, ref)
    return u if u.startswith(('http:', 'https:')) else None

def references(text, url, is_html=False):
    refs = set()
    if is_html:
        soup = BeautifulSoup(text, 'html.parser')
        for e in soup.find_all(['script', 'img', 'source', 'video']):
            if e.get('src'):
                refs.add(e['src'])
            if e.get('poster'):
                refs.add(e['poster'])
        for e in soup.find_all('link'):
            if set(e.get('rel') or []).intersection({'stylesheet', 'icon', 'modulepreload'}):
                refs.add(e.get('href', ''))
        for e in soup.select('script[type="importmap"]'):
            refs.update(json.loads(e.string or e.get_text()).get('imports', {}).values())
    for pattern in [r'(?:from\s*|import\s*\(|import\s+|new URL\s*\()([\"\'])([^\"\']+)\1', r'url\(\s*[\"\']?([^\)\"\']+)', r'fetch\(\s*[\"\']([^\"\']+)']:
        for match in re.finditer(pattern, text):
            ref = match[2] if match.lastindex == 2 else match[1]
            if ref.startswith(('.', '/', 'http:','https:')):
                refs.add(ref)
    return {ref: asset_url(url, ref) for ref in refs if asset_url(url, ref)}

def local_asset(url, depth=0):
    if url in assets:
        return assets[url]
    if depth > 5:
        problems.append({'url': url, 'reason': 'dependency-depth-limit'})
        return None
    row = fetch_batch([url], kind='demo-dependency')[url]
    if row.get('error'):
        problems.append(row)
        return None
    suffix = Path(urlsplit(url).path).suffix or Path(row['file']).suffix
    target = Path('demos/_assets') / (hashlib.sha256(url.encode()).hexdigest()[:20] + suffix)
    assets[url] = target.as_posix()
    (WEB / target).parent.mkdir(exist_ok=True)
    payload = (ROOT / row['file']).read_bytes()
    if suffix in ['.js', '.mjs', '.css']:
        text = payload.decode('utf-8')
        for ref, resolved in references(text, url).items():
            dep = local_asset(resolved, depth + 1)
            if dep:
                text = text.replace(ref, './' + Path(dep).name)
        payload = text.encode('utf-8')
    (WEB / target).write_bytes(payload)
    return target.as_posix()

def clean_html(raw):
    # Remove online telemetry and injected challenge probes from offline copies only.
    def script(match):
        text = match[0]
        return '' if any(k in text for k in ['cloudflareinsights.com', '__CF$cv$params', 'googletagmanager.com']) else text
    return re.sub(r'<script\b[\s\S]*?</script>', script, raw, flags=re.I)

for url, target in pages.items():
    raw = text_for(url)
    if not raw:
        problems.append({'url': url, 'reason': 'missing-page'})
        continue
    raw = clean_html(raw)
    # An import-map prefix denotes a directory, not an asset to download.
    # Expand the prefixes actually used by this page into exact module mappings.
    parsed = BeautifulSoup(raw, 'html.parser')
    for script in parsed.select('script[type="importmap"]'):
        original = script.string or script.get_text()
        mapping = json.loads(original)
        expanded = {}
        imports = re.findall(r'(?:from\s*|import\s*\(|import\s+)[\"\']([^\"\']+)', raw)
        for key, value in mapping.get('imports', {}).items():
            if key.endswith('/'):
                for specifier in imports:
                    if specifier.startswith(key):
                        expanded[specifier] = urljoin(value, specifier[len(key):])
            else:
                expanded[key] = value
        mapping['imports'] = expanded
        raw = raw.replace(original, json.dumps(mapping))
    for ref, resolved in references(raw, url, True).items():
        dep = local_asset(resolved)
        if dep:
            relative = os.path.relpath(WEB / dep, (WEB / target).parent).replace('\\', '/')
            raw = raw.replace(ref, relative)
    save(target, raw)

def comparison(title, urls, source):
    return '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>' + html.escape(title) + '</title><style>body{font:16px system-ui;background:#f7f0de;color:#352819;margin:24px}iframe{width:100%;height:520px;border:1px solid #ccb88e;background:white}section{margin:30px 0}a{color:#385843}</style><h1>' + html.escape(title) + '</h1><p>原始演示已保存到本地。<a href="' + source + '">原始来源</a></p>' + ''.join('<section><h2>' + html.escape(Path(pages[u]).stem) + '</h2><p><a href="' + os.path.relpath(WEB / pages[u], WEB / 'demos/sites').replace('\\', '/') + '">单独打开</a></p><iframe loading="lazy" src="' + os.path.relpath(WEB / pages[u], WEB / 'demos/sites').replace('\\', '/') + '"></iframe></section>' for u in urls) + '</html>'
save('demos/sites/rustfisher-compare.html', comparison('RustFisher 三模型原始演示', rust_pages, rust_source))
save('demos/sites/baiguangru-compare.html', comparison('白露横江 2D / 3D 原始演示', baiguangru_pages, baiguangru_source))

# Archive the actual code linked by the ohmyopus page. It is Python/pybevy,
# so label the source accurately rather than promising a standalone HTML game.
oh = BeautifulSoup((AUDIT / 'demo-before/demos/sites/ohmyopus.html').read_text(encoding='utf-8') if (AUDIT / 'demo-before/demos/sites/ohmyopus.html').exists() else (WEB / 'demos/sites/ohmyopus.html').read_text(encoding='utf-8'), 'html.parser')
poster = next((urljoin('https://ohmyopus.com/', x['src']) for x in oh.select('img[src]') if 'pelican-threejs/poster' in x['src']), None)
if poster:
    poster_result = fetch_batch([poster], kind='demo-poster', media=True)[poster]
    poster_local = os.path.relpath(ROOT / poster_result['file'], WEB / 'demos/sites').replace('\\', '/') if not poster_result.get('error') else None
else:
    poster_local = None
gist = 'https://gist.github.com/blaind/c54d9c17f04e7b9ad4209cb5fd18b7bb'
raw_code = next((u for u in records() if u.startswith(gist + '/raw/')), None)
if raw_code:
    code = text_for(raw_code)
    save('demos/sites/ohmyopus-pelican.py', code)
save('demos/sites/ohmyopus.html', '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>ohmyopus 原始资料</title><style>body{max-width:900px;margin:40px auto;font:18px system-ui;background:#f7f0de}img{max-width:100%}</style><h1>ohmyopus 鹈鹕骑车：原始资料</h1><p>原页面只保存了展示网页；页面提供的 Gist 源码是 Python / pybevy，不能直接当作 HTML 游戏运行。</p>' + (f'<img src="{poster_local}" alt="原页面预览图">' if poster_local else '') + f'<p><a href="https://ohmyopus.com/en/c/pelican-threejs">原网页</a> · <a href="{gist}">原始 Gist</a> · <a href="ohmyopus-pelican.py" download>下载原始 Python 源码</a></p></html>')

blender = ROOT / 'gpt-6-astra-blender-pelican-bicycle-main'
with ZipFile(WEB / 'repos/blender-astra.zip', 'w', ZIP_DEFLATED) as z:
    for p in blender.rglob('*'):
        if p.is_file():
            z.write(p, p.relative_to(ROOT).as_posix())
with ZipFile(WEB / 'repos/blender-astra.zip') as z:
    assert z.testzip() is None

data = json.loads((WEB / 'data.js').read_text(encoding='utf-8').split('=', 1)[1].strip().removesuffix(';'))
byid = {x['id']: x for x in data['timeline']}
demo_map = {
    'tihuqiche-game': 'demos/tihuqiche/index.html',
    'claude-opus-playable-coast': 'demos/riba-opus-coast.html',
    'x-jp-aichan-opus-oneprompt-games-2026-09-25': 'demos/riba-opus-coast.html',
    'pelican-ride-lab-15': 'demos/pelican-ride-lab/index.html',
    'baiguangru-2d3d-regression': 'demos/sites/baiguangru-compare.html',
    'juejin-parrot-variant-astra-2026-09-17': 'demos/sites/parrot-ccvibe.html',
    'x-2103050156228874298': 'demos/sites/rustfisher-compare.html',
}
for key, path in demo_map.items():
    byid[key]['demo'] = path
    if not byid[key].get('media'):
        byid[key].update(mediaStatus='interactive', mediaNote='已保存本地交互演示，可直接打开。')
for repo in data['repos']:
    if repo.get('zip'):
        folder = Path(repo['zip']).stem
        if (WEB / 'demos' / folder / 'index.html').is_file():
            repo['demo'] = f'demos/{folder}/index.html'
    if repo['id'] in ['site-tihu', 'repo-licoy-tihuqiche']:
        repo['demo'] = 'demos/tihuqiche/index.html'
    if repo['id'] == 'site-ohmyopus':
        repo.update(demoLabel='本地资料', sourceCode='demos/sites/ohmyopus-pelican.py', notes='原始预览与 Gist 已保存；Gist 为 Python / pybevy 源码，需要相应运行环境。')
if 'repo-staypzy' not in {x['id'] for x in data['repos']}:
    data['repos'].append(dict(id='repo-staypzy', title='prab（原文件 staypzy.zip）', url='', date='2026', notes='DeepSeek V4.1 Flash 生成的鹈鹕骑车 HTML；原包已核验，原仓库地址待确认。', zip='repos/staypzy.zip', demo='demos/staypzy/index.html', form='html-anim'))
byid['zeos-submission-site-2026-09-26']['notes'] = '中文投稿小站：存源码和实际提示词，不打分。原帖视频已存档；原帖中的 t.co 实际指向视频，未提供站点域名，域名仍待作者公开。'
byid['roger-rabbit-1988']['date'] = '1988'
data['stats']['repos'] = len(data['repos'])
(WEB / 'data.js').write_text('window.PELICAN = ' + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + ';\n', encoding='utf-8')
(AUDIT / 'demo-recovery.json').write_text(json.dumps(dict(pages=pages, assets=assets, problems=problems), ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'demo_pages': len(pages), 'dependencies': len(assets), 'problems': problems}, ensure_ascii=False), flush=True)
