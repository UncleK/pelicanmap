// Preserve the licensed original SVG sources privately, plus public license copies.
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {ROOT} from './import_collection_batch.mjs';
const batch='2026-10-01-source-backfill';
const archive=path.join(ROOT,'pelican-archive/research',batch);
const media=path.join(ROOT,'pelican-web/media/collected',batch);
for(const [from,to] of [['Apache-2.0.txt','apache-2.0.txt'],['bbinwang-LICENSE','bbinwang-MIT.txt']]) {
  await fs.copyFile(path.join(archive,from),path.join(media,to));
}
const rows=(await fs.readFile(path.join(archive,'hf-data.jsonl'),'utf8')).trim().split('\n').map(x=>JSON.parse(x));
const target=path.join(archive,'hf-original-svg');
await fs.mkdir(target,{recursive:true});
const hashes=[],queue=[...rows];
async function worker(){
  while(queue.length){
    const row=queue.shift();
    if(!/^svg\/[A-Za-z0-9_.-]+\.svg$/.test(row.svg))throw Error('Unreviewed source path');
    const url='https://huggingface.co/datasets/sergiopaniego/pelican-svg-drawings/resolve/548f58a232c4aadf05f4798c2d69b8bd95e4b502/'+row.svg;
    const file=path.join(target,path.basename(row.svg));
    let bytes;
    try{bytes=await fs.readFile(file);}catch(e){if(e.code!=='ENOENT')throw e;const r=await fetch(url,{headers:{'User-Agent':'PelicanMap-Collector/1.0'},signal:AbortSignal.timeout(60000)});if(!r.ok)throw Error('Source HTTP '+r.status);bytes=Buffer.from(await r.arrayBuffer());await fs.writeFile(file,bytes,{flag:'wx'});}
    if(bytes.length<100 || bytes.length>512*1024)throw Error('Invalid raw source size');
    hashes.push({id:row.id,url,bytes:bytes.length,sha256:crypto.createHash('sha256').update(bytes).digest('hex'),publiclyDisplayed:Boolean(row.png)});
  }
}
await Promise.all(Array.from({length:4},worker));
await fs.writeFile(path.join(archive,'hf-original-svg-manifest.json'),JSON.stringify(hashes.sort((a,b)=>a.id.localeCompare(b.id)),null,2));
console.log(JSON.stringify({originalSourcesArchived:hashes.length,licensedVisibleOutputs:hashes.filter(x=>x.publiclyDisplayed).length}));
