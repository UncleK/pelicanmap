"""Restore real source media and record provenance without inventing illustrations."""
from archive_io import ROOT, WEB, AUDIT, records, text_for, fetch_batch
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from zipfile import ZipFile, ZIP_DEFLATED
from collections import Counter
import json
import re
import shutil
import xml.etree.ElementTree as ET

data = json.loads((AUDIT / 'before-data.js').read_text(encoding='utf-8').split('=', 1)[1].strip().removesuffix(';'))
cases = json.loads((ROOT / 'pelican-archive/normalized/community-cases.json').read_text(encoding='utf-8'))
case_by_id = {x['id']: x for x in cases}
items = {x['id']: x for x in data['timeline']}
for c in cases:
    if c['id'] in items:
        continue
    date = c.get('date', '')
    level = c.get('level', 'meta')
    x = {k: c.get(k, '') for k in ['id', 'date', 'author', 'handle', 'model', 'form', 'level', 'lang', 'notes']}
    x.update(ym=date[:7] if re.match(r'\d{4}-\d{2}', date) else 'undated', levelN=level[:2] if level.startswith('L') else 'meta', url=c['source_url'], media='', src='community')
    data['timeline'].append(x)
    items[x['id']] = x

plan = {}
def add(item_id, source, caption='', poster=None, local=None):
    rows = plan.setdefault(item_id, [])
    if any(x.get('source') == source and x.get('local') == local for x in rows):
        return
    row = dict(source=source, caption=caption)
    if poster:
        row['poster_source'] = poster
    if local:
        row['local'] = local
    rows.append(row)

def tweet_assets(item_id, tweet, label='原帖附件'):
    for media in (tweet.get('media') or {}).get('all', []):
        if media.get('url'):
            url = media['url']
            if records().get(url, {}).get('error', '').startswith('Response exceeds'):
                variants = [v for v in media.get('variants', []) if v.get('content_type') == 'video/mp4' and 0 < v.get('bitrate', 0) <= 3000000]
                if variants:
                    url = max(variants, key=lambda v: v['bitrate'])['url']
            add(item_id, url, label, media.get('thumbnail_url'))

for item in data['timeline']:
    match = re.search(r'/status/(\d+)', item['url'])
    if not match:
        continue
    raw = text_for('https://api.fxtwitter.com/status/' + match[1])
    if not raw:
        continue
    tweet = json.loads(raw).get('tweet') or {}
    tweet_assets(item['id'], tweet)
    if not plan.get(item['id']) and not item.get('media'):
        tweet_assets(item['id'], tweet.get('quote') or {}, '所引用原帖的附件')
    if item['id'] in ['x-1896464903247995080', 'x-1905810013286789275']:
        parent = json.loads(text_for('https://api.fxtwitter.com/status/' + tweet['replying_to_status'])).get('tweet') or {}
        tweet_assets(item['id'], parent, '同一作者所回复的原帖附件')
    item['sourceChecked'] = True
    if not plan.get(item['id']) and not item.get('media'):
        item.update(mediaStatus='text-only', mediaNote='原帖未附图片或视频，可打开原帖查看文字与引用。')

def page_assets(item_id, url, pattern=None, video=False):
    soup = BeautifulSoup(text_for(url), 'html.parser')
    body = soup.select_one('#primary') or soup.select_one('main') or soup
    if video:
        for v in body.find_all('video'):
            source = v.get('src') or (v.find('source') or {}).get('src')
            if source:
                add(item_id, urljoin(url, source), '原文视频', urljoin(url, v['poster']) if v.get('poster') else None)
        return
    for img in body.find_all('img'):
        src = img.get('src') or img.get('data-src') or ''
        if not src or src.startswith('data:'):
            continue
        if pattern and not re.search(pattern, src, re.I):
            continue
        add(item_id, urljoin(url, src), img.get('alt') or '原文配图')

page_assets('roger-rabbit-1988', items['roger-rabbit-1988']['url'], video=True)
page_assets('google-io-2025-05-20', items['google-io-2025-05-20']['url'], video=True)
for item_id in ['github-simonw-pelican-bicycle', 'origin-simon-2024-10-25']:
    for name in ['claude-3-5-sonnet-20240620.svg', 'claude-3-5-sonnet-20241022.svg', 'gpt-4o.svg', 'gemini-1.5-flash-001.svg']:
        add(item_id, items[item_id]['url'], '原点仓库中的 ' + name, local='media/origin/' + name)
add('deepseek-r1-stock-pelican-2025-01', items['deepseek-r1-stock-pelican-2025-01']['url'], '原文的 DeepSeek R1 演示页', local='media/zoo/specimen_ai-worlds-fair-2025-10.jpeg')
page_assets('elo-june-2025', items['elo-june-2025']['url'], r'ai-worlds-fair-2025-31\.jpeg')
for item_id, url, pattern in [
    ('x-1902509366244471291', 'https://simonwillison.net/2025/Mar/19/o1-pro/', r'o1-pro.*pelican'),
    ('x-1972728005878538430', 'https://simonwillison.net/2025/Sep/23/gpt-5-codex/', r'pelican'),
    ('x-1989123523206578351', 'https://simonwillison.net/2025/Nov/13/gpt-51/', r'pelican'),
    ('v2-prompt-gemini3-2025-11', 'https://simonwillison.net/2025/Nov/18/gemini-3/', r'gemini-3-breeding-pelican'),
    ('x-1990858057153142870', 'https://simonwillison.net/2025/Nov/18/gemini-3/', r'gemini-3-breeding-pelican'),
    ('x-2016168039809773925', 'https://simonwillison.net/2026/Jan/27/kimi-k25/', r'pelican'),
    ('x-2021665936328306924', 'https://simonwillison.net/2026/Feb/11/glm-5/', r'pelican'),
    ('x-2024544280451350689', 'https://simonwillison.net/2026/Feb/19/gemini-31-pro/', r'pelican'),
    ('x-2026996387158589594', 'https://simonwillison.net/2026/Feb/12/gemini-3-deep-think/', r'pelican'),
    ('qwen36-beats-opus47-2026-04-16', 'https://simonwillison.net/2026/Apr/16/qwen-beats-opus/', r'pelican|flamingo'),
    ('x-simon-qwen36-2026-04-22', 'https://simonwillison.net/2026/Apr/22/qwen36-27b/', r'Qwen3\.6-27B'),
    ('x-simon-granite-21quant-2026-05-04', 'https://simonwillison.net/2026/May/4/granite-41-3b-svg-pelican-gallery/', r'pelican'),
    ('x-2072068898648949184', 'https://simonwillison.net/2026/Jun/30/claude-sonnet-5/', r'pelican'),
    ('astra-grid-2026-09-04', 'https://simonwillison.net/2026/Sep/4/astra-pelicans/', r'astra-grid'),
    ('x-jp-ai-joryushi-2026-09-23', 'https://simonwillison.net/2026/Sep/22/opus-and-sol-and-luna/', r'pelicans-grid'),
    ('jimu-14model-ik-score', 'https://bbs.jimu.chat/t/topic/92', r'/uploads/'),
    ('juejin-12model-3d-2026-09-13', 'https://juejin.cn/post/7684937171811221513', r'xtjj'),
    ('juejin-parrot-variant-astra-2026-09-17', 'https://juejin.cn/post/7686318450944671787', r'xtjj'),
]:
    page_assets(item_id, url, pattern)
add('fable-51-max-animated-2026-09-01', items['fable-51-max-animated-2026-09-01']['url'], '原文 max 档 SVG 动画', local='media/zoo/live_fable-5.1-max.svg')
for filename in ['pelican-bicycle.png', 'pelican-bicycle-festival.png', 'pelican-coastal-parade.png']:
    dest = WEB / 'media/blender' / filename
    dest.parent.mkdir(exist_ok=True)
    shutil.copy2(ROOT / 'gpt-6-astra-blender-pelican-bicycle-main/outputs' / filename, dest)
    add('blender-astra-2026-09-05', items['blender-astra-2026-09-05']['url'], '仓库原始 Blender 渲染图', local=dest.relative_to(WEB).as_posix())
with ZipFile(WEB / 'repos/tihuqiche.zip') as z:
    name = next(n for n in z.namelist() if n.endswith('/docs/preview.png'))
    dest = WEB / 'media/recovered/tihuqiche-preview.png'
    dest.parent.mkdir(exist_ok=True)
    dest.write_bytes(z.read(name))
    add('tihuqiche-game', items['tihuqiche-game']['url'], '仓库原始游戏截图', local=dest.relative_to(WEB).as_posix())

# The gist contains the actual generated SVG, rather than a fabricated replacement.
gist_page = 'https://gist.github.com/simonw/d8a50200edd5d463b7ce0791c2242c87'
for url, row in records().items():
    if url.startswith(gist_page + '/raw/'):
        blocks = re.findall(r'```(?:svg|xml|html)?\s*(<svg\b[\s\S]*?</svg>)\s*```', text_for(url))
        if blocks:
            svg = blocks[-1]
            ET.fromstring(svg)
            path = WEB / 'media/recovered/qwq-original.svg'
            path.write_text(svg, encoding='utf-8')
            add('x-1871621125991715036', gist_page, '原帖链接 Gist 中的原始 SVG', local=path.relative_to(WEB).as_posix())

for item in data['gallery']:
    if item.get('media'):
        continue
    page_assets(item['id'], item['url'], r'/fed/')
    # Submission dates are present in the archived specimen URL.
    date = re.search(r'\d{4}-\d{2}-\d{2}$', item['url'])
    if date:
        item.update(date=date[0], ym=date[0][:7], form='svg')

(AUDIT / 'media-plan.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding='utf-8')
urls = []
for rows in plan.values():
    for row in rows:
        if not row.get('local'):
            urls.append(row['source'])
        if row.get('poster_source'):
            urls.append(row['poster_source'])
fetched = fetch_batch(urls, kind='media', media=True)
for item in data['timeline'] + data['gallery']:
    restored = []
    for row in plan.get(item['id'], []):
        local = row.get('local')
        if not local:
            result = fetched[row['source']]
            if result.get('error'):
                continue
            local = (ROOT / result['file']).relative_to(WEB).as_posix()
        media = dict(src=local, source=row['source'], caption=row['caption'])
        if row.get('poster_source'):
            poster = fetched.get(row['poster_source'])
            if poster and not poster.get('error'):
                media['poster'] = (ROOT / poster['file']).relative_to(WEB).as_posix()
        restored.append(media)
    if restored:
        item.update(media=restored[0]['src'], mediaItems=restored, local=True, mediaStatus='local')
        item.pop('mediaNote', None)
    elif item.get('media', '').startswith(('http:', 'https:')):
        item.update(externalMediaUrl=item['media'], media='', mediaStatus='interactive', mediaNote='交互页面或外部视频，请打开演示。')
    elif not item.get('media') and not item.get('mediaStatus'):
        item.update(mediaStatus='unavailable', mediaNote='原始来源尚未提供可下载的媒体。')
    elif item.get('media'):
        item.update(local=True, mediaStatus='local')

data['simon'] = json.loads((AUDIT / 'simon-posts-complete.json').read_text(encoding='utf-8'))
for post in data['simon']:
    row = records().get(post['url'])
    if row and row.get('file'):
        post['snapshot'] = '../' + row['file']
data['timeline'].sort(key=lambda x: (x.get('ym', ''), x.get('date', ''), x['id']))
data['stats'].update(timeline=len(data['timeline']), gallery=len(data['gallery']), simon=len(data['simon']), timeline_local=sum(bool(x.get('media')) for x in data['timeline']), gallery_local=sum(bool(x.get('media')) for x in data['gallery']), years=dict(Counter(x['ym'][:4] for x in data['timeline'])))
(WEB / 'data.js').write_text('window.PELICAN = ' + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + ';\n', encoding='utf-8')
print(json.dumps({'timeline': len(data['timeline']), 'timeline_with_media': data['stats']['timeline_local'], 'gallery_with_media': data['stats']['gallery_local'], 'no_media': [(x['id'], x.get('mediaStatus')) for x in data['timeline'] if not x.get('media')], 'media_failures': [x for x in fetched.values() if x.get('error')]}, ensure_ascii=False), flush=True)
