"""Generate GitHub project pages from reviewed public catalog metadata only."""
import base64
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs'
SITE = 'https://pelicanmap.aveniqa.com'
REPO = 'https://github.com/UncleK/pelicanmap'
PAGES = 'https://unclek.github.io/pelicanmap'
SELECTED = [
    'origin-claude-3-5-sonnet-20241022-svg-fd622f85',
    'simon-gemini-flash-default-2025-04-17',
    'simon-gpt61-sol-medium-2026-09-29',
]
E = lambda value: html.escape(str(value), quote=True)


def build(language):
    en = language == 'en'
    T = lambda zh, english: english if en else zh
    catalog = json.loads((ROOT / ('site/catalog.en.json' if en else 'site/catalog.json')).read_text(encoding='utf8'))
    by_id = {x['id']: x for x in catalog['items']}
    counts = catalog['counts']
    prefix = '../' if en else ''
    live = SITE + ('/en' if en else '')
    canonical = PAGES + ('/en/' if en else '/')
    title = T('pelicanmap · 一只鸟，一辆车，一段 AI 小史。', 'pelicanmap · One bird. One bicycle. A small history of AI.')
    description = T('可追溯的双语鹈鹕骑车 AI 标本馆：真实输出、时间线、来源与只读 API / MCP。', 'A bilingual field guide to AI pelicans riding bicycles: actual outputs, a timeline, original sources and read-only API / MCP.')
    selected = []
    for identifier in SELECTED:
        x = by_id[identifier]
        assert x['caseVisible'] and not x.get('referenceOnly') and x['format'] == 'svg'
        selected.append(f'''<article class="card"><a class="cover" href="{E(x['url'])}"><img src="{E(SITE+x['thumbnail'])}" alt="{E(x['model'])} · {E(x['date'])}" width="640" height="420" loading="lazy"></a><div class="card-body"><h3><a href="{E(x['url'])}">{E(x['model'])}</a></h3><p>{E(x['author'])} · {T('来源模型标注', 'source-reported model')}</p></div><div class="card-foot"><span>#{x['caseNumber']}</span><time>{E(x['date'])}</time><a href="{E(x['url'])}">{T('查看记录 ↗','Record ↗')}</a></div></article>''')
    stat_labels = [T('独立作品 · 含不同实际档位', 'Works · actual settings counted separately'), T('时间线代表图 · 作品子集', 'Timeline representatives · a subset'), T('Simon 来源索引 · 不计作品', 'Source articles · not artwork counts'), T('Benchmark 合集 · 单列参考', 'Benchmark collection · separate reference')]
    stats = ''.join(f'<div class="stat"><strong>{counts[key]:,}</strong><span>{label}</span></div>' for key, label in zip(['cases', 'timeline', 'sourceIndex', 'benchmarkCollections'], stat_labels))
    paths = [
        ('01 / THE COLLECTION', T('沿着时间，看见回答', 'Follow the answers through time'), T('从早期 SVG 到跨媒体输出，按年份与模型家族浏览。', 'From early SVGs to work across media. Browse by year and model family.'), '/timeline/', T('探索时间线 →', 'Explore the timeline →')),
        ('02 / THE PROVENANCE', T('每一份输出，都有来处', 'Every output has a source'), T('保留作者、原帖、日期依据、提示词和真实生成条件。', 'Keep the creator, original post, date evidence, prompt and actual creation conditions.'), '/sources/', T('顺着出处读下去 →', 'Follow the sources →')),
        ('03 / THE INTERFACE', T('让资料，也能被程序读懂', 'An archive programs can read'), T('中英文共用审核目录，提供 JSON、CSV、HTTP API 与 MCP。', 'One reviewed bilingual catalog. JSON, CSV, HTTP API and MCP.'), '/developers/', T('查看数据接口 →', 'Explore the interfaces →')),
    ]
    path_html = ''.join(f'<a class="path" href="{live+url}"><span class="eyebrow">{number}</span><h3>{heading}</h3><p>{text}</p><span class="arrow">{label}</span></a>' for number, heading, text, url, label in paths)
    result = f'''<!doctype html>
<html lang="{'en' if en else 'zh-CN'}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><meta name="description" content="{description}"><meta name="theme-color" content="#f6f2e9"><link rel="canonical" href="{canonical}">
<link rel="alternate" hreflang="zh-CN" href="{PAGES}/"><link rel="alternate" hreflang="en" href="{PAGES}/en/">
<meta property="og:type" content="website"><meta property="og:title" content="{title}"><meta property="og:description" content="{description}"><meta property="og:url" content="{canonical}"><meta property="og:image" content="{PAGES}/assets/social-preview.png"><meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="{prefix}assets/logo.png"><link rel="stylesheet" href="{prefix}assets/project.css"></head>
<body><a class="skip" href="#main">{T('跳到正文','Skip to content')}</a>
<header class="head"><div class="wrap head-inner"><a class="brand" href="{prefix or './'}"><img src="{prefix}assets/logo.png" width="49" height="49" alt=""><span><strong>pelicanmap</strong><small>AN AI FIELD GUIDE</small></span></a><nav aria-label="{T('主导航','Main navigation')}"><a href="#explore">{T('探索','Explore')}</a><a href="#developers">API / MCP</a><a href="{REPO}">GitHub ↗</a><a href="{'../' if en else 'en/'}" lang="{'zh-CN' if en else 'en'}">{T('English','中文')}</a></nav></div></header>
<main id="main" class="wrap"><section class="hero"><div><div class="eyebrow">THE PELICAN QUESTION · OPEN ARCHIVE</div><h1>{T('一只鹈鹕。<br>无数种<em>可能。</em>', 'One pelican.<br><em>Endless possibilities.</em>')}</h1><p class="intro">{T('一只鸟，一辆车，一段 AI 小史。<br>把真实输出整理成可浏览、可追溯的双语标本馆。从 SVG 到动画、视频、三维与交互，保留作品的来处，也保留失败的原貌。', 'One bird. One bicycle. A small history of AI.<br>A bilingual field guide to actual outputs, from SVG to animation, video, 3D and interaction. Keep the source. Keep the failures, too.')}</p><div class="actions"><a class="button" href="{live}/">{T('进入标本馆','Visit the collection')} <span>↗</span></a><a class="button secondary" href="{REPO}">{T('查看项目源码','Explore the source')} <span>→</span></a></div><div class="tiny">{T('一个持续整理的资料馆 · 精选与时间线不是排名', 'A continuously curated archive · selections are not rankings')}</div></div>
<figure class="plate"><div class="plate-label"><span>PELICAN MAP</span><span>FIELD GUIDE / 01</span></div><img class="mark" src="{prefix}assets/logo.png" alt="{T('项目标志：深绿色鹈鹕骑自行车','Project identity: a green pelican riding a bicycle')}" width="400" height="258"><div class="prompt">“Generate an SVG of a pelican<br>riding a bicycle.”</div><figcaption><span>{T('一个小问题，一部不断展开的故事','A small prompt. An unfolding story.')}</span><span>2024—2026</span></figcaption></figure></section>
<div class="stats">{stats}</div><p class="snapshot">SNAPSHOT / {catalog['updated']} · {T('时间线是作品子集；上游评分单列。最新数据见正式馆藏。', 'Timeline entries are a subset. Upstream scores stay separate. Visit the live collection for current data.')}</p>
<section class="section" id="explore"><div class="section-head"><div><div class="eyebrow">THE CURATOR'S SELECTION</div><h2>{T('同一个问题，不同的回答','One question. Different answers.')}</h2><p>{T('三个已收录的真实输出。保留署名与出处，点击阅读完整记录。', 'Three actual archived outputs. Follow each image to its credited record.')}</p></div><a class="text-link" href="{live}/specimens/">{T('浏览全部作品 ↗','Browse all works ↗')}</a></div><div class="grid">{''.join(selected)}</div><p class="note">{T('模型标签按来源保留，未独立认证；日期按记录中的证据精度。预览取自正式馆藏，作品权利归原作者。', 'Model labels are source-reported, not independently authenticated. Dates keep their documented precision. Previews come from the live collection; rights remain with the creators.')}</p></section>
<section class="section"><div class="section-head"><div><div class="eyebrow">FIELD NOTES</div><h2>{T('带着问题逛一逛','Take a question with you')}</h2></div></div><div class="paths">{path_html}</div></section>
<section class="quote"><h2>{T('好作品值得停留，<br>失败也值得收藏。','Good work deserves a closer look.<br>Failures deserve an archive.')}</h2><div><p>{T('一个有据可查的输出，记作一件作品。不同实际设置分别记录，转载与同一视频的多个帧不重复计数。完整原图、来源链接和生成过程尽量保留；不重画，不替失败“修图”。', 'One documented output is one work. Actual different settings are recorded separately; reposts and multiple frames of the same video do not add works. Preserve originals, source links and creation context. Never redraw a failed output.')}</p><a href="{live}/about/">{T('了解收录方法 →','Read the collection method →')}</a></div></section>
<section class="section" id="developers"><div class="developers"><div><div class="eyebrow">DATA &amp; AGENTS</div><h2>{T('为人浏览，也为程序阅读','For people. For programs.')}</h2><p>{T('中英文页面、数据导出与接口共用一份审核目录。公开服务只读；默认检索排除来源存档与 Benchmark，按稳定 ID 查询仍可读。', 'Pages, exports and interfaces share one reviewed bilingual catalog. Public services are read-only. Default search excludes context and benchmark references; direct stable-ID lookup remains available.')}</p><div class="link-row"><a href="{live}/data/catalog.json">JSON</a><a href="{live}/data/catalog.csv">CSV</a><a href="{SITE}/openapi.json">OpenAPI</a><a href="{live}/llms.txt">llms.txt</a><a href="{live}/feed.xml">RSS</a></div></div><div><pre><code>GET /api/v1/specimens?q=Gemini&amp;lang=en&amp;limit=3
GET /api/v1/timeline?family=Claude&amp;sort=oldest

MCP · Streamable HTTP
https://pelicanmap.aveniqa.com/mcp

search_specimens · get_specimen · get_timeline</code></pre><div class="link-row"><a href="{live}/developers/">{T('阅读接入文档 ↗','Read the developer guide ↗')}</a><a href="{REPO}/blob/main/CONTRIBUTING.md">{T('参与维护 →','Contribute →')}</a></div></div></div></section></main>
<footer><div class="wrap"><div class="footer-top"><div class="footer-brand">{T('一只鸟，一辆车，一段 AI 小史。','One bird. One bicycle. A small history of AI.')}</div><div class="footer-links"><a href="{REPO}">GitHub</a><a href="{live}/rights/">{T('来源与使用','Rights &amp; sources')}</a><a href="{REPO}/issues/new/choose">{T('提交来源 / 更正','Sources / corrections')}</a><a href="#main">↑</a></div></div><p class="rights">{T('项目原创代码 MIT。馆藏作品与上游资料沿用原作者许可，收录不改变其权利。原始题目与早期实验来自 Simon Willison。本页为项目介绍，完整馆藏、原始媒体和只读服务见正式网站。', 'Original project code: MIT. Artworks and upstream materials keep their authors’ rights and licenses. The original prompt and early experiments come from Simon Willison. This is the project introduction; the complete archive, media and services are on the live website.')}</p></div></footer></body></html>'''
    dest = OUT / ('en/index.html' if en else 'index.html')
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(result, encoding='utf8')


def cover():
    logo = ROOT / 'site/assets/logo-a.png'
    (OUT / 'assets').mkdir(parents=True, exist_ok=True)
    (OUT / 'assets/logo.png').write_bytes(logo.read_bytes())
    data = base64.b64encode(logo.read_bytes()).decode()
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1200" height="630" viewBox="0 0 1200 630" role="img" aria-labelledby="title desc"><title id="title">pelicanmap</title><desc id="desc">One bird. One bicycle. A small history of AI. A bilingual, source-linked field guide.</desc><rect width="1200" height="630" fill="#f6f2e9"/><rect x="26" y="26" width="1148" height="578" fill="none" stroke="#d9d5c6"/><path d="M68 102H1132M68 534H1132" stroke="#d9d5c6"/><g fill="#a64f32" font-family="monospace" font-size="13" letter-spacing="2"><text x="68" y="75">THE PELICAN QUESTION</text><text x="913" y="75">AN AI FIELD GUIDE</text></g><text x="66" y="242" fill="#385647" font-family="Georgia,serif" font-size="86" letter-spacing="-4">pelicanmap</text><text x="70" y="327" fill="#282d25" font-family="Georgia,'Microsoft YaHei',serif" font-size="31">一只鸟，一辆车，一段 AI 小史。</text><text x="70" y="384" fill="#646957" font-family="Georgia,serif" font-size="22">One bird. One bicycle. A small history of AI.</text><g fill="#385647" font-family="monospace" font-size="13" letter-spacing="1"><text x="70" y="470">COLLECTION / TIMELINE / PROVENANCE / API + MCP</text></g><rect x="803" y="160" width="285" height="285" fill="#e9e4d6"/><rect x="793" y="150" width="285" height="285" fill="#fffcf5" stroke="#d9d5c6"/><image x="822" y="179" width="227" height="227" xlink:href="data:image/png;base64,{data}"/><text x="68" y="569" fill="#646957" font-family="monospace" font-size="13">A SMALL PROMPT. AN UNFOLDING STORY.</text><text x="856" y="569" fill="#385647" font-family="monospace" font-size="13">pelicanmap.aveniqa.com</text></svg>'''
    (OUT / 'assets/github-cover.svg').write_text(svg, encoding='utf8')


if __name__ == '__main__':
    cover()
    build('zh')
    build('en')
    (OUT / 'robots.txt').write_text('User-agent: *\nAllow: /\nSitemap: '+PAGES+'/sitemap.xml\n', encoding='utf8')
    (OUT / 'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>'+PAGES+'/</loc></url><url><loc>'+PAGES+'/en/</loc></url></urlset>', encoding='utf8')
    print('Generated bilingual project pages and GitHub cover from public catalog snapshots.')
