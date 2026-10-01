const english=document.documentElement.lang==='en';
const t=(zh,en)=>english?en:zh;
// Listing search, sorting and pagination live in the shared browse.js module.
document.querySelector('[data-copy]')?.addEventListener('click',async e=>{
  try{await navigator.clipboard.writeText(document.querySelector('link[rel=canonical]').href);e.target.textContent=t('链接已复制','Link copied');}
  catch{e.target.textContent=t('请复制浏览器地址栏中的网址','Please copy the URL from your address bar');}
});

document.querySelector('[data-demo-fullscreen]')?.addEventListener('click',()=>{
  document.querySelector('iframe[data-local-demo]')?.requestFullscreen?.();
});
document.querySelectorAll('img').forEach(img=>img.addEventListener('error',()=>{img.alt=t('图片暂时无法加载，请查看原始来源','Image unavailable; please consult the original source');}));

document.querySelector('[data-language]')?.addEventListener('click',e=>{const target=new URL(e.currentTarget.href);target.search=location.search;target.hash=location.hash;e.currentTarget.href=target.href;});

const sourceSearch=document.querySelector('[data-source-search]');
const sourceYear=document.querySelector('[data-source-year]');
function filterSources(){
  const q=sourceSearch.value.trim().toLowerCase(),year=sourceYear.value;
  let visible=0;
  document.querySelectorAll('[data-source-entry]').forEach(row=>{
    row.hidden=!!((year&&row.dataset.year!==year)||(q&&!row.textContent.toLowerCase().includes(q)));
    if(!row.hidden)visible++;
  });
  document.querySelector('[data-source-count]').textContent=visible+t(' 条索引',' entries');
  document.querySelector('[data-source-empty]').hidden=visible>0;
}
sourceSearch?.addEventListener('input',filterSources);
sourceYear?.addEventListener('change',filterSources);

// Fit all source-labelled models onto one line, including dynamically paged cards.
const fittedModelRows=new WeakSet();
function fitModelRow(row){
  let size=row.classList.contains('timeline-model')?(row.closest('.compact-view')?12:15):(row.closest('.compact-view')?11:12);
  row.style.fontSize=size+'px';
  while(row.clientWidth>0&&row.scrollWidth>row.clientWidth&&size>8){
    size-=0.5;row.style.fontSize=size+'px';
  }
}
const modelRowResize=new ResizeObserver(entries=>entries.forEach(entry=>fitModelRow(entry.target)));
function watchModelRows(){
  document.querySelectorAll('.specimen-card .card-models,.timeline-card .timeline-model').forEach(row=>{
    if(fittedModelRows.has(row))return;
    fittedModelRows.add(row);modelRowResize.observe(row);fitModelRow(row);
  });
}
watchModelRows();
new MutationObserver(watchModelRows).observe(document.querySelector('main'),{childList:true,subtree:true});
document.fonts.ready.then(()=>document.querySelectorAll('.specimen-card .card-models,.timeline-card .timeline-model').forEach(fitModelRow));

// Keep long timelines and filtered collections easy to navigate.
if (/^\/(?:en\/)?(?:timeline|specimens|play|collections)(?:\/|$)/.test(location.pathname)) {
  const backToTop=document.createElement('button');
  backToTop.type='button';
  backToTop.className='floating-top';
  backToTop.textContent='↑ '+t('回到顶部','Back to top');
  backToTop.setAttribute('aria-label',t('回到页面顶部','Back to the top of the page'));
  backToTop.hidden=true;
  document.body.append(backToTop);
  const updateTopButton=()=>{backToTop.hidden=window.scrollY<600;};
  window.addEventListener('scroll',updateTopButton,{passive:true});
  updateTopButton();
  backToTop.addEventListener('click',()=>{
    const heading=document.querySelector('h1');
    if(heading){heading.setAttribute('tabindex','-1');heading.focus({preventScroll:true});}
    window.scrollTo({top:0,behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});
  });
}
