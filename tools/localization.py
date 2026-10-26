"""Additional interface editions; archival text and original media stay intact."""
import copy
import hashlib
import html
import json
import re
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET
from bs4 import BeautifulSoup, NavigableString

ROOT=Path(__file__).resolve().parents[1]
BASE='https://pelicanmap.aveniqa.com'
LOCALES=json.loads((ROOT/'site/i18n/locales.json').read_text(encoding='utf8'))

def artwork_year_range(items):
    from case_policy import is_case
    years=sorted({x.get('date','')[:4] for x in items if is_case(x) and re.match(r'^\d{4}',x.get('date',''))})
    return years[0]+('—'+years[-1] if years[-1]!=years[0] else '') if years else ''

def write_runtime():
    """The browser dictionary is generated from the same reviewed locale registry."""
    data=json.dumps(LOCALES,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
    runtime=r'''
(() => {
  const locales=__DATA__;
  const lang=document.documentElement.lang;
  const locale=locales[lang];
  const ru=lang==='ru';
  function text(value){
    if(!locale?.strings)return value;
    const key=value.trim(),mapped=locale.strings[key];
    if(mapped)return value.replace(key,mapped);
    let m;
    if((m=/^View all (\d+) works of this version$/.exec(key)))return ru?`Показать все работы этой версии (${m[1]})`:`Ver todas as ${m[1]} obras desta versão`;
    if((m=/^(\d+) works of this version$/.exec(key)))return ru?`Работы этой версии: ${m[1]}`:`${m[1]} obras desta versão`;
    if((m=/^(\d+) cases · (\d+) model versions · Page (\d+) \/ (\d+)$/.exec(key)))return ru?`${m[1]} работ · ${m[2]} версий моделей · Страница ${m[3]} / ${m[4]}`:`${m[1]} obras · ${m[2]} versões de modelos · Página ${m[3]} / ${m[4]}`;
    if((m=/^(\d+) (?:cases|matching samples) · Page (\d+) \/ (\d+)$/.exec(key)))return ru?`${m[1]} работ · Страница ${m[2]} / ${m[3]}`:`${m[1]} obras · Página ${m[2]} / ${m[3]}`;
    if((m=/^Page (\d+) \/ (\d+)$/.exec(key)))return ru?`Страница ${m[1]} / ${m[2]}`:`Página ${m[1]} / ${m[2]}`;
    if((m=/^Show (\d+) more works (of this version|from this group)$/.exec(key)))return ru?`Ещё ${m[1]} работ ${m[2].startsWith('of')?'этой версии':'этой группы'}`:`Mostrar mais ${m[1]} obras ${m[2].startsWith('of')?'desta versão':'deste grupo'}`;
    if((m=/^Current: (.*); switch to (.*) · (\d+) per page$/.exec(key)))return ru?`Сейчас: ${text(m[1])}; переключить: ${text(m[2])} · ${m[3]} на странице`:`Atual: ${text(m[1])}; mudar para ${text(m[2])} · ${m[3]} por página`;
    if((m=/^(↑ |↓ |← )(.*)$/.exec(key)))return m[1]+text(m[2]);
    if((m=/^(.*) →$/.exec(key)))return text(m[1])+' →';
    return value;
  }
  globalThis.PelicanI18n={lang,text,locales};
  if(!locale?.strings)return;
  const translate=root=>{
    const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
    const nodes=[];while(walker.nextNode())nodes.push(walker.currentNode);
    for(const node of nodes){
      if(node.parentElement?.closest('script,style,code,pre,[data-preserve-source],.note'))continue;
      const next=text(node.nodeValue);if(next!==node.nodeValue)node.nodeValue=next;
    }
    for(const element of root.querySelectorAll?.('[title],[aria-label],[placeholder]')||[]){
      for(const attr of ['title','aria-label','placeholder'])if(element.hasAttribute(attr)){const old=element.getAttribute(attr),next=text(old);if(old!==next)element.setAttribute(attr,next);}
    }
    for(const a of root.querySelectorAll?.('a[href^="/en/"]')||[])if(!a.hasAttribute('data-language'))a.setAttribute('href',locale.prefix+a.getAttribute('href').slice(3));
  };
  addEventListener('DOMContentLoaded',()=>{
    translate(document.body);
    let scheduled=false;
    new MutationObserver(()=>{if(!scheduled){scheduled=true;queueMicrotask(()=>{scheduled=false;translate(document.querySelector('main'));});}}).observe(document.querySelector('main'),{childList:true,subtree:true,characterData:true});
  },{once:true});
})();
'''.replace('__DATA__',data)
    target=ROOT/'site/assets/locale-data.js'
    if not target.exists() or target.read_text(encoding='utf8')!=runtime:target.write_text(runtime,encoding='utf8',newline='\n')

def translate(text,lang):
    strings=LOCALES[lang].get('strings',{})
    core=text.strip()
    if core in strings:return text.replace(core,strings[core])
    ru=lang=='ru'
    if core.startswith('LAST UPDATED / '):return text.replace('LAST UPDATED / ','ОБНОВЛЕНО / ' if ru else 'ATUALIZADO EM / ')
    patterns=[(r'^(\d+) cases · Page (\d+) / (\d+)$',lambda m:f'{m[1]} работ · Страница {m[2]} / {m[3]}' if ru else f'{m[1]} obras · Página {m[2]} / {m[3]}'),
      (r'^Page (\d+) / (\d+)$',lambda m:f'Страница {m[1]} / {m[2]}' if ru else f'Página {m[1]} / {m[2]}'),
      (r'^(.*) · Page (\d+)$',lambda m:translate(m[1],lang)+(f' · Страница {m[2]}' if ru else f' · Página {m[2]}'))]
    for pattern,render in patterns:
        match=re.fullmatch(pattern,core)
        if match:return text.replace(core,render(match))
    for prefix in ('↓ ','↑ '):
        if core.startswith(prefix):return text.replace(core,prefix+translate(core[len(prefix):],lang))
    return text

def locale_path(path,lang):
    return LOCALES[lang]['prefix']+path

def rewrite_url(value,lang):
    if value.startswith(BASE+'/en/'):
        return BASE+locale_path(value[len(BASE+'/en'):],lang)
    if value.startswith('/en/'):return locale_path(value[3:],lang)
    return value

def localized_catalog(english,lang):
    value=copy.deepcopy(english)
    value.update(language=lang,recordTextLanguage='en',translationScope='interface; archival descriptions retain their existing English translation or source language',translationNotice=LOCALES[lang]['notice'])
    value['benchmarkUrl']=locale_path('/tags/benchmark/',lang)
    for item in value['items']:
        for key in ('path','url','markdown'):
            if item.get(key):item[key]=rewrite_url(item[key],lang)
        for key in ('sourceLabel','formatLabel'):
            item[key]=translate(item.get(key,''),lang)
        if item.get('batch'):
            item['batch']['path']=rewrite_url(item['batch']['path'],lang)
    return value

def statistics(catalog):
    from case_policy import is_case
    works=[x for x in catalog['items'] if is_case(x)]
    years=Counter(x.get('date','')[:4] or 'unknown' for x in works)
    sources=Counter(x['source'] for x in works)
    counts=catalog['counts']
    assert len(works)==counts['cases']
    return {'version':catalog['version'],'collectionVersion':catalog.get('collectionVersion'), 'updated':catalog['updated'],
        'counts':counts,'works':counts['cases'],'timeline':counts['timeline'],
        'derivatives':sum('derivative' in x.get('topicTags',[]) for x in works),
        'years':[{'key':k,'total':v} for k,v in sorted(years.items())],
        'sources':[{'key':k,'total':v} for k,v in sorted(sources.items())]}

def language_links(path,lang):
    primary='en' if lang!='en' else 'zh'
    def anchor(key):
        item=LOCALES[key]
        return f'<a data-language href="{locale_path(path,key)}" hreflang="{item["tag"]}" lang="{item["tag"]}">{html.escape(item["name"])}</a>'
    label={'zh':'语言','en':'Languages','ru':'Языки','pt-BR':'Idiomas'}[lang]
    return anchor(primary)+f'<details class="language-menu"><summary aria-label="{label}" title="{label}">🌐</summary><div>'+''.join(anchor(key) for key in LOCALES if key!=lang)+'</div></details>'

def alternates(path):
    return ''.join(f'<link rel="alternate" hreflang="{item["tag"]}" href="{BASE+locale_path(path,key)}">' for key,item in LOCALES.items())+f'<link rel="alternate" hreflang="x-default" href="{BASE+path}">'

def shared_head(text,path,lang,version):
    text=re.sub(r'<link\b[^>]*\bhreflang=[^>]+>','',text)
    text=text.replace('</head>',alternates(path)+'</head>')
    text=re.sub(r'<details class="language-menu">.*?</details>','',text,flags=re.S)
    text=re.sub(r'<a\b[^>]*\bdata-language(?:="[^"]*")?[^>]*>.*?</a>','',text,flags=re.S)
    menu=language_links(path,lang)
    primary,dropdown=menu.split('<details',1)
    text=text.replace('</nav>',primary+'</nav><details'+dropdown,1)
    if '/assets/locale-data.js?' not in text:
        # HTML serialization can reorder src/defer attributes in added editions.
        text=re.sub(r'(<script\b(?=[^>]*\bsrc="/assets/site\.js)[^>]*>)',lambda m:f'<script src="/assets/locale-data.js?v={version}" defer></script>'+m[0],text,count=1)
    else:
        text=re.sub(r'/assets/locale-data\.js\?v=[a-f0-9]{12}',f'/assets/locale-data.js?v={version}',text)
    return text

def localized_html(text,path,lang,version,counts=None):
    soup=BeautifulSoup(text,'html.parser')
    soup.html['lang']=LOCALES[lang]['tag']
    editorial=LOCALES[lang].get('editorial',{}).get(path.strip('/'))
    if editorial:
        content='<div class="page-top"><h1>'+html.escape(editorial['title'])+'</h1></div><article class="prose">'+''.join('<p>'+html.escape(p)+'</p>' for p in editorial['paragraphs'])+'</article>'
        counts=counts or {}
        if path=='/about/':
            labels={'ru':['Все работы','Обычная хронология','Производные работы'],'pt-BR':['Todas as obras','Linha do tempo regular','Obras derivadas']}[lang]
            content+='<div class="stats-strip">'+''.join(f'<div><strong data-stat="{key}">{counts[key]}</strong><span>{label}</span></div>' for key,label in zip(('cases','timeline','derivatives'),labels))+'</div>'
        content+='<p>'+''.join(f'<a href="/{lang}/{target}">{label}</a> · ' for target,label in [('specimens/',LOCALES[lang]['strings']['All works']),('derivatives/',LOCALES[lang]['strings']['Derivative works']),('data/catalog.json','JSON'),('data/catalog.csv','CSV'),('llms.txt','Agent'),('developers/', 'HTTP / MCP')])+'<a href="https://github.com/UncleK/pelicanmap/issues">GitHub Issues ↗</a></p>'
        if path=='/developers/':content+='<pre>GET /api/v1/stats\nGET /api/v1/specimens?lang='+lang+'&amp;limit=10\nGET /api/v1/timeline?lang='+lang+'\nMCP https://pelicanmap.aveniqa.com/mcp</pre>'
        soup.select_one('main').clear()
        soup.select_one('main').append(BeautifulSoup(content,'html.parser'))
        soup.title.string=editorial['title']+' · Pelican Bicycle Archive'
        for tag in soup.select('meta[name=description],meta[property="og:description"],meta[name="twitter:description"]'):tag['content']=editorial['paragraphs'][0][:200]
        for tag in soup.select('meta[property="og:title"],meta[name="twitter:title"]'):tag['content']=editorial['title']
    for tag in soup.select('link[hreflang], a[data-language], .language-menu'):tag.decompose()
    for tag in soup.find_all(True):
        for key in ('href','data-base'):
            if tag.get(key):tag[key]=rewrite_url(tag[key],lang)
        for key in ('title','aria-label','placeholder','alt'):
            if tag.get(key):tag[key]=translate(tag[key],lang)
        if tag.name=='meta' and tag.get('content'):
            if tag.get('property')=='og:locale':tag['content']='ru_RU' if lang=='ru' else 'pt_BR'
            elif tag.get('property')=='og:url':tag['content']=BASE+locale_path(path,lang)
            else:tag['content']=translate(tag['content'],lang)
        if tag.name=='script' and tag.get('type')=='application/ld+json':
            data=json.loads(tag.string)
            if editorial:data.update(name=editorial['title'],description=editorial['paragraphs'][0])
            def localized(value):
                if isinstance(value,dict):return {k:LOCALES[lang]['tag'] if k=='inLanguage' and isinstance(v,str) else localized(v) for k,v in value.items()}
                if isinstance(value,list):return [localized(v) for v in value]
                if isinstance(value,str):return translate(rewrite_url(value,lang),lang)
                return value
            tag.string=json.dumps(localized(data),ensure_ascii=False).replace('<','\\u003c')
    for node in list(soup.find_all(string=True)):
        if node.parent.name in ('script','style','code','pre') or not str(node).strip():continue
        # Source descriptions, prompts, proper model names and historical quotations are archival text.
        if node.find_parent(attrs={'data-preserve-source':True}):continue
        value=translate(str(node),lang)
        if value!=str(node):node.replace_with(value)
    soup.title.string=translate(soup.title.get_text().split(' · Pelican Bicycle Archive')[0],lang)+' · '+LOCALES[lang]['strings']['Pelican Bicycle Archive']
    notice=soup.new_tag('p',attrs={'class':'locale-notice','data-translation-scope':'interface'})
    notice.string=LOCALES[lang]['notice']
    soup.select_one('main').insert(0,notice)
    # Mark untranslated source prose for assistive reading; never invent a translated prompt.
    for tag in soup.select('.card-body .note, blockquote, pre, .prompt-text'):
        tag['lang']='en'
    return shared_head(str(soup),path,lang,version)

def build(output,cache=None):
    from editorial_content import csv_text
    from incremental_site import write_text
    from asset_versions import asset_version
    output=Path(output);version=asset_version(ROOT/'site/assets',output/'assets')
    english=json.loads((output/'en/data/catalog.json').read_text(encoding='utf8'))
    write=lambda p,s:write_text(output/p,s)
    stats=statistics(english)
    write('data/stats.json',json.dumps(stats,ensure_ascii=False,separators=(',',':')))
    code=hashlib.sha256(Path(__file__).read_bytes()+(ROOT/'site/i18n/locales.json').read_bytes()).hexdigest()
    sources=sorted((output/'en').rglob('*.html'))
    for source in sources:
        relative=source.relative_to(output/'en').as_posix()
        path='/'+relative.removesuffix('index.html')
        text=source.read_text(encoding='utf8')
        for lang in ('zh','en'):
            target=output/(LOCALES[lang]['prefix'].strip('/')+'/'+relative).lstrip('/')
            if target.is_file():write_text(target,shared_head(target.read_text(encoding='utf8'),path,lang,version))
        for lang in ('ru','pt-BR'):
            dest=output/lang/relative;md=dest.with_suffix('.md')
            dependency=[code,hashlib.sha256(text.encode()).hexdigest()]
            if cache and cache.page(locale_path(path,lang),dependency,[dest,md])[0]:continue
            result=localized_html(text,path,lang,version,{**english['counts'],'derivatives':stats['derivatives']})
            write_text(dest,result)
            body=BeautifulSoup(result,'html.parser').select_one('main')
            write_text(md, '# '+LOCALES[lang]['strings']['Pelican Bicycle Archive']+'\n\n'+body.get_text('\n',strip=True)+'\n\n'+BASE+locale_path(path,lang)+'\n')
    for lang in ('ru','pt-BR'):
        value=localized_catalog(english,lang)
        write(f'{lang}/data/catalog.json',json.dumps(value,ensure_ascii=False,separators=(',',':')))
        write(f'{lang}/data/catalog.csv',csv_text(value['items']))
        guide=LOCALES[lang]['notice']+'\n\n'+f"{stats['works']} / {stats['timeline']} / {stats['derivatives']} (all / classic timeline / derivatives; subsets, do not add).\n"
        guide+='\n'.join(f'{name}: {BASE}/{lang}/{target}' for name,target in [('JSON','data/catalog.json'),('CSV','data/catalog.csv'),('Guide','developers/')])
        guide+=f'\nHTTP / MCP: lang={lang}; stable IDs, dates and original media.\n'+english['countingNote']
        write(f'{lang}/llms.txt',guide)
        feed=(output/'en/feed.xml').read_text(encoding='utf8').replace(BASE+'/en/',BASE+f'/{lang}/')
        write(f'{lang}/feed.xml',feed)
    # All editions have reciprocal alternates. Existing dates and canonical URLs remain stable.
    ns={'s':'http://www.sitemaps.org/schemas/sitemap/0.9','x':'http://www.w3.org/1999/xhtml'}
    tree=ET.fromstring((output/'sitemap.xml').read_text(encoding='utf8'))
    rows=[]
    for row in tree:
        loc=row.find('s:loc',ns).text
        if loc.startswith(BASE+'/en/'):continue
        path=loc.removeprefix(BASE)
        date=row.find('s:lastmod',ns)
        for lang in LOCALES:
            links=''.join(f'<xhtml:link rel="alternate" hreflang="{item["tag"]}" href="{BASE+locale_path(path,key)}"/>' for key,item in LOCALES.items())+f'<xhtml:link rel="alternate" hreflang="x-default" href="{BASE+path}"/>'
            rows.append(f'<url><loc>{BASE+locale_path(path,lang)}</loc><lastmod>{date.text if date is not None else english["updated"]}</lastmod>{links}</url>')
    write('sitemap.xml','<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="'+ns['s']+'" xmlns:xhtml="'+ns['x']+'">'+''.join(rows)+'</urlset>')
    print(json.dumps({'additionalLocales':['ru','pt-BR'],'sourcePages':len(sources),'stats':{k:stats[k] for k in ('works','timeline','derivatives')}}))
