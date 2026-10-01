"""Stage nine explicitly mapped 2025 outputs; not an automatic intake policy."""
import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from audit_nile_history import ROOT, OUT, fetcher

SOURCES = {s['position']: s for s in json.loads((OUT / 'sources.json').read_text(encoding='utf8'))['sources']}
GISTS = {s['sourceUrl'].rsplit('/', 1)[-1]: s for s in json.loads((OUT / 'linked-gists.json').read_text(encoding='utf8'))}


def output_svg(text):
    headings = list(re.finditer(r'^#{2,3} Response:?\s*$', text, re.M))
    if headings:
        text = text[headings[-1].end():]
        next_heading = re.search(r'^#{1,3}\s+[^\n]+$', text, re.M)
        if next_heading:
            text = text[:next_heading.start()]
    blocks = re.findall(r'<svg\b[\s\S]*?</svg\s*>', text, re.I)
    assert len(blocks) == 1, 'Only a reviewed final response is an output'
    assert not re.search(r'<(?:animate\w*|set|script)\b|@keyframes|\banimation\s*:', blocks[0], re.I)
    return blocks[0].encode()


def provenance_notes(zh, en, date_basis):
    if date_basis == 'source-reported-response-timestamp':
        date_zh = '日期取原始日志中的响应时间戳；原文公开日另列。'
        date_en = 'The date uses the response timestamp in the original log; the article publication date is recorded separately.'
    else:
        date_zh = '日期依据原文公开日，不推测具体生成时间。'
        date_en = 'The date follows the article publication; the exact generation time is not inferred.'
    return {
        'zh': zh + ' 模型按来源标注、未独立认证。' + date_zh + '生成时间未独立认证。归档原始字节，不重画或改善。',
        'en': en + ' Model attribution is source-reported, not independently authenticated. ' + date_en + ' Generation time is not independently authenticated. Original bytes archived without redrawing or improving.'
    }


def stage():
    specs = [
        ('simon-kimi-k2-0711-2025-07-11', 21, 0, 'kimi-k2-0711-preview', 'Moonshot API · max_tokens 2000', '39aba6a1d4895ad7516bffe9485031db',
         '作者用 kimi-k2 别名调用 kimi-k2-0711-preview，max_tokens 2000 是输出长度限制，不是推理档位。',
         'The source maps its kimi-k2 alias to kimi-k2-0711-preview. max_tokens 2000 is an output limit, not a reasoning level.'),
        ('simon-qwen3-coder-480b-2025-07-22', 22, 0, 'qwen3-coder-480b-a35b-instruct', 'Hyperbolic playground', None,
         '作者明确通过 Hyperbolic playground 测试该模型。只归档鹈鹕静态图，不收同帖价格表。',
         'The author explicitly tests this model in the Hyperbolic playground. Only the static pelican is archived, not the pricing table.'),
        ('simon-qwen3-235b-instruct-2507-2025-07-22', 23, 0, 'openrouter/qwen/qwen3-235b-a22b-07-25:free', 'OpenRouter · non-reasoning', None,
         '保留作者命令中的实际模型标识及 free 别名，不把聚合时间线的 Qwen3-Coder 标签当事实。',
         'Preserves the actual model identifier and free alias in the author’s command, not the aggregator’s Qwen3-Coder label.'),
        ('simon-qwen3-235b-thinking-2507-2025-07-25', 25, 1, 'Qwen3-235B-A22B-Thinking-2507', 'OpenRouter · source final response', 'f013772544fabba02fca9e28fd54cdee',
         '作者明确区分 thinking trace 与 finished pelican；提取最终 Response 对应 SVG，不收推理截图，不修复失败构图。',
         'The source distinguishes its thinking trace from the finished pelican. Archives the final-response SVG, not a reasoning screenshot; failed geometry is preserved.'),
        ('simon-glm45-chat-2025-07-28', 26, 0, 'GLM 4.5', 'chat.z.ai · reasoning enabled', None,
         '作者在 chat.z.ai 开启 reasoning 测试 GLM 4.5；图和后一张 Air 输出按原文标签分开收录。',
         'Source test in chat.z.ai with reasoning enabled. This GLM 4.5 output and the following Air output are split using the author’s labels.'),
        ('simon-glm45-air-chat-2025-07-28', 26, 1, 'GLM 4.5 Air', 'chat.z.ai · reasoning enabled', None,
         '作者明确标为 GLM 4.5 Air 的独立输出；不同于翌日 3bit 本地运行，不依据量化名称合并。',
         'The source explicitly labels this separate output GLM 4.5 Air; it is not the following day’s local 3bit run.'),
        ('simon-xbai-o4-6bit-2025-08-03', 29, 0, 'XBai o4', 'MLX 6bit · LM Studio', '78182fc3409e36f8d22217992967b9d6',
         '原文说明使用 Ivan Fioravanti 的 6bit MLX 量化（24.81GB）在 LM Studio 运行；只收最终静态 SVG，不收同帖 Space Invaders 游戏。',
         'Source run in LM Studio using Ivan Fioravanti’s 6bit MLX quantization (24.81GB). Only the final static SVG is collected, not the Space Invaders game.'),
        ('simon-claude-opus41-2025-08-05', 30, 0, 'anthropic/claude-opus-4-1-20250805', 'source single run', '7fead138d31d751d65c7253a1c18751b',
         '模型标识按作者原始日志保留，与同日 Opus 4 新运行分开，不把厂商其他能力分数带入本馆。',
         'Model identifier preserved from the original log. Separate from the same-day fresh Opus 4 run; unrelated vendor scores are not museum scores.'),
        ('simon-claude-opus4-2025-08-05', 30, 1, 'anthropic/claude-opus-4-0', 'fresh source comparison run', '96a958e39aaed10e1e47c1aab2d05e20',
         '原文明确称 fresh new pelican，是同日重新运行的 Opus 4 输出，不用新版图覆盖早期 Opus 4 作品。',
         'The author explicitly calls this a fresh new pelican: a new same-day Opus 4 run, not a replacement for earlier Opus 4 works.'),
    ]
    cases = []
    for ident, pos, image_index, model, variant, gid, zh, en in specs:
        source = SOURCES[pos]
        image = source['images'][image_index]
        parts = source['sourceUrl'].split('/')
        month = {'Jul': '07', 'Aug': '08'}[parts[4]]
        date = parts[3] + '-' + month + '-' + parts[5].zfill(2)
        assert date < '2026-01-01'
        data, meta = fetcher.request(image['url'])
        assert meta.get('status') == 200
        preview = {'url': image['url'], 'filename': ident + Path(image['url']).suffix,
                   'sha256': hashlib.sha256(data).hexdigest(),
                   'caption': {'zh': '上游发布的静态 SVG 预览', 'en': 'Source-published static SVG preview'}}
        c = {'id': ident, 'sourceUrl': source['sourceUrl'], 'date': date, 'dateBasis': 'source-publication',
             'sourcePublicationDate': date, 'model': model, 'author': 'Simon Willison', 'format': 'svg',
             'variant': variant, 'unitType': 'single-model-output', 'modelToMediaVerified': True,
             'title': {'zh': model + ' · ' + variant, 'en': model + ' · ' + variant},
             'notes': provenance_notes(zh, en, 'source-publication'),
             'rights': {'zh': '作品权利归原作者；公开归档不改变原作品许可，不将模型权重许可套用于输出。',
                        'en': 'Rights remain with the original author; archiving does not change the source licence or apply a model-weight licence to its output.'},
             'prompt': 'Generate an SVG of a pelican riding a bicycle', 'evidence': [source['sourceUrl'], image['url']],
             'reviewPreviewUrl': image['url'], 'media': [preview]}
        if gid:
            gist = GISTS[gid]
            assert gist['updated'] < '2026-01-01'
            assert len(gist['files']) == 1
            f = gist['files'][0]
            svg = output_svg(f['text'])
            original, rawmeta = fetcher.request(f['url'])
            assert rawmeta.get('status') == 200 and output_svg(original.decode()) == svg
            c['media'] = [{'url': f['url'], 'filename': ident + '.svg', 'sha256': hashlib.sha256(svg).hexdigest(),
                           'svgFromTranscript': True, 'svgIndex': 0,
                           **({'responseIndex': 0} if '## Response' in f['text'] else {}),
                           'caption': {'zh': '原始最终输出 SVG（逐字提取）', 'en': 'Original final SVG output (verbatim extraction)'}},
                          {**preview, 'detailOnly': True}]
            c['sourceCodeUrl'] = gist['sourceUrl']
            c['evidence'].extend([gist['sourceUrl'], f['url']])
            stamp = re.search(r'^# (2025-\d\d-\d\dT\d\d:\d\d:\d\d)', f['text'])
            if stamp:
                c['sourceResponseTimestamp'] = stamp[1]
                c['dateBasis'] = 'source-reported-response-timestamp'
                c['notes'] = provenance_notes(zh, en, c['dateBasis'])
        cases.append(c)
    manifest = {'reviewed': False, 'batch': '2026-10-01-nile-history', 'scope': 'nine source-mapped 2025 outputs, positions 21–30', 'cases': cases}
    target = OUT / 'manifest.json'
    encoded = (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode()
    if target.exists():
        assert target.read_bytes() == encoded, 'Refusing to change previously staged evidence'
    else:
        target.write_bytes(encoded)
    if not (OUT / 'before-published-catalog.json').exists():
        (OUT / 'before-published-catalog.json').write_bytes((ROOT / 'public-site/data/catalog.json').read_bytes())
    print(json.dumps({'staged': len(cases), 'svgOriginals': sum(len(c['media']) == 2 for c in cases)}))


if __name__ == '__main__':
    stage()
