"""Build an English-first, screenshot-led GitHub project site."""
import base64
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs'
SITE = 'https://pelicanmap.aveniqa.com'
REPO = 'https://github.com/UncleK/pelicanmap'
PAGES = 'https://unclek.github.io/pelicanmap'
E = lambda value: html.escape(str(value), quote=True)


def build(language):
    en = language == 'en'
    T = lambda zh, english: english if en else zh
    catalog = json.loads((ROOT / ('site/catalog.en.json' if en else 'site/catalog.json')).read_text(encoding='utf8'))
    counts = catalog['counts']
    live = SITE + ('/en' if en else '')
    canonical = PAGES + ('/' if en else '/zh/')
    title = T('pelicanmap · 收集所有鹈鹕骑车案例', 'pelicanmap · The pelican-on-a-bicycle archive')
    description = T('收集各模型、各时间段、所有媒体类型的鹈鹕骑车真实案例。', 'Collecting all documented pelican-riding-a-bicycle cases across AI models, dates and media.')
    labels = [T('独立作品','Works'), T('时间线代表 · 作品子集','Timeline representatives · a subset'), T('来源文章','Source articles'), T('独立评分参考合集','Separate benchmark collection')]
    stats = ''.join(f'<div class="stat"><strong>{counts[key]:,}</strong><span>{label}</span></div>' for key, label in zip(['cases','timeline','sourceIndex','benchmarkCollections'], labels))
    shots = [
        ('pelican-history-wall.png', T('看看更早的回答。','The earlier answers.'), T('2025 年的 20 件真实输出截图','Twenty documented outputs from 2025'), '/specimens/?year=2025&view=images', 1200, 730),
        ('selected-works-en.png', T('每张图，都有自己的故事。','Every image has a story.'), T('精选作品：模型、日期与出处','Selected works with models, dates and original sources'), '/', 1200, 1137),
    ]
    galleries = ''.join(f'<section class="shot-section"><div class="shot-heading"><h2>{heading}</h2><a class="text-link" href="{live+url}">{T("打开馆藏 ↗","Open the archive ↗")}</a></div><a class="screenshot" href="{live+url}"><img src="../assets/{name}" alt="{alt}" width="{width}" height="{height}" loading="lazy"></a></section>' for name, heading, alt, url, width, height in shots)
    result = f'''<!doctype html>
<html lang="{'en' if en else 'zh-CN'}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title><meta name="description" content="{description}"><meta name="theme-color" content="#f6f2e9"><link rel="canonical" href="{canonical}"><link rel="alternate" hreflang="en" href="{PAGES}/"><link rel="alternate" hreflang="zh-CN" href="{PAGES}/zh/"><meta property="og:type" content="website"><meta property="og:title" content="{title}"><meta property="og:description" content="{description}"><meta property="og:url" content="{canonical}"><meta property="og:image" content="{PAGES}/assets/social-preview{'-en' if en else ''}.png"><meta name="twitter:card" content="summary_large_image"><link rel="icon" href="../assets/logo.png"><link rel="stylesheet" href="../assets/project.css"></head>
<body><a class="skip" href="#main">{T('跳到正文','Skip to content')}</a><header class="head"><div class="wrap head-inner"><a class="brand" href="../"><img src="../assets/logo.png" width="49" height="49" alt=""><span><strong>pelicanmap</strong><small>{T('鹈鹕骑车案例馆','THE PELICAN ARCHIVE')}</small></span></a><nav aria-label="{T('主导航','Main navigation')}"><a href="#gallery">{T('图片','Gallery')}</a><a href="#developers">API / MCP</a><a href="{REPO}">GitHub ↗</a><a href="{'../zh/' if en else '../'}" lang="{'zh-CN' if en else 'en'}">{T('English','Chinese')}</a></nav></div></header>
<main id="main" class="wrap"><section class="visual-hero"><div class="visual-title"><div><div class="eyebrow">{T('真实输出 · 原始出处','ACTUAL OUTPUTS. ORIGINAL SOURCES.')}</div><h1>{T('一个问题。<br><em>一大群鹈鹕。</em>','One prompt.<br><em>A whole flock.</em>')}</h1></div><div class="hero-side"><p>{description}</p><div class="actions"><a class="button" href="{live}/specimens/?view=images">{T('浏览所有作品','Browse all works')} ↗</a><a class="button secondary" href="{REPO}">GitHub →</a></div><code>Generate an SVG of a pelican riding a bicycle.</code></div></div><figure class="wall" id="gallery"><a href="{live}/specimens/?view=images"><img src="../assets/pelican-wall.png" alt="{T('正式馆藏纯图片视图：30 件真实输出','Thirty actual outputs in the collection’s image-only view')}" width="1200" height="1100" fetchpriority="high"></a><figcaption><span>{T('30 件真实输出，点击查看原记录。','30 documented outputs. Follow the images to their sources.')}</span><a href="{live}/specimens/?view=images">{T('纯图片视图 ↗','Images-only view ↗')}</a></figcaption></figure></section><div class="stats">{stats}</div><p class="snapshot">{T('统计快照','SNAPSHOT')} / {catalog['updated']}</p>
{galleries}
<section class="code-section" id="developers"><div><div class="eyebrow">{T('数据与接口','DATA &amp; AGENTS')}</div><h2>{T('把资料读进程序。','Read the archive.')}</h2><div class="link-row"><a href="{live}/data/catalog.json">JSON</a><a href="{live}/data/catalog.csv">CSV</a><a href="{SITE}/openapi.json">OpenAPI</a><a href="{live}/developers/">{T('接入文档','Docs')} ↗</a></div></div><pre><code>GET /api/v1/specimens?q=Gemini&amp;lang=en&amp;limit=3
GET /api/v1/timeline?family=Claude&amp;lang=en

MCP  https://pelicanmap.aveniqa.com/mcp
     search_specimens · get_specimen · get_timeline</code></pre></section></main>
<footer><div class="wrap"><div class="footer-top"><div class="footer-brand">{T('一只鸟，一辆车，一段 AI 小史。','One bird. One bicycle. A small history of AI.')}</div><div class="footer-links"><a href="{REPO}">GitHub</a><a href="{live}/about/">{T('收录方法','Method')}</a><a href="{live}/rights/">{T('来源与许可','Credits')}</a><a href="{REPO}/issues/new/choose">{T('补充案例','Submit a case')}</a></div></div><p class="rights">{T('截图来自正式馆藏；作品权利归原作者。来源模型标注未独立认证，精选不是排名。','Screenshots from the live archive. Artwork rights remain with the creators. Source-reported models are not independently authenticated; selections are not rankings.')}</p></div></footer></body></html>'''
    dest = OUT / ('en/index.html' if en else 'zh/index.html')
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(result, encoding='utf8')


def cover():
    logo = ROOT / 'site/assets/logo-a.png'
    (OUT / 'assets').mkdir(parents=True, exist_ok=True)
    (OUT / 'assets/logo.png').write_bytes(logo.read_bytes())
    data = base64.b64encode(logo.read_bytes()).decode()
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1200" height="630" viewBox="0 0 1200 630" role="img" aria-labelledby="title desc"><title id="title">pelicanmap</title><desc id="desc">One bird. One bicycle. A small history of AI. A bilingual, source-linked field guide.</desc><rect width="1200" height="630" fill="#f6f2e9"/><rect x="26" y="26" width="1148" height="578" fill="none" stroke="#d9d5c6"/><path d="M68 102H1132M68 534H1132" stroke="#d9d5c6"/><g fill="#a64f32" font-family="monospace" font-size="13" letter-spacing="2"><text x="68" y="75">THE PELICAN QUESTION</text><text x="913" y="75">AN AI FIELD GUIDE</text></g><text x="66" y="242" fill="#385647" font-family="Georgia,serif" font-size="86" letter-spacing="-4">pelicanmap</text><text x="70" y="327" fill="#282d25" font-family="Georgia,'Microsoft YaHei',serif" font-size="31">一只鸟，一辆车，一段 AI 小史。</text><text x="70" y="384" fill="#646957" font-family="Georgia,serif" font-size="22">One bird. One bicycle. A small history of AI.</text><g fill="#385647" font-family="monospace" font-size="13" letter-spacing="1"><text x="70" y="470">COLLECTION / TIMELINE / PROVENANCE / API + MCP</text></g><rect x="803" y="160" width="285" height="285" fill="#e9e4d6"/><rect x="793" y="150" width="285" height="285" fill="#fffcf5" stroke="#d9d5c6"/><image x="822" y="179" width="227" height="227" xlink:href="data:image/png;base64,{data}"/><text x="68" y="569" fill="#646957" font-family="monospace" font-size="13">A SMALL PROMPT. AN UNFOLDING STORY.</text><text x="856" y="569" fill="#385647" font-family="monospace" font-size="13">pelicanmap.aveniqa.com</text></svg>'''
    (OUT / 'assets/github-cover.svg').write_text(svg, encoding='utf8')
    english_svg = svg.replace('一只鸟，一辆车，一段 AI 小史。', 'One bird. One bicycle.').replace('One bird. One bicycle. A small history of AI.</text>', 'Collecting every documented pelican-on-a-bicycle case.</text>').replace('font-size="22">Collecting', 'font-size="19">Collecting')
    (OUT / 'assets/github-cover-en.svg').write_text(english_svg, encoding='utf8')


if __name__ == '__main__':
    cover()
    build('zh')
    build('en')
    english = (OUT / 'en/index.html').read_text(encoding='utf8').replace('../assets/', 'assets/').replace('href="../zh/"', 'href="zh/"').replace('href="../"', 'href="./"')
    (OUT / 'index.html').write_text(english, encoding='utf8')
    (OUT / 'robots.txt').write_text('User-agent: *\nAllow: /\nSitemap: '+PAGES+'/sitemap.xml\n', encoding='utf8')
    (OUT / 'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>'+PAGES+'/</loc></url><url><loc>'+PAGES+'/zh/</loc></url></urlset>', encoding='utf8')
    print('Generated English-first visual project pages with separate Chinese translation.')
