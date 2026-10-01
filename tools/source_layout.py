"""Compact, bilingual provenance page shared by local and automated builds."""
import html
from pathlib import Path
from urllib.parse import quote

def render(data,items,language='zh'):
    en=language=='en'; E=lambda s:html.escape(str(s or ''),quote=True)
    T=lambda zh,eng:eng if en else zh
    def link(url,label):
        if not url:return ''
        return f'<a href="{E(url)}"'+(' target="_blank" rel="noopener noreferrer"' if url.startswith('https://') else '')+f'>{E(label)}</a>'
    desc={
      'repo-simonw-pelican-bicycle':'The original repository and early SVG outputs.',
      'repo-licoy-tihuqiche':'An island cycling game built with Vue 3 and Three.js.',
      'repo-scosman':'A curated gallery of model-generated SVGs.',
      'repo-auto-pelican':'An agent that generates and evaluates SVG animations.',
      'repo-blender-astra':'A cycling pelican built in local Blender with Astra.',
      'repo-pedalican':'A cycling pelican desktop pet for Codex.',
      'repo-jojohanse':'SVG outputs compared across multiple models.',
      'repo-youngbrioche':'Iterative pelican drawing with an agent.',
      'repo-xiiiblue':'HTML animations compared across models.',
      'repo-taikongren':'A seaside cycling scene in animated SVG.',
      'repo-xinhan':'A collection exploring bicycles and pelicans.',
      'repo-superxian':'Cycling expressed in pure SVG animation.',
      'repo-heysong':'An SVG-based pelican web app.',
      'repo-sebseb7':'A collection of model-generated SVG experiments.',
      'site-riba':'A playable coastal 3D scene with waves and cycling.',
      'site-tihu':'The online edition of the open-source cycling game.',
      'site-demobench':'A 4 KB demo with GIF, assembly source and a WASM runtime.',
      'repo-chnaicorp':'A single-file SVG and HTML animation.',
      'repo-vastxie':'Original HTML animations and model runs; 164 extracted files.',
      'repo-vulcan575':'A dependency-free teal city bicycle animation.',
      'site-rustfisher':'Astra, Gemini 3.8 Flash and DeepSeek 4.1 Flash compared.',
      'site-ohmyopus':'An archived preview with Python / pybevy source.',
      'repo-staypzy':'Attributed to DeepSeek V4.1 Flash; upstream repository unverified.'}
    titles={'site-rustfisher':'RustFisher · 3-model comparison','site-ohmyopus':'ohmyopus · 3D city','repo-staypzy':'prab · upstream unverified'}
    body='<div class="page-top"><div class="eyebrow">PROVENANCE</div><h1>'+T('资料与来源','Sources & repositories')+'</h1><p>'+T('沿着作品，找到代码、作者与最初的问题。','Follow each work back to its code, creator and original question.')+'</p></div>'
    body+='<p class="source-license">'+T('这里是原始出处与仓库的阅读索引，不计作品数。全部作品与时间线接受全时间段、所有媒体类型的真实输出；动画、视频、三维、游戏与 Agent 项目保留实际生成条件、迭代和人工参与。模型按来源标注，未独立认证。','A reading index of sources and repositories, not an artwork count. The collection and timeline accept all dates and media. Animation, video, 3D, games and agent projects retain their generation conditions, iterations and human involvement. Model labels are source-reported, not independently authenticated.')+'</p>'
    body+='<div class="source-heading"><h2>'+T('仓库与演示','Repositories & demos')+'</h2><span class="small">'+str(len(data['repos']))+T(' 个入口',' entry points')+'</span></div><p class="source-license">'+T('作品沿用原作者许可；使用前请查看仓库 LICENSE。来源未核实的包不公开下载。','Original licenses apply; check each repository’s LICENSE. Unverified source packages are not available for download.')+'</p><div class="repo-collage">'
    for n,r in enumerate(data['repos']):
        demo='https://pelicanmap-demos.aveniqa.com/'+quote(r['demo'],safe='/') if r.get('demo') else ''
        match=next((x for x in items if x.get('thumbnail') and ((demo and x.get('demoUrl')==demo) or (r.get('url') and x['sourceUrl'].rstrip('/')==r['url'].rstrip('/')))),None)
        visual=f'<img class="repo-thumb" src="{E(match["thumbnail"])}" alt="" width="80" height="80" loading="lazy">' if match else ''
        buttons=link(r.get('url'),T('来源 ↗','Source ↗'))
        if match and match.get('interactive'):buttons+=link(match['path'],T('站内交互 →','Interact on site →'))
        elif demo:buttons+=link(demo,T('历史预览 ↗','Historical preview ↗'))
        if r.get('zip') and r['zip']!='repos/staypzy.zip':buttons+=link('/downloads/'+Path(r['zip']).name,'ZIP ↓')
        if r.get('sourceCode'):buttons+=link('https://pelicanmap-demos.aveniqa.com/'+quote(r['sourceCode'],safe='/'),T('代码 ↗','Code ↗'))
        body+=f'<article class="repo-tile"><div class="repo-topline"><span>{n+1:02d}</span><span>{E(r.get("form","archive"))}</span></div>{visual}<h2>{E(titles.get(r["id"],r["title"]) if en else r["title"])}</h2><p>{E(desc.get(r["id"],r.get("notes","")) if en else r.get("notes",""))}</p><div class="repo-links">{buttons}</div></article>'
    body+='</div><section class="simon-section" aria-labelledby="simon-title"><div class="simon-intro"><div><div class="eyebrow">THE PERSON BEHIND THE PROMPT</div><h2 id="simon-title">Simon<br>Willison<span>↗</span></h2><p>'+T('Django 联合创始人 · Datasette 创作者','Django co-creator · Creator of Datasette')+'</p>'+link('https://simonwillison.net/about/',T('他的个人介绍 ↗','About Simon ↗'))+'</div><div><h3>'+T('为什么鹈鹕骑车总会提到他？','Why does this pelican lead back to Simon?')+'</h3><p>'+T('2024 年 10 月 25 日，Simon 公开了同一个提示词在 16 个模型中的 SVG 输出。他选鹈鹕，一是因为喜欢这种鸟，二是当时认为网上几乎没有“鹈鹕骑车”的 SVG，较不容易直接复用已有样本。','On October 25, 2024, Simon published SVG outputs from 16 models using the same prompt. He chose pelicans because he liked them and believed bicycle-riding pelican SVGs were then rare in training data.')+'</p><blockquote>Generate an SVG of a pelican riding a bicycle</blockquote><p>'+T('社区将这个题目延伸到动画、视频、三维与游戏，原始出处仍保留在索引中。本馆通过全媒体独立作品与来源模型标签观察时间变化；不同条件的单个样本不等于整体模型能力。','The community extended the prompt into animation, video, 3D and games; original sources remain indexed. The timeline follows individual works across media and source-reported model labels. Different generation conditions and single samples do not establish overall capability.')+'</p>'+link('https://simonwillison.net/2024/Oct/25/pelicans-on-a-bicycle/',T('阅读最初的实验 ↗','Read the original experiment ↗'))+'</div></div>'
    years=sorted({x.get('date','')[:4] for x in data['simon'] if x.get('date')},reverse=True)
    body+='<div class="source-index"><div class="source-heading"><h3>'+T('Simon 的相关文章','Simon’s related writing')+'</h3><span class="small" data-source-count>'+str(len(data['simon']))+T(' 条索引',' entries')+'</span></div><div class="source-controls"><label>'+T('检索文章','Search articles')+'<input type="search" data-source-search placeholder="'+T('标题或关键词','Title or keyword')+'"></label><label>'+T('年份','Year')+'<select data-source-year><option value="">'+T('全部年份','All years')+'</option>'+''.join(f'<option>{E(y)}</option>' for y in years)+'</select></label></div><div class="source-window" tabindex="0" role="region" aria-label="'+T('相关文章，可上下滚动','Related articles, scroll to browse')+'"><ul class="source-list">'
    for s in sorted(data['simon'],key=lambda x:x.get('date',''),reverse=True):
        body+=f'<li data-source-entry data-year="{E(s.get("date","")[:4])}"><time>{E(s.get("date",""))}</time>{link(s["url"],s.get("title") or s["url"])}</li>'
    body+='</ul><p class="small source-empty" data-source-empty hidden>'+T('没有匹配的文章。','No matching articles.')+'</p></div><p class="small source-scroll-hint">'+T('在列表内上下滚动浏览；这些是延伸阅读索引，不计入作品数量。','Scroll within the list to browse. These reading references are not counted as artworks.')+'</p></div></section>'
    return body
