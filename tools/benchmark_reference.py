"""Independent, bilingual upstream scoring references; never gallery cases."""
import hashlib
import html
import json
import re
from collections import Counter
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ['model', 'access', 'provider', 'task', 'sample', 'reward', 'structure_score', 'semantic_score', 'gate_passed', 'violations', 'judge_model', 'judge_blind_caption', 'latency', 'svg', 'png']
E = lambda x: html.escape(str(x), quote=True)


def load():
    return json.loads((ROOT/'site/benchmarks/openenv-2026-07-29.json').read_text(encoding='utf8'))


def index_page(language='zh'):
    en = language == 'en'
    t = lambda zh, english: english if en else zh
    definitions = json.loads((ROOT/'site/benchmarks/index.json').read_text(encoding='utf8'))
    title = t('Benchmark 合集', 'Benchmark collections')
    desc = t('评分对照资料单独展示，不进入主时间线、全部作品和案例总数。先选择 Benchmark 合集，再查看模型汇总与原始样本。', 'Independent scoring references, excluded from the main timeline, collection and case total. Choose a benchmark, then inspect model summaries and original samples.')
    body = f'<div class="page-top"><div class="eyebrow">BENCHMARK COLLECTIONS</div><h1>{E(title)}</h1></div><div class="benchmark-collections">'
    for definition in definitions:
        data = json.loads((ROOT/'site/benchmarks'/definition['file']).read_text(encoding='utf8'))
        rows = [x for x in data['rows'] if x['config'] == 'default']
        models = sorted({x['model'] for x in rows})
        chosen = [next(x for x in rows if x['model'] == model and x.get('localPng')) for model in models[:6]]
        images = ''.join(f'<img src="{E(x["localPng"])}" alt="{E(x["model"])} · {t("原始样本", "Original sample")}" width="320" height="210" loading="lazy">' for x in chosen)
        path = ('/en' if en else '')+definition['path']
        body += f'<article class="benchmark-collection" data-benchmark-collection="{E(definition["id"])}"><a class="benchmark-collection-cover" href="{E(path)}" aria-label="{E(definition["title"][language])}">{images}</a><div><p class="small">{E(data["publicationDate"])} · {len(models)} {t("个模型标签", "model labels")} · {len(rows)} {t("条主任务记录", "main-task rows")}</p><h2><a href="{E(path)}">{E(definition["title"][language])}</a></h2><p>{E(definition["description"][language])}</p><a class="text-link" href="{E(path)}">'+t('进入合集 →', 'Open benchmark →')+'</a></div></article>'
    return '/tags/benchmark/', title, desc, body+'</div>'


def model_path(model):
    slug = re.sub(r'[^a-z0-9]+', '-', model.lower()).strip('-')
    return '/benchmarks/openenv-2026-07-29/'+slug+'-'+hashlib.sha256(model.encode()).hexdigest()[:6]+'/'


def species(row):
    caption = row.get('judge_blind_caption') or ''
    found = [x for x in ['pelican', 'stork', 'duck', 'goose', 'swan', 'heron', 'flamingo'] if re.search(r'\b'+x+r's?\b', caption, re.I)]
    if len(found) == 1:
        return found[0]
    if len(found) > 1:
        return 'multiple labels'
    return 'bird' if re.search(r'\bbirds?\b', caption, re.I) else 'not identified'


def stats(rows):
    return {'n': len(rows), 'rendered': sum(bool(x.get('localPng')) for x in rows),
            'reward': mean(x['reward'] for x in rows),
            'structure_score': mean(x['structure_score'] for x in rows),
            'semantic_score': mean(x['semantic_score'] for x in rows),
            'species': dict(Counter(species(x) for x in rows))}


def record_details(item, language='zh'):
    if not item.get('referenceOnly'):
        return ''
    en = language == 'en'
    row = item.get('datasetSample', {})
    metadata = {key: row.get(key) for key in FIELDS}
    title = 'Upstream outputs, not a Pelican Map ranking' if en else '上游输出，非本馆排名'
    text = 'Scoring reference only; excluded from the timeline, collection and case count.' if en else '仅作评分参考；不进入主时间线、全部作品或案例总数。'
    svg = item.get('benchmarkMedia', {}).get('svg')
    source = f'<p><a href="{E(svg)}">{("Archived original SVG" if en else "本地原始静态 SVG")} ↗</a></p>' if svg else ''
    return f'<section class="benchmark-note"><strong>{title}</strong><p>{text}</p>{source}<details><summary>{"Original scoring fields" if en else "上游原始评分字段"}</summary><pre>{E(json.dumps(metadata, ensure_ascii=False, indent=2))}</pre></details></section>'


def pages(items, language='zh'):
    data = load()
    en = language == 'en'
    t = lambda zh, english: english if en else zh
    local = lambda path: ('/en' if en else '')+path
    disclaimer = data['disclaimer'][language]
    title = t('评分对照', 'Scoring reference')
    description = t('独立的 HuggingFace / OpenEnv 评分参考，不进入主时间线、全部作品和案例总数。', 'An independent HuggingFace / OpenEnv scoring reference, excluded from the main timeline, collection and case total.')
    main = [x for x in data['rows'] if x['config'] == 'default' and x['task'] == 'pelican_bicycle']
    groups = {}
    for row in main:
        groups.setdefault(row['model'], []).append(row)
    groups = dict(sorted(groups.items()))  # Alphabetical, never score-ranked.
    known = {x['datasetSample']['id']: x for x in items if x.get('referenceOnly')}

    def header(heading, desc):
        return f'<div class="page-top"><div class="eyebrow">HF / OPENENV · REFERENCE ONLY</div><h1>{E(heading)}</h1><p>{E(desc)}</p></div><div class="callout benchmark-disclaimer"><strong>{E(disclaimer)}</strong><p>{E(description)}</p></div>'

    def metadata(row):
        values = {key: row.get(key) for key in FIELDS}
        return '<details class="benchmark-fields"><summary>'+t('原始字段与盲评描述', 'Original fields and blind caption')+'</summary><pre>'+E(json.dumps(values, ensure_ascii=False, indent=2))+'</pre></details>'

    def sample(row, caption=''):
        image = f'<img src="{E(row["localPng"])}" alt="{E(row["id"])}" width="640" height="420" loading="lazy">' if row.get('localPng') else '<p class="benchmark-unrenderable">'+t('截断 SVG，无可显示 PNG；原始 reward = 0，仍纳入分母。', 'Truncated SVG; no PNG available. Original reward = 0 remains in the denominator.')+'</p>'
        item = known.get(row['id'])
        href = item['path'] if item else ''
        picture = f'<a href="{E(href)}">{image}</a>' if href else image
        links = f'<a href="{E(row["sourceUrl"])}" target="_blank" rel="noopener noreferrer">'+t('上游 SVG ↗', 'Upstream SVG ↗')+'</a>'
        if row.get('localSvg'):
            links += f' · <a href="{E(row["localSvg"])}">'+t('本地 SVG', 'Local SVG')+'</a>'
        return f'<article class="benchmark-sample" data-batch-sample data-search-text="{E(((row.get("model") or "")+" "+row["id"]).lower())}"><figure>{picture}<figcaption>{E(caption or row["id"])}</figcaption></figure><p class="small">{E(disclaimer)} · reward {row["reward"]:.3f}</p><p>{E(row.get("judge_blind_caption") or t("盲评描述缺失", "Blind caption unavailable"))}</p><p class="small">{links}</p>{("<p class=\"small\">"+E(t("原始 SVG 含动画，未镜像；这里只展示上游静态 PNG。", "Animated source SVG is not mirrored; only its upstream static PNG is shown."))+"</p>") if row.get('svgDeferredReason') else ''}{metadata(row)}</article>'

    def folds():
        sections = ''
        for model, rows in groups.items():
            rendered = [x for x in rows if x.get('localPng')]
            previews = ''.join(f'<img src="{E(x["localPng"])}" alt="" width="120" height="80" loading="lazy">' for x in rendered[:3])
            sections += f'<details class="batch-model" data-model="{E(model)}"><summary><span class="batch-model-title">{E(model)}<small data-model-count>{len(rows)} {t("条记录", "rows")} · {len(rendered)} {t("张图", "images")}</small></span><span class="batch-model-previews" aria-hidden="true">{previews}</span><span class="batch-chevron" aria-hidden="true">＋</span></summary><p class="benchmark-model-link"><a href="{local(model_path(model))}">'+t('模型汇总与代表图 →', 'Model summary and representative images →')+'</a></p><div class="benchmark-samples">'+''.join(sample(x) for x in rows)+'</div></details>'
        return sections

    provenance = f'<dl class="benchmark-provenance"><dt>{t("发布者", "Publisher")}</dt><dd>{E(data["author"])}</dd><dt>Dataset</dt><dd><a href="{data["sourceUrl"]}" target="_blank" rel="noopener noreferrer">HuggingFace pelican-svg-drawings ↗</a></dd><dt>Environment</dt><dd><a href="{data["envUrl"]}" target="_blank" rel="noopener noreferrer">pelican-svg-env ↗</a> · <a href="{data["repositoryUrl"]}" target="_blank" rel="noopener noreferrer">OpenEnv code ↗</a></dd><dt>{t("许可", "License")}</dt><dd><a href="{data["licenseUrl"]}">Apache-2.0</a> · <a href="{data["attributionUrl"]}">{t("署名", "Attribution")}</a></dd><dt>{t("固定题面", "Fixed prompt")}</dt><dd><code>{E(data["prompt"])}</code></dd><dt>{t("公开日期 / 运行日", "Publication / run date")}</dt><dd>2026-07-29 / {t("未单独公开，不能以公开日代替运行日", "Not separately published; publication is not the run date")}</dd><dt>{t("固定版本", "Pinned revision")}</dt><dd><code>{data["revision"]}</code></dd></dl>'
    table_rows = ''
    for model, rows in groups.items():
        values = stats(rows)
        table_rows += f'<tr><th scope="row"><a href="{local(model_path(model))}">{E(model)}</a></th><td>{len(rows)}</td><td>{values["reward"]:.3f}</td><td>{values["structure_score"]:.3f}</td><td>{values["semantic_score"]:.3f}</td></tr>'
    table = '<div class="benchmark-table"><table><caption>'+E(disclaimer)+' · '+t('按模型名排序，失败样本纳入分母', 'Alphabetical by model; failed rows remain in the denominator')+'</caption><thead><tr><th>'+t('上游模型标签', 'Source model label')+'</th><th>n</th><th>'+t('平均 reward', 'Mean reward')+'</th><th>structure</th><th>semantic</th></tr></thead><tbody>'+table_rows+'</tbody></table></div>'
    intro = header(title, description)+provenance+'<p class="small">'+t('模型按来源原样保留，未独立认证。不同提供商与采样条件不等价；分数来自上游评判模型，不代表本馆对模型能力的结论。139 条主任务记录，138 张可显示图像，1 条失败记录。', 'Model labels follow the source and are not independently authenticated. Providers and sampling conditions differ; scores come from the upstream judge, not a Pelican Map capability assessment. 139 main-task rows, 138 viewable images and one failed row.')+'</p>'+table+f'<p><a href="{local("/benchmarks/openenv-2026-07-29/catalogue/")}">'+t('任务目录：30 组题面（29 组非主任务） →', 'Task catalogue: 30 prompts (29 non-main tasks) →')+'</a> · <a href="/data/benchmark.json">JSON</a></p>'
    options = ''.join(f'<option value="{E(model)}">{E(model)}</option>' for model in groups)
    controls = f'<div data-batch-page="openenv-2026-07-29" data-reference-only="true"><form class="filters" data-batch-search role="search"><label>{t("仅检索下方样本", "Search samples below")}<input type="search" name="q" maxlength="200"></label><label>{t("模型标签", "Model label")}<select name="model"><option value="">{t("全部模型", "All models")}</option>{options}</select></label><button class="button" type="submit">{t("检索", "Search")}</button><button class="button secondary" type="reset">{t("重置", "Reset")}</button></form><div class="browse-toolbar"><p data-batch-count>139 {t("条记录 · 不计案例总数", "rows · excluded from case count")}</p><div class="browse-buttons"><button type="button" class="browse-button" data-batch-expand="true">{t("展开全部", "Expand all")}</button><button type="button" class="browse-button" data-batch-expand="false">{t("收起全部", "Collapse all")}</button></div></div>'
    body = intro+'<h2>'+t('按模型展开原始样本', 'Expand original samples by model')+'</h2>'+controls+folds()+'<p data-batch-empty hidden>'+t('没有匹配的样本。', 'No matching samples.')+'</p></div>'
    yield index_page(language)
    yield '/collections/openenv-2026-07-29/', t('OpenEnv 鹈鹕评分对照', 'OpenEnv pelican scoring reference'), description, body

    for model, rows in groups.items():
        values = stats(rows)
        distribution = ' · '.join(f'{name}: {count}/{len(rows)}' for name, count in sorted(values['species'].items()))
        perfect = next((x for x in rows if x['reward'] == 1 and x.get('localPng')), None)
        mistaken = next((x for x in rows if species(x) not in {'pelican', 'not identified'} and x.get('localPng')), None)
        reps = ((sample(perfect, t('满分样本（上游 reward = 1）', 'Perfect upstream reward = 1')) if perfect else '<p>'+t('无满分样本', 'No perfect-reward sample')+'</p>')+(sample(mistaken, t('盲评未称为鹈鹕的样本', 'Sample not called a pelican by the blind caption')) if mistaken else '<p>'+t('无可显示误认代表图', 'No viewable misidentified representative')+'</p>'))
        detail = header(model, disclaimer)+f'<p>{t("样本量", "Rows")}: {len(rows)} · {t("可显示图像", "Viewable images")}: {values["rendered"]} · {t("上游平均 reward", "Upstream mean reward")}: {values["reward"]:.6f}</p><h2>'+t('上游盲评物种词分布', 'Species words in upstream blind captions')+'</h2><p>'+E(distribution)+'</p><p class="small">'+t('按原始 caption 中物种词匹配；不是本站重新判图。多物种词单列，缺失或未识别仍计分母。原始描述见样本字段。', 'Matches species words in original captions; no new image judging. Multiple labels and missing/unidentified captions remain in the denominator. Original captions are retained below.')+'</p><div class="benchmark-representatives">'+reps+'</div><details class="batch-model"><summary>'+t('展开全部样本', 'Expand all samples')+f' ({len(rows)})</summary><div class="benchmark-samples">'+''.join(sample(x) for x in rows)+'</div></details><p><a href="'+local('/tags/benchmark/')+'">← '+t('返回评分对照', 'Back to scoring reference')+'</a></p>'
        yield model_path(model), model, description, detail

    coverage = [x for x in data['rows'] if x['config'] == 'coverage']
    desc = t('题面覆盖样本单列，不进入七模型主对照；来源未给出的模型、提供商和运行编号保持为空。', 'Prompt-coverage samples stay outside the seven-model comparison. Model, provider and run fields absent from the source remain null.')
    coverage_body = header(t('评分参考 · 任务目录', 'Scoring reference · Task catalogue'), desc)+'<p>'+E(desc)+'</p><div class="benchmark-samples">'+''.join(sample(x, x['task']+(' · benchmark-catalogue' if x['task'] != 'pelican_bicycle' else ' · '+t('覆盖样本，模型未公开', 'Coverage sample; model not published'))) for x in coverage)+'</div><p><a href="'+local('/tags/benchmark/')+'">← '+t('返回评分对照', 'Back to scoring reference')+'</a></p>'
    yield '/benchmarks/openenv-2026-07-29/catalogue/', t('评分参考 · 任务目录', 'Scoring reference · Task catalogue'), desc, coverage_body

    yield from pelicanbenchmark_pages(language)


def pelicanbenchmark_pages(language='zh'):
    en = language == 'en'
    t = lambda zh, english: english if en else zh
    local = lambda path: ('/en' if en else '')+path
    data = json.loads((ROOT/'site/benchmarks/pelicanbenchmark-2026-09-28.json').read_text(encoding='utf8'))
    disclaimer = data['disclaimer'][language]
    title = t('Pelican Benchmark · 动态 HTML 评测跑道', 'Pelican Benchmark · Animated HTML track')
    description = t('pelicanbenchmark.com 评测站公开的动态 HTML track。收录 29 个模型独立代码生成的自包含 HTML 动画原件与运行预览。', 'The animated HTML track from pelicanbenchmark.com. Features 29 standalone code-generated HTML animations and runtime previews across models.')
    rows = data['rows']
    groups = {}
    for r in rows:
        groups.setdefault(r['model'], []).append(r)
    groups = dict(sorted(groups.items()))

    def header(heading, desc):
        return f'<div class="page-top"><div class="eyebrow">PELICAN BENCHMARK · REFERENCE TRACK</div><h1>{E(heading)}</h1><p>{E(desc)}</p></div><div class="callout benchmark-disclaimer"><strong>{E(disclaimer)}</strong><p>{E(description)}</p></div>'

    provenance = f'<dl class="benchmark-provenance"><dt>{t("发布者", "Publisher")}</dt><dd>{E(data["author"])}</dd><dt>{t("来源基准站", "Benchmark Site")}</dt><dd><a href="{data["sourceUrl"]}" target="_blank" rel="noopener noreferrer">pelicanbenchmark.com ↗</a></dd><dt>{t("评测跑道", "Benchmark Track")}</dt><dd><code>animated_html</code> · {len(rows)} {t("件动态原件", "animated originals")} ({len(groups)} {t("个模型标签", "model labels")})</dd><dt>{t("许可与权利", "License & Rights")}</dt><dd>{t("原作者署名 · 保留原件代码与运行帧", "Creator attribution · Code and frames preserved")}</dd><dt>{t("固定题面", "Fixed prompt")}</dt><dd><code>{E(data["prompt"])}</code></dd><dt>{t("公开日期", "Publication date")}</dt><dd>{E(data["publicationDate"])}</dd></dl>'

    table_rows = ''
    for model, m_rows in groups.items():
        sample_item = m_rows[0]
        table_rows += f'<tr><th scope="row"><a href="#model-{hashlib.sha256(model.encode()).hexdigest()[:6]}">{E(model)}</a></th><td>{len(m_rows)}</td><td>{E(sample_item.get("author",""))}</td><td>{E(sample_item.get("thinkingLevel") or "-")}</td><td><a href="{E(sample_item["specimenPath"])}">{t("馆藏详情", "Specimen")}</a> · <a href="{E(sample_item["localHtml"])}" target="_blank" rel="noopener noreferrer">{t("站内演示 ↗", "Demo ↗")}</a></td></tr>'
    table = f'<div class="benchmark-table"><table><caption>{E(disclaimer)} · {t("按模型名排序", "Alphabetical by model")}</caption><thead><tr><th>{t("模型标签", "Model label")}</th><th>n</th><th>{t("提交者", "Submitter")}</th><th>{t("思考档位", "Thinking")}</th><th>{t("链接", "Links")}</th></tr></thead><tbody>{table_rows}</tbody></table></div>'

    options = ''.join(f'<option value="{E(model)}">{E(model)}</option>' for model in groups)
    controls = f'<div data-batch-page="pelicanbenchmark-2026-09-28" data-reference-only="true"><form class="filters" data-batch-search role="search"><label>{t("仅检索下方样本", "Search samples below")}<input type="search" name="q" maxlength="200" placeholder="{t("模型、提交者…", "Model, submitter…")}"></label><label>{t("模型标签", "Model label")}<select name="model"><option value="">{t("全部模型", "All models")}</option>{options}</select></label><button class="button" type="submit">{t("检索", "Search")}</button><button class="button secondary" type="reset">{t("重置", "Reset")}</button></form><div class="browse-toolbar"><p data-batch-count>{len(rows)} {t("条记录 · 不计案例总数", "rows · excluded from case count")}</p><div class="browse-buttons"><button type="button" class="browse-button" data-batch-expand="true">{t("展开全部", "Expand all")}</button><button type="button" class="browse-button" data-batch-expand="false">{t("收起全部", "Collapse all")}</button></div></div>'

    def sample_card(row):
        image = f'<img src="{E(row["localPng"])}" alt="{E(row["model"])}" width="640" height="420" loading="lazy">'
        href = row.get("specimenPath") or ""
        picture = f'<a href="{E(href)}">{image}</a>' if href else image
        links = f'<a href="{E(row["specimenPath"])}">{t("馆藏详情", "Specimen")}</a> · <a href="{E(row["localHtml"])}" target="_blank" rel="noopener noreferrer">{t("站内演示 ↗", "Demo ↗")}</a> · <a href="{E(row["sourceUrl"])}" target="_blank" rel="noopener noreferrer">{t("上游结果 ↗", "Source ↗")}</a>'
        thinking = f' · {t("思考档位: ", "Thinking: ")}{E(row["thinkingLevel"])}' if row.get("thinkingLevel") else ''
        author = f'{t("提交者: ", "Submitter: ")}{E(row.get("author", ""))}'
        search_text = f'{row.get("model", "")} {row.get("author", "")} {row.get("id", "")}'.lower()
        return f'<article class="benchmark-sample" data-batch-sample data-search-text="{E(search_text)}"><figure>{picture}<figcaption>{E(row["model"])}</figcaption></figure><p class="small">{E(author)}{thinking}</p><p class="small">{links}</p></article>'

    sections = ''
    for model, m_rows in groups.items():
        previews = ''.join(f'<img src="{E(x["localPng"])}" alt="" width="120" height="80" loading="lazy">' for x in m_rows[:3])
        model_id = f'model-{hashlib.sha256(model.encode()).hexdigest()[:6]}'
        sections += f'<details class="batch-model" id="{model_id}" data-model="{E(model)}"><summary><span class="batch-model-title">{E(model)}<small data-model-count>{len(m_rows)} {t("件原件", "original")}</small></span><span class="batch-model-previews" aria-hidden="true">{previews}</span><span class="batch-chevron" aria-hidden="true">＋</span></summary><div class="benchmark-samples">{"".join(sample_card(x) for x in m_rows)}</div></details>'

    intro = header(title, description)+provenance+'<p class="small">'+t('模型按来源原样保留，未独立认证。自包含 HTML 原件在站内隔离子域安全运行，包含独立脚本、动画逻辑与真实渲染帧。29 件动态作品由用户独立代码生成并提交至 Pelican Benchmark。', 'Model labels follow the source and are not independently authenticated. Standalone HTML originals run safely on the isolated domain, preserving code, animations, and rendered frames. 29 animated works generated by models and submitted to Pelican Benchmark.')+'</p>'+table
    empty = f'<p data-batch-empty hidden>{t("没有匹配的样本。", "No matching samples.")}</p>'
    back = f'<p><a href="{local("/tags/benchmark/")}">← {t("返回 Benchmark 合集", "Back to benchmark collections")}</a></p>'
    body = intro+'<h2>'+t('按模型浏览评测原件', 'Browse benchmark originals by model')+'</h2>'+controls+sections+empty+back+'</div>'

    yield '/collections/pelicanbenchmark-2026-09-28/', title, description, body

