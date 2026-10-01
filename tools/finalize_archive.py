from archive_io import ROOT, WEB, AUDIT, records, text_for, fetch_batch
from bs4 import BeautifulSoup
from pathlib import Path
from collections import Counter
from urllib.parse import quote
import csv
import html
import json
import shutil

data = json.loads((WEB / 'data.js').read_text(encoding='utf-8').split('=', 1)[1].strip().removesuffix(';'))
byid = {x['id']: x for x in data['timeline']}
byid['baiguangru-2d3d-regression'].update(demoRequiresServer=True, mediaNote='本地 2D / 3D 演示已保存；3D 模块需要通过 HTTP 服务打开。')
byid['x-janek-db32-4kb-2026-09-26']['demoRequiresServer'] = True

# Preserve the generated output from the public Discourse conversation verbatim.
discourse_url = 'https://meta.discourse.org/discourse-ai/ai-bot/shared-ai-conversations/ujjnF7YOi1EJiVXaX8Gp0g'
soup = BeautifulSoup(text_for(discourse_url), 'html.parser')
markup = soup.select_one('pre code.lang-html').get_text()
css = soup.select_one('pre code.lang-css').get_text()
path = WEB / 'demos/sites/discourse-gemini25.html'
path.write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Gemini 2.5 Pro — original shared output</title><style>' + css + '</style><body>' + markup + '</body></html>', encoding='utf-8')
byid['x-1935168106227450264'].update(demo='demos/sites/discourse-gemini25.html', mediaStatus='interactive', mediaNote='原始对话提供的是 HTML / CSS 动画，已组合为本地演示。', form='html-css-animated', level='L2', levelN='L2')

# A quote contains an X long-form article, whose attachments are not in tweet.media.
tweet = json.loads(text_for('https://api.fxtwitter.com/status/2082838625520365629'))['tweet']
article = tweet['quote']['article']
article_url = tweet['quote']['url']
article_images = [article['cover_media']] + article.get('media_entities', [])
image_urls = [x['media_info']['original_img_url'] for x in article_images if x.get('media_info', {}).get('original_img_url')]
fetched = fetch_batch(image_urls, kind='article-media', media=True)
media = [dict(src=(ROOT / fetched[u]['file']).relative_to(WEB).as_posix(), source=article_url, caption='所引用的 OpenEnv 原文配图') for u in image_urls if not fetched[u].get('error')]
byid['x-2082838625520365629'].update(media=media[0]['src'], mediaItems=media, mediaStatus='local', local=True)
byid['x-2082838625520365629'].pop('mediaNote', None)
article_path = WEB / 'demos/sites/openenv-article.html'
article_path.write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>' + html.escape(article['title']) + '</title><style>body{max-width:900px;margin:40px auto;font:18px/1.6 system-ui;padding:20px;background:#faf7ee}img{max-width:100%}pre{white-space:pre-wrap}</style><h1>' + html.escape(article['title']) + '</h1><p><a href="' + article_url + '">Original article</a></p>' + ''.join('<p>' + html.escape(b.get('text', '')) + '</p>' for b in article['content']['blocks']) + ''.join('<img src="../../' + m['src'] + '" alt="Original article attachment">' for m in media) + '</html>', encoding='utf-8')
byid['x-2082838625520365629']['sourceCode'] = 'demos/sites/openenv-article.html'

mimo_url = 'https://aistudio.xiaomimimo.com/#/share/e2b2554412f608bd4755709d64b5d8c1'
byid['x-2048412520977772602'].update(mediaStatus='source-deleted', mediaNote='MiMo 分享页提示：原对话已被删除，无法继续查看分享。', externalMediaUrl=mimo_url)
(AUDIT / 'source-limitations.json').write_text(json.dumps([
    dict(id='x-2048412520977772602', url=mimo_url, evidence='Browser accessibility tree on 2026-09-27: 原对话已被删除，无法继续查看分享', status='source-deleted'),
    dict(id='zeos-submission-site-2026-09-26', evidence='Original tweet API facets identify t.co/SWuigjh4EO as the attached video, not a website link. Video recovered; no site hostname provided.', status='site-domain-unpublished'),
    dict(id='repo-staypzy', evidence='Existing staypzy.zip has root prab-main and commit 228883ff3cece701b38d0bf8ec23875becf7926e; owner/repository URL not present. Candidate GitHub URL returned 404.', status='original-url-unverified'),
    dict(id='x-1884153275223793752', evidence='The public tweet was archived. Linked WSJ article returned HTTP 401; no attempt was made to bypass access restrictions.', status='article-access-restricted'),
    dict(id='x-simon-openai-livestream-3d-2026-07-09', evidence='Original public YouTube link retained; full livestream has not been downloaded.', status='external-video'),
    dict(id='browser-validation', evidence='Browser tool refused file:///D:/VP/pelican/pelican-web/index.html under its URL security policy. No browser workaround was attempted.', status='local-browser-check-blocked')
], ensure_ascii=False, indent=2), encoding='utf-8')

staypzy = next(x for x in data['repos'] if x['id'] == 'repo-staypzy')
staypzy.update(title='prab（原文件 staypzy.zip）', url='', notes='原包 README 标注为 DeepSeek V4.1 Flash 生成。ZIP 和本地演示均已保存；原仓库地址尚无法核实。')

# Add index pages for extracted specimen sets, so every retained demo is discoverable.
def listing(title, files, root):
    return '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>' + html.escape(title) + '</title><style>body{max-width:1100px;margin:36px auto;padding:20px;font:16px/1.7 system-ui;background:#f7f0de;color:#352819}input{font:inherit;padding:10px;width:90%}ul{columns:2;column-width:340px}li{break-inside:avoid;overflow-wrap:anywhere}a{color:#365344}</style><h1>' + html.escape(title) + '</h1><p>HTML / SVG 为原始收集文件；DB32 交互运行需要 HTTP 服务。</p><input placeholder="筛选文件名" oninput="document.querySelectorAll(\'li\').forEach(x=>x.hidden=!x.textContent.toLowerCase().includes(this.value.toLowerCase()))"><ul>' + ''.join('<li><a href="' + quote(p.relative_to(root).as_posix()) + '" target="_blank">' + html.escape(p.relative_to(root).as_posix()) + '</a></li>' for p in files) + '</ul></html>'

for repo in data['repos']:
    if not repo.get('zip'):
        continue
    folder = WEB / 'demos' / Path(repo['zip']).stem
    if not folder.is_dir():
        continue
    files = sorted(p for p in folder.rglob('*') if p.is_file() and p.suffix.lower() in ['.html', '.svg'])
    if files and not (folder / 'index.html').exists():
        (folder / 'index.html').write_text(listing(repo['title'], files, folder), encoding='utf-8')
    if (folder / 'index.html').exists():
        repo['demo'] = (folder / 'index.html').relative_to(WEB).as_posix()
all_demos = sorted(p for p in (WEB / 'demos').rglob('*') if p.is_file() and p.suffix.lower() in ['.html', '.svg'] and p != WEB / 'demos/index.html' and '_assets' not in p.parts)
(WEB / 'demos/index.html').write_text(listing('本地演示目录', all_demos, WEB / 'demos'), encoding='utf-8')

# Keep the archival schema, preserve historical metadata, and bring it in sync
# with the website. Raw source snapshots remain separate and unmodified.
normalized = ROOT / 'pelican-archive/normalized'
for name in ['catalog.json', 'catalog.csv', 'community-cases.json']:
    backup = AUDIT / ('before-' + name)
    if not backup.exists():
        shutil.copy2(normalized / name, backup)
old_catalog = json.loads((AUDIT / 'before-catalog.json').read_text(encoding='utf-8'))
old_cases = json.loads((AUDIT / 'before-community-cases.json').read_text(encoding='utf-8'))
old_galleries = {x.get('page_url'): x for x in old_catalog if x['collection'] in ['pelicans.wtf', 'pelicanzoo.ai']}
catalog = []
for item in data['gallery']:
    row = dict(old_galleries.get(item['url'], {}))
    row.setdefault('id', item['id'])
    row.update(date=item['date'], model=item['model'], form=item['form'], collection={'origin': 'simonw/pelican-bicycle', 'zoo': 'pelicanzoo.ai', 'wtf': 'pelicans.wtf'}[item['src']], page_url=item['url'], local_media='../pelican-web/' + item['media'])
    row.setdefault('source_url', item['url'])
    row.setdefault('prompt_version', item.get('prompt', 'classic'))
    catalog.append(row)
updated_cases = []
for case in old_cases:
    item = byid[case['id']]
    case = dict(case)
    case.update(form=item['form'], level=item['level'], local_media=('../pelican-web/' + item['media']) if item.get('media') else '', capture_status=item['mediaStatus'], local_demo=('../pelican-web/' + item['demo']) if item.get('demo') else '', media_items=item.get('mediaItems', []))
    if case['id'] in ['zeos-submission-site-2026-09-26', 'x-2048412520977772602']:
        case['capture_note'] = item.get('mediaNote', item.get('notes'))
    updated_cases.append(case)
    row = {k: case.get(k, '') for k in ['id', 'date', 'model', 'vendor', 'effort', 'prompt_version', 'form', 'level', 'collection', 'lang', 'source_url', 'notes']}
    row.update(page_url=case['source_url'], local_media=case['local_media'], capture_status=case['capture_status'], local_demo=case['local_demo'])
    catalog.append(row)
for post in data['simon']:
    catalog.append(dict(id='simon:' + post['url'], date=post['date'], model='', vendor='', effort='', prompt_version='', form='blog-post', level='', collection='simonwillison.net', lang='en', source_url=post['url'], page_url=post['url'], local_media='', local_snapshot=post.get('snapshot', '').replace('../pelican-archive/', ''), notes=post['title']))
assert len({x['id'] for x in catalog}) == len(catalog)
catalog.sort(key=lambda x: (x.get('date') or '', x['id']))
(normalized / 'catalog.json').write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding='utf-8')
(normalized / 'community-cases.json').write_text(json.dumps(updated_cases, ensure_ascii=False, indent=2), encoding='utf-8')
fields = list(dict.fromkeys(k for row in catalog for k in row))
with (normalized / 'catalog.csv').open('w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(catalog)

for name in ['simon-posts.full.json']:
    path = ROOT / 'pelican-archive/raw' / name
    backup = AUDIT / ('before-' + name)
    if not backup.exists():
        shutil.copy2(path, backup)
    path.write_text(json.dumps(data['simon'], ensure_ascii=False, indent=2), encoding='utf-8')

media_files = [p for p in (WEB / 'media').rglob('*') if p.is_file()]
data['stats'].update(timeline=len(data['timeline']), gallery=len(data['gallery']), simon=len(data['simon']), catalog=len(catalog), repos=len(data['repos']), demo_files=len(all_demos), timeline_local=sum(bool(x.get('media')) for x in data['timeline']), gallery_local=sum(bool(x.get('media')) for x in data['gallery']), zoo_media=sum(x['src']=='zoo' and bool(x.get('media')) for x in data['gallery']), local_clips=sum(p.suffix.lower() in ['.mp4', '.webm'] for p in media_files), local_media_files=len(media_files))
(WEB / 'data.js').write_text('window.PELICAN = ' + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + ';\n', encoding='utf-8')
print(json.dumps(data['stats'], ensure_ascii=False))
