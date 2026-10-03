"""Bilingual paged listings with shared browsing controls."""
import html
import math
import hashlib
import json
from experiment_batches import group_records, batch_card
from model_chronology import ordered_timeline, timeline_year, timeline_month


def legacy_years(output, prefix=''):
    """Refresh removed year routes too: old non-AI context must not survive as cards."""
    folder=output/prefix/'timeline'
    return {x.name for x in folder.iterdir() if x.is_dir() and len(x.name)==4 and x.name.isdigit()} if folder.is_dir() else set()


def legacy_page_count(output, base, minimum):
    """Keep old paginated URLs as refreshed noindex aliases, never stale cards."""
    folder = output/base.lstrip('/')/'page'
    old = [int(x.name) for x in folder.iterdir() if x.is_dir() and x.name.isdigit()] if folder.exists() else []
    return max([minimum, *old])


def listing(items, base, scope, card, language='zh', number=1, year='', years=None, archive_link=False):
    en = language == 'en'
    t = lambda zh, eng: eng if en else zh
    e = lambda s: html.escape(str(s), quote=True)
    from case_policy import is_case
    items = [x for x in items if (not x.get('referenceOnly') if scope=='play' else is_case(x))]
    # Pin hydrated browsing to this rendered collection, not an old CDN entry.
    catalog_version = hashlib.sha256(json.dumps(items, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf8')).hexdigest()[:20]
    filtered = [x for x in items if not year or (timeline_year(x)==year if scope=='timeline' else x['date'].startswith(year))]
    selected = sorted(filtered, key=lambda x: (x['date'], x['id']), reverse=True) if scope=='play' else ordered_timeline(filtered)
    selected = group_records(selected,include_references=scope=='play')
    pages = max(1, math.ceil(len(selected)/24))
    number = max(1, min(number, pages))
    part = selected[(number-1)*24:number*24]
    years = [y for y in (years or sorted({timeline_year(x) if scope=='timeline' else x['date'][:4] for x in items if x['date']}, reverse=True)) if y!='unknown']
    year_name=lambda y:y
    years_html = ''.join(f'<option value="{e(y)}"'+(' selected' if y == year else '')+f'>{e(year_name(y))}</option>' for y in years)
    source_options = [('origin', t('原点仓库','Original experiment')), ('zoo','Pelican Zoo'), ('wtf','pelicans.wtf'), ('community',t('社区记录','Community record'))]
    format_options = [('svg',t('静态 SVG','Static SVG')),('image',t('图像','Image')),('animation',t('动画','Animation')),('3d',t('三维作品','3D work')),('game',t('游戏 / 交互','Game / interactive')),('video',t('视频','Video')),('audio',t('音频','Audio')),('other',t('其他媒体','Other media'))]
    options = lambda opts: ''.join(f'<option value="{k}">{v}</option>' for k,v in opts)
    browse_base = ('/en' if en else '')+'/timeline/' if scope=='timeline' else base
    year_href = lambda y: browse_base+(y+'/' if y else '') if scope=='timeline' else browse_base+('?year='+y if y else '')
    year_links = '<nav class="year-links" aria-label="'+(t('模型发布年份筛选','Model release year filters') if scope=='timeline' else t('年份快速筛选','Quick year filters'))+'">'+''.join('<a href="'+e(year_href(y))+'" data-year="'+e(y)+'"'+(' aria-current="true"' if y==year else '')+'>'+e(year_name(y) if y else t('全部年份','All years'))+'</a>' for y in ['',*years])+'</nav>'
    controls = f'''<div data-browser data-catalog-version="{catalog_version}" data-scope="{scope}" data-base="{e(browse_base)}" data-initial-page="{number}" data-initial-year="{e(year)}">
<form class="filters browse-search-panel" id="browse-search-panel" data-search role="search" hidden><label>{t('检索馆藏','Search the archive')}<input type="search" name="q" maxlength="200" placeholder="{t('模型、作者、备注…','Model, creator, notes…')}"></label><label>{t('年份','Year')}<select name="year"><option value="">{t('全部年份','All years')}</option>{years_html}</select></label><label>{t('来源','Source')}<select name="source"><option value="">{t('全部来源','All sources')}</option>{options(source_options)}</select></label><label>{t('形式','Format')}<select name="format"><option value="">{t('全部形式','All formats')}</option>{options(format_options)}</select></label><input type="hidden" name="sort" value="newest"><button class="button" type="submit">{t('检索','Search')}</button><button class="button secondary" type="reset">{t('重置','Reset')}</button></form>
<div class="browse-family-row"><div class="browse-buttons"><button type="button" class="browse-button browse-search-toggle" data-search-toggle aria-expanded="false" aria-controls="browse-search-panel"><svg width="16" height="16" viewBox="0 0 20 20" fill="none" aria-hidden="true"><circle cx="8.5" cy="8.5" r="5.5" stroke="currentColor" stroke-width="1.6"/><path d="m13 13 4 4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg><span>{t('搜索','Search')}</span><span class="search-active" data-search-active hidden aria-label="{t('已应用检索条件','Search filters applied')}"></span></button><button type="button" class="browse-button" data-sort-toggle aria-label="{t('切换时间排序','Change chronological order')}">↓ {t('最新在前','Newest first')}</button><button type="button" class="browse-button" data-density-toggle aria-pressed="false" title="{t('当前：标准视图；点击切换：紧凑视图 · 每页 48 张','Current: Standard view; switch to Compact view · 48 per page')}"><svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true"><path fill="currentColor" d="M1 1h4v4H1zm6 0h4v4H7zm6 0h4v4h-4zM1 7h4v4H1zm6 0h4v4H7zm6 0h4v4h-4zM1 13h4v4H1zm6 0h4v4H7zm6 0h4v4h-4z"/></svg><span>{t('标准视图','Standard view')}</span></button></div></div>
<div class="browse-toolbar">{year_links}<p class="result-count" data-result-count>{t(f'{len(selected)} 个案例 · 第 {number} / {pages} 页',f'{len(selected)} cases · Page {number} / {pages}')}</p></div>'''
    controls = controls.replace(' 条记录 · ', ' 个案例 · ').replace(' records · ', ' cases · ')
    if scope=='timeline':
        controls=controls.replace('<label>'+t('年份','Year')+'<select', '<label>'+t('模型发布年份','Model release year')+'<select')
        controls=controls.replace('<input type="hidden" name="sort"', '<input type="hidden" name="collapse" value=""><input type="hidden" name="sort"')
        controls+='<div class="timeline-options"><span>'+t('按模型发布时间排列 · 卡片保留作品日期','Ordered by model release · cards keep artwork dates')+'</span><label><input type="checkbox" data-model-collapse> '+t('折叠相同型号','Fold identical model versions')+'</label></div>'
    families=sorted({f for x in items for f in x.get('modelFamilies',[])})
    family_control='<label>'+t('模型家族','Model family')+'<select name="family"><option value="">'+t('全部家族','All families')+'</option>'+''.join('<option value="'+e(f)+'">'+e(f)+'</option>' for f in families)+'</select></label>'
    controls=controls.replace('<input type="hidden" name="sort"',family_control+'<input type="hidden" name="sort"')
    controls=controls.replace('<div class="browse-family-row">','<div class="browse-family-row"><nav class="family-links" aria-label="'+t('模型快速筛选','Quick model filters')+'">'+''.join('<button type="button" data-family="'+e(f)+'" aria-pressed="false">'+e(f)+'</button>' for f in ['Gemini','GPT','Claude','Qwen','DeepSeek','Llama'] if f in families)+'</nav>')
    render_card = lambda x: batch_card(x, language) if x.get('isBatch') else card(x)
    results = render_results(part, render_card, scope, language)
    def href(n): return base if n == 1 else base+f'page/{n}/'
    previous = f'<a href="{href(number-1)}" data-page="{number-1}" rel="prev">← {t("上一页","Previous")}</a>' if number > 1 else f'<span aria-disabled="true">← {t("上一页","Previous")}</span>'
    following = f'<a href="{href(number+1)}" data-page="{number+1}" rel="next">{t("下一页","Next")} →</a>' if number < pages else f'<span aria-disabled="true">{t("下一页","Next")} →</span>'
    pagination = f'''<nav class="pagination" aria-label="{t('馆藏分页','Collection pages')}" data-pagination>{previous}<span data-page-summary>{t(f'第 {number} / {pages} 页',f'Page {number} / {pages}')}</span>{following}<form data-page-jump><label>{t('跳至','Go to')} <input name="page" type="number" min="1" max="{pages}" value="{number}" required aria-label="{t('页码','Page number')}"></label><button type="submit">{t('跳转','Go')}</button></form></nav>'''
    archive = '<a class="archive-link" href="'+('/en' if en else '')+'/collections/source-records/">'+t('原帖合集与未计数来源存档 →','Source collections & uncounted archives →')+'</a>' if archive_link else ''
    return controls+f'<div data-results>{results}</div><div class="browse-footer">'+pagination+archive+'</div></div>'


def render_results(items, card, scope, language='zh'):
    if scope != 'timeline':
        return '<div class="grid">'+''.join(card(x) for x in items)+'</div>'
    result = ''; month = None
    for item in items:
        key = timeline_month(item)
        if key != month:
            if month is not None: result += '</div></section>'
            label = '' if key=='unknown' else key
            result += f'<section data-release-month="{html.escape(key)}"><div class="month-title"><h2>{html.escape(label)}</h2></div><div class="grid">'
            month = key
        result += card(item)
    return result+('</div></section>' if month is not None else '')
