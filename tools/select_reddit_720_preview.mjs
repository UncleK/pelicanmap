// Use Reddit's original 720p video track for the public page, not a re-encode.
// The downloaded original 1080p track is retained unchanged in the local archive.
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {ROOT} from './import_collection_batch.mjs';
const url='https://v.redd.it/t6907e2rdirh1/CMAF_720.mp4';
const r=await fetch(url,{headers:{'User-Agent':'PelicanMap-Collector/1.0'}});
if(!r.ok)throw Error('Original 720p track missing');
const bytes=Buffer.from(await r.arrayBuffer());
if(bytes.toString('ascii',4,8)!=='ftyp'||bytes.length>24*1024*1024)throw Error('Not a publishable original MP4 track');
const relative='/media/collected/2026-10-01-source-backfill/reddit-blaind0-pelicans-day-opus55-20260924-720p.mp4';
const file=path.join(ROOT,'pelican-web',relative.slice(1));
const sha256=crypto.createHash('sha256').update(bytes).digest('hex');
try{await fs.writeFile(file,bytes,{flag:'wx'});}catch(e){if(e.code!=='EEXIST')throw e;if(crypto.createHash('sha256').update(await fs.readFile(file)).digest('hex')!==sha256)throw Error('Refusing to replace original track');}
const additionsFile=path.join(ROOT,'site/additions.json');
const additions=JSON.parse(await fs.readFile(additionsFile,'utf8'));
const item=additions.find(x=>x.id==='reddit-blaind0-pelicans-day-opus55-2026-09-24');
const before={...item.media[0]};
Object.assign(item.media[0],{src:relative,source:url,sha256,caption:'作者标注 Opus 5.5 · 鹈鹕的一天 · Reddit 原始 720p 静音视频轨',captionEn:'Author-labelled Opus 5.5 · A pelican’s day · Original Reddit 720p silent video track'});
item.notes+=' 网站使用 Reddit 原始 720p 视频轨，1080p 原轨也在本地存档。';
item.i18n.en.notes+=' The website uses Reddit’s original 720p track; the 1080p track is also retained locally.';
await fs.writeFile(additionsFile,JSON.stringify(additions,null,2)+'\n');
await fs.writeFile(path.join(ROOT,'pelican-archive/research/2026-10-01-source-backfill/media-selection-correction.json'),JSON.stringify({id:item.id,before,after:item.media[0],reason:'Original 720p track fits the public asset limit without transcoding; original 1080p retained locally.'},null,2));
console.log(JSON.stringify({id:item.id,publicOriginalBytes:bytes.length,sha256}));
