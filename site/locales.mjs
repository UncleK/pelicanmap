import locales from './i18n/locales.json' with {type:'json'};
export const localeKeys=Object.keys(locales);
const cache=new WeakMap();
export function editions(catalogs){
  if(cache.has(catalogs))return cache.get(catalogs);
  const result={...catalogs};
  for(const lang of localeKeys.filter(x=>!result[x])){
    const data=structuredClone(catalogs.en),prefix=locales[lang].prefix;
    const rewrite=value=>value?.replace(/^(https:\/\/pelicanmap\.aveniqa\.com)?\/en\//,(_,host)=>(host||'')+prefix+'/');
    Object.assign(data,{language:lang,recordTextLanguage:'en',translationScope:'interface; archival descriptions retain their existing English translation or source language',translationNotice:locales[lang].notice,benchmarkUrl:prefix+'/tags/benchmark/'});
    for(const item of data.items){
      for(const key of ['path','url','markdown'])if(item[key])item[key]=rewrite(item[key]);
      for(const key of ['sourceLabel','formatLabel'])item[key]=locales[lang].strings[item[key]]||item[key];
      if(item.batch)item.batch.path=rewrite(item.batch.path);
    }
    result[lang]=data;
  }
  cache.set(catalogs,result);return result;
}
export function statistics(catalog){
  const works=catalog.items.filter(x=>!x.referenceOnly&&x.caseVisible!==false);
  const partition=key=>{
    const map=new Map();for(const x of works){const value=key(x);map.set(value,(map.get(value)||0)+1);}
    return [...map].sort(([a],[b])=>a<b?-1:a>b?1:0).map(([key,total])=>({key,total}));
  };
  if(works.length!==catalog.counts.cases)throw Error('Invalid catalog work count');
  return {version:catalog.version,collectionVersion:catalog.collectionVersion??null,updated:catalog.updated,counts:catalog.counts,works:works.length,timeline:catalog.counts.timeline,derivatives:works.filter(x=>x.topicTags?.includes('derivative')).length,years:partition(x=>x.date?.slice(0,4)||'unknown'),sources:partition(x=>x.source)};
}
