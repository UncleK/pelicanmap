"""Explicit, source-reviewed experiment batches; keep original sample records."""
import copy
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
E = lambda value: html.escape(str(value), quote=True)


def representative_samples(items, limit=6):
    chosen = []
    models = set()
    for item in items:
        if item['model'] not in models:
            models.add(item['model'])
            chosen.append(item)
            if len(chosen) == limit:
                return chosen
    return (chosen+[x for x in items if x not in chosen])[:limit]


def apply_batches(items, language='zh', definitions=None):
    definitions = definitions if definitions is not None else json.loads((ROOT/'site/experiment-batches.json').read_text(encoding='utf8'))
    result = copy.deepcopy(items)
    for definition in definitions:
        members = [x for x in result if x['id'].startswith(definition['memberIdPrefix'])
                   and x['date'] == definition['date'] and x['author'] == definition['author']
                   and x['sourceUrl'].startswith(definition['sourcePrefix'])
                   and x.get('datasetSample', {}).get('revision') == definition['revision']]
        assert len(members) == definition['expectedMembers'], f"Review batch membership: {definition['id']}"
        assert len({x['kind'] for x in members}) == 1, 'Do not conflate gallery and timeline records'
        batch = {'id': definition['id'], 'title': definition['title'][language],
                 'description': definition['description'][language], 'sourceUrl': definition['sourceUrl'],
                 'path': ('/en' if language == 'en' else '')+'/collections/'+definition['id']+'/',
                 'total': len(members), 'models': len({x['model'] for x in members}),
                 'referenceOnly': definition.get('referenceOnly', False),
                 'modelLabels': sorted({x['model'] for x in members})}
        for item in members:
            assert not item.get('batch') or item['batch']['id'] == batch['id'], 'Overlapping batches'
            item['batch'] = batch
            if batch['referenceOnly']:
                item['referenceOnly'] = True
                item['kind'] = 'reference'
                item['tags'] = definition.get('tags', [])[:]
    return result


def group_records(items, include_references=False):
    """Group after filtering; an exact single-sample search stays directly accessible."""
    from case_policy import is_case
    items = [x for x in items if include_references or is_case(x)]
    grouped = {}
    for item in items:
        if item.get('batch'):
            grouped.setdefault(item['batch']['id'], []).append(item)
    result, seen = [], set()
    for item in items:
        batch = item.get('batch')
        if not batch or len(grouped[batch['id']]) < 2:
            result.append(item)
        elif batch['id'] not in seen:
            seen.add(batch['id'])
            members = grouped[batch['id']]
            previews = representative_samples(members)
            case = {**item, 'id': 'batch-'+batch['id'], 'originalId': 'batch-'+batch['id'],
                           'isBatch': True, 'title': batch['title'], 'notes': batch['description'],
                           'model': ', '.join(batch['modelLabels']), 'sourceUrl': batch['sourceUrl'],
                           'modelNames': batch['modelLabels'][:],
                           'sourceCodeUrl': batch['sourceUrl'], 'path': batch['path'],
                           'url': 'https://pelicanmap.aveniqa.com'+batch['path'], 'markdown': batch['path']+'index.md',
                           'previews': [{'thumbnail': x['thumbnail'], 'title': x['title']} for x in previews],
                           'media': [x['media'][0] for x in previews], 'matchingSamples': len(members),
                           'sampleIds': [x['id'] for x in members], 'originalLevel': ''}
            case.pop('datasetSample', None)
            case.pop('i18n', None)
            result.append(case)
    return result


def case_counts(items):
    from case_policy import in_timeline
    cases = group_records(items)
    return {'cases': len(cases), 'records': len(items),
            'gallery': sum(x['kind'] == 'gallery' for x in cases),
            'timeline': sum(in_timeline(x) for x in cases),
            'contextRecords': sum(not x.get('referenceOnly') and not x.get('caseVisible',True) for x in items),
            'variantCases': sum(bool(x.get('representativeOf')) and x.get('caseVisible',True) for x in cases),
            'batches': sum(bool(x.get('isBatch')) for x in cases),
            'samples': sum(x['batch']['total'] for x in cases if x.get('isBatch')),
            'mainRecords': sum(not x.get('referenceOnly') for x in items),
            'referenceRecords': sum(bool(x.get('referenceOnly')) for x in items)}


def batch_card(item, language='zh'):
    from card_metadata import card_footer
    en = language == 'en'
    t = lambda zh, english: english if en else zh
    batch = item['batch']
    previews = ''.join(f'<img src="{E(x["thumbnail"])}" alt="{E(x["title"])}" width="320" height="210" loading="lazy">' for x in item['previews'])
    count = t(f'{batch["models"]} 个模型标签 · {batch["total"]} 个样本', f'{batch["models"]} model labels · {batch["total"]} samples')
    matched = '' if item['matchingSamples'] == batch['total'] else t(f' · 当前匹配 {item["matchingSamples"]} 个', f' · {item["matchingSamples"]} matching')
    return f'''<article class="card specimen-card batch-card" data-batch-card="{E(batch['id'])}"><a class="card-cover batch-cover" href="{E(batch['path'])}" aria-label="{E(batch['title']+' · '+count)}">{previews}<span class="batch-badge">{batch['total']} {t('样本','samples')}</span></a><div class="card-body" tabindex="0" aria-label="{t('作品说明','Work description')}"><div class="card-meta">{E(item['date'])} · {t('实验合集 · 计 1 个案例','Experiment batch · 1 case')}</div><h3><a href="{E(batch['path'])}">{E(batch['title'])}</a></h3><p class="note">{E(count+matched)}</p></div>{card_footer(item,language)}</article>'''


def batch_pages(items, language='zh'):
    """Native disclosures work without JS; search/expand-all enhance them."""
    en = language == 'en'
    t = lambda zh, english: english if en else zh
    batches = {}
    for item in items:
        if item.get('batch') and not item.get('referenceOnly'):
            batches.setdefault(item['batch']['id'], []).append(item)
    for members in batches.values():
        batch = members[0]['batch']
        models = {}
        for item in sorted(members, key=lambda x: (x['model'], x.get('datasetSample', {}).get('sample', 0), x['id'])):
            models.setdefault(item['model'], []).append(item)
        options = ''.join(f'<option value="{E(model)}">{E(model)}</option>' for model in models)
        header = f'''<div class="page-top"><div class="eyebrow">EXPERIMENT BATCH · {E(members[0]['date'])}</div><h1>{E(batch['title'])}</h1><p>{E(batch['description'])}</p><a class="text-link" href="{E(batch['sourceUrl'])}" target="_blank" rel="noopener noreferrer">{t('查看原始数据集 ↗','Original dataset ↗')}</a></div>'''
        controls = f'''<div data-batch-page="{E(batch['id'])}"><form class="filters" data-batch-search role="search"><label>{t('检索合集样本','Search batch samples')}<input type="search" name="q" maxlength="200" placeholder="{t('模型、样本编号…','Model, sample number…')}"></label><label>{t('模型标签','Model label')}<select name="model"><option value="">{t('全部模型','All models')}</option>{options}</select></label><button class="button" type="submit">{t('检索','Search')}</button><button class="button secondary" type="reset">{t('重置','Reset')}</button></form><div class="browse-toolbar"><p class="result-count" data-batch-count>{t(f'{len(members)} 个样本 · {len(models)} 个模型标签 · 计 1 个案例',f'{len(members)} samples · {len(models)} model labels · 1 case')}</p><div class="browse-buttons"><button type="button" class="browse-button" data-batch-expand="true">{t('展开全部','Expand all')}</button><button type="button" class="browse-button" data-batch-expand="false">{t('收起全部','Collapse all')}</button></div></div>'''
        sections = ''
        for model, samples in models.items():
            previews = ''.join(f'<img src="{E(x["thumbnail"])}" alt="" width="120" height="80" loading="lazy">' for x in samples[:3])
            cards = ''
            for x in samples:
                search = ' '.join(str(x.get(k, '')) for k in ('title', 'author', 'model', 'originalLevel'))
                cards += f'''<article class="card" data-batch-sample data-search-text="{E(search.lower())}"><a class="card-cover" href="{E(x['path'])}"><img src="{E(x['thumbnail'])}" alt="{E(x['title'])}" width="640" height="420" loading="lazy"><span class="sample-number">{E(x['originalLevel'])}</span></a></article>'''
            sections += f'''<details class="batch-model" data-model="{E(model)}"><summary><span class="batch-model-title">{E(model)}<small data-model-count>{len(samples)} {t('个样本','samples')}</small></span><span class="batch-model-previews" aria-hidden="true">{previews}</span><span class="batch-chevron" aria-hidden="true">＋</span></summary><div class="batch-samples">{cards}</div></details>'''
        empty = f'<p class="result-empty" data-batch-empty hidden>{t("没有匹配的样本。","No matching samples.")}</p>'
        footer = f'''<div class="share-row"><a class="button secondary" href="{'/en' if en else ''}/specimens/">{t('返回全部作品','Back to the collection')}</a><a class="button secondary" href="{'/en' if en else ''}/timeline/">{t('返回时间线','Back to the timeline')}</a></div>'''
        yield batch, header+controls+sections+empty+'</div>'+footer
