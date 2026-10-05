"""Build the public archive from verified local records; never modify originals."""
import csv
import hashlib
import html
import io
import json
import math
import os
import re
import shutil
import subprocess
from collections import defaultdict
from pathlib import Path
from atomic_files import replace_with_retry
from urllib.parse import quote
from PIL import Image, ImageDraw, ImageFont, ImageOps
from catalog_policy import apply_demo_policy, playable_records
from collection_views import listing, legacy_page_count, legacy_years
from detail_presentation import record_content, apply_motion_previews, cover_media
from experiment_batches import apply_batches, group_records, case_counts, batch_pages
from card_metadata import apply_card_metadata, card_footer
from model_chronology import apply_model_chronology, timeline_year
from detail_frames import apply_detail_frames
from benchmark_reference import pages as benchmark_pages, record_details as benchmark_record_details, load as load_benchmark
from thumbnail_overrides import apply_thumbnail_overrides
from record_overrides import apply_record_overrides
from case_policy import apply_case_policy, is_case, in_timeline, relationship_html
from editorial_content import INTRO as INTROS, CATALOG_VERSION, csv_text, scope_sections, sections_html, agent_sections, agent_guide, home_schema, record_schema, openapi
from editorial_content import listing_notes, HOME_COPY
from historical_context import HISTORY_ID, historical_hero, historical_markdown, historical_display

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'pelican-web'
OUT = Path(os.environ.get('PELICAN_OUTPUT_DIR',ROOT / 'public-site'))
DEMOS = ROOT / 'public-demos'
BASE = 'https://pelicanmap.aveniqa.com'
DEMO_BASE = os.environ.get('PELICAN_DEMO_ORIGIN', 'https://pelicanmap-demos.aveniqa.com').rstrip('/')
UPDATED = '2026-10-05'
# Baseline imports keep their archival update date; a new compilation is not
# a modification of every historical work. New additions carry their own date.
LEGACY_RECORD_UPDATED = '2026-10-01'
SITE = '鹈鹕骑车标本馆'
ASSET_VERSION = hashlib.sha256(b''.join((ROOT / 'site/assets' / name).read_bytes() for name in ('site.css', 'site.js', 'browse.js', 'motion.js'))).hexdigest()[:12]
INTRO = INTROS['zh']
DATA = json.loads((SOURCE / 'data.js').read_text(encoding='utf-8').split('=', 1)[1].strip().rstrip(';'))
SOURCES = {'origin':'原点仓库','zoo':'Pelican Zoo','wtf':'pelicans.wtf','community':'社区记录'}
FORMATS = {'svg':'静态 SVG','image':'图像','animation':'动画','3d':'三维作品','game':'游戏 / 交互','video':'视频','audio':'音频','other':'其他媒体','text':'文字 / 资料'}
PAGES = []
COUNTS = {}
CAPTURES = json.loads((ROOT/'site/captures/manifest.json').read_text(encoding='utf-8'))

def e(value):
    return html.escape(str(value or ''), quote=True)

def dump(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary=path.with_name(path.name+'.tmp')
    temporary.write_text(content, encoding='utf-8')
    replace_with_retry(temporary,path)

def jdump(path, value):
    dump(path, json.dumps(value, ensure_ascii=False, separators=(',', ':')))

def copy_file(source, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists() or dest.stat().st_size != source.stat().st_size or source.stat().st_mtime > dest.stat().st_mtime:
        shutil.copy2(source, dest)

def asset(path):
    if not path:
        return ''
    if path.startswith('https://'):
        return path
    if path.startswith('demos/'):
        return DEMO_BASE + '/' + quote(path, safe='/')
    if path.startswith('media/'):
        return '/' + quote(path, safe='/')
    return ''

def fmt(record):
    value = record.get('form', '').lower()
    if any(x in value for x in ['game','interactive','playable']):
        return 'game'
    if any(x in value for x in ['3d','threejs','blender']):
        return '3d'
    if any(x in value for x in ['anim','html','demoscene']):
        return 'animation'
    if 'svg' in value:
        return 'svg'
    if record.get('media','').endswith('.mp4') or value in ['film','video']:
        return 'video'
    return 'text'

def thumb(path):
    if not path or path.startswith('https://'):
        return asset(path)
    source = SOURCE / path
    if source.suffix.lower() == '.svg':
        return asset(path)
    if source.suffix.lower() in ['.mp4','.webm']:
        return ''
    if not source.exists():
        return ''
    key = hashlib.sha256(path.encode()).hexdigest()[:16]
    target = OUT / 'assets/thumbs' / (key + '.webp')
    if not target.exists():
        with Image.open(source) as im:
            im = ImageOps.exif_transpose(im)
            im.thumbnail((960, 720), Image.Resampling.LANCZOS)
            if im.mode not in ('RGB','RGBA'):
                im = im.convert('RGBA')
            target.parent.mkdir(parents=True, exist_ok=True)
            im.save(target, 'WEBP', quality=84, method=6)
    return '/assets/thumbs/' + target.name

def normalize(record, kind):
    original_id = str(record['id'])
    suffix = hashlib.sha256((kind + ':' + original_id).encode()).hexdigest()[:8]
    slug = re.sub('[^a-z0-9]+', '-', original_id.lower()).strip('-')[:90] + '-' + suffix
    path = '/specimens/' + slug + '/'
    media = record.get('mediaItems') or ([{'src':record['media']}] if record.get('media') else [])
    media = [{'src':asset(m['src']), 'source':m.get('source') or record.get('url',''), 'caption':m.get('caption',''), 'poster':asset(m.get('poster',''))} for m in media if asset(m.get('src',''))]
    cover = (record.get('mediaItems') or [{}])[0].get('poster') or record.get('media','')
    captured = CAPTURES.get(original_id)
    captured_thumbnail = ''
    if captured:
        captured_thumbnail = '/assets/captures/' + captured['file']
        copy_file(ROOT/'site/captures'/captured['file'], OUT/captured_thumbnail.lstrip('/'))
        media.insert(0, {'src':captured_thumbnail,'source':captured['source'],'caption':captured['caption'],'poster':''})
    category = record.get('prompt','')
    return {'id':slug,'originalId':original_id,'kind':kind,
        'title':record.get('model') or record.get('title') or '未标注模型',
        'model':record.get('model',''),'author':record.get('author') or record.get('handle') or '',
        'date':record.get('date',''),'month':record.get('ym',''),'notes':record.get('notes',''),
        'source':record.get('src','community'),'sourceLabel':SOURCES.get(record.get('src'),'社区记录'),
        'sourceUrl':record.get('url',''),'format':fmt(record),'formatLabel':FORMATS[fmt(record)],
        'originalForm':record.get('form',''),'originalLevel':record.get('level') or record.get('levelN',''),
        'promptCategory':category,'promptStatus':'原始逐条提示词未在目录中完整记录，请查看来源',
        'mediaStatus':record.get('mediaStatus','local' if media else 'text-only'),
        'mediaNote':record.get('mediaNote',''),'media':media,'thumbnail':captured_thumbnail or thumb(cover),
        'demoUrl':asset(record.get('demo','')),'externalUrl':record.get('externalMediaUrl',''),
        'sourceCodeUrl':asset(record.get('sourceCode','')),
        'path':path,'url':BASE+path,'markdown':path+'index.md',
        'updated':record.get('updated',LEGACY_RECORD_UPDATED),'rights':'作品权利归原作者；本站收录不改变原作品许可。'}

def link(url, label, cls=''):
    if not url:
        return ''
    external = ' target="_blank" rel="noopener noreferrer"' if url.startswith('https://') else ''
    return f'<a href="{e(url)}" class="{e(cls)}"{external}>{e(label)}</a>'

def card(item):
    if not is_case(item) and not item.get('referenceOnly') and not item.get('interactive'):
        return '<article class="callout source-archive-link">'+link(item['path'],item['title']+' · 来源存档')+'</article>'
    if item['thumbnail']:
        cover = cover_media(item, item['title']+' · '+item['formatLabel'])
    else:
        label = '来源已删除' if item['mediaStatus']=='source-deleted' else '交互演示' if item['demoUrl'] else '文字记录'
        cover = f'<div class="media-note"><strong>{label}</strong><span>查看资料与原始出处</span></div>'
    note = item['notes'] or item['author'] or '查看作品、提示词分类与原始出处。'
    return f'<article class="card specimen-card"><a class="card-cover" href="{item["path"]}" aria-label="{e(item["title"])}">{cover}<span class="media-label">{item["formatLabel"]}</span><span class="source-label" title="{e(item["sourceLabel"])}">{e(item["sourceLabel"])}</span></a><div class="card-body" tabindex="0" aria-label="作品说明"><h3><a href="{item["path"]}">{e(item["title"])}</a></h3><p class="note">{e(note)}</p></div>{card_footer(item)}</article>'

def cards(items):
    return ''.join(card(x) for x in items)

def timeline_card(item):
    return f'<article class="card timeline-card"><a class="card-cover" href="{item["path"]}" aria-label="{e(item["title"])}">{cover_media(item, item["model"]+" · "+item["date"])}</a>{card_footer(item,timeline=True)}</article>'

def top(title, desc, eyebrow='THE COLLECTION'):
    return f'<div class="page-top"><div class="eyebrow">{eyebrow}</div><h1>{e(title)}</h1>{('<p>'+e(desc)+'</p>') if desc else ''}</div>'

def page(path, title, description, body, nav='', schema=None, markdown=None, noindex=False):
    if 'data-browser data-scope=' in body or path in ['/tags/benchmark/', '/sources/']:
        body += listing_notes(COUNTS, nav.strip('/').replace('tags/', ''))
    canonical = BASE + path
    navitems = [('/','首页'),('/timeline/','时间线'),('/specimens/','全部作品'),('/play/','可玩演示'),('/tags/benchmark/','Benchmark'),('/sources/','资料与来源')]
    navigation = ''.join(f'<a href="{p}"'+(' aria-current="page"' if p==nav else '')+f'>{t}</a>' for p,t in navitems)
    schema = schema or {'@context':'https://schema.org','@type':'CollectionPage','name':title,'description':description,'url':canonical,'inLanguage':'zh-CN','isPartOf':{'@type':'WebSite','name':SITE,'url':BASE+'/'},'dateModified':UPDATED}
    social_image=schema.get('image') if schema.get('image','').lower().endswith(('.png','.jpg','.jpeg','.webp')) else BASE+'/assets/og-cover.png'
    social_type='article' if schema['@type']=='CreativeWork' else 'website'
    serialized = json.dumps(schema, ensure_ascii=False).replace('<','\\u003c')
    alternate = f'<link rel="alternate" type="text/markdown" href="{e(markdown)}">' if markdown else ''
    robots = 'noindex,follow' if noindex else 'index,follow,max-image-preview:large'
    result = f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)} · {SITE}</title><meta name="description" content="{e(description[:180])}"><meta name="robots" content="{robots}">
<link rel="canonical" href="{canonical}"><link rel="icon" href="/assets/logo-a.png" type="image/png"><link rel="apple-touch-icon" href="/assets/logo-a.png">
<meta property="og:type" content="{social_type}"><meta property="og:locale" content="zh_CN"><meta property="og:locale:alternate" content="en_US"><meta property="og:site_name" content="{SITE}"><meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(description[:180])}"><meta property="og:url" content="{canonical}"><meta property="og:image" content="{e(social_image)}"><meta property="og:image:alt" content="{e(title)}">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{e(title)}"><meta name="twitter:description" content="{e(description[:180])}"><meta name="twitter:image" content="{e(social_image)}"><meta name="twitter:image:alt" content="{e(title)}">
<link rel="stylesheet" href="/assets/site.css?v={ASSET_VERSION}">{alternate}<link rel="describedby" href="/llms.txt"><link rel="alternate" type="application/rss+xml" title="馆藏更新" href="/feed.xml">
<script type="application/ld+json">{serialized}</script><script src="/assets/site.js?v={ASSET_VERSION}" defer></script><script type="module" src="/assets/browse.js?v={ASSET_VERSION}"></script><script type="module" src="/assets/motion.js?v={ASSET_VERSION}"></script></head>
<body id="top"><a class="skip" href="#main">跳到正文</a><header class="site-head"><div class="wrap head-inner"><a class="brand" href="/"><img src="/assets/logo-a.png" width="56" height="56" alt=""><span><strong>{SITE}</strong><small>PELICAN MAP · AN AI FIELD GUIDE</small></span></a><nav class="nav" aria-label="主导航">{navigation}</nav></div></header>
<main id="main" class="wrap">{body}</main><footer class="site-footer"><div class="wrap"><div class="footer-top"><div class="footer-brand">一只鸟，一辆车，一段 AI 小史。</div><div class="footer-links"><a href="/about/">关于与收录方法</a><a href="/rights/">来源与使用说明</a><a href="/developers/">数据与 Agent</a><a href="/feed.xml">RSS</a><a href="#top">回到顶部 ↑</a></div></div><div class="footer-bottom"><p class="small">Pelican Map</p><p class="copyright">作品归原作者 · 模型标注未独立认证</p></div></div></footer></body></html>'''
    dest = OUT / path.strip('/') / 'index.html' if path.endswith('/') else OUT / path.lstrip('/')
    dump(dest, result)
    if not noindex:
        PAGES.append(path)

def search_form(scope=''):
    opts = ''.join(f'<option value="{key}">{label}</option>' for key,label in SOURCES.items())
    formats = ''.join(f'<option value="{key}">{label}</option>' for key,label in FORMATS.items())
    return f'<form class="filters" id="search" data-search data-scope="{scope}" role="search"><label>检索馆藏<input type="search" name="q" placeholder="模型、作者、备注…" maxlength="200"></label><label>来源<select name="source"><option value="">全部来源</option>{opts}</select></label><label>形式<select name="format"><option value="">全部形式</option>{formats}</select></label><label>排序<select name="sort"><option value="">默认顺序</option><option value="newest">从新到旧</option><option value="oldest">从旧到新</option></select></label><button class="button" type="submit">检索</button><button class="button secondary" type="reset">重置</button></form>'

def prepare_assets():
    OUT.mkdir(exist_ok=True)
    for f in (ROOT/'site/assets').iterdir():
        copy_file(f, OUT/'assets'/f.name)
    for f in (SOURCE/'media').rglob('*'):
        if f.is_file():
            # Large source video gets a web derivative; original remains in the archive.
            dest = OUT/f.relative_to(SOURCE)
            if f.stat().st_size < 24*1024*1024:
                copy_file(f,dest)
            elif not dest.exists():
                ffmpeg = shutil.which('ffmpeg') or next(str(p) for p in Path(os.environ['LOCALAPPDATA']).glob('Microsoft/WinGet/Packages/Gyan.FFmpeg*/**/ffmpeg.exe'))
                dest.parent.mkdir(parents=True, exist_ok=True)
                subprocess.run([ffmpeg,'-y','-i',str(f),'-vf','scale=1280:-2','-c:v','libx264','-crf','28','-preset','fast','-c:a','aac','-b:a','96k','-movflags','+faststart',str(dest)],check=True,capture_output=True)
                assert dest.stat().st_size < 24*1024*1024, 'Video derivative too large'
    # Demo HTML runs on a separate origin. Keep original relative paths intact.
    shutil.copytree(SOURCE/'demos',DEMOS/'demos',dirs_exist_ok=True)
    shutil.copytree(OUT/'media',DEMOS/'media',dirs_exist_ok=True)
    dump(DEMOS/'robots.txt','User-agent: *\nDisallow: /\n')
    dump(DEMOS/'_headers','/*\n  X-Robots-Tag: noindex, nofollow\n  Referrer-Policy: no-referrer\n  X-Content-Type-Options: nosniff\n  Permissions-Policy: camera=(), microphone=(), geolocation=()\n')
    # Preserve full source ZIPs as byte-identical parts when above static asset limit.
    downloads = {}
    for f in (SOURCE/'repos').glob('*.zip'):
        if f.name=='staypzy.zip':
            continue
        if f.stat().st_size < 24*1024*1024:
            copy_file(f,OUT/'downloads'/f.name)
        else:
            chunks=[]
            with f.open('rb') as source:
                n=0
                while data:=source.read(8*1024*1024):
                    name=f'/_download-parts/{f.stem}-{n:03}.bin'
                    dest=OUT/name.lstrip('/')
                    dest.parent.mkdir(parents=True,exist_ok=True)
                    dest.write_bytes(data)
                    chunks.append(name)
                    n+=1
            downloads['/downloads/'+f.name]={'parts':chunks,'size':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()}
    jdump(ROOT/'site/downloads.json',downloads)
    fontpath=Path('C:/Windows/Fonts/msyh.ttc')
    if not fontpath.exists():
        fontpath=Path('C:/Windows/Fonts/simhei.ttf')
    # Keep the selected imagegen artwork; resize only for delivery assets.
    with Image.open(ROOT/'site/assets/logo-a.png') as logo:
        logo.thumbnail((256,256),Image.Resampling.LANCZOS)
        logo.save(OUT/'assets/logo-a.png',optimize=True)
        logo.resize((180,180),Image.Resampling.LANCZOS).save(OUT/'assets/apple-touch-icon.png')
        for language in ['zh','en']:
            cover=Image.new('RGB',(1200,630),'#f6f2e9')
            d=ImageDraw.Draw(cover)
            cover.paste(logo,(860,175),logo)
            d.line((70,90,1130,90),fill='#d9d5c6',width=2)
            d.text((70,45),'PELICAN MAP / AN AI FIELD GUIDE',fill='#164b35',font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',22))
            heading='一只鹈鹕。\n无数种可能。' if language=='zh' else 'One pelican.\nEndless possibilities.'
            d.multiline_text((65,165),heading,fill='#164b35',font=ImageFont.truetype(str(fontpath) if language=='zh' else 'C:/Windows/Fonts/georgia.ttf',64 if language=='zh' else 58),spacing=18)
            d.text((70,510),'资料馆 ＋ 精选展示' if language=='zh' else 'AN ARCHIVE & CURATED EXHIBITION',fill='#646957',font=ImageFont.truetype(str(fontpath) if language=='zh' else 'C:/Windows/Fonts/consola.ttf',25))
            cover.save(OUT/('assets/og-cover.png' if language=='zh' else 'assets/og-cover-en.png'),optimize=True)

def detail(item, items):
    item = historical_display(item)
    body = f'<div class="breadcrumb"><a href="/">首页</a> / <a href="/specimens/">馆藏</a> / 标本详情</div>'
    if item.get('batch'):
        body += '<p class="batch-parent">所属实验合集：'+link(item['batch']['path'], item['batch']['title']+' · '+str(item['batch']['total'])+' 个样本 →')+'</p>'
    body = '<div class="page-top">'+body+f'<div class="eyebrow">{e(item["sourceLabel"])} · {e(item["date"])}</div><h1>{e(item["title"])}</h1></div>'
    body += benchmark_record_details(item)
    facts=[('记录日期',item['date'] or '未记录'),('日期精度',{'day':'日','month':'月（具体日未核实）','year':'年'}.get(item.get('datePrecision'),'按上游记录')),('日期依据',item.get('dateBasis') or '按上游记录，生成日期未独立核实'),('模型（来源标注）',item['model'] or '未标注；不推断'),('模型归属', '按来源保留，未独立认证'),('作者 / 发布者',item['author'] or '请见原始出处'),('形式',item['formatLabel']),('提示词分类',item['promptCategory'] or '未单独记录'),('原始提示词',item['promptStatus']),('更新日期',UPDATED)]
    demo=item.get('demoUrl') or item.get('previewUrl')
    buttons=link(item['sourceUrl'],'查看原始出处 ↗','button')+link('#demo' if demo else '', '在本页操作 ↓' if item.get('interactive') else '观看动画预览 ↓','button secondary')+link(item['externalUrl'],'外部演示 / 分享 ↗','button secondary')+link(item['sourceCodeUrl'],'查看源文件 ↗','button secondary')
    buttons+=link(item.get('licenseUrl'),'署名与许可说明 ↗','button secondary')+''.join(link(url,'许可全文 ↗','button secondary') for url in item.get('licenseFiles',[]))
    body += record_content(item,items,OUT,facts,buttons)
    body+=f'<div class="share-row"><button type="button" data-copy>复制标本链接</button>{link(item["markdown"],"Markdown 资料","button secondary")}</div>'
    related=[x for x in items if (bool(x.get('referenceOnly')) if item.get('referenceOnly') else is_case(x)) and x['id']!=item['id'] and x['source']==item['source'] and x['format']==item['format']][:3]
    body+='<section class="section"><div class="section-head"><h2>继续观察</h2><a href="/specimens/" class="text-link">查看全部馆藏 ↗</a></div><div class="grid">'+cards(related)+'</div></section>'
    schema=record_schema(item)
    page(item['path'],item['title'],f'{item["title"]}，{item["date"]}。{item["notes"] or item["formatLabel"]}。查看作品、资料与原始出处。',body,nav='/tags/benchmark/' if item.get('referenceOnly') else '/specimens/',schema=schema,markdown=item['markdown'])
    md=f'# {item["title"]}\n\n{item["notes"]}\n\n'
    md+='\n'.join('- '+key+': '+str(item[key]) for key in ['caseRole','caseNumber','timelineVisible','datePrecision','dateBasis','parentId','representativeOf','canonicalId','comparisonIds','cropProvenance'] if key in item)+'\n\n'
    md+='\n'.join(f'- {k}: {v}' for k,v in facts)
    md+=f'\n- 来源: {item["sourceUrl"]}\n- 本站记录: {item["url"]}\n- 媒体状态: {item["mediaStatus"]}\n- 使用说明: {item["rights"]}\n\n'
    md+='\n'.join(f'- 媒体: {BASE+m["src"] if m["src"].startswith("/") else m["src"]}\n  原始来源: {m["source"]}' for m in item['media'])
    if item.get('licenseUrl'):md+='\n- 署名与许可说明: '+BASE+item['licenseUrl']
    for url in item.get('licenseFiles',[]):md+='\n- 许可全文: '+BASE+url
    if item['demoUrl']:
        md+='\n- 演示: '+item['demoUrl']
    if item.get('previewUrl'):md+='\n- 动画预览: '+item['previewUrl']
    if item.get('referenceOnly'):md+='\n\n上游输出，非本馆排名。不进入主时间线、全部作品或案例总数。\n\n```json\n'+json.dumps(item['datasetSample'],ensure_ascii=False,indent=2)+'\n```\n'
    if item['id']==HISTORY_ID:md+=historical_markdown()
    dump(OUT/item['markdown'].lstrip('/'),md+'\n')

def build(items=None,prepare=True):
    PAGES.clear()
    if prepare:prepare_assets()
    if items is None:
        items=[normalize(r,kind) for kind in ['gallery','timeline'] for r in DATA[kind]]
        additions=ROOT/'site/additions.json'
        if additions.exists():items+=json.loads(additions.read_text(encoding='utf-8'))
    excluded=json.loads((ROOT/'site/publication-exclusions.json').read_text(encoding='utf-8'))
    excluded_ids={x['id'] for x in excluded}
    items=[x for x in items if x['id'] not in excluded_ids]
    items=apply_record_overrides(items,OUT)
    items=apply_thumbnail_overrides(items,OUT)
    items=apply_demo_policy(items)
    items=apply_batches(items)
    items=apply_case_policy(items,OUT)
    items=apply_card_metadata(items)
    items=apply_model_chronology(items)
    items=apply_motion_previews(items,OUT)
    items=apply_detail_frames(items,OUT)
    COUNTS.update(case_counts(items),sourceIndex=len(DATA['simon']),benchmarkCollections=len(json.loads((ROOT/'site/benchmarks/index.json').read_text(encoding='utf8'))))
    assert all(x['thumbnail'] and x['media'] for x in items), 'Public works need visible media'
    removed_paths=[]
    for item in excluded:
        for prefix in ['', 'en/']:
            for name in ['index.html','index.md']:
                relative=f'{prefix}specimens/{item["id"]}/{name}'
                target=(OUT/relative).resolve()
                assert target.is_relative_to(OUT.resolve())
                target.unlink(missing_ok=True)
                removed_paths.append(relative)
            folder=target.parent
            if folder.exists() and not any(folder.iterdir()):folder.rmdir()
    jdump(ROOT/'deploy-build/removed-public-pages.json',removed_paths)
    assert len({x['id'] for x in items})==len(items)
    by_original={x['originalId']:x for x in items}
    body=f'''<section class="hero"><div><div class="hero-kicker"><span class="eyebrow">THE PELICAN QUESTION</span><span class="edition">VOL. 01 / 2024—2026</span></div><h1 class="hero-title"><span>一只鹈鹕，</span><span class="hero-second">无数种<em>可能。</em></span></h1><div class="hero-subline">A SMALL PROMPT. AN UNFOLDING STORY.</div><p class="hero-question">{e(HOME_COPY['zh']['question'])}</p><p class="intro">{e(HOME_COPY['zh']['description'])}</p><div class="actions"><a class="button" href="/timeline/">时间线 <span>↗</span></a><a class="button secondary" href="/specimens/">全部作品 <span>→</span></a></div><p class="small">一个持续整理的资料馆 · 模型标注按来源保留，未独立认证</p></div>{historical_hero(items)}</section>
<div class="stats-strip"><div><strong data-total-records data-total-cases>{COUNTS['cases']}</strong><span>独立作品 · 含不同档位输出</span></div><div><strong>{COUNTS["timeline"]}</strong><span>进化轴代表图 · 作品子集</span></div><div><strong>{COUNTS["sourceIndex"]}</strong><span>Simon 来源索引 · 不计作品</span></div><div><strong>{COUNTS["benchmarkCollections"]}</strong><span>Benchmark 合集 · 单列参考</span></div><span class="updated">LAST UPDATED / {UPDATED}</span></div>'''
    topics=[('origins','01 / THE BEGINNING','为什么是鹈鹕骑车？','从原点仓库开始，认识这个小题目。'),('beyond-svg','02 / ACROSS MEDIA','跨介质探索','动画、三维与交互，保留各自生成条件。'),('reading-the-test','03 / A CLOSER LOOK','一张图能说明什么？','了解提示词、版本与比较的边界。')]
    body+='<section class="section"><div class="section-head"><div><div class="eyebrow">FIELD NOTES</div><h2>带着问题逛一逛</h2></div></div><div class="topics">'+''.join(f'<a class="topic" href="/collections/{slug}/"><span class="eyebrow">{ey}</span><h3>{title}</h3><p>{desc}</p><span>阅读专题 →</span></a>' for slug,ey,title,desc in topics)+'</div></section>'
    body+='<section class="quote-band"><h2>好作品值得停留，<br>失败也值得收藏。</h2><div><p>每一份记录尽量保留模型、时间、媒体与原始出处。这里的并置是一种观察：同一题目如何被理解，又如何不断被改写。</p><p><a href="/about/">了解收录方法 →</a></p></div></section>'
    schema=home_schema('鹈鹕骑车：AI 作品资料馆与精选展示')
    schema['dateModified']=UPDATED
    page('/','鹈鹕骑车：AI 作品资料馆与精选展示',INTRO,body,nav='/',schema=schema,markdown='/index.md')
    from bs4 import BeautifulSoup
    home_soup=BeautifulSoup(body,'html.parser')
    home_links='\n'.join('- '+a.get_text(' ',strip=True)+': '+(BASE+a['href'] if a['href'].startswith('/') else a['href']) for a in home_soup.select('a[href]'))
    dump(OUT/'index.md','# 鹈鹕骑车：AI 作品资料馆与精选展示\n\n'+home_soup.get_text('\n',strip=True)+'\n\n## 链接\n'+home_links+'\n')
    for n in range(math.ceil(len(items)/24)):
        path='/specimens/' if n==0 else f'/specimens/page/{n+1}/'
        title='全部作品' if n==0 else f'全部作品 · 第 {n+1} 页'
        body=top(title,'')+listing(items,'/specimens/','',card,number=n+1,archive_link=True)
        page(path,title,'按模型、作者、形式与来源检索鹈鹕骑车及衍生 AI 作品。',body,nav='/specimens/',noindex=n>=math.ceil(COUNTS['cases']/24))
    timeline=[x for x in items if in_timeline(x)]
    years=sorted({timeline_year(x) for x in timeline if timeline_year(x)!='unknown'},reverse=True)
    archived_years={x['date'][:4] for x in items if re.match(r'^\d{4}',x['date'])}
    for year in [None]+sorted(set(years)|legacy_years(OUT)|archived_years|{'unknown'},reverse=True):
        active_year='' if year=='unknown' else year or ''
        selected=timeline if not active_year else [x for x in timeline if timeline_year(x)==active_year]
        base='/timeline/'+(year+'/' if year else '')
        for n in range(legacy_page_count(OUT,base,max(1,math.ceil(len(selected)/24)))):
            body=top('时间线'+(' · '+active_year if active_year else ''),'','CHRONOLOGY')
            if active_year and active_year not in years:body+='<p class="callout">该年份没有符合单模型代表作品口径的输出。旧背景资料仍保留在 <a href="/collections/source-records/">来源存档</a>，不计作品数。</p>'
            body+=listing(timeline,base,'timeline',timeline_card,number=n+1,year=active_year,years=sorted(set(years)|({active_year} if active_year else set()),reverse=True))
            page(base+(f'page/{n+1}/' if n else ''),'鹈鹕骑车时间线'+(' · '+active_year if active_year else ''),'按型号顺序浏览全媒体代表作品；发布日期未有依据时采用最早作品月份暂定位置，卡片保留作品真实日期。',body,nav='/timeline/',noindex=bool(year and year not in years) or n>=max(1,math.ceil(len(group_records(selected))/24)))
    for batch, batch_body in batch_pages(items):
        page(batch['path'],batch['title'],batch['description'],batch_body,nav='/specimens/',markdown=batch['path']+'index.md')
        dump(OUT/(batch['path']+'index.md').lstrip('/'), '# '+batch['title']+'\n\n'+batch['description']+'\n\n原始数据集：'+batch['sourceUrl']+'\n\n'+'\n'.join('- ['+x['title']+']('+BASE+x['path']+')' for x in items if x.get('batch',{}).get('id')==batch['id'])+'\n')
    for item in items:
        detail(item,items)
    from bs4 import BeautifulSoup
    for path, title, description, benchmark_body in benchmark_pages(items):
        page(path,title,description,benchmark_body,nav='/tags/benchmark/',markdown=path+'index.md')
        dump(OUT/(path+'index.md').lstrip('/'), '# '+title+'\n\n'+BeautifulSoup(benchmark_body,'html.parser').get_text('\n',strip=True)+'\n')
    jdump(OUT/'data/benchmark.json',load_benchmark())
    build_editorial(items,by_original)
    build_sources(items)
    archives=[x for x in items if not is_case(x) and not x.get('referenceOnly')]
    archive_body=top('原帖合集与来源存档','已拆分的合集、转载和归属待核对资料保留在这里，不重复计作品数。')+'<ul>'+''.join('<li>'+link(x['path'],x['date']+' · '+x['title'])+'</li>' for x in archives)+'</ul>'
    page('/collections/source-records/','原帖合集与来源存档','完整原帖和未计数资料。',archive_body,nav='/sources/')
    build_machine_data(items)
    page('/404.html','页面未找到','页面地址可能有误，或馆藏目录已经调整。',top('这份标本不在这里','页面地址可能有误，或馆藏目录已经调整。')+'<p><a class="button" href="/specimens/">返回馆藏</a></p>',noindex=True)
    dump(OUT/'robots.txt',f'User-agent: *\nAllow: /\nDisallow: /api/\nDisallow: /mcp\nDisallow: /_download-parts/\n\nSitemap: {BASE}/sitemap.xml\n')
    dump(OUT/'sitemap.xml','<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(f'<url><loc>{BASE}{e(p)}</loc><lastmod>{UPDATED}</lastmod></url>' for p in PAGES)+'</urlset>')
    dump(OUT/'feed.xml','<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>'+SITE+'</title><link>'+BASE+'/</link><description>'+INTRO+'</description>'+''.join(f'<item><title>{e(x["title"])}</title><link>{x["url"]}</link><guid isPermaLink="true">{x["url"]}</guid><description>{e(x["notes"] or x["formatLabel"])}</description></item>' for x in group_records(sorted(timeline,key=lambda x:x['date'],reverse=True))[:30])+'</channel></rss>')
    headers="""/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=()
  Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' https: data:; media-src 'self' https:; connect-src 'self'; frame-src https://pelicanmap-demos.aveniqa.com; object-src 'none'; base-uri 'self'; frame-ancestors 'none'
  X-Frame-Options: DENY
/assets/*
  Cache-Control: public, max-age=3600
/media/*
  Cache-Control: public, max-age=86400
/data/*
  Access-Control-Allow-Origin: *
  Cache-Control: public, max-age=300
/downloads/*
  Content-Disposition: attachment
  Cache-Control: public, max-age=86400
"""
    dump(OUT/'_headers',headers)
    print(json.dumps({'pages':len(PAGES),'cases':COUNTS['cases'],'records':len(items),'batch_samples':COUNTS['samples'],'demo_origin':DEMO_BASE,'output':str(OUT)},ensure_ascii=False))

def build_editorial(items, by_id):
    origin=by_id['github-simonw-pelican-bicycle']
    playable=playable_records(items)
    page('/play/','可玩演示','经操作、许可与安全审核的本站交互作品；自动动画或播放控制不算可玩。',top('可玩演示','','INTERACTIVE CABINET')+listing(playable,'/play/','play',card),nav='/play/')
    origin_text=f'''<h2>从一个具体的小题目开始</h2><p>2024 年 10 月 25 日，Simon Willison 发表了关于鹈鹕骑自行车的 SVG 实验，并分享相关模型输出。用代码画一只鸟和一辆车，让不同模型的理解以可见的形式呈现出来。</p><p>经典提示是 <code>Generate an SVG of a pelican riding a bicycle</code>。当前收录与时间线不限时间段和媒体类型，也包含明确的题面变体；保留动画、视频、三维和交互的实际生成条件，不能假定所有记录条件相同。</p><p>你可以先看车轮、车架与身体如何连接，再看喙、喉囊、脚和踏板。不同作品的差异，往往出现在这些具体关系里。</p><p>{link("https://simonwillison.net/2024/Oct/25/pelicans-on-a-bicycle/","阅读原点文章 ↗")} · {link(origin["path"],"查看原点仓库记录")}</p><h2>22 份原点 SVG</h2><p>下列内容来自本地归档的原点仓库。它们是历史样本，模型标注按来源保留、未独立认证，不代表对应模型今天的最新表现。</p>'''
    page('/collections/origins/','为什么是鹈鹕骑车？', '从 Simon Willison 的原点文章与 22 份 SVG 开始，认识鹈鹕骑车这个 AI 小题目。',top('为什么是鹈鹕骑车？','FIELD NOTE 01 · 从一个具体问题出发')+'<article class="prose">'+origin_text+'</article><div class="grid">'+cards([x for x in items if x['source']=='origin'])+'</div>',markdown='/collections/origins/index.md')
    dump(OUT/'collections/origins/index.md','# 为什么是鹈鹕骑车？\n\n2024-10-25，Simon Willison 分享了鹈鹕骑车 SVG 实验。\n\n经典提示：Generate an SVG of a pelican riding a bicycle\n\n本站包含提示词变体，不能假定所有作品使用相同条件。\n\n来源：https://simonwillison.net/2024/Oct/25/pelicans-on-a-bicycle/\n')
    chosen=[by_id[k] for k in ['github-simonw-pelican-bicycle','pelican-ride-lab-15','blender-astra-2026-09-05','tihuqiche-game','x-janek-db32-4kb-2026-09-26']]
    text='<h2>跨介质作品，同样保留来源</h2><p>收录与时间线不限时间段和媒体类型。动画、视频、三维、游戏和交互等真实输出经核验后均可入馆；原链接、原媒体及工具、迭代和人工参与记录保留。同项目多视角或视频多帧不重复计数。</p><h2>形式变化，也改变了观察方式</h2><p>静态 SVG 可观察形状与空间关系；动画加入时间与运动；三维涉及视角与环境；游戏涉及输入与反馈。各作品的模型、提示、工具和人工参与程度不同，不能将这些形式排成模型能力进化或性能排行榜。</p><h2>作品与资料入口</h2><p>原点仓库、动态对照、Blender 作品、骑行游戏与 DB32 演示均保留出处。站内操作仅在许可清楚、安全隔离且经过实测的演示详情中提供，普通动画不冒充可玩。</p>'
    page('/collections/beyond-svg/','跨介质探索','动画、视频、三维与交互的真实输出，保留来源和生成条件；时间线不限媒体。',top('跨介质探索','FIELD NOTE 02 · 全媒体馆藏')+'<article class="prose">'+text+'</article><div class="grid">'+cards(chosen)+'</div>',markdown='/collections/beyond-svg/index.md')
    dump(OUT/'collections/beyond-svg/index.md','# 跨介质探索\n\n全时间段、所有媒体类型均可收录并进入时间线；保存真实输出、原媒体与来源，同项目视角或视频帧不重复计数。不同模型、提示、工具与人工参与程度不能组成统一能力排名。\n\n'+'\n'.join(f'- [{x["title"]}]({x["url"]})' for x in chosen))
    text='''<h2>能观察到什么？</h2><p>一份作品可以展示模型在一次生成中的形状表达、元素关系与代码表现；可运行作品还可以观察运动是否连贯、操作是否有反馈。失败的细节也能成为有趣的记录。</p><h2>哪些条件需要一起看？</h2><ul><li>模型的完整版本与生成日期。</li><li>提示词是否相同，是否多轮修正。</li><li>是否使用工具、现成库、参考素材或人工修改。</li><li>输出是否经过挑选，是否展示多次尝试。</li></ul><h2>本馆怎样处理不确定性？</h2><p>未记录的提示词不会自动补成经典提示；没有可展示媒体的文字记录与失效来源不进入公开作品列表；无法确认的归属会标注。L0～L4 等原目录标签保留在详情中作为整理背景，不作为本站发布的统一能力评分。</p><h2>引用时带上条件</h2><p>引用一张作品时，建议同时带上作品链接、来源、日期和已知生成条件。单个样本能提供观察材料，完整能力结论需要可复现的评测设计。</p>'''
    page('/collections/reading-the-test/','一张图能说明什么？','理解鹈鹕骑车样本的提示词、模型版本、工具使用与比较边界。',top('一张图能说明什么？','FIELD NOTE 03 · 带着条件看作品')+'<article class="prose">'+text+'</article>',markdown='/collections/reading-the-test/index.md')
    dump(OUT/'collections/reading-the-test/index.md','# 一张图能说明什么？\n\n观察形状、关系、代码与交互时，需要同时记录模型版本、日期、提示词、修改轮次和工具使用。单个样本不足以得出整体能力排名。\n\n本馆提示词缺失时保持缺失，等级标签只是历史整理标签。\n')
    about='<h2>一个关于小题目的资料馆</h2><p>'+e(INTRO)+'</p>'+sections_html(scope_sections(COUNTS))
    about+='<p>2026-10-01 历史链接补档：逐一核验用户提供的 37 个入口，新增 36 张漏收静态输出，并将已有 DeepSeek 对照拆为 2 个独立作品；合并一组重复的 Qwen 出处。全部输出按原始日期保留，时间线仅展示作者默认／medium 或原页默认运行；损坏 SVG 不修图、不计数。</p>'
    about+='<p>2026-10-01 早期时间线续查：回到 Nile 索引链接的 Simon 原文，补 Gemma 3n 两种量化／运行环境和 Grok 4 共 3 件静态输出。Mistral Small 3.2 图与旧 X 输出相同，不重复计数；Gemma 未明确默认／medium 代表，先留全部作品，不擅自选入进化轴。原始预览和来源标签保留，发布日期不冒充生成日。</p>'
    about+='<p>2026-10-01 旧案例第二批：继续核对 Nile 21–30 卡的原文，新增 2025 年 7–8 月的 Kimi K2、Qwen3、GLM 4.5／Air、XBai o4、Claude Opus 4／4.1 共 9 件独立静态输出及 9 张时间线代表图。5 件附逐字提取的原始 SVG，4 件保存上游静态预览；原媒体和逐条时间依据保留，既有 Qwen 输出不重收，不收推理截图、视频或游戏。其余入口未核完，不宣称历史完整。</p>'
    about+='<h2>收录方法</h2><p>保存公开来源、作者或发布者、可证日期、模型标注及本地媒体。提示词缺失时保持缺失；上游分数与对照均须标明「上游输出，非本馆排名」，不把历史 L0～L4 标签当本站评测。</p><h2>维护记录</h2><p>2026-10-01 最新授权：收录和时间线扩展为全时间段、所有媒体类型；同步采集规则、中英文范围、SEO 与 Agent/API 说明。真实交互仍须许可、安全和操作审核。</p><p>2026-09-27：补齐可获取媒体、来源索引、双语详情与机器可读目录。可打开不等于独立复现。</p><p>2026-10-01：HF/OpenEnv 迁入独立评分参考；按单模型单输出整理既有合集、拆分六月回顾与社区网格，补 5 件历史静态 SVG。保留旧 ID、原图与出处，增加家族筛选；同步修正双语精选、统计说明、SEO 元数据、结构化数据及 Agent/API 导读。</p><p><a href="/sources/">来源索引</a> · <a href="/collections/source-records/">合集与未计数资料</a> · <a href="/rights/">使用说明</a> · <a href="/developers/">数据与 Agent</a></p>'
    about+='<p>2026-10-01：复核全目录详情展示，已有动态媒体与站内演示前置，同模型对照先于单图，补充原图与溯源记录折叠保留；中英文共用顺序。年份、数量页码与源存档入口重排，视图按钮显示当前模式；作品与时间线计数不变。</p>'
    about+='<h3>2026-10-01 社区全媒体批次</h3><p>从 10 个 LINUX DO 原帖及其回复核验并归档 26 份独立输出，包含 2025 年对照、2026 年动画和三维预览，保留 36 份原始媒体与模型原标注。18 件进入时间线；8 件同日对照没有明确默认档／默认运行，只计全部作品，不擅自选最佳。未核实代码许可的项目不镜像为可玩演示。</p>'
    about+='<p>同批通过已获授权的登录浏览器核验 2 个 X 公开原帖，补 5 件静态 SVG 预览及 5 张时间线代表图；四模型原图按标签拆为 4 件，另一帖的两张同作截图仅计 1 件。保存 3 份完整原图和 5 份忠实像素裁切，详情可核原图、坐标和来源。作者提到的后续动画没有在该帖发布，不冒充动画或可玩项目。</p>'
    about+='<h3>2026-10-01 原文回链与跨媒体补档</h3><p>继续核对 Nile 31–55 卡回链的 25 篇原文，新增 25 件 Simon 单模型输出、15 件 beetle_b 原始 POV-Ray 渲染、3 件 MIT 许可的 Sonnet 4.5 视觉反馈版本和 1 件来源明确标注的 GEPA / Opus 4.6 零样本图，共 44 件作品、32 张时间线代表及 58 份原始媒体。14 份最终 SVG 与原文预览逐图核对；转载、已有同图和多模型归属不明的输出不重收。POV-Ray 修错与看图迭代明确记录，不冒充一次生成。12 件同日档位／运行／迭代没有代表证据或非代表档，仅留全部作品；不同模型身份未核清的优化后图暂缓。日期按日志时间、原文公开日或明确追加日保留，公开提交日不冒充已认证生成日。未镜像项目代码或新增可玩演示。</p>'
    about+='<h3>2026-10-02 社区动画与原文拆分</h3><p>核验两个 LINUX DO 原帖、Pelecanus 固定版本及 Nile 56–60 的五篇原文，新增 45 件独立作品：29 份原始动画 WebP、3 份动态网页静态预览、8 份明确模型标签的 Three.js 场景裁切、2 份二月 SVG 预览及从旧未计数存档拆出的 3 份单输出。15 张代表进入时间线；29 次重复运行没有明确默认代表，加严题面沿用已有经典图代表，不擅自选最佳。保留源图、裁切坐标、哈希与 Apache-2.0 许可；三张已有计数的同图不重收，三个拆分输出复用原媒体，不将录屏或转载计为新作品。动画逐帧可解码，缺失鹈鹕的原始失败画面不补画。作者怀疑的 low/medium 映射问题明确保留，模型、档位与生成日期均不独立认证。本批不镜像代码，不新增 Play。</p>'
    about+='<h3>2026-10-02 论坛续查与 X 原帖</h3><p>七个论坛原帖及回复和两个 X 作者作品经核验补 16 件作品，保留 19 份原媒体与实帧封面：5 件原始 GIF/WebP 动画、1 件完整视频和 10 件动态网页真实静态预览。模型采用作者原标注，不扩写 astra、6pro 或未经认证的路由身份；MiniMax 看图迭代和 Grok 一次修改均明确记录，不冒充一次生成。昼夜场景、修改前后、同作回复与视频帧不重复计数，已存在 GIF 不重收；另两件有来源过程证据的衍生题如实标明。Chrome 只读核验公开原帖和作者回复，未镜像无许可项目代码或新增 Play，未扩充 Benchmark。原生成日期与被删旧帖日期未知时保留未知，不把重发公开日当新生成日。</p>'
    about+='<h3>2026-10-02 Reddit 与 X 原帖补档</h3><p>从公开原帖及作者回复补 19 件独立作品，归档 34 份原媒体、忠实裁切和实帧封面（含三份原字节 PNG 规范后缀副本，旧链接保留）：包含两张 2025 年 AI Studio 旧预览、SVG 对照单图、7 份可播放动画／Blender 录屏。双模型视频按明确标签无损拆分，每帧解码哈希与原区域一致；完整对照视频与原图在详情折叠保留。四张同为 high 的免费／付费及题面对照不冒充推理档位，未指定默认条件时只计全部作品；14 张代表进入时间线。另一条 X 动画与已有 Reddit 作品只是编码不同，视觉帧核对后不重计；转载回溯原作者。型号只标 2.5 或 Astra 时不补猜完整名称。Chrome 仅只读公开内容，无代码镜像、Play 或 Benchmark 新增。</p>'
    about+='<h3>2026-10-02 历史论坛回复与动画</h3><p>七个历史 Reddit 原帖及作者评论、一个固定版本 GitHub 项目核出 13 件独立作品和 13 张时间线代表，含 6 件 2025 年输出及 3 件动画。归档 17 个原媒体、忠实裁切和实帧封面；两个同帖模型按明确标签拆图，完整对照与同作品静态预览在详情折叠。评论中的模型、题面和量化设置逐条核对，不继承楼主未证明的生成条件。旧 GPT-5 及 Gemini 3 Deep Think 转载不重计，四月重用的二月对照不改日期。另一个 X 视频正文与画面模型标签矛盾，整项暂缓，不猜归属或计入总数。Chrome 只读公开内容；无代码镜像、Play 或 Benchmark 新增，模型与生成日期未独立认证。</p>'
    about+='<h3>2026-10-02 社区动画与档位拆分</h3><p>从公开原帖和本人回复补齐 13 件独立作品、9 张时间线代表；其中 5 段原始动画录屏可在本站播放，3 件来源描述为动画但仅提供静态预览，如实区分。复用旧合集的三段原视频，按明确模型标签拆出单件，旧 ID 与原媒体保持；另归档两段新原视频。五档 Qwen 作品逐条对应同一作者，时间线仅展示 medium，其余仍计全部作品并在详情对照。X 中未经提供商或会话证实的型号仅保留为作者声称，不认证版本或宣传结论。新增 15 份媒体与实帧封面，Luna 封面避开无鹈鹕片头；动态文件前置，播放控件不算可玩。未提供真实输出或完整模型归属的评论留待核验；无代码镜像或 Benchmark 扩充。</p>'
    about+='<h3>2026-10-02 动画原件与单作品整理</h3><p>原 Opus 5.5 四格录屏按标签拆为四件真实动画，180 帧逐帧像素与源区域一致；旧合集 ID 与完整视频保留但不再重复计数。medium 的详细提示与看图细化不冒充第四种档位，时间线只用原始 medium。另补一件 X 原帖动画静态预览，明确未取得动态文件；本批净增四件独立作品、时间线净增一张。三件已有 Variora 作品复核固定版本 MIT 许可和原代码安全性后，以原字节在本站隔离域播放；暂停与倍速不算可玩，不重复增加总数。保留旧媒体、日期和封面，未扩充 Benchmark。缺少明确模型的另一段新视频暂缓；来源声称的模型与路由不独立认证。</p>'
    about+='<h3>2026-10-02 动态预览自动播放</h3><p>已有真实动态原件的卡片在进入屏幕时自动播放，时间线、全部作品的三档视图与双语详情共用规则。视频默认静音循环；离开屏幕、后台标签和未展开附件暂停。可一键暂停或恢复，尊重系统减少动画偏好。站内动画源码仍在隔离域，不修改原始字节，不自动跳到源网站；交互详情保留作者操作及游戏状态。仅存静态截图的作品不伪造动画，作品、时间线和 Benchmark 计数不变。</p>'
    about+='<h3>2026-10-02 X 原帖续查</h3><p>按 Chrome 公开原帖逐件核验，补入 Jack、STEVExKONG 两段 Sonnet 5.5 原始动画和 Nikita 一张单作品预览，共三件独立作品及三张时间线代表。两段原视频完整解码并配真实封面帧，在卡片和详情静音自动播放；只取得截图的作品不伪造动画。日期保留原帖 UTC 公开日，不冒充生成日；模型与档位均按作者标注，未独立认证。Ebi 的同作品转载按视觉对照去重，模型自述截图、引用新闻视频不增加计数。原媒体字节及旧 ID 保留，无代码镜像或 Benchmark 扩充。</p>'
    about+='<h3>2026-10-02 模型对照拆分与动画续查</h3><p>从 EvoLink 和 Haleemah 公开原帖及作者回复补六件独立作品、六张时间线代表：两段 Blender 动画和四张来源标注 SVG 的静态预览。双模型视频按一致标签拆分，每件 150 帧解码像素与原区域相同；四格原图按明确标签忠实裁切。归档十个媒体与真实封面文件，完整原视频／原图在详情折叠保留，不用拼图作主封面，不把帧或转载重计。日期为原帖 UTC 公开日，模型按来源保留且未独立认证，不转述宣传优劣为本馆结论。只取得静态预览的作品不伪造运动；代码许可未知，不镜像代码或新增 Play，Benchmark 保持。</p>'
    about+='<h3>2026-10-02 X 较早作品与公开来源核对</h3><p>核验四个 X 作者原帖及 OrcaRouter 同作者公告回复，补五件独立作品、五张时间线代表：一段完整骑行动画、两张明确标签的写实 SVG 预览裁切及两位作者各自的 Space Bunny Alpha 单图。395 帧原视频可解码且真实运动，真实第 1 秒封面和卡片／详情静音自动播放；裁切像素与原图一致，完整对照仅详情附件。保留匿名／路由模型原标签，不猜厂商；原帖 UTC 公开日不是生成日。73 图公开图库另留逐输出日期核验游标，不因数量直接导入，转载和不明模型不重计；无代码镜像、Play 或 Benchmark 扩充。</p>'
    about+='<h3>2026-10-02 三模型原动画与仓库续查</h3><p>从 Cat 的 X 原帖及本人回复核出四件独立作品：grok-4.7、grok-4.6 与 gemini-3.8-flash 的三段 high 第一次运行原动画，以及 grok-4.6 第二次运行的失败预览。三段各 300 帧无损面板裁切逐帧像素与完整原视频对应，保留真实封面与折叠原视频；第二次运行只有作者上传的静态截图，不补造动画。两次 grok-4.6 都没有可证默认／medium 代表，仅计全部作品，其余两件进入时间线。模型和 UTC 公开日按来源保留，不认证身份或生成日；Grok 实际用了文件工具的说明保留，不声称严格无工具生成。28 份仓库元数据已核，但缺原预览或统一代码许可，另两项目缺权利／模型证据，继续暂缓，不执行或镜像代码。无 Play 或 Benchmark 扩充。</p>'
    about+='<p>2026-10-02：时间线按有出处的型号首次公开时间排列，卡片保留作品日期；同型号默认展开，可选折叠。详情增加原视频真实多帧与已有多幅图横滑，不增加作品数，右侧信息及说明位置不变。</p>'
    about+='<h2>2026-10-02 展示更新</h2><p>时间线与全部作品共用型号顺序；发布日期缺少依据时用最早可证作品月份暂定位置，不再单列待核标签，作品日期与编号保持。首页展示 1988 年电影中的非 AI 鹈鹕骑车片段，补齐双语制作背景与来源，不推定它启发了 AI 提示词，也不增加作品总数。</p>'
    about+='<h3>2026-10-05 原动画恢复</h3><p>逐份复核 Variora 固定版本的 MIT 许可及 SWE-2、MiMo V2.6 Flash Free 原 HTML，恢复两件既有代码作品的原始动态展示。原字节和完整许可保留在隔离预览域；后台浏览器确认车轮、腿部与背景真实运动，与各自原截图对应。不改变作品日期、ID、封面或原媒体，不重复计数；SWE-2 点击变速只是播放控制，MiMo 原页面没有操作控件，均不新增可玩演示。其余原件仍须逐份审核，未审核下载不当作已恢复。</p>'
    about+='<h3>2026-10-05 原作者历史 SVG 预览补档</h3><p>沿 2024–2025 年原帖续查，补入卡尔的AI沃茨于 2025-10-14 公开的 Ring-1T 与 DeepSeek V3.2 两件代码生成作品及两张时间线代表。原帖明确左右型号与 SVG 题面，保存两幅独立原 JPG 预览，不使用拼图、不裁切或重画；仅有静态预览，不伪造动画，也不把线程中的其它题目纳入。日期为原帖 UTC 公开日，实际生成日、推理档和迭代过程未公开。对 1,397 份旧可解码媒体做哈希与视觉近邻核验，无重复。不声明开放许可、不镜像未获许可代码；无新增可玩演示或评分参考。</p>'
    about+='<h3>2026-10-05 Nebius 历史代码作品补档</h3><p>从 Nebius 官方 cookbook 固定原始提交补入 11 件 2025 年 8 月的 SVG 代码生成作品，时间线新增三张代表。原 PNG、型号标注图与 SVG 共 33 份原媒体，完整 MIT 许可及 Nebius B.V. 署名保留；附件不是额外作品。日期取原文件首次公开提交的 UTC 日期，实际生成日未知，不使用抓取日或型号发布日期。文件编号不冒充推理档位；四组同日重复响应未说明默认或 medium，不擅自挑选最佳图进入时间线。与 1,364 份旧可解码媒体做哈希与视觉近邻核验，无重复。保留失败输出，无新增可玩演示或评分参考。</p>'
    about+='<h3>2026-10-03 历史代码作品集中补档</h3><p>从原作者固定仓库提交、博客和 X 原帖补入 44 件旧作品：2024 年 1 件、2025 年 43 件，时间线新增 41 张代表。Robert Glaser 的 13 次看图迭代各计一件，67 张原始过程 JPG 保留但不把每轮修改多计；denamwangi 的原始截图按明确型号拆出 14 件，Harald Nezbeda 的 GPT-5 对照拆出三件，其余 14 件来自历史 X 原帖。原公开日、确切来源标签、完整原图、忠实裁切坐标和哈希保留，失败输出不重画。与 1,259 份旧可解码媒体核对；已收录动画与转载不重复收录。此批只有可证原始静态预览，不伪造动态；没有已核代码许可的项目不镜像源码，不新增 Play 或评分 Benchmark。</p>'
    about+='<h3>2026-10-03 X 代码作品档位补档</h3><p>在原作者公开文章核验 Claude Code 生成 SVG 的过程，按明确标签收录 Opus 5.5 与 Opus 5 各四档、合计八幅真实静态预览。忠实像素裁切保留坐标与原图／裁切哈希，完整八格原图只在详情作为附件；不把每档三次运行的报告当作 24 幅已公开作品。时间线分别取作者明确的默认档 medium 与 high，共两张代表，详情先展示同型号档位对照。作品日期保留原帖 2026-09-23 UTC 公开日，不改成收录日或型号发布日期；作者的用时、成本与成功率不是本站排名。未取得 SVG 源码，不镜像未核许可代码，不新增 Play 或 Benchmark。</p>'
    about+='<h3>2026-10-03 Gist 原预览补档</h3><p>核验原作者 Gist 固定版本及本人评论，新增三件五月／六月真实输出：DiffusionGemma 一件，grok 4.3 的 bike／bicycle 题面各一件。保留作者已发布的原始 PNG、署名、UTC 公开日与哈希，不以本次收录日改写作品日期。两个 Grok 输出是追加题面对照，不冒充推理档位或新会话；没有明确默认／medium 时仅计全部作品，DiffusionGemma 进入时间线。两份原 SVG 有重复属性无法解码，不修复、补画或镜像未核许可代码；此批只展示来源真实预览，无新增动画、Play 或 Benchmark。公开仓库缺逐型号对应或原预览的候选继续暂缓，不按数量充数。</p>'
    about+='<h3>2026-10-03 代码生成收录范围更新</h3><p>标本馆主要收藏大模型生成代码的作品。SVG、网页动画、三维场景与交互项目，以及这些代码作品的真实录屏仍可收；不按视频文件后缀排除作品。四条明确的直接文生视频旧记录转为不计数资料，原 ID、来源、日期、详情与媒体保留，按 ID 可查，不进入主馆、时间线、编号或默认搜索。尚未发布的四个 Veo 2 拆分输出撤回，研究证据保留，不作为新增。后续导入须记录代码生成方式与公开来源证据；过程不明暂缓，不猜模型能力或日期。首页原文、动态展示、Play 与 Benchmark 参考边界保持。</p>'
    page('/about/','关于与收录方法','Pelican Map 的定位、馆藏范围、统计口径、来源处理与维护记录。',top('把作品留下，把出处讲清楚','ABOUT PELICAN MAP')+'<article class="prose">'+about+'</article>',markdown='/about/index.md')
    from bs4 import BeautifulSoup
    dump(OUT/'about/index.md','# Pelican Map / 鹈鹕骑车标本馆\n\n'+BeautifulSoup(about,'html.parser').get_text('\n',strip=True)+'\n')
    rights='''<h2>作品与来源</h2><p>馆藏媒体、代码和原文链接均指向各自来源，作品权利归其原作者。本站收录、生成预览或提供下载不会改变原作品的许可，也不代表原作者认可本站。</p><h2>使用与下载</h2><p>引用时请保留原作者与原始链接。使用代码或媒体前，请查看原仓库的 LICENSE 和作者说明。未核实许可的记录不标为开放许可；来源 URL 未核实的源码包暂不提供公开下载。</p><h2>已知来源状态</h2><ul><li>Zeos 投稿站的域名未能从原帖确认，保留可获取的附件。</li><li>受限文章保留公开索引和原始链接。</li><li>一条 YouTube 直播使用在线入口。</li></ul><h2>更正与移除</h2><p>如果你是作品作者，或发现来源、日期、署名有误，请通过本站发布者分享本馆的原始渠道联系，并附本站作品地址、原始来源及需要更正或移除的内容。</p><h2>访问与隐私</h2><p>本站目前不提供注册、评论或广告追踪。页面由 Hetzner 托管并通过 Cloudflare 分发，服务运行可能产生必要的访问与错误日志。点击外部来源后，适用对应网站的政策。</p>'''
    page('/rights/','来源与使用说明','作品署名、许可状态、下载使用、来源限制与更正说明。',top('来源与使用说明','CREDITS & USE')+'<article class="prose">'+rights+'</article>')

def build_sources(items):
    from source_layout import render
    page('/sources/','资料与来源','原始仓库、演示与 Simon Willison 的鹈鹕骑车实验来历。',render(DATA,[x for x in items if not x.get('referenceOnly')]),nav='/sources/')


def build_machine_data(items):
    catalog={'version':CATALOG_VERSION,'updated':UPDATED,'site':BASE,'counts':dict(COUNTS),'countingNote':'counts.cases 是独立作品数（各档位分别计）；counts.timeline 是进化轴代表图数，与作品数不相加。caseVisible=false 的合集/转载/待核对资料和 referenceOnly 评分不进入主列表、总数、编号或默认 API。timelineVisible 控制时间线；kind 是历史来源分类。完整 items 保留旧档案及原图，不能按 items.length 计算案例数。','collectingPolicy':'/data/collecting-policy.json','benchmarkUrl':'/tags/benchmark/','benchmarkDataUrl':'/data/benchmark.json','items':items}
    jdump(OUT/'data/collecting-policy.json',json.loads((ROOT/'site/collecting-policy.json').read_text(encoding='utf8')))
    catalog['timelineSortBasis']='model-release'
    catalog['worksSortBasis']='model-release'
    catalog['modelReleaseRegistry']='/data/model-releases.json'
    jdump(OUT/'data/model-releases.json',json.loads((ROOT/'site/model-releases.json').read_text(encoding='utf8')))
    jdump(OUT/'data/catalog.json',catalog)
    jdump(ROOT/'site/catalog.json',catalog)
    dump(OUT/'data/catalog.csv',csv_text(items))
    intro=agent_guide(COUNTS,UPDATED)
    dump(OUT/'llms.txt',intro)
    dump(OUT/'developers/index.md',intro)
    body=top('让资料也能被程序读懂','公开、只读、带出处。与网页使用同一份目录数据。','DATA & AGENTS')
    body+=f'''<article class="prose"><h2>下载与引用</h2><p>{link('/data/catalog.json','完整 JSON')} · {link('/data/catalog.csv','CSV 目录')} · {link('/llms.txt','Agent 导读')} · {link('/openapi.json','OpenAPI 说明')}</p><p>目录版本 {CATALOG_VERSION}，更新于 {UPDATED}。网页、导出和公开 API 使用同一份审核目录。</p>{sections_html(scope_sections(COUNTS))}<h2>只读 HTTP API</h2><pre>GET /api/v1/specimens?q=Gemini&amp;format=svg&amp;limit=10
GET /api/v1/specimens/{{id}}?lang=en
GET /api/v1/timeline?family=Gemini&amp;sort=oldest&amp;limit=20</pre>{sections_html(agent_sections())}<h2>连接 MCP</h2><p>在支持远程 MCP 的客户端中添加 Streamable HTTP 地址：</p><pre>{BASE}/mcp</pre><p>search_specimens、get_specimen、get_timeline 三个只读工具支持 lang: zh/en，过滤和分页与 HTTP 一致，无需登录。</p></article>'''
    from ingestion_docs import section
    body+=section()
    page('/developers/','数据与 Agent 接入','JSON、CSV、Markdown、只读 HTTP API 与 MCP 接口，检索鹈鹕骑车馆藏并保留出处。',body,markdown='/developers/index.md')
    jdump(OUT/'openapi.json',openapi())

if __name__=='__main__':
    build()
    from build_english import build as build_english
    build_english()
