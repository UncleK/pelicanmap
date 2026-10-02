"""Publish a complete English edition with stable paired URLs and shared media."""
import copy
import csv
import hashlib
import html
import io
import json
import math
import os
import re
from collections import defaultdict
from pathlib import Path
from bs4 import BeautifulSoup
from catalog_policy import playable_records
from collection_views import listing, legacy_page_count, legacy_years
from detail_presentation import record_content
from experiment_batches import apply_batches, group_records, batch_pages
from card_metadata import card_footer
from case_policy import is_case, in_timeline, relationship_html
from benchmark_reference import pages as benchmark_pages, record_details as benchmark_record_details
from editorial_content import INTRO as INTROS, CATALOG_VERSION, featured as select_featured, csv_text, scope_sections, sections_html, agent_sections, agent_guide, home_schema, record_schema

ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('PELICAN_OUTPUT_DIR',ROOT/'public-site'))
BASE='https://pelicanmap.aveniqa.com'
UPDATED='2026-10-01'
PAGES=[]
COUNTS={}
E=lambda value:html.escape(str(value or ''),quote=True)
SOURCES={'origin':'Original experiment','zoo':'Pelican Zoo','wtf':'pelicans.wtf','community':'Community record'}
FORMATS={'svg':'Static SVG','image':'Image','animation':'Animation','3d':'3D work','game':'Game / interactive','video':'Video','audio':'Audio','other':'Other media','text':'Text / reference'}
INTRO=INTROS['en']
ASSET_VERSION=hashlib.sha256(b''.join((ROOT/'site/assets'/n).read_bytes() for n in ['site.css','site.js','browse.js'])).hexdigest()[:12]

def dump(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.tmp')
    temporary.write_text(value,encoding='utf-8')
    temporary.replace(path)

def jdump(path,value): dump(path,json.dumps(value,ensure_ascii=False,separators=(',',':')))

def translations():
    originals=json.loads((ROOT/'site/i18n/record-strings.json').read_text(encoding='utf-8'))
    lines=(ROOT/'site/i18n/records.en.txt').read_text(encoding='utf-8').splitlines()
    values={int(line.split('\t',1)[0]):line.split('\t',1)[1] for line in lines if line.strip()}
    assert set(values)==set(range(len(originals))), 'Incomplete record translations'
    return {value:values[n] for n,value in enumerate(originals)}

def link(url,text,cls=''):
    if not url:return ''
    attrs=' target="_blank" rel="noopener noreferrer"' if url.startswith('https://') else ''
    return f'<a class="{E(cls)}" href="{E(url)}"{attrs}>{E(text)}</a>'

def local(path): return '/en'+path

def card(x):
    if not is_case(x) and not x.get('referenceOnly') and not x.get('interactive'):
        return '<article class="callout source-archive-link">'+link(x['path'],x['title']+' · source archive')+'</article>'
    image=f'<img src="{E(x["thumbnail"])}" alt="{E(x["title"])}" width="640" height="420" loading="lazy">' if x['thumbnail'] else '<div class="media-note"><strong>'+('Source deleted' if x['mediaStatus']=='source-deleted' else 'Text record')+'</strong><span>Read the context and original source</span></div>'
    note=x['notes'] or x['author'] or 'Explore the work, prompt category and original source.'
    return f'<article class="card specimen-card"><a class="card-cover" href="{x["path"]}">{image}<span class="media-label">{x["formatLabel"]}</span><span class="source-label" title="{E(x["sourceLabel"])}">{E(x["sourceLabel"])}</span></a><div class="card-body" tabindex="0" aria-label="Work description"><h3>{link(x["path"],x["title"])}</h3><p class="note">{E(note)}</p></div>{card_footer(x,"en")}</article>'

def cards(items):return ''.join(card(x) for x in items)

def timeline_card(x):
    return f'<article class="card timeline-card"><a class="card-cover" href="{x["path"]}"><img src="{E(x["thumbnail"])}" alt="{E(x["model"])} · {E(x["date"])}" width="640" height="420" loading="lazy"></a>{card_footer(x,"en",timeline=True)}</article>'
def top(title,desc,eyebrow='THE COLLECTION'):return f'<div class="page-top"><div class="eyebrow">{E(eyebrow)}</div><h1>{E(title)}</h1><p>{E(desc)}</p></div>'

def page(path,title,desc,body,nav='',schema=None,noindex=False):
    en=local(path); canonical=BASE+en
    navitems=[('/','Selected'),('/timeline/','Timeline'),('/specimens/','Collection'),('/play/','Play'),('/tags/benchmark/','Benchmarks'),('/sources/','Sources')]
    navigation=''.join(f'<a href="{local(p)}"'+(' aria-current="page"' if p==nav else '')+f'>{label}</a>' for p,label in navitems)
    schema=schema or {'@context':'https://schema.org','@type':'CollectionPage','name':title,'description':desc,'url':canonical,'inLanguage':'en','isPartOf':{'@type':'WebSite','name':'Pelican Map','url':BASE+'/en/'},'dateModified':UPDATED}
    social_image=schema.get('image') if schema.get('image','').lower().endswith(('.png','.jpg','.jpeg','.webp')) else BASE+'/assets/og-cover-en.png'
    social_type='article' if schema['@type']=='CreativeWork' else 'website'
    serialized=json.dumps(schema,ensure_ascii=False).replace('<','\\u003c')
    md=en+'index.md' if path.endswith('/') else ''
    result=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)} · Pelican Map</title><meta name="description" content="{E(desc[:200])}"><meta name="robots" content="{'noindex,follow' if noindex else 'index,follow,max-image-preview:large'}">
<link rel="canonical" href="{canonical}"><link rel="alternate" hreflang="zh-CN" href="{BASE+path}"><link rel="alternate" hreflang="en" href="{canonical}"><link rel="alternate" hreflang="x-default" href="{BASE+path}">
<link rel="icon" href="/assets/logo-a.png" type="image/png"><link rel="apple-touch-icon" href="/assets/logo-a.png"><link rel="stylesheet" href="/assets/site.css?v={ASSET_VERSION}">
<meta property="og:type" content="{social_type}"><meta property="og:locale" content="en_US"><meta property="og:locale:alternate" content="zh_CN"><meta property="og:site_name" content="Pelican Map"><meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc[:200])}"><meta property="og:url" content="{canonical}"><meta property="og:image" content="{E(social_image)}"><meta property="og:image:alt" content="{E(title)}"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{E(title)}"><meta name="twitter:description" content="{E(desc[:200])}"><meta name="twitter:image" content="{E(social_image)}"><meta name="twitter:image:alt" content="{E(title)}">
<link rel="describedby" href="/en/llms.txt"><link rel="alternate" type="application/rss+xml" title="Archive updates" href="/en/feed.xml">{f'<link rel="alternate" type="text/markdown" href="{md}">' if md else ''}
<script type="application/ld+json">{serialized}</script><script src="/assets/site.js?v={ASSET_VERSION}" defer></script><script type="module" src="/assets/browse.js?v={ASSET_VERSION}"></script></head>
<body id="top"><a class="skip" href="#main">Skip to content</a><header class="site-head"><div class="wrap head-inner"><a class="brand" href="/en/"><img src="/assets/logo-a.png" width="56" height="56" alt=""><span><strong>Pelican Map</strong><small>AN AI FIELD GUIDE</small></span></a><nav class="nav" aria-label="Main navigation">{navigation}<a class="nav-search" href="/en/specimens/#search">Search ↗</a><a class="language-switch" data-language href="{path}" hreflang="zh-CN" lang="zh-CN" aria-label="切换到中文">中文</a></nav></div></header>
<main id="main" class="wrap">{body}</main><footer class="site-footer"><div class="wrap"><div class="footer-top"><div><div class="footer-brand">One bird. Two wheels. A little history of AI.</div><p class="small">Pelican Map · An archive & curated exhibition</p></div><div class="footer-links"><a href="/en/about/">About & methods</a><a href="/en/rights/">Credits & use</a><a href="/en/developers/">Data & agents</a><a href="/en/feed.xml">RSS</a><a href="#top">Back to top ↑</a></div></div><div class="copyright">Compiled {UPDATED}. Original creators retain their rights; source-reported models are not independently authenticated. The timeline is a representative subset of all works. Benchmark references are counted separately.</div></div></footer></body></html>'''
    dest=OUT/en.strip('/')/'index.html' if path.endswith('/') else OUT/en.lstrip('/')
    dump(dest,result)
    if md:
        soup=BeautifulSoup(body,'html.parser')
        text=soup.get_text('\n',strip=True)
        refs='\n'.join(f'- {a.get_text(" ",strip=True)}: {BASE+a["href"] if a["href"].startswith("/") else a["href"]}' for a in soup.select('a[href]'))
        dump(OUT/md.lstrip('/'),f'# {title}\n\n{text}\n\n## Links\n{refs}\n')
    if not noindex:PAGES.append(en)

def search_form():
    opts=''.join(f'<option value="{k}">{v}</option>' for k,v in SOURCES.items())
    forms=''.join(f'<option value="{k}">{v}</option>' for k,v in FORMATS.items())
    return f'<form class="filters" id="search" data-search role="search"><label>Search the archive<input type="search" name="q" placeholder="Model, creator, notes…" maxlength="200"></label><label>Source<select name="source"><option value="">All sources</option>{opts}</select></label><label>Format<select name="format"><option value="">All formats</option>{forms}</select></label><label>Sort<select name="sort"><option value="">Default order</option><option value="newest">Newest first</option><option value="oldest">Oldest first</option></select></label><button class="button" type="submit">Search</button><button class="button secondary" type="reset">Reset</button></form>'

def detail(x,items):
    body='<div class="page-top"><div class="breadcrumb"><a href="/en/">Home</a> / <a href="/en/specimens/">Collection</a> / Record</div>'+f'<div class="eyebrow">{E(x["sourceLabel"])} · {E(x["date"])}</div><h1>{E(x["title"])}</h1></div>'
    if x.get('batch'):
        body += '<p class="batch-parent">Part of: '+link(x['batch']['path'], x['batch']['title']+' · '+str(x['batch']['total'])+' samples →')+'</p>'
    body += benchmark_record_details(x,'en')
    facts=[('Recorded date',x['date'] or 'Not recorded'),('Date precision',{'day':'Day','month':'Month; exact day unverified','year':'Year'}.get(x.get('datePrecision'),'Upstream record')),('Date basis',x.get('dateBasis') or 'Upstream record; generation date not independently verified'),('Model (source label)',x['model'] or 'Not specified; not inferred'),('Model attribution','Source-reported, not independently authenticated'),('Creator / publisher',x['author'] or 'See original source'),('Format',x['formatLabel']),('Prompt category',x['promptCategory'] or 'Not separately recorded'),('Original prompt',x['promptStatus']),('Last updated',UPDATED)]
    demo=x.get('demoUrl') or x.get('previewUrl')
    buttons=link(x['sourceUrl'],'Original source ↗','button')+link('#demo' if demo else '', 'Interact on this page ↓' if x.get('interactive') else 'Watch animation preview ↓','button secondary')+link(x['externalUrl'],'External demo / share ↗','button secondary')+link(x['sourceCodeUrl'],'Source file ↗','button secondary')
    buttons+=link(x.get('licenseUrl'),'Attribution ↗','button secondary')+''.join(link(url,'License ↗','button secondary') for url in x.get('licenseFiles',[]))
    body += record_content(x,items,OUT,facts,buttons,'en')
    body+=f'<div class="share-row"><button type="button" data-copy>Copy record link</button>{link(x["markdown"],"Markdown record","button secondary")}</div>'
    related=[r for r in items if (bool(r.get('referenceOnly')) if x.get('referenceOnly') else is_case(r)) and r['id']!=x['id'] and r['source']==x['source'] and r['format']==x['format']][:3]
    body+='<section class="section"><div class="section-head"><h2>Keep exploring</h2><a class="text-link" href="/en/specimens/">Explore the collection ↗</a></div><div class="grid">'+cards(related)+'</div></section>'
    schema=record_schema(x,'en')
    page(x['path'][3:],x['title'],x['notes'] or f'{x["title"]}: archived {x["formatLabel"].lower()} with sources and context.',body,nav='/tags/benchmark/' if x.get('referenceOnly') else '/specimens/',schema=schema)
    md=f'# {x["title"]}\n\n{x["notes"]}\n\n'+'\n'.join(f'- {k}: {v}' for k,v in facts)
    md+='\n'+'\n'.join('- '+key+': '+str(x[key]) for key in ['caseRole','caseNumber','timelineVisible','datePrecision','dateBasis','parentId','representativeOf','canonicalId','comparisonIds','cropProvenance'] if key in x)
    md+=f'\n- Original source: {x["sourceUrl"]}\n- Archive record: {x["url"]}\n- Rights: {x["rights"]}\n'
    md+='\n'.join(f'- Media: {BASE+m["src"] if m["src"].startswith("/") else m["src"]}\n  Source: {m["source"]}' for m in x['media'])
    if x.get('licenseUrl'):md+='\n- Attribution: '+BASE+x['licenseUrl']
    for url in x.get('licenseFiles',[]):md+='\n- Full license: '+BASE+url
    if x['demoUrl']:md+='\n- Interactive demo: '+x['demoUrl']
    if x.get('previewUrl'):md+='\n- Animation preview: '+x['previewUrl']
    dump(OUT/x['markdown'].lstrip('/'),md+'\n')

def build_editorial(items,byid,data):
    content={
    '/about/':('About & methods','An archive of a small question',[
      ('What this is',INTRO),
      *scope_sections(COUNTS,'en'),
      ('How records are handled','We preserve public sources, dates, creator names, source-provided model labels and media. Model names reflect their sources; they are not independently certified by this site. Missing prompts are identified rather than reconstructed. English notes are translations of the archive summaries; source links and original creator names are retained.'),
      ('October 1 community all-media batch','Twenty-six independent outputs from ten LINUX DO topics and their replies were source-checked and archived: 2025 comparisons, 2026 animation and 3D previews, with 36 original media files and source-reported model labels. Eighteen enter the timeline; eight same-day comparison outputs have no documented default setting or default run, so they count as works without a guessed best representative. Projects with unverified code licences are not mirrored as Play demos.'),
      ('Public X originals in the same batch','Two public original posts were checked in an authorized signed-in browser, yielding five static SVG previews and five timeline representatives. A labelled four-model image was split into four works; two screenshots of another single output count only once. Three complete originals and five faithful pixel crops are archived with coordinates and source evidence. A future animation mentioned by its author was not published in that post and is not presented as an animation or Play demo.'),
      ('Original-source and cross-media follow-up','Twenty-five original articles linked by Nile entries 31–55 were reviewed. Forty-four works were added: 25 single-model Simon outputs, 15 original beetle_b POV-Ray renders, three MIT-licensed Sonnet 4.5 visual-feedback versions and one explicitly labelled GEPA / Opus 4.6 zero-shot baseline. They provide 32 timeline representatives and 58 original media files. Fourteen final SVGs were visually matched to source previews. Reposts, previously archived images and unresolved multi-model outputs are not added again. POV-Ray error correction and visual feedback are documented, not presented as one-shot generation. Twelve same-day settings/runs/iterations lack representative evidence or are non-representative alternatives and remain only in the collection. The optimized GEPA image is held pending model attribution. Log timestamps, publication dates and explicit dated updates are preserved; public commit dates are not authenticated generation dates. No project code or new Play demo is mirrored.'),
      ('Maintenance','Latest October 1 authorization: the collection and timeline accept all dates and media; collection rules, bilingual scope, SEO and Agent/API descriptions are synchronized. Interactive mirrors still require permission, safety and operation review. September 27, 2026: accessible media, sources, bilingual pages and machine-readable catalogs archived. October 1: HF/OpenEnv moved to separate Benchmark references; labelled compilations and community grids split, five historical static SVGs added, original IDs and media preserved, model-family filtering introduced. Bilingual selection, counting text, SEO metadata, structured data and Agent/API guides updated together. Later historical-link batch: 37 submitted entry points checked, 36 missing static outputs archived and two existing DeepSeek comparison outputs split into works; one duplicated Qwen archive pair merged for counting. Dates preserved, only source-default/medium or page-default runs represent the timeline; broken SVGs are not repaired or counted. Early-timeline follow-up: original Simon articles linked by Nile yielded three additional static outputs: two Gemma 3n quantizations/runtimes and Grok 4. The Mistral Small 3.2 illustration duplicates an existing X output and is not counted again. No default/medium Gemma representative is documented, so both remain outside the evolution axis. Original previews and source labels retained; publication dates are not claimed as generation dates. Second early-timeline batch: Nile entries 21–30 were traced to original articles and yielded nine July–August 2025 static works and nine dated representatives: Kimi K2, Qwen3, GLM 4.5/Air, XBai o4 and Claude Opus 4/4.1. Five include verbatim final SVG code and four retain source-published static previews. Per-response timestamps or publication-date bases are preserved; existing Qwen output, reasoning screenshots, videos and games are not added again. Remaining entry points still require review; coverage is not claimed complete. Media availability is not independent reproduction.')]),
    '/rights/':('Credits & use','Credits & use',[
      ('Works and sources','Media, code and source links retain their original attribution. Archiving, creating a preview or offering a download does not change a work’s license or imply endorsement by its creator.'),
      ('Using the material','Keep creator names and original links when citing. Check the upstream LICENSE and creator’s terms before reusing media or code. Unverified licenses are not presented as open licenses; packages without a verified source URL are not offered for public download.'),
      ('Known source limitations','The Zeos submission-site domain could not be confirmed from its post. Restricted articles retain public index information and original links. The OpenAI livestream is linked online, with a clearly labeled frame preview.'),
      ('Corrections and removal','Creators and readers can contact the site publisher through the original channel where this archive was shared. Include the archive record URL, original source and requested correction or removal.'),
      ('Privacy','This site has no registration, comments or advertising trackers. Cloudflare and the hosting service may generate operational access and error logs. External sites have their own policies.')]),
    '/collections/origins/':('Why a pelican on a bicycle?','Why a pelican on a bicycle?',[
      ('A very specific small question','On October 25, 2024, Simon Willison published an SVG experiment involving a pelican riding a bicycle and shared the outputs of several models. Asking code to describe a bird and a bicycle made differences in interpretation visible.'),
      ('The classic prompt','Generate an SVG of a pelican riding a bicycle. The collection and timeline accept all dates and media, including explicit prompt or species variants. Animation, video, 3D and interactions retain their documented tools, iterations and generation conditions. Consult the source; not all records share identical conditions.'),
      ('Look at the connections','Start with the wheels, frame and body, then look at the beak, pouch, feet and pedals. Differences often emerge in these relationships. The 22 original SVGs below are historical samples, not evidence of the models’ current performance.')]),
    '/collections/beyond-svg/':('Historical explorations beyond SVG','Historical explorations beyond SVG',[
      ('Works across media','The collection and timeline accept all dates and media. Source-verifiable animation, video, 3D, games and interactions retain original assets and generation conditions. Multiple frames or views of one work are not additional works.'),
      ('New forms, different conditions','Animation adds time and movement; 3D introduces viewpoint and environment; games add input and feedback. All these media can appear on the dated timeline, but differences in models, prompts, tools and human involvement do not constitute a controlled capability comparison or performance ranking.'),
      ('Preserved source entry points','Original repository, animation comparisons, Blender works, cycling games and DB32 keep their provenance. On-site operation is available only in previously reviewed demo details.')]),
    '/collections/reading-the-test/':('What can one image tell us?','What can one image tell us?',[
      ('What you can observe','A work can reveal how a model represents shapes and relationships in a particular generation. Runnable examples also show whether movement is coherent and controls provide feedback. Failure can be informative too.'),
      ('Keep the conditions in view','Record the complete model version and generation date, whether prompts were identical, how many revisions were made, which tools or libraries were used, and whether outputs were selected from multiple attempts.'),
      ('Uncertainty stays visible','Missing prompts are not replaced by the classic prompt. Text-only records and unavailable sources without displayable media are omitted from the public collection. Uncertain attribution is identified. L0–L4 labels are historical catalog annotations, not scores from a standardized benchmark.'),
      ('Cite the conditions','Include the work, source, date and known generation conditions. A single sample offers material to observe; broader capability claims require reproducible evaluation.')])}
    content['/about/'][2].append(('Detail presentation update','October 1, 2026: existing moving media and reviewed on-site demos now appear before stills. Same-model comparisons precede the individual image; originals and provenance remain available in collapsed sections. Chinese and English share the layout. Year shortcuts, counts/page summary and the archive entry have been repositioned; the view button names the current mode. Artwork and timeline totals are unchanged.'))
    for path,(title,heading,sections) in content.items():
        body=top(heading,'An AI field guide · Pelican Map')+'<article class="prose">'+''.join(f'<h2>{E(h)}</h2><p>{E(p)}</p>' for h,p in sections)
        if path.endswith('origins/'):
            body+=link('https://simonwillison.net/2024/Oct/25/pelicans-on-a-bicycle/','Read the original article ↗')+'</article><div class="grid">'+cards([x for x in items if x['source']=='origin'])+'</div>'
        elif path.endswith('beyond-svg/'):
            body+='</article><div class="grid">'+cards([byid[k] for k in ['github-simonw-pelican-bicycle','pelican-ride-lab-15','blender-astra-2026-09-05','tihuqiche-game','x-janek-db32-4kb-2026-09-26']])+'</div>'
        else:body+='</article>'
        page(path,title,sections[0][1],body)
    from source_layout import render
    page('/sources/','Sources & repositories','Original repositories, runnable demos and the story behind Simon Willison’s pelican bicycle experiment.',render(data,[x for x in items if not x.get('referenceOnly')],'en'),nav='/sources/')
    body=top('An archive that agents can read','Public, read-only and source-attributed. The same records power the website and data exports.','DATA & AGENTS')+f'''<article class="prose"><h2>Download & cite</h2><p><a href="/en/data/catalog.json">English JSON</a> · <a href="/en/data/catalog.csv">English CSV</a> · <a href="/en/llms.txt">Agent guide</a> · <a href="/openapi.json">OpenAPI</a></p><p>Catalog version {CATALOG_VERSION}, compiled {UPDATED}. Website, exports and public API use the same reviewed catalog.</p>{sections_html(scope_sections(COUNTS,'en'))}<h2>Read-only HTTP API</h2><pre>GET /api/v1/specimens?q=Gemini&amp;lang=en&amp;limit=10
GET /api/v1/specimens/{{id}}?lang=en
GET /api/v1/timeline?family=Gemini&amp;sort=oldest&amp;lang=en&amp;limit=20</pre>{sections_html(agent_sections('en'))}<h2>Connect with MCP</h2><p>Add this Streamable HTTP server to a compatible MCP client:</p><pre>{BASE}/mcp</pre><p>search_specimens, get_specimen and get_timeline support lang: zh/en and the same filtering and pagination as HTTP. No login is required.</p></article>'''
    from ingestion_docs import section
    body+=section(True)
    page('/developers/','Data & agent access','JSON, CSV, Markdown, a read-only HTTP API and MCP tools for exploring the archive with attribution.',body)

def build():
    PAGES.clear()
    mapping=translations()
    catalog=copy.deepcopy(json.loads((OUT/'data/catalog.json').read_text(encoding='utf-8')))
    items=catalog['items']
    COUNTS.update(catalog['counts'])
    for x in items:
        for field in ['title','notes','promptCategory','mediaNote']:
            value=x.get(field,''); x[field]=x.get('i18n',{}).get('en',{}).get(field,mapping.get(value,value))
        x['sourceLabel']=SOURCES[x['source']];x['formatLabel']=FORMATS[x['format']]
        x['promptStatus']=x.get('i18n',{}).get('en',{}).get('promptStatus','The complete original prompt is not recorded here; consult the source.')
        x['rights']='Works belong to their original creators. Archiving does not change their licenses.'
        x['path']=local(x['path']);x['url']=BASE+x['path'];x['markdown']=local(x['markdown'])
        for m in x['media']:
            if m.get('captionEn'):m['caption']=m['captionEn']
            elif '直播画面截图' in m['caption']:m['caption']='Livestream frame · 17:55 · captured 2026-09-27'
            elif '实际运行截图' in m['caption']:m['caption']='Screenshot of the running demo · captured 2026-09-27'
            elif re.search(r'[\u4e00-\u9fff]',m['caption']):m['caption']='Archived media from the original source'
    items=apply_batches(items,'en')
    catalog['items']=items
    catalog.update(language='en',benchmarkUrl='/en/tags/benchmark/')
    catalog['countingNote']='counts.cases counts independent outputs, including settings separately; counts.timeline counts timeline representatives, not an additional set of works. caseVisible=false source/context archives and referenceOnly scoring references do not enter main lists, counts, numbering or default API. timelineVisible controls the timeline; kind retains historical source classification. Raw items preserves original archives and is not a case count.'
    jdump(OUT/'en/data/catalog.json',catalog);jdump(ROOT/'site/catalog.en.json',catalog)
    dump(OUT/'en/data/catalog.csv',csv_text(items))
    byid={x['originalId']:x for x in items}
    featured=select_featured(items)
    hero=featured[-1]
    body=f'''<section class="hero"><div><div class="hero-kicker"><span class="eyebrow">THE PELICAN QUESTION</span><span class="edition">VOL. 01 / 2024—2026</span></div><h1 class="hero-title"><span>One pelican.</span><span class="hero-second">Endless <em>possibilities.</em></span></h1><div class="hero-subline">A SMALL PROMPT. AN UNFOLDING STORY.</div><p class="intro">{INTRO}</p><div class="actions"><a class="button" href="/en/timeline/">Timeline <span>↗</span></a><a class="button secondary" href="/en/specimens/">All works <span>→</span></a></div><p class="small">An evolving archive · Source-reported models, not independently authenticated</p></div><figure class="hero-figure"><span class="plate-no">MODEL OUTPUT / #{hero["caseNumber"]}</span><a href="{hero["path"]}"><img class="cover" src="{E(hero["thumbnail"])}" alt="{E(hero["model"])} · {E(hero["date"])} · Static SVG output preview" width="960" height="720" fetchpriority="high"></a><figcaption><span>{E(hero["date"])} · {E(hero["model"])} (source label)</span>{link(hero["path"],"View record ↗")}</figcaption></figure></section>
<div class="stats-strip"><div><strong data-total-records data-total-cases>{COUNTS['cases']}</strong><span>independent works · settings included</span></div><div><strong>{COUNTS["timeline"]}</strong><span>timeline representatives · a subset</span></div><div><strong>{COUNTS["sourceIndex"]}</strong><span>Simon sources · not artworks</span></div><div><strong>{COUNTS["benchmarkCollections"]}</strong><span>Benchmark collections · separate</span></div><span class="updated">LAST UPDATED / {UPDATED}</span></div>
<section class="section" id="featured"><div class="section-head"><div><div class="eyebrow">THE CURATOR'S SELECTION</div><h2>Start with these</h2><p>From the 2024 originals to recent outputs: one model, one image. A selection, not a ranking.</p></div><a class="text-link" href="/en/specimens/">Explore the collection ↗</a></div><div class="grid">{cards(featured)}</div></section>'''
    topics=[('origins','01 / THE BEGINNING','Why a pelican on a bicycle?','Start with the original repository and a very specific question.'),('beyond-svg','02 / ACROSS MEDIA','Explorations beyond SVG','Animation, 3D and interactions with their generation conditions preserved.'),('reading-the-test','03 / A CLOSER LOOK','What can one image tell us?','Read the conditions behind each comparison.')]
    body+='<section class="section"><div class="section-head"><div class="eyebrow">FIELD NOTES</div><h2>Bring a question</h2></div><div class="topics">'+''.join(f'<a class="topic" href="/en/collections/{slug}/"><span class="eyebrow">{ey}</span><h3>{title}</h3><p>{desc}</p><span>Read the field note →</span></a>' for slug,ey,title,desc in topics)+'</div></section><section class="quote-band"><h2>Keep the beautiful.<br>Keep the failures, too.</h2><div><p>Preserving the model, date, media and source makes it possible to observe how one question is understood, reinterpreted and changed.</p><p><a href="/en/about/">About the archive →</a></p></div></section>'
    schema=home_schema('Pelican bicycle AI archive & curated exhibition',featured,'en')
    schema['dateModified']=UPDATED
    page('/','Pelican bicycle AI archive & curated exhibition',INTRO,body,nav='/',schema=schema)
    total=math.ceil(len(items)/24)
    for n in range(total):
        path='/specimens/' if n==0 else f'/specimens/page/{n+1}/'
        title='The collection' if n==0 else f'The collection · Page {n+1}'
        body=top(title,f'{COUNTS["cases"]} independent outputs, including different settings; {COUNTS["timeline"]} timeline representatives are a subset, not additional works. Source compilations, reposts and scoring references are not counted again.')+listing(items,'/en/specimens/','',card,'en',number=n+1,archive_link=True)
        page(path,title,'Search AI pelican bicycle works by model, creator, format and source.',body,nav='/specimens/',noindex=n>=math.ceil(COUNTS['cases']/24))
    timeline=[x for x in items if in_timeline(x)];years=sorted({x['date'][:4] for x in timeline},reverse=True)
    archived_years={x['date'][:4] for x in items if re.match(r'^\d{4}',x['date'])}
    for year in [None]+sorted(set(years)|legacy_years(OUT,'en')|archived_years,reverse=True):
        selected=[x for x in timeline if not year or x['date'].startswith(year)]
        base='/timeline/'+(year+'/' if year else '')
        for n in range(legacy_page_count(OUT,'/en'+base,max(1,math.ceil(len(selected)/24)))):
            body=top('Timeline'+(' · '+year if year else ''),'All dates and media. One date, one source-labelled model, one representative work; moving works use original previews or real frames. Author default first, otherwise medium; other outputs remain in details. Date precision follows evidence. Benchmark references are excluded. Filter by year or model family.','CHRONOLOGY')
            if year and year not in years:body+='<p class="callout">No source-labelled single-model representatives for this year. Historical context remains in <a href="/en/collections/source-records/">source archives</a>, not artwork totals.</p>'
            body+=listing(timeline,'/en'+base,'timeline',timeline_card,'en',number=n+1,year=year or '',years=sorted(set(years)|({year} if year else set()),reverse=True))
            page(base+(f'page/{n+1}/' if n else ''),'Pelican bicycle timeline'+(' · '+year if year else ''),'Browse single-model representatives across all media by year, model family and date. Source labels are not independently authenticated; not a museum ranking.',body,nav='/timeline/',noindex=bool(year and year not in years) or n>=max(1,math.ceil(len(group_records(selected))/24)))
    for batch, batch_body in batch_pages(items,'en'):
        page(batch['path'][3:],batch['title'],batch['description'],batch_body,nav='/specimens/')
    for x in items:detail(x,items)
    for path, title, description, benchmark_body in benchmark_pages(items,'en'):
        page(path,title,description,benchmark_body,nav='/tags/benchmark/')
    page('/play/','Interactive demos','On-site interactions reviewed for operation, permission and safety; playback alone is not Play.',top('Interactive demos','Open a record to rotate a view, control a ride or operate a scene on our isolated demo domain, without automatic source redirects. Only verified meaningful interactions with clear permission qualify. The collection and timeline accept all media.','INTERACTIVE CABINET')+listing(playable_records(items),'/en/play/','play',card,'en'),nav='/play/')
    data=json.loads((ROOT/'pelican-web/data.js').read_text(encoding='utf-8').split('=',1)[1].strip().rstrip(';'))
    build_editorial(items,byid,data)
    archives=[x for x in items if not is_case(x) and not x.get('referenceOnly')]
    page('/collections/source-records/','Source collections & archives','Original compilations, duplicates and unresolved attribution are preserved without adding artwork counts.',top('Source collections & archives','Original compilations and context are retained here, not counted as additional artworks.')+'<ul>'+''.join('<li>'+link(x['path'],x['date']+' · '+x['title'])+'</li>' for x in archives)+'</ul>',nav='/sources/')
    page('/404.html','Page not found','This address may be incorrect or the record may have moved.',top('This specimen is not here','Try searching the collection.')+link('/en/specimens/','Back to the archive','button'),noindex=True)
    guide=agent_guide(COUNTS,UPDATED,'en')
    dump(OUT/'en/llms.txt',guide)
    dump(OUT/'en/feed.xml','<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>Pelican Map</title><link>'+BASE+'/en/</link><description>'+E(INTRO)+'</description>'+''.join(f'<item><title>{E(x["title"])}</title><link>{x["url"]}</link><guid isPermaLink="true">{x["url"]}</guid><description>{E(x["notes"] or x["formatLabel"])}</description></item>' for x in group_records(sorted(timeline,key=lambda x:x['date'],reverse=True))[:30])+'</channel></rss>')
    # Paired links are real HTML links. Language switching never relies on client JS.
    zh_paths=[]
    for p in sorted(OUT.rglob('*.html')):
        if p.relative_to(OUT).parts[0]=='en':continue
        soup=BeautifulSoup(p.read_text(encoding='utf-8'),'html.parser');canonical=soup.select_one('link[rel=canonical]')['href'];path=canonical.removeprefix(BASE)
        for tag in soup.select('link[hreflang], a[data-language]'):tag.decompose()
        for lang,url in [('zh-CN',canonical),('en',BASE+local(path)),('x-default',canonical)]:soup.head.append(soup.new_tag('link',rel='alternate',hreflang=lang,href=url))
        switch=soup.new_tag('a',href=local(path),hreflang='en',lang='en',attrs={'class':'language-switch','data-language':'','aria-label':'Switch to English'});switch.string='EN';soup.select_one('.nav').append(switch)
        dump(p,str(soup))
        if path!='/404.html' and not soup.select_one('meta[name=robots]')['content'].startswith('noindex'):zh_paths.append(path)
    urls=[]
    for path in zh_paths:
        for loc in [path,local(path)]:urls.append(f'<url><loc>{BASE+loc}</loc><lastmod>{UPDATED}</lastmod><xhtml:link rel="alternate" hreflang="zh-CN" href="{BASE+path}"/><xhtml:link rel="alternate" hreflang="en" href="{BASE+local(path)}"/><xhtml:link rel="alternate" hreflang="x-default" href="{BASE+path}"/></url>')
    dump(OUT/'sitemap.xml','<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">'+''.join(urls)+'</urlset>')
    print(json.dumps({'english_pages':len(PAGES),'localized_records':len(items),'translated_record_strings':len(mapping)}))

if __name__=='__main__':build()
