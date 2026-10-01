// Read-only provenance/dedup evidence for the approved Nile historical source.
// Rendering is analysis only: museum originals are never changed.
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const sharp=require('sharp');
const root=path.resolve(import.meta.dirname,'..');
const manifestPath=process.argv[2]?path.resolve(process.argv[2]):path.join(root,'pelican-archive/research/2026-10-01-nile-early/manifest.json');
const out=path.dirname(manifestPath);
const manifest=JSON.parse(await fs.readFile(manifestPath,'utf8'));
const catalog=JSON.parse(await fs.readFile(path.join(root,'public-site/data/catalog.json'),'utf8'));
const digest=b=>crypto.createHash('sha256').update(b).digest('hex');
async function standard(b,size=48) {
  try{return await sharp(b,{limitInputPixels:40000000,density:72}).flatten({background:'#fff'}).trim({background:'#fff',threshold:12}).resize(size,size,{fit:'contain',background:'#fff'}).removeAlpha().raw().toBuffer();}
  catch{return await sharp(b,{limitInputPixels:40000000,density:72}).flatten({background:'#fff'}).resize(size,size,{fit:'contain',background:'#fff'}).removeAlpha().raw().toBuffer();}
}
const old=[];
for(const x of catalog.items.filter(x=>!x.referenceOnly)) for(const m of x.media) {
  if(!/\.(svg|png|jpe?g|webp)$/i.test(m.src))continue;
  try{const b=await fs.readFile(path.join(root,'pelican-web',m.src.slice(1)));old.push({id:x.id,model:x.model,date:x.date,case:x.caseVisible,src:m.src,hash:digest(b),bytes:b});}catch{}
}
const unique=[...new Map(old.map(x=>[x.src,x])).values()];
for(const x of unique)try{x.pixels=await standard(x.bytes);}catch{}
const rows=[],layers=[];
for(const [index,c] of manifest.cases.entries()) {
  const sourceMedia=c.reviewPreviewUrl?c.media.find(x=>x.url===c.reviewPreviewUrl):c.media[0];
  const file=path.join(out,'evidence',digest(Buffer.from(sourceMedia.url)).slice(0,16)+'.bin');
  const b=await fs.readFile(file),sha=digest(b);
  if(sha!==sourceMedia.sha256)throw Error('Candidate source hash changed');
  const pixels=await standard(b);
  const nearest=unique.filter(x=>x.pixels?.length===pixels.length).map(x=>{
    let error=0;for(let i=0;i<pixels.length;i++)error+=Math.abs(pixels[i]-x.pixels[i]);
    return {id:x.id,src:x.src,case:x.case,date:x.date,model:x.model,error:error/pixels.length};
  }).sort((a,b)=>a.error-b.error).slice(0,3);
  const row={id:c.id,sha256:sha,exact:old.filter(x=>x.hash===sha).map(({id,src,case:visible})=>({id,src,case:visible})),nearest};
  rows.push(row);console.log(JSON.stringify(row));
  for(let col=0;col<4;col++) {
    const input=col===0?b:await fs.readFile(path.join(root,'pelican-web',nearest[col-1].src.slice(1)));
    layers.push({input:await sharp(input,{limitInputPixels:40000000}).flatten({background:'#fff'}).resize(290,210,{fit:'contain',background:'#fff'}).png().toBuffer(),left:col*300,top:index*245});
    const label=(col===0?c.id:nearest[col-1].id).replace(/[&<>]/g,'');
    layers.push({input:Buffer.from(`<svg width="300" height="35"><text x="4" y="14" font-family="Arial" font-size="10">${label.slice(0,44)}</text><text x="4" y="29" font-family="Arial" font-size="10">${col===0?'candidate':nearest[col-1].error.toFixed(4)}</text></svg>`),left:col*300,top:index*245+210});
  }
}
await fs.writeFile(path.join(out,'dedup.json'),JSON.stringify(rows,null,2)+'\n');
await sharp({create:{width:1200,height:rows.length*245,channels:3,background:'#e8e6dc'}}).composite(layers).jpeg({quality:92}).toFile(path.join(out,'dedup-review.jpg'));
console.log(JSON.stringify({candidates:rows.length,existingMedia:unique.length,counts:catalog.counts}));
