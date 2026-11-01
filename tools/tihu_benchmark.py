"""Source-bound Tihu benchmark snapshots; original specimen URLs stay valid."""
import html
import hashlib
import json
from collections import Counter
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
E = lambda value: html.escape(str(value), quote=True)
COLLECTION = 'tihu-2026-11-01'
PATH = '/collections/'+COLLECTION+'/'


@lru_cache(maxsize=1)
def load():
    return json.loads((ROOT/'site/benchmarks'/f'{COLLECTION}.json').read_text(encoding='utf8'))


def record_details(item, language='zh'):
    en = language == 'en'
    t = lambda zh, english: english if en else zh
    local = ('/en' if en else '')+PATH
    label = t('上游输出，非本馆排名', 'Upstream outputs, not a Pelican Bicycle Archive ranking')
    note = t('Tihu Benchmark 样本；不计入常规馆藏或时间线。', 'Tihu Benchmark sample; excluded from the main collection and timeline.')
    old = item['archivedCaseNumber']
    return ('<section class="benchmark-note" data-tihu-reference="true"><strong>'+E(label)+'</strong><p>'+E(note)+
            '</p><p>'+E(t('原馆藏编号', 'Former archive number'))+f' #{old}</p><p><a href="{local}">'+
            E(t('查看 Tihu Benchmark 合集 →', 'Open Tihu Benchmark collection →'))+'</a></p></section>')


def pages(items, language='zh'):
    en = language == 'en'
    t = lambda zh, english: english if en else zh
    data = load()
    by_id = {item['id']: item for item in items}
    rows = data['rows']
    assert all(by_id[row['id']].get('referenceOnly') for row in rows)
    title = t('Tihu · 鹈鹕 SVG 专项评测', 'Tihu · Pelican SVG benchmark')
    description = t('按模型与档位集中查看 Tihu 公开测试样本；不计入常规馆藏或时间线。',
                    'Browse Tihu source samples by model and effort; excluded from the main collection and timeline.')
    groups = {}
    for row in rows:
        groups.setdefault(row['model'], []).append(row)
    groups = dict(sorted(groups.items()))
    setting_sizes = Counter((row['model'],row['effort']) for row in rows)
    effort_order = {'default':0, 'low':1, 'medium':2, 'high':3, 'xhigh':4, 'max':5}

    def sample(row):
        specimen = by_id[row['id']]['path']
        total = setting_sizes[(row['model'],row['effort'])]
        label = f'{row["effort"]} · '+t(f'样本 {row["sample"]}/{total}', f'Sample {row["sample"]}/{total}')
        score = '<p class="small">'+E(t('上游 AI 参考分', 'Source AI reference score'))+': '+E(row['upstreamScoreText'])+'</p>' if row.get('upstreamScoreText') else ''
        text = f'{row["model"]} {row["effort"]} {row["sample"]} {row["id"]}'.lower()
        return (f'<article class="benchmark-sample" data-batch-sample data-search-text="{E(text)}">'
                f'<figure><a href="{E(specimen)}"><img src="{E(row["localPreview"])}" alt="{E(row["model"]+" · "+label)}" width="640" height="420" loading="lazy"></a>'
                f'<figcaption>{E(label)}</figcaption></figure>{score}<p class="small">'+E(t('原馆藏编号', 'Former archive number'))+f' #{row["originalCaseNumber"]}</p>'
                f'<p class="small"><a href="{E(specimen)}">'+E(t('样本详情', 'Sample details'))+
                f'</a> · <a href="{E(row["localSvg"])}">SVG</a> · <a href="{E(row["sourceUrl"])}" target="_blank" rel="noopener noreferrer">'+
                E(t('原始出处 ↗', 'Original source ↗'))+'</a></p></article>')

    sections = ''
    for model, members in groups.items():
        members = sorted(members, key=lambda row:(effort_order.get(row['effort'],99),row['effort'],row['sample']))
        previews = ''.join(f'<img src="{E(row["localPreview"])}" alt="" width="120" height="80" loading="lazy">' for row in members[::3])
        count = t(f'{len(members)} 个样本', f'{len(members)} samples')
        sections += (f'<details class="batch-model" data-model="{E(model)}"><summary><span class="batch-model-title">{E(model)}'
                     f'<small data-model-count>{E(count)}</small></span><span class="batch-model-previews" aria-hidden="true">{previews}</span>'
                     '<span class="batch-chevron" aria-hidden="true">＋</span></summary><div class="benchmark-samples">'+
                     ''.join(sample(row) for row in members)+'</div></details>')
    options = ''.join(f'<option value="{E(model)}">{E(model)}</option>' for model in groups)
    body = (f'<div class="page-top"><div class="eyebrow">TIHU · BENCHMARK</div><h1>{E(title)}</h1><p>{E(description)}</p></div>'
            '<div class="callout benchmark-disclaimer"><strong>'+E(t('上游输出，非本馆排名', 'Upstream outputs, not a Pelican Bicycle Archive ranking'))+'</strong><p>'+
            E(t('评分来自 Tihu 的 AI 评委，本站未重新打分，也不据此排列模型。', 'Scores come from Tihu AI judges. This archive neither rescores the samples nor ranks models by them.'))+'</p></div>'
            '<dl class="benchmark-provenance"><dt>'+E(t('发布者', 'Publisher'))+f'</dt><dd><a href="{E(data["sourceUrl"])}">Tihu ↗</a></dd><dt>'+E(t('测试日期', 'Test date'))+
            f'</dt><dd>{E(data["runDate"])}</dd><dt>'+E(t('固定提示词', 'Fixed prompt'))+f'</dt><dd><code>{E(data["prompt"])}</code></dd><dt>'+E(t('来源规则', 'Source rules'))+
            f'</dt><dd><a href="{E(data["rulesUrl"])}">Tihu ↗</a></dd></dl><p class="small">'+E(t(f'{len(groups)} 个模型标签 · {len(setting_sizes)} 个档位组合 · {len(rows)} 个样本',
            f'{len(groups)} model labels · {len(setting_sizes)} effort groups · {len(rows)} samples'))+'</p><p class="small">'+E(t('日期和型号按来源保留，未独立认证。', 'Dates and model labels follow the source and are not independently authenticated.'))+'</p>'
            f'<div data-batch-page="{COLLECTION}" data-reference-only="true"><form class="filters" data-batch-search role="search"><label>'+E(t('仅检索下方样本', 'Search samples below'))+
            '<input type="search" name="q" maxlength="200"></label><label>'+E(t('模型标签', 'Model label'))+'<select name="model"><option value="">'+E(t('全部模型', 'All models'))+
            f'</option>{options}</select></label><button class="button" type="submit">'+E(t('检索', 'Search'))+'</button><button class="button secondary" type="reset">'+E(t('重置', 'Reset'))+
            f'</button></form><div class="browse-toolbar"><p data-batch-count>{len(rows)} '+E(t('个样本 · 不计案例总数', 'samples · excluded from case count'))+'</p><div class="browse-buttons"><button type="button" class="browse-button" data-batch-expand="true">'+
            E(t('展开全部', 'Expand all'))+'</button><button type="button" class="browse-button" data-batch-expand="false">'+E(t('收起全部', 'Collapse all'))+'</button></div></div>'+sections+
            '<p data-batch-empty hidden>'+E(t('没有匹配的样本。', 'No matching samples.'))+'</p></div><details><summary>'+E(t('来源许可与归档说明', 'Source terms and archival notes'))+'</summary><p>'+E(data['rights']['en' if en else 'zh'])+
            '</p><p>'+E(t('保留原样本 ID、详情链接、SVG 原件和历史馆藏编号；主馆显示编号仍由计数作品派生。后续同类批量评测归入 Benchmark。',
            'Original sample IDs, detail URLs, SVG files and former archive numbers are preserved. Current main-collection numbers remain derived from counted works. Further systematic evaluation batches belong in Benchmark.'))+'</p></details>')
    script_hash = hashlib.sha256((ROOT/'site/assets/tihu-benchmark.js').read_bytes()).hexdigest()[:12]
    body += f'<script src="/assets/tihu-benchmark.js?v={script_hash}" defer></script>'
    yield PATH, title, description, body
