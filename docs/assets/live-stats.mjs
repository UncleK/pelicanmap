const API = 'https://pelicanmap.aveniqa.com/api/v1/';
const sourceLabels = {
  en: {origin:'Original experiment', zoo:'Pelican Zoo', wtf:'pelicans.wtf', community:'Community · X, forums & GitHub'},
  zh: {origin:'原点实验', zoo:'Pelican Zoo', wtf:'pelicans.wtf', community:'社区 · X、论坛与 GitHub'}
};

export function validateSummary(summary) {
  if (!Number.isSafeInteger(summary.total) || summary.total < 0 || !/^\d{4}-\d{2}-\d{2}$/.test(summary.updated)) throw Error('Invalid collection summary');
  return summary;
}

export async function loadLiveStats(fetcher = fetch) {
  const query = async (route, filters = {}) => {
    const url = new URL(route, API);
    url.search = new URLSearchParams({lang:'en', limit:'1', ...filters});
    const response = await fetcher(url, {signal:AbortSignal.timeout(15000), credentials:'omit'});
    if (!response.ok) throw Error('Collection summary unavailable');
    return validateSummary(await response.json());
  };
  const works = await query('specimens', {sort:'oldest'});
  const lastYear = Number(works.updated.slice(0,4));
  const firstYear = Number(works.items?.[0]?.date?.slice(0,4)) || lastYear;
  if (firstYear < 1900 || firstYear > lastYear) throw Error('Invalid collection year range');
  const years = Array.from({length:lastYear-firstYear+1}, (_, i)=>String(firstYear+i));
  const sources = Object.keys(sourceLabels.en);
  const [timeline, ...groups] = await Promise.all([
    query('timeline'),
    ...years.map(year=>query('specimens', {year})),
    ...sources.map(source=>query('specimens', {source}))
  ]);
  const yearGroups = years.map((key,i)=>({key,total:groups[i].total}));
  const sourceGroups = sources.map((key,i)=>({key,total:groups[years.length+i].total}));
  // A release can switch between requests. Keep the last complete view in that case.
  if (timeline.total > works.total || [yearGroups,sourceGroups].some(rows=>rows.reduce((sum,row)=>sum+row.total,0)!==works.total) || [timeline,...groups].some(group=>group.updated!==works.updated)) throw Error('Collection release changed during refresh');
  return {works:works.total,timeline:timeline.total,updated:works.updated,years:yearGroups,sources:sourceGroups};
}

function chart(container, rows, lang, total) {
  const list = document.createElement('ul');
  list.className = 'stat-bars';
  for (const row of rows) {
    const item = document.createElement('li');
    const link = document.createElement('a');
    const destination = new URL((lang==='en'?'/en':'')+'/specimens/', 'https://pelicanmap.aveniqa.com');
    destination.searchParams.set(container.dataset.chart==='years'?'year':'source', row.key);
    destination.searchParams.set('view','images');
    link.href = destination;
    const label = document.createElement('span');
    label.textContent = sourceLabels[lang][row.key] || row.key;
    const count = document.createElement('strong');
    count.textContent = row.total.toLocaleString(lang==='en'?'en-US':'zh-CN');
    const track = document.createElement('span');
    track.className = 'bar-track';
    track.setAttribute('aria-hidden','true');
    const fill = document.createElement('span');
    fill.style.width = `${total ? row.total/total*100 : 0}%`;
    track.append(fill);
    link.append(label,count,track);
    item.append(link);
    list.append(item);
  }
  container.replaceChildren(list);
}

export function startLiveStats() {
  const section = document.querySelector('[data-live-stats]');
  if (!section) return;
  const lang = document.documentElement.lang==='en'?'en':'zh';
  const status = document.querySelector('[data-stats-status]');
  const button = document.querySelector('[data-refresh-stats]');
  let busy = false, loaded = false;
  async function refresh() {
    if (busy) return;
    busy = true;
    button.disabled = true;
    section.setAttribute('aria-busy','true');
    try {
      const result = await loadLiveStats();
      const values = {cases:result.works,timeline:result.timeline,sourceCategories:result.sources.filter(r=>r.total>0).length,years:result.years.filter(r=>r.total>0).length};
      for (const [key,value] of Object.entries(values)) section.querySelector(`[data-stat="${key}"]`).textContent=value.toLocaleString(lang==='en'?'en-US':'zh-CN');
      for (const kind of ['years','sources']) chart(section.querySelector(`[data-chart="${kind}"]`), result[kind],lang,result.works);
      const time = new Date().toLocaleTimeString(lang==='en'?'en-GB':'zh-CN',{hour:'2-digit',minute:'2-digit'});
      status.textContent = lang==='en'?`Live data · catalog ${result.updated} · checked ${time}`:`在线数据 · 目录 ${result.updated} · ${time} 已同步`;
      status.dataset.state = 'live';
      loaded = true;
    } catch {
      status.textContent = lang==='en'?(loaded?'Last successful update · retrying in 5 minutes':`Snapshot ${section.dataset.snapshot} · live data temporarily unavailable`):(loaded?'保留上次同步结果 · 5 分钟后重试':`${section.dataset.snapshot} 快照 · 在线数据暂不可用`);
      status.dataset.state = 'snapshot';
    } finally {
      section.removeAttribute('aria-busy');
      button.disabled = false;
      busy = false;
    }
  }
  button.addEventListener('click',refresh);
  refresh();
  setInterval(()=>{if(!document.hidden)refresh();},300000);
}

if (typeof document !== 'undefined') startLiveStats();
