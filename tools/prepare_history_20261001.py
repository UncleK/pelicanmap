"""Approved five static-SVG cases and the existing June 2025 page repair.

Read public source data; never run upstream scripts or modify original media.
The reviewed manifest is consumed by import_collection_batch.mjs.
"""
import hashlib
import io
import json
import re
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BATCH = '2026-10-01-history-static'
ARCHIVE = ROOT/'pelican-archive/research'/BATCH
ARCHIVE.mkdir(parents=True, exist_ok=True)


def fetch(url):
    with urlopen(Request(url, headers={'User-Agent': 'PelicanMap-HistoryCollector/1.0'}), timeout=35) as response:
        assert response.status == 200
        data = response.read(8*1024*1024+1)
        assert len(data) <= 8*1024*1024
        return data


def preserve(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        assert path.read_bytes() == data, 'Refusing to replace '+str(path)
    else:
        path.write_bytes(data)


sources = [
    ('simon-gemini-flash-default-2025-04-17', 'afce6639ed10c712a0778fc779efd756',
     'https://simonwillison.net/2025/Apr/17/start-building-with-gemini-25-flash/', '2025-04-17',
     'gemini-2.5-flash-preview-04-17', '默认 thinking', 'default thinking',
     'Gemini 2.5 Flash · 默认 thinking', 'Gemini 2.5 Flash · default thinking',
     '作者使用默认 thinking 设置获得的静态 SVG；与当天 maximum-budget 输出不是同一次运行。'),
    ('simon-gemini-flash-budget-zero-2025-04-17', '182679e918ab5263f98f6a65691874d1',
     'https://simonwillison.net/2025/Apr/17/start-building-with-gemini-25-flash/', '2025-04-17',
     'gemini-2.5-flash-preview-04-17', 'thinking_budget=0', 'thinking_budget=0',
     'Gemini 2.5 Flash · thinking budget 0', 'Gemini 2.5 Flash · thinking budget 0',
     '作者以 thinking_budget 0 单独运行同一题面；原文仍报告少量 thinking tokens，不改写为绝对没有思考。'),
    ('simon-gemini-flash-budget-zero-2025-05-20', '3e6740d2a99be4922af455d14bc1c943',
     'https://simonwillison.net/2025/May/20/gemini-25/', '2025-05-20',
     'gemini-2.5-flash-preview-05-20', 'thinking_budget=0', 'thinking_budget=0',
     'Gemini 2.5 Flash 05-20 · thinking budget 0', 'Gemini 2.5 Flash 05-20 · thinking budget 0',
     '原文关闭 thinking 的独立静态输出，不是另一张已收录作品的动画前帧，也不包含 Now animate it 后续。'),
    ('community-imbajin-opus41-2025-08-12', 'dc784c771bef6c569fb6e2955ad257b5',
     'https://gist.github.com/imbajin/dc784c771bef6c569fb6e2955ad257b5', '2025-08-12',
     'Claude 4.1 Opus（作者标注）', '作者报告的一次输出', 'author-reported single output',
     'imbajin · Claude 4.1 Opus 静态 SVG', 'imbajin · Claude 4.1 Opus static SVG',
     '作者公开 Gist 标为 duckduckgo - claude4.1 opus，并在同页给出经典提示词及未添加其他用户规则的说明；底层模型与访问方式仅为作者报告。'),
    ('simon-qwen30b-thinking-2025-07-30', 'b523c029152f646ce4efb3c4dd5e1d01',
     'https://simonwillison.net/2025/Jul/30/qwen3-30b-a3b-thinking-2507/', '2025-07-30',
     'Qwen3-30B-A3B-Thinking-2507', 'chat.qwen.ai · reasoning', 'chat.qwen.ai · reasoning',
     'Qwen3-30B-A3B-Thinking-2507 · 原始静态输出', 'Qwen3-30B-A3B-Thinking-2507 · original static output',
     'Simon 在 chat.qwen.ai 选择 reasoning 后取得的原始静态 SVG。保留错位的车架和鸟形，不以修正图替代；这不是后来的比格犬衍生题输出。'),
]
english_notes = [
    'A static SVG generated with the default thinking setting, not the separate maximum-budget run from the same date.',
    'A separate run with thinking_budget 0. The original article still reports some thinking tokens; this is not relabelled as absolutely no thinking.',
    'The independently generated non-thinking static output, not a frame from the already archived animation. The later Now animate it follow-up is excluded.',
    'The public Gist is labelled duckduckgo - claude4.1 opus by its author, who provides the classic prompt and says no other user rules were added. Both the model and access method are author-reported only.',
    'Simon selected reasoning in chat.qwen.ai. The original SVG geometry is preserved, including the misplaced bicycle frame and bird, without replacing it with a corrected drawing. It is not a later beagle-task output.',
]
cases = []
for index, entry in enumerate(sources):
    ident, gid, source, date, model, variant, variant_en, title, title_en, notes = entry
    api_url = 'https://api.github.com/gists/'+gid
    api = fetch(api_url)
    preserve(ARCHIVE/(ident+'-gist.json'), api)
    gist = json.loads(api)
    assert gist['owner']['login'] == ('imbajin' if index == 3 else 'simonw')
    assert gist['created_at'][:10] == date
    assert len(gist['files']) == 1
    file = next(iter(gist['files'].values()))
    assert not file.get('truncated')
    raw_url = file['raw_url']
    raw = fetch(raw_url)
    preserve(ARCHIVE/(ident+'-source.txt'), raw)
    body = raw.decode('utf8')
    response = re.split(r'^## Response\s*$', body, flags=re.M)[-1]
    blocks = re.findall(r'<svg\b[\s\S]*?</svg\s*>', response, flags=re.I)
    assert len(blocks) == 1
    assert not re.search(r'<(?:animate|animateTransform|animateMotion|set|script)\b|@keyframes|\banimation\s*:', blocks[0], re.I)
    svg = blocks[0].encode() if not file['filename'].endswith('.svg') else raw
    if source.startswith('https://simonwillison.net/'):
        preserve(ARCHIVE/(ident+'-article.html'), fetch(source))
    cases.append({
        'id': ident, 'sourceUrl': source, 'date': date, 'dateBasis': 'source-publication',
        'model': model, 'modelEn': model.replace('（作者标注）', ' (author-reported)'),
        'author': 'imbajin' if index == 3 else 'Simon Willison', 'format': 'svg', 'variant': variant,
        'unitType': 'single-model-output', 'modelToMediaVerified': True,
        'title': {'zh': title, 'en': title_en},
        'notes': {'zh': notes+' 模型标签按来源保留，未独立认证。日期为原文或 Gist 公开日期。SVG 从固定版本的原始响应中逐字提取，没有重画或优化。',
                  'en': english_notes[index]+' Model labels follow the source and are not independently authenticated. The date is the article or Gist publication date. The SVG is copied verbatim from the version-pinned original response, not redrawn or optimized.'},
        'prompt': 'Generate an SVG of a pelican riding a bicycle', 'sourceCodeUrl': gist['html_url'],
        'rights': {'zh': '权利归原作者；原文与 Gist 未提供单独的开放输出许可。本站保留原始来源与署名，不将模型许可当作作品许可。',
                   'en': 'Rights remain with the original author. No separate open output licence was found in the article or Gist. Attribution and source links are retained; a model licence is not treated as an artwork licence.'},
        'evidence': [source, gist['html_url'], api_url, raw_url],
        'media': [{'url': raw_url, 'filename': ident+'.svg', 'sha256': hashlib.sha256(svg).hexdigest(),
                   'svgFromTranscript': not file['filename'].endswith('.svg'),
                   'caption': {'zh': '原始静态 SVG · '+variant, 'en': 'Original static SVG · '+variant_en}}],
    })

manifest = {'reviewed': True, 'batch': BATCH, 'cases': cases}
(ROOT/'deploy-build/history-static-reviewed.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf8')

# Repair the existing page without creating per-slide duplicates or losing its table.
article = 'https://simonwillison.net/2025/Jun/6/six-months-in-llms/'
html = fetch(article)
preserve(ARCHIVE/'simon-june-6-article.html', html)
soup = BeautifulSoup(html, 'html.parser')
images = {int(re.search(r'-([0-9]+)\.jpeg$', img['src'])[1]): img for img in soup.select('.entry img') if re.search(r'ai-worlds-fair-2025-([0-9]+)\.jpeg$', img.get('src', ''))}
captions = {
    26: ('Claude Sonnet 4 / Claude Opus 4 / Gemini 2.5 Pro preview 05-06 · 原文静态 SVG 对照', 'Claude Sonnet 4 / Claude Opus 4 / Gemini 2.5 Pro preview 05-06 · original static SVG comparison'),
    5: ('Amazon Nova Lite / Micro / Pro · 原文静态 SVG', 'Amazon Nova Lite / Micro / Pro · original static SVGs'),
    6: ('Llama 3.1 405B / Llama 3.3 70B · 原文静态 SVG', 'Llama 3.1 405B / Llama 3.3 70B · original static SVGs'),
    7: ('DeepSeek V3 · 原文静态 SVG', 'DeepSeek V3 · original static SVG'),
    10: ('DeepSeek R1 · 原文静态 SVG', 'DeepSeek R1 · original static SVG'),
    11: ('Mistral Small 3 · 原文静态 SVG', 'Mistral Small 3 · original static SVG'),
    13: ('Claude 3.7 Sonnet · 原文静态 SVG', 'Claude 3.7 Sonnet · original static SVG'),
    15: ('GPT-4.5 · 原文静态 SVG', 'GPT-4.5 · original static SVG'),
    18: ('o1-pro · 原文静态 SVG', 'o1-pro · original static SVG'),
    19: ('Gemini 2.5 Pro · 原文静态 SVG', 'Gemini 2.5 Pro · original static SVG'),
    23: ('Llama 4 Scout / Maverick · 原文静态 SVG', 'Llama 4 Scout / Maverick · original static SVGs'),
    24: ('GPT-4.1 nano / mini / GPT-4.1 · 原文静态 SVG', 'GPT-4.1 nano / mini / GPT-4.1 · original static SVGs'),
    25: ('o3 / o4-mini · 原文静态 SVG', 'o3 / o4-mini · original static SVGs'),
    32: ('Gemini 2.5 Pro preview 05-06 / Llama 3.3 70B · 上游对照与判断，非本馆排名', 'Gemini 2.5 Pro preview 05-06 / Llama 3.3 70B · upstream comparison and judgement, not a Pelican Map ranking'),
}
media = []
for number, (zh, en) in captions.items():
    url = urljoin(article, images[number]['src'])
    basename = url.rsplit('/', 1)[-1]
    old = ROOT/'pelican-web/media/zoo'/('specimen_'+basename)
    data = fetch(url)
    if old.exists():
        assert old.read_bytes() == data, 'Old source slide differs from current original'
        src = '/media/zoo/'+old.name
    else:
        src = '/media/collected/'+BATCH+'/'+basename
        preserve(ROOT/'pelican-web'/src.lstrip('/'), data)
    with Image.open(io.BytesIO(data)) as im:
        im.load()
        assert im.width > 20 and im.height > 20
    media.append({'src': src, 'source': url, 'sha256': hashlib.sha256(data).hexdigest(), 'caption': zh, 'captionEn': en, 'poster': ''})
catalog = json.loads((ROOT/'public-site/data/catalog.json').read_text(encoding='utf8'))['items']
existing = next(x for x in catalog if x['id'] == 'elo-june-2025-3ea5a875')
table = dict(next(m for m in existing['media'] if m['source'].endswith('-31.jpeg')))
table['sha256'] = hashlib.sha256((ROOT/'pelican-web'/table['src'].lstrip('/')).read_bytes()).hexdigest()
table['caption'] = '原文 Elo 分数表 · 上游输出，非本馆排名；34 幅作品、560 次对照（作者报告）。'
table['captionEn'] = 'Original Elo table · upstream outputs, not a Pelican Map ranking; 34 drawings and 560 comparisons (author-reported).'
media.append(table)
notes = '此页归档 Simon 2025 年 6 月演讲中的 14 张静态 SVG 作品／对照图及原始 Elo 表，不是只显示评分表。原文涉及 34 幅绘图；本页不声称已归档全部 34 份 SVG 源文件，也不将演讲中的已有作品重复拆成新案例。模型名与花费、560 次对照等按作者报告保留，未独立认证。评分由 GPT-4.1 mini 对图片作比较，属于上游输出，非本馆排名；2025-06-06 是文章公开日期，不是这些历史绘图统一生成日。'
notes_en = 'This page archives 14 original static-SVG illustration/comparison slides and the original Elo table from Simon’s June 2025 talk, rather than displaying only a score table. The article discusses 34 drawings; this page does not claim to archive all 34 SVG source files or count already collected illustrations as new cases. Model names, costs and the reported 560 comparisons are source-reported and not independently authenticated. GPT-4.1 mini judged image pairs: upstream outputs, not a Pelican Map ranking. 2025-06-06 is the article publication date, not a shared generation date for these historical drawings.'
models = 'Amazon Nova Lite / Amazon Nova Micro / Amazon Nova Pro / Llama 3.1 405B / Llama 3.3 70B / DeepSeek V3 / DeepSeek R1 / Mistral Small 3 / Claude 3.7 Sonnet / GPT-4.5 / o1-pro / Gemini 2.5 Pro / Llama 4 Scout / Llama 4 Maverick / GPT-4.1 nano / GPT-4.1 mini / GPT-4.1 / o3 / o4-mini / Claude Sonnet 4 / Claude Opus 4 / Gemini 2.5 Pro preview 05-06'
repair = {existing['id']: {'sourceUrl': article, 'fields': {
    'title': '2025 上半年 · SVG 鹈鹕作品回顾与 Elo 对照', 'model': models,
    'notes': notes, 'promptStatus': 'Generate an SVG of a pelican riding a bicycle',
    'thumbnail': media[0]['src'], 'media': media,
    'i18n': {'en': {'title': 'First half of 2025 · SVG pelican retrospective and Elo comparison', 'notes': notes_en, 'promptStatus': 'Generate an SVG of a pelican riding a bicycle'}},
    'recordRepair': {'date': '2026-10-01', 'sourceUrl': article, 'reason': 'The old page displayed only the Elo table, omitting the actual illustration slides.', 'preservedOriginalId': existing['originalId'], 'originalMediaCount': 1, 'staticIllustrationSlides': 14},
}}}
(ROOT/'site/record-overrides.json').write_text(json.dumps(repair, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
print(json.dumps({'reviewedCases': len(cases), 'existingPage': existing['id'], 'illustrationSlides': 14, 'mediaTotal': len(media)}, ensure_ascii=False))
