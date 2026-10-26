const demoOrigin = 'https://pelicanmap-demos.aveniqa.com/demos/';
export function catalogHref(english, version) {
  const prefix=typeof english==='string'?({'en':'/en','ru':'/ru','pt-BR':'/pt-BR'}[english]||''):(english?'/en':'');
  const base=prefix+'/data/catalog.json';
  return /^[a-f0-9]{20}$/.test(version||'') ? base+'?collection='+version : base;
}
export const isCase = x => !x.referenceOnly && x.caseVisible !== false;
export const inTimeline = x => isCase(x) && (x.timelineVisible ?? x.kind === 'timeline');
export function groupRecords(items, includeReferences = false) {
  items = items.filter(x => includeReferences || isCase(x));
  const groups = new Map();
  for (const item of items) if (item.batch) {
    const members = groups.get(item.batch.id) || [];
    members.push(item); groups.set(item.batch.id, members);
  }
  const result = [], seen = new Set();
  for (const item of items) {
    const batch = item.batch, members = batch && groups.get(batch.id);
    if (!batch || members.length < 2) {result.push(item); continue;}
    if (seen.has(batch.id)) continue;
    seen.add(batch.id);
    const previews = [], models = new Set();
    for (const x of members) if (!models.has(x.model)) {
      models.add(x.model); previews.push(x); if (previews.length === 6) break;
    }
    for (const x of members) if (previews.length < 6 && !previews.includes(x)) previews.push(x);
    const record = {...item, id:'batch-'+batch.id, originalId:'batch-'+batch.id,
      isBatch:true, title:batch.title, notes:batch.description, model:batch.modelLabels.join(', '),
      modelNames:[...batch.modelLabels],
      sourceUrl:batch.sourceUrl, sourceCodeUrl:batch.sourceUrl, path:batch.path,
      url:'https://pelicanmap.aveniqa.com'+batch.path, markdown:batch.path+'index.md',
      previews:previews.map(x=>({thumbnail:x.thumbnail,title:x.title})), media:previews.map(x=>x.media[0]),
      matchingSamples:members.length, sampleIds:members.map(x=>x.id), originalLevel:''};
    delete record.datasetSample; delete record.i18n;
    result.push(record);
  }
  return result;
}
const cmp = (a,b) => a < b ? -1 : a > b ? 1 : 0;
const modelKey = x => x.modelTimeline?.key || 'unverified:'+String(x.model||'').trim().toLowerCase().replace(/[\s_-]+/g,'-');
const modelSortDate = x => x.modelTimeline?.sortDate || x.modelTimeline?.releaseDate || '';
export const timelineYear = x => modelSortDate(x).slice(0,4) || 'unknown';
export const timelineMonth = x => modelSortDate(x).slice(0,7) || 'unknown';
export function compareArtwork(a,b,sort='newest') {
  const direction=sort==='oldest'?1:-1;
  return direction*(cmp(a.date||'',b.date||'')||cmp(a.id,b.id));
}
export function compareTimeline(a,b,sort='newest',activity) {
  const ad=modelSortDate(a),bd=modelSortDate(b);
  if(!ad!==!bd)return ad?-1:1;
  const direction=sort==='oldest'?1:-1;
  const ak=modelKey(a),bk=modelKey(b);
  if(ak===bk)return compareArtwork(a,b,sort);
  const latest=x=>activity?.get(modelKey(x)) || {date:x.modelTimeline?.latestArtworkDate||x.date,id:x.modelTimeline?.latestArtworkId||x.id};
  const aa=latest(a),ba=latest(b);
  return ad?direction*(cmp(ad.slice(0,7),bd.slice(0,7))||cmp(aa.date,ba.date)||cmp(aa.id,ba.id)||cmp(ad,bd)||cmp(ak,bk)):cmp(ak,bk);
}
export function groupModelRecords(items) {
  const groups=new Map();
  for(const x of items){const key=modelKey(x);if(!groups.has(key))groups.set(key,{...x,modelMembers:[]});groups.get(key).modelMembers.push(x);}
  return [...groups.values()];
}
export function groupRunRecords(items) {
  const groups=new Map();
  for(const item of items){
    const run=item.modelRunGroup || (item.representativeOf || (item.variantIds?.length ? item.id : ''));
    const key=run ? modelKey(item)+'\u0000'+run : 'single\u0000'+item.id;
    if(!groups.has(key))groups.set(key,{...item,runKey:key,runMembers:[]});
    groups.get(key).runMembers.push(item);
  }
  for(const group of groups.values()){
    const rows=group.runMembers;
    const primary=rows.find(x=>x.authorDefault===true)
      || rows.find(x=>rows.some(other=>other.representativeOf===x.id))
      || rows.find(x=>String(x.originalLevel).toLowerCase()==='medium') || rows[0];
    group.runMembers=[primary,...rows.filter(x=>x!==primary)];
  }
  return [...groups.values()];
}
export function selectRecords(records, {scope = '', year = '', q = '', source = '', format = '', family = '', sort = 'newest'} = {}) {
  q = q.trim().toLowerCase();
  let items = records.filter(x => (scope==='play' ? !x.referenceOnly : isCase(x)) && (!scope || scope === 'play' || (scope==='timeline' ? inTimeline(x) : scope==='derivative' ? x.topicTags?.includes('derivative') : x.kind === scope))
    && (scope !== 'play' || (x.interactive === true && x.demoUrl?.startsWith(demoOrigin)))
    && (!year || (scope==='timeline'?(year==='unknown'?!x.modelTimeline?.releaseDate:timelineYear(x)===year):x.date.startsWith(year))) && (!source || x.source === source) && (!format || x.format === format)
    && (!family || x.modelFamilies?.includes(family))
    && (!q || [x.title, x.author, x.notes, x.date, x.model, x.promptCategory].join(' ').toLowerCase().includes(q)));
  const activity=new Map();
  if(scope==='timeline')for(const x of items){
    const key=modelKey(x), info=x.modelTimeline, current=activity.get(key);
    const latest={date:info?.latestArtworkDate||x.date,id:info?.latestArtworkId||x.id};
    if(!current || cmp(latest.date,current.date)>0 || (latest.date===current.date && cmp(latest.id,current.id)>0))activity.set(key,latest);
  }
  items.sort(scope==='timeline'?(a,b)=>compareTimeline(a,b,sort,activity):(a,b)=>compareArtwork(a,b,sort));
  if (scope === 'play') {
    const seen = new Set();
    items = items.filter(x => !x.canonicalId || !items.some(y=>y.id===x.canonicalId && y.demoUrl===x.demoUrl));
    items = items.filter(x => !seen.has(x.demoUrl) && !!seen.add(x.demoUrl));
  }
  return items;
}
const viewSizes = {standard:24, compact:48, images:60};
export function viewPageSize(view, width=Infinity) {
  if (view !== 'images') return viewSizes[normalizeView(view)];
  if (width <= 720) return width < 400 ? 96 : 120;
  return width <= 900 ? 48 : 60;
}
const normalizeView = view => view === true ? 'compact' : Object.hasOwn(viewSizes,view) ? view : 'standard';
export function nextView(view) {
  return {standard:'compact',compact:'images',images:'standard'}[normalizeView(view)];
}
export function viewLabel(view, english=false) {
  const labels=english?{standard:'Standard view',compact:'Compact view',images:'Images only'}:{standard:'标准视图',compact:'紧凑视图',images:'纯图片'};
  return labels[normalizeView(view)];
}
export function paginate(items, requested = 1, view = 'standard', width=Infinity) {
  const size = viewPageSize(normalizeView(view), width);
  const pages = Math.max(1, Math.ceil(items.length / size));
  const page = Math.max(1, Math.min(pages, Math.trunc(Number(requested)) || 1));
  return {items: items.slice((page - 1) * size, page * size), page, pages, total: items.length, size};
}
export function pageHref(base, page, values = {}) {
  const params = new URLSearchParams();
  for (const [name, value] of Object.entries(values)) if (value) params.set(name, value);
  params.set('page', String(page));
  return base + '?' + params;
}

export function rowTextHeight(heights, limit=190) {
  return Math.ceil(Math.min(limit,Math.max(72,...heights.filter(Number.isFinite))));
}

function bootAdaptiveCardRows(main) {
  let pending=false;
  const widths=new WeakMap(),watched=new Set();
  const schedule=()=>{
    if(pending)return;
    pending=true;
    requestAnimationFrame(()=>{pending=false;layout();});
  };
  const resize=new ResizeObserver(entries=>{
    for(const entry of entries){
      const width=entry.contentRect.width;
      if(widths.get(entry.target)!==width){widths.set(entry.target,width);schedule();}
    }
  });
  function layout(){
    const grids=new Set(main.querySelectorAll('.grid'));
    for(const grid of watched)if(!grids.has(grid)){resize.unobserve(grid);watched.delete(grid);}
    for(const grid of grids){
      if(!watched.has(grid)){watched.add(grid);resize.observe(grid);}
      const rows=[];
      for(const card of grid.children){
        if(!card.classList.contains('specimen-card'))continue;
        const body=card.querySelector('.card-body');
        if(!body || getComputedStyle(body).display==='none')continue;
        const style=getComputedStyle(body),top=card.getBoundingClientRect().top;
        let natural=parseFloat(style.paddingTop)+parseFloat(style.paddingBottom);
        for(const child of body.children){
          const childStyle=getComputedStyle(child);
          natural+=child.getBoundingClientRect().height+parseFloat(childStyle.marginTop)+parseFloat(childStyle.marginBottom);
        }
        let row=rows.find(x=>Math.abs(x.top-top)<2);
        if(!row){row={top,cards:[],heights:[],limit:parseFloat(getComputedStyle(card).getPropertyValue('--card-text-limit'))||190};rows.push(row);}
        row.cards.push(card);row.heights.push(natural);
      }
      for(const row of rows){
        const height=rowTextHeight(row.heights,row.limit)+'px';
        for(const card of row.cards)if(card.style.getPropertyValue('--card-text')!==height)card.style.setProperty('--card-text',height);
      }
    }
  }
  new MutationObserver(schedule).observe(main,{childList:true,subtree:true});
  document.fonts.ready.then(schedule);
  schedule();
}

const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]));
function cardFooter(x, english, timeline=false) {
  const names=x.modelNames?.length?x.modelNames:[english?'Model not specified':'模型未标注'];
  const number=x.caseNumber ? '#'+x.caseNumber : (english?'Source archive':'来源存档');
  const date=x.date || (english?'Date not recorded':'日期未记录');
  const dateLabel=date+(x.datePrecision==='month'?(english?' · exact day unknown':' · 具体日未知'):'');
  const time=`<time class="${timeline?'timeline-date':'card-date'}" datetime="${esc(x.date)}" title="${esc(dateLabel)}" aria-label="${esc(dateLabel)}">${esc(date)}</time>`;
  const models=timeline?`<a href="${esc(x.path)}">${esc(names[0])}</a>`:names.map(name=>`<span class="model-name">${esc(name)}</span>`).join('');
  return `<div class="${timeline?'timeline-meta':'card-foot'}"><span class="case-number" aria-label="${esc(number)}">${esc(number)}</span><div class="${timeline?'timeline-model':'card-models'}" tabindex="0" aria-label="${english?'Source-labelled models':'来源标注的模型'}" title="${esc(x.model)}">${models}</div>${time}</div>`;
}
export function renderCard(x, {view='standard', english=false, timeline=false} = {}) {
  const t = (zh,en) => english ? (globalThis.PelicanI18n?.text(en)||en) : zh;
  if (x.isBatch) {
    const batch=x.batch;
    const count=t(`${batch.models} 个模型标签 · ${batch.total} 个样本`,`${batch.models} model labels · ${batch.total} samples`);
    const previews=x.previews.map(p=>`<img src="${esc(p.thumbnail)}" alt="${esc(p.title)}" width="320" height="210" loading="lazy">`).join('');
    const cover=`<a class="card-cover batch-cover" href="${esc(batch.path)}" aria-label="${esc(batch.title+' · '+count)}">${previews}<span class="batch-badge">${batch.total} ${t('样本','samples')}</span></a>`;
    const matched=x.matchingSamples===batch.total?'':t(` · 当前匹配 ${x.matchingSamples} 个`,` · ${x.matchingSamples} matching`);
    return `<article class="card ${view==='images'?'':'specimen-card '}batch-card" data-batch-card="${esc(batch.id)}">${cover}${view==='images'?'':`<div class="card-body" tabindex="0" aria-label="${t('作品说明','Work description')}"><div class="card-meta">${esc(x.date)} · ${t('实验合集 · 计 1 个案例','Experiment batch · 1 case')}</div><h3><a href="${esc(batch.path)}">${esc(batch.title)}</a></h3><p class="note">${esc(count+matched)}</p></div>${cardFooter(x,english)}`}</article>`;
  }
  const motion = x.motionPreview, kind = motion?.type, src = esc(motion?.src);
  const attrs = kind==='image'?` data-motion-kind="image" data-motion-src="${src}" data-motion-poster="${esc(x.thumbnail)}"`:'';
  let image = `<img src="${esc(x.thumbnail)}" alt="${esc(x.title)}" width="640" height="420" loading="lazy"${attrs}>`;
  if(kind==='video')image+=`<video class="motion-layer" data-motion-kind="video" data-motion-src="${src}" autoplay muted loop playsinline preload="none" aria-hidden="true" tabindex="-1"></video>`;
  if(kind==='iframe')image+=`<span class="motion-layer motion-frame"><iframe data-motion-kind="iframe" data-motion-src="${src}" title="${esc(x.title)}" loading="lazy" scrolling="no" sandbox="allow-scripts allow-same-origin" referrerpolicy="no-referrer" aria-hidden="true" tabindex="-1"></iframe></span>`;
  const cover = `<a class="card-cover" href="${esc(x.path)}" aria-label="${esc(x.title)}">${image}${view==='images'?'':`<span class="media-label">${esc(x.formatLabel)}</span>${x.sourceLabel?`<span class="source-label" title="${esc(x.sourceLabel)}">${esc(x.sourceLabel)}</span>`:''}`}</a>`;
  if (view === 'images') return `<article class="card">${cover}</article>`;
  if (timeline) {
    return `<article class="card timeline-card"><a class="card-cover" href="${esc(x.path)}" aria-label="${esc(x.title)}">${image}</a>${cardFooter(x,english,true)}</article>`;
  }
  return `<article class="card specimen-card">${cover}<div class="card-body" tabindex="0" aria-label="${t('作品说明','Work description')}"><h3><a href="${esc(x.path)}">${esc(x.title)}</a></h3>${x.topicTags?.includes("derivative")?`<div class="card-meta"><a href="${english?"/en":""}/derivatives/" rel="tag">${t("衍生作品","Derivative works")}</a></div>`:""}<p class="note">${esc(x.notes || x.author)}</p></div>${cardFooter(x,english)}</article>`;
}

export function modelGroupMembers(group) {
  return groupRunRecords(group.modelMembers).flatMap(run=>run.runMembers);
}

export function renderModelCard(group, {view='standard',english=false,index=0}={}) {
  const members=modelGroupMembers(group),primary=members[0];
  const label=(english?(globalThis.PelicanI18n?.text(`View all ${members.length} works of this version`)||`View all ${members.length} works of this version`):`查看该型号的全部 ${members.length} 件作品`)+' · '+primary.model;
  const button=`<button type="button" class="model-more" data-model-more="${index}" aria-haspopup="dialog" aria-label="${esc(label)}" title="${esc(label)}"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M6 18 18 6M6 6h12v12" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></button>`;
  return renderCard(primary,{view,english,timeline:true})
    .replace('<article class="','<article data-model-group="'+esc(modelKey(group))+'" class="model-more-card ')
    .replace('</article>',button+'</article>');
}

function modelWorksDialog(root,t) {
  const dialog=document.createElement('dialog');
  dialog.className='model-dialog';dialog.setAttribute('aria-labelledby','model-dialog-title');
  dialog.innerHTML=`<header class="model-dialog-head"><div><h2 id="model-dialog-title"></h2><p data-model-dialog-count></p></div><div class="model-dialog-actions"><button type="button" class="model-dialog-close" data-model-dialog-close autofocus aria-label="${t('关闭浮窗','Close dialog')}" title="${t('关闭浮窗','Close dialog')}">×</button></div></header><div class="model-dialog-body"></div>`;
  root.append(dialog);
  const body=dialog.querySelector('.model-dialog-body'),cache=new Map();
  let trigger,position,motionHome;
  const notify=()=>root.dispatchEvent(new CustomEvent('pelican-dialog-change',{bubbles:true}));
  function close(){if(dialog.open)dialog.close();}
  dialog.querySelector('[data-model-dialog-close]').addEventListener('click',close);
  dialog.addEventListener('cancel',event=>{event.preventDefault();close();});
  dialog.addEventListener('click',event=>{
    if(event.target!==dialog)return;
    const box=dialog.getBoundingClientRect();
    if(event.clientX<box.left||event.clientX>box.right||event.clientY<box.top||event.clientY>box.bottom)close();
  });
  dialog.addEventListener('close',()=>{
    document.documentElement.classList.remove('model-dialog-open');
    if(motionHome){const {node,parent,next}=motionHome;if(next?.parentNode===parent)parent.insertBefore(node,next);else parent.append(node);motionHome=null;}
    notify();
    if(position)window.scrollTo({left:position.x,top:position.y,behavior:'instant'});
    if(trigger?.isConnected)trigger.focus({preventScroll:true});
  });
  return (group,{view,english},opener)=>{
    const members=modelGroupMembers(group),key=view+'\u0000'+members.map(x=>x.id).join('\u0000');
    let collection=cache.get(key);
    if(!collection){
      collection=document.createElement('div');collection.className='model-dialog-collection';
      collection.innerHTML='<div class="grid">'+members.map(x=>renderCard(x,{view,english,timeline:true})).join('')+'</div>';
      body.append(collection);cache.set(key,collection);
    }
    for(const child of body.children)child.hidden=child!==collection;
    dialog.querySelector('h2').textContent=group.model;
    dialog.querySelector('[data-model-dialog-count]').textContent=t(`同型号 ${members.length} 件作品`,`${members.length} works of this version`);
    dialog.classList.toggle('compact-view',view==='compact');dialog.classList.toggle('image-view',view==='images');
    trigger=opener;position={x:window.scrollX,y:window.scrollY};
    const motion=document.querySelector('[data-motion-toggle]');
    if(motion&&!motionHome){motionHome={node:motion,parent:motion.parentNode,next:motion.nextSibling};dialog.querySelector('.model-dialog-actions').prepend(motion);}
    document.documentElement.classList.add('model-dialog-open');
    dialog.showModal();body.scrollTop=0;notify();
  };
}

function bootBrowser(root) {
  const english = document.documentElement.lang !== 'zh-CN';
  const t = (zh, en) => english ? (globalThis.PelicanI18n?.text(en)||en) : zh;
  const form = root.querySelector('[data-search]');
  const results = root.querySelector('[data-results]');
  const pager = root.querySelector('[data-pagination]');
  const count = root.querySelector('[data-result-count]');
  const sortButton = root.querySelector('[data-sort-toggle]');
  const densityButton = root.querySelector('[data-density-toggle]');
  const searchToggle = root.querySelector('[data-search-toggle]');
  const setSearchOpen = open => {
    form.hidden = !open;
    searchToggle.setAttribute('aria-expanded', String(open));
    if (open) {
      form.scrollIntoView({block:'nearest', behavior:'instant'});
      form.elements.namedItem('q').focus({preventScroll:true});
    }
  };
  searchToggle.addEventListener('click', () => setSearchOpen(form.hidden));
  if (location.hash === '#search') setSearchOpen(true);
  window.addEventListener('hashchange', () => {if (location.hash === '#search') setSearchOpen(true);});
  form.addEventListener('keydown', event => {
    if (event.key !== 'Escape') return;
    event.preventDefault(); setSearchOpen(false); searchToggle.focus({preventScroll:true});
  });
  const params = new URLSearchParams(location.search);
  for (const name of ['q','year','source','format','family','sort','collapse']) if (params.has(name) && form.elements.namedItem(name)) form.elements.namedItem(name).value = params.get(name);
  const collapseToggle=root.querySelector('[data-model-collapse]');
  if(collapseToggle)collapseToggle.checked=form.elements.namedItem('collapse').value==='1';
  const mobile = matchMedia('(max-width:720px)').matches;
  const viewPreferenceKey = mobile ? 'pelican-card-view-mobile' : 'pelican-card-view';
  let view = normalizeView(params.get('view'));
  if (!params.has('view')) {
    view = mobile ? 'compact' : 'standard';
    try {const saved=localStorage.getItem(viewPreferenceKey);if(saved)view=normalizeView(saved);} catch {}
  }
  let currentPage = params.get('page') || root.dataset.initialPage || 1;
  let renderedSize = viewPageSize(view, innerWidth);
  let catalogPromise, revision = 0;
  const card = x => renderCard(x,{view,english,timeline:root.dataset.scope==='timeline'});
  const values = () => ({...Object.fromEntries(new FormData(form)), view});
  const showModelWorks=root.dataset.scope==='timeline'?modelWorksDialog(root,t):null;
  let shownGroups=[];
  results.addEventListener('click',event=>{
    const button=event.target.closest('[data-model-more]');
    if(!button||!shownGroups[Number(button.dataset.modelMore)])return;
    showModelWorks(shownGroups[Number(button.dataset.modelMore)],{view,english},button);
  });
  async function render(requested = 1, updateUrl = true) {
    const turn = ++revision;
    root.classList.toggle('compact-view', view === 'compact');
    root.classList.toggle('image-view', view === 'images');
    root.dataset.view = view;
    densityButton.setAttribute('aria-pressed', String(view !== 'standard'));
    const labels = Object.fromEntries(Object.keys(viewSizes).map(key=>[key,viewLabel(key,english)]));
    const next = nextView(view);
    densityButton.querySelector('span').textContent = labels[view];
    const nextSize = viewPageSize(next, innerWidth);
    densityButton.title = t(`当前：${labels[view]}；点击切换：${labels[next]} · 每页 ${nextSize} 张`,`Current: ${labels[view]}; switch to ${labels[next]} · ${nextSize} per page`);
    const filters = values();
    const searchActive = ['q','source','format','family','year'].some(name => filters[name]?.trim());
    searchToggle.querySelector('[data-search-active]').hidden = !searchActive;
    root.querySelectorAll('[data-year]').forEach(link=>{
      if(link.dataset.year===filters.year) link.setAttribute('aria-current','true');
      else link.removeAttribute('aria-current');
      link.href=pageHref(root.dataset.base,1,{...filters,year:link.dataset.year});
    });
    root.querySelectorAll('[data-family]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.family===filters.family)));
    sortButton.textContent = filters.sort === 'oldest' ? '↑ '+t('最早在前','Oldest first') : '↓ '+t('最新在前','Newest first');
    try {
      catalogPromise ||= fetch(catalogHref(document.documentElement.lang,root.dataset.catalogVersion), {cache:'no-cache'})
        .then(r => {if (!r.ok) throw Error('catalog'); return r.json();})
        .catch(error => {catalogPromise = undefined; throw error;});
      const catalog = await catalogPromise;
      if (turn !== revision) return;
      const selected=groupRecords(selectRecords(catalog.items,{scope:root.dataset.scope,...filters}),root.dataset.scope==='play');
      const folded=root.dataset.scope==='timeline'&&filters.collapse==='1';
      const page = paginate(folded?groupModelRecords(selected):selected, requested, view, innerWidth);
      shownGroups=folded?page.items:[];
      currentPage = page.page;
      renderedSize = page.size;
      let content = '';
      if (root.dataset.scope === 'timeline') {
        let month;
        for (const [index,item] of page.items.entries()) {
          const next = timelineMonth(item);
          if (month !== next) {
            if (month) content += '</div></section>';
            const label=next==='unknown'?'':next;
            content += `<section data-release-month="${esc(next)}"><div class="month-title"><h2>${esc(label)}</h2></div><div class="grid">`;
            month = next;
          }
          if(folded&&item.modelMembers.length>1){
            content+=renderModelCard(item,{view,english,index});
          }else content += card(item);
        }
        if (month) content += '</div></section>';
      } else content = '<div class="grid">'+page.items.map(card).join('')+'</div>';
      results.innerHTML = page.total ? content : `<p class="result-empty">${t('没有找到相关标本。试试其他年份或减少筛选条件。','No matching records. Try another year or fewer filters.')}</p>`;
      const samplesOnly = page.total && page.items.every(x=>x.batch && !x.isBatch);
      count.textContent = folded?t(`${selected.length} 个案例 · ${page.total} 个型号 · 第 ${page.page} / ${page.pages} 页`,`${selected.length} cases · ${page.total} model versions · Page ${page.page} / ${page.pages}`):samplesOnly ? t(`${page.total} 个匹配样本 · 第 ${page.page} / ${page.pages} 页`,`${page.total} matching samples · Page ${page.page} / ${page.pages}`) : t(`${page.total} 个案例 · 第 ${page.page} / ${page.pages} 页`,`${page.total} cases · Page ${page.page} / ${page.pages}`);
      const pageLink = (number, text, rel) => `<a href="${esc(pageHref(root.dataset.base,number,filters))}" data-page="${number}" rel="${rel}">${text}</a>`;
      pager.innerHTML = (page.page > 1 ? pageLink(page.page-1,'← '+t('上一页','Previous'),'prev') : `<span aria-disabled="true">← ${t('上一页','Previous')}</span>`)
        + `<span data-page-summary>${t(`第 ${page.page} / ${page.pages} 页`,`Page ${page.page} / ${page.pages}`)}</span>`
        + (page.page < page.pages ? pageLink(page.page+1,t('下一页','Next')+' →','next') : `<span aria-disabled="true">${t('下一页','Next')} →</span>`)
        + `<form data-page-jump><label>${t('跳至','Go to')} <input name="page" type="number" min="1" max="${page.pages}" value="${page.page}" required aria-label="${t('页码','Page number')}"></label><button type="submit">${t('跳转','Go')}</button></form>`;
      if (updateUrl) history.replaceState(null,'',pageHref(root.dataset.base,page.page,filters));
    } catch {
      count.textContent = t('检索暂时不可用，请通过下方分页浏览。','Search is unavailable; use the page links below.');
    }
  }
  form.addEventListener('submit', event => {event.preventDefault(); render(1);});
  let timer;
  form.addEventListener('input', () => {clearTimeout(timer); timer = setTimeout(() => render(1),180);});
  form.addEventListener('change', () => {clearTimeout(timer); render(1);});
  collapseToggle?.addEventListener('change',()=>{form.elements.namedItem('collapse').value=collapseToggle.checked?'1':'0';render(1);});
  root.querySelectorAll('[data-family]').forEach(button=>button.addEventListener('click',()=>{const select=form.elements.namedItem('family');select.value=select.value===button.dataset.family?'':button.dataset.family;render(1);}));
  root.querySelectorAll('[data-year]').forEach(link=>link.addEventListener('click',event=>{
    if(event.ctrlKey||event.metaKey||event.shiftKey||event.altKey)return;
    event.preventDefault();form.elements.namedItem('year').value=link.dataset.year;render(1);
  }));
  form.addEventListener('reset', () => setTimeout(() => {form.elements.namedItem('year').value='';if(collapseToggle){collapseToggle.checked=true;form.elements.namedItem('collapse').value='1';}render(1);},0));
  sortButton.addEventListener('click', () => {form.elements.namedItem('sort').value = form.elements.namedItem('sort').value==='oldest'?'newest':'oldest'; render(1);});
  densityButton.addEventListener('click', () => {
    const firstIndex = (Number(currentPage)-1)*renderedSize;
    view = nextView(view);
    try {localStorage.setItem(viewPreferenceKey,view);} catch {}
    render(Math.floor(firstIndex/viewPageSize(view,innerWidth))+1);
  });
  let resizeTimer;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      const size = viewPageSize(view, innerWidth);
      if (size !== renderedSize) render(Math.floor((Number(currentPage)-1)*renderedSize/size)+1);
    }, 120);
  });
  pager.addEventListener('click', event => {
    const a = event.target.closest('a[data-page]');
    if (!a || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    event.preventDefault(); render(a.dataset.page);
    root.scrollIntoView({behavior:'instant'});
  });
  pager.addEventListener('submit', event => {
    if (!event.target.matches('[data-page-jump]')) return;
    event.preventDefault(); render(new FormData(event.target).get('page'));
    root.scrollIntoView({behavior:'instant'});
  });
  render(currentPage);
}
if (typeof document !== 'undefined') document.querySelectorAll('[data-browser]').forEach(bootBrowser);
if (typeof document !== 'undefined' && document.querySelector('main')) bootAdaptiveCardRows(document.querySelector('main'));

function bootBatch(root) {
  const english=document.documentElement.lang!=='zh-CN';
  const t=(zh,en)=>english?en:zh;
  const form=root.querySelector('[data-batch-search]');
  const params=new URLSearchParams(location.search);
  for (const name of ['q','model']) if (params.has(name)) form.elements.namedItem(name).value=params.get(name);
  const filter=(updateUrl=true)=>{
    const q=form.elements.namedItem('q').value.trim().toLowerCase(), model=form.elements.namedItem('model').value;
    let total=0, models=0;
    for (const section of root.querySelectorAll('.batch-model')) {
      let count=0;
      for (const sample of section.querySelectorAll('[data-batch-sample]')) {
        sample.hidden=!!((model&&section.dataset.model!==model)||(q&&!sample.dataset.searchText.includes(q)));
        if (!sample.hidden) count++;
      }
      section.hidden=count===0;
      section.querySelector('[data-model-count]').textContent=count+' '+t('个样本',count===1?'sample':'samples');
      if (count) {total+=count; models++; if (q||model) section.open=true;}
    }
    root.querySelector('[data-batch-count]').textContent=root.dataset.referenceOnly==='true'?t(`${total} 条参考记录 · ${models} 个模型标签 · 不计案例总数`,`${total} reference rows · ${models} model labels · excluded from case count`):t(`${total} 个样本 · ${models} 个模型标签 · 计 1 个案例`,`${total} ${total===1?'sample':'samples'} · ${models} model ${models===1?'label':'labels'} · 1 case`);
    root.querySelector('[data-batch-empty]').hidden=total>0;
    if (updateUrl) {const p=new URLSearchParams(); if(q)p.set('q',form.elements.namedItem('q').value.trim()); if(model)p.set('model',model);history.replaceState(null,'',location.pathname+(p.size?'?'+p:''));}
  };
  form.addEventListener('submit',event=>{event.preventDefault();filter();});
  form.addEventListener('input',()=>filter());
  form.addEventListener('change',()=>filter());
  form.addEventListener('reset',()=>setTimeout(()=>{root.querySelectorAll('.batch-model').forEach(x=>x.open=false);filter();},0));
  root.querySelectorAll('[data-batch-expand]').forEach(button=>button.addEventListener('click',()=>{
    root.querySelectorAll('.batch-model:not([hidden])').forEach(section=>section.open=button.dataset.batchExpand==='true');
  }));
  filter(false);
}
if (typeof document !== 'undefined') document.querySelectorAll('[data-batch-page]').forEach(bootBatch);
