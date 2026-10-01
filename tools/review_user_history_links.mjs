// Evidence only: render SVG data, not upstream scripts; never edit records.
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {createRequire} from 'node:module';
import {validateSvg} from './import_collection_batch.mjs';
const require=createRequire(import.meta.url);
const sharp=require('C:/Users/kolin/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
const root=path.resolve(import.meta.dirname,'..');
const out=path.join(root,'pelican-archive/research/2026-10-01-user-history-links');
const manifest=JSON.parse(await fs.readFile(path.join(out,'staged-manifest.json'),'utf8'));
const items=JSON.parse(await fs.readFile(path.join(root,'public-site/data/catalog.json'),'utf8')).items;
const digest=b=>crypto.createHash('sha256').update(b).digest('hex');
const normalize=b=>digest(Buffer.from(b.toString('utf8').replace(/<!--[\s\S]*?-->/g,'').replace(/\s+/g,' ').replace(/>\s+</g,'><').trim()));
const old=[];
for(const x of items.filter(x=>!x.referenceOnly)) for(const m of x.media) {
  if(!/\.(svg|png|jpe?g|webp)$/i.test(m.src))continue;
  const file=path.join(root,'pelican-web',m.src.slice(1));
  try { const bytes=await fs.readFile(file);old.push({id:x.id,model:x.model,date:x.date,case:x.caseVisible,src:m.src,file,hash:digest(bytes),normalized:m.src.endsWith('.svg')?normalize(bytes):'',bytes}); }catch{}
}
const unique=[...new Map(old.map(x=>[x.src,x])).values()];
async function standard(bytes,size) {
  let image=sharp(bytes,{limitInputPixels:40000000,density:72}).flatten({background:'#fff'});
  try {return await image.trim({background:'#fff',threshold:12}).resize(size,size,{fit:'contain',background:'#fff'}).removeAlpha().raw().toBuffer();}
  catch{return await sharp(bytes,{limitInputPixels:40000000,density:72}).flatten({background:'#fff'}).resize(size,size,{fit:'contain',background:'#fff'}).removeAlpha().raw().toBuffer();}
}
for(const x of unique)try{x.pixels=await standard(x.bytes,48);}catch{}
const rows=[];
for(const c of manifest.cases) {
  const bytes=await fs.readFile(path.join(out,'staged',c.id+'.svg'));
  const row={id:c.id,model:c.model,date:c.date,variant:c.variant,sha256:digest(bytes),source:c.sourceUrl};
  try {
    validateSvg(bytes);
    row.exact=old.filter(x=>x.hash===row.sha256 || (x.normalized && x.normalized===normalize(bytes))).map(({id,src,case:visible})=>({id,src,case:visible}));
    const pixels=await standard(bytes,48);
    row.nearest=unique.filter(x=>x.pixels?.length===pixels.length).map(x=>{
      let error=0;for(let i=0;i<pixels.length;i++)error+=Math.abs(pixels[i]-x.pixels[i]);
      return {id:x.id,src:x.src,case:x.case,date:x.date,model:x.model,error:error/pixels.length};
    }).sort((a,b)=>a.error-b.error).slice(0,3);
  }catch(e){row.error=e.message;}
  rows.push(row);
  console.log(JSON.stringify(row));
}
await fs.writeFile(path.join(out,'dedup.json'),JSON.stringify(rows,null,2));
for(let offset=0;offset<rows.length;offset+=7) {
  const page=rows.slice(offset,offset+7),layers=[];
  for(let r=0;r<page.length;r++)for(let col=0;col<4;col++) {
    const row=page[r],src=col===0?path.join(out,'staged',row.id+'.svg'):row.nearest?.[col-1]?.src;
    if(!src)continue;
    const file=col===0?src:path.join(root,'pelican-web',src.slice(1));
    try{layers.push({input:await sharp(file).flatten({background:'#fff'}).resize(290,210,{fit:'contain',background:'#fff'}).png().toBuffer(),left:col*300,top:r*245});}catch{}
    const label=col===0?row.id:row.nearest[col-1].id;
    const text=label.replace(/[&<>]/g,'');
    layers.push({input:Buffer.from(`<svg width="300" height="35"><text x="5" y="14" font-family="Arial" font-size="10">${text.slice(0,42)}</text><text x="5" y="29" font-family="Arial" font-size="10">${col===0?row.variant:row.nearest[col-1].error.toFixed(4)}</text></svg>`),left:col*300,top:r*245+210});
  }
  await sharp({create:{width:1200,height:page.length*245,channels:3,background:'#e8e6dc'}}).composite(layers).jpeg({quality:92}).toFile(path.join(out,`review-${offset/7+1}.jpg`));
}
console.log('Reviewed candidates',rows.length,'existing media',unique.length);
