"""Chronological display numbers and conservative, source-labelled model names."""
import html
import re

# Reviewed labels that mix model names with tools, effort settings or commentary.
# The original model field and attribution caveats remain intact in the record.
MODEL_LABELS = {
    '16 models (Claude 3.5 / GPT-4o / Gemini 1.5 / Llama 3.1 ...)': ['Claude 3.5', 'GPT-4o', 'Gemini 1.5', 'Llama 3.1'],
    '34 pelicans; Gemini 2.5 Pro preview won': ['Gemini 2.5 Pro preview'],
    '14 models; gpt-6-astra 98': ['gpt-6-astra'],
    '12 models, Astra 1st (94)': ['Astra'],
    'ChatGPT Agent + Excalidraw': [], 'Claude + ffmpeg geq': ['Claude'],
    'Claude render-iterate': ['Claude'], 'Claude 3.5 Sonnet new vs previous': ['Claude 3.5 Sonnet'],
    'GPT-5.3 Codex Spark vs Codex': ['GPT-5.3 Codex Spark', 'Codex'],
    'GPT-4.1-mini consortium 9x2': ['GPT-4.1-mini'],
    'GPT-3.5 → GPT-6 montage': ['GPT-3.5', 'GPT-6'],
    'DeepSeek-V3.1 instruct vs reasoner': ['DeepSeek-V3.1 (instruct)', 'DeepSeek-V3.1 (reasoner)'],
    'GPT-5.4 all efforts via Codex': ['GPT-5.4'],
    'Gemini 1.5 Flash 001/002': ['Gemini 1.5 Flash 001', 'Gemini 1.5 Flash 002'],
    'Gemini 3 / GPT-5.1 / Sonnet 4.5': ['Gemini 3', 'GPT-5.1', 'Sonnet 4.5'],
    'Gemini 3 Pro / Heavy / Opus 4.5': ['Gemini 3 Pro', 'Heavy', 'Opus 4.5'],
    'Gemini 3.0 Latest A/B ckpt': ['Gemini 3.0'],
    'Gemini 3.0 Pro Arena lithimflow': ['Gemini 3.0 Pro'],
    'Gemini 4 Pro checkpoint 1 vs 2 (unofficial label)': ['Gemini 4 Pro checkpoint 1', 'Gemini 4 Pro checkpoint 2'],
    'alleged Gemini 4 Pro ckpts': ['Gemini 4 Pro'],
    'GPT Astra leak': ['GPT Astra'], 'Codex Astra': ['Astra'],
    'relay wrappers spoofing GPT-6 Astra': [],
    'Luna / Sol / Astra × 5 effort': ['Luna', 'Sol', 'Astra'],
    'Astra/Sol/Luna multi-effort': ['Astra', 'Sol', 'Luna'],
    'Astra / Gemini 3.8 Flash / DeepSeek 4.1 Flash': ['Astra', 'Gemini 3.8 Flash', 'DeepSeek 4.1 Flash'],
    'Opus 5.5 / GPT-6 Sol / Luna': ['Opus 5.5', 'GPT-6 Sol', 'Luna'],
    'Muse Spark / 1.1 / 1.2': ['Muse Spark', 'Muse Spark 1.1', 'Muse Spark 1.2'],
    'Hermes Agent -> FAL -> FLUX': ['FLUX'],
    'Qwen3.6-35B-A3B (Q4 laptop) vs Claude Opus 4.7': ['Qwen3.6-35B-A3B', 'Claude Opus 4.7'],
    'Qwen3.6 vs Opus 4.7 flamingo': ['Qwen3.6', 'Opus 4.7'],
    'Qwen3.6 distill Claude vs base': ['Qwen3.6 (Claude distill)', 'Qwen3.6 (base)'],
    'Step 5 Preview / OpenCode V2': ['Step 5 Preview'],
    'Gemini Flash 3.8 high Antigravity': ['Gemini Flash 3.8'],
    'multi + Grok 3 mashup': ['Grok 3'], 'talkie vintage LM': ['talkie'],
    'Codex（底层模型未公开）/ Claude Opus 5.5（作者标注）': ['Claude Opus 5.5'],
}
UNKNOWN_LABELS = {'', 'multi', 'multi aiznb.com', 'multi best/worst', 'four models', '6 models Space Invaders',
                  '22 SVGs in repo', 'AI 3D print', 'AI 3D printable mesh', 'QBasic', 'Pelicycle meme',
                  'Quiver + Cursor + Remotion', 'OpenEnv RL env', 'human+AI product', 'meta',
                  'Google I/O keynote', 'Google I/O keynote cameo', 'OpenAI livestream 3D pelicans',
                  'mystery voxel', 'stacked tests', 'survey', 'practical+animation', 'wild variant',
                  '多模型 / 多推理档位', 'POV-Ray variant by BeetleB', 'DeepSeek OSS 15min'}


def model_names(label):
    if label in MODEL_LABELS:
        return MODEL_LABELS[label][:]
    if label in UNKNOWN_LABELS or label.lower().startswith('unspecified'):
        return []
    # Slash-delimited provider IDs (e.g. Qwen/Qwen3.6-27B) are not split.
    parts = re.split(r'\s+(?:/|vs|\+)\s+', label)
    names = []
    for part in parts:
        part = re.sub(r'（(?:作者标注|上游标注)）|\((?:author-reported|claimed|site claims|free tier|Free|xhigh|Q4 laptop)\)', '', part).strip()
        part = re.split(r'\s+·\s+|\s+→\s+|\s+×\s+|\s+(?:via|on|lineage|wave observation|medium|multi-effort|降智监测|default vs high|checkpoints|family|ckpt|enhanced)\b', part)[0]
        part = re.sub(r'\s+(?:Max|max|high|1\.5TB|16\.8GB|15GB|20GB|17GB GGUF|GGUF)$', '', part)
        part = re.sub(r'\s+\(compared with.*\)$', '', part)
        if part in {'After Effects', 'OpenSCAD', 'local Blender', 'p5.js', 'enhanced prompt'}:
            continue
        if part and part not in names:
            names.append(part)
    return names


def apply_card_metadata(items):
    from experiment_batches import group_records
    cases = sorted(group_records(items), key=lambda x: (x['date'], x['id']))
    numbers = {x['id']: number for number, x in enumerate(cases, 1)}
    for item in items:
        key = 'batch-'+item['batch']['id'] if item.get('batch') else item['id']
        item['caseNumber'] = numbers.get(key)
        item['modelNames'] = item.get('reviewedModelNames') or model_names(item['model'])
    return items


def card_footer(item, language='zh', timeline=False):
    escape = lambda value: html.escape(str(value), quote=True)
    en = language == 'en'
    names = item.get('modelNames') or ['Model not specified' if language == 'en' else '模型未标注']
    models = ''.join(f'<span class="model-name">{escape(name)}</span>' for name in names)
    number = ('Scoring reference' if language == 'en' else '评分参考') if item.get('referenceOnly') else '#'+str(item['caseNumber']) if item.get('caseNumber') else ('Source archive' if language=='en' else '来源存档')
    date = item.get('date') or ('Date not recorded' if en else '日期未记录')
    date_label = date + ((' · exact day unknown' if en else ' · 具体日未知') if item.get('datePrecision') == 'month' else '')
    date_class = 'timeline-date' if timeline else 'card-date'
    time = f'<time class="{date_class}" datetime="{escape(item.get("date", ""))}" title="{escape(date_label)}" aria-label="{escape(date_label)}">{escape(date)}</time>'
    if timeline:
        models = '<a href="'+escape(item['path'])+'">'+escape(names[0])+'</a>'
    row_class, model_class = ('timeline-meta', 'timeline-model') if timeline else ('card-foot', 'card-models')
    return f'<div class="{row_class}"><span class="case-number" aria-label="{escape(number)}">{escape(number)}</span><div class="{model_class}" tabindex="0" aria-label="{"Source-labelled models" if en else "来源标注的模型"}" title="{escape(item["model"])}">{models}</div>{time}</div>'
