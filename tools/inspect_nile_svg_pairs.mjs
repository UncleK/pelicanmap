// Analysis render only. Source bytes and museum media are never rewritten.
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {createRequire} from 'node:module';
import {extractTranscriptSvg} from './import_collection_batch.mjs';
const require=createRequire(import.meta.url);
const sharp=require('sharp');
const root=path.resolve(import.meta.dirname,'..');
const out=path.join(root,'pelican-archive/research/2026-10-01-nile-history');
const manifest=JSON.parse(await fs.readFile(path.join(out,'manifest.json'),'utf8'));
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const file=url=>path.join(out,'evidence',hash(Buffer.from(url)).slice(0,16)+'.bin');
const layers=[],rows=[];
for(const c of manifest.cases.filter(x=>x.media[0].svgFromTranscript)) {
  const svg=extractTranscriptSvg(await fs.readFile(file(c.media[0].url)),c.media[0]);
  const preview=await fs.readFile(file(c.reviewPreviewUrl));
  if(hash(svg)!==c.media[0].sha256)throw Error('Verbatim SVG hash differs');
  for(const [col,bytes] of [svg,preview].entries()) {
    layers.push({input:await sharp(bytes,{density:96}).flatten({background:'#fff'}).resize(360,250,{fit:'contain',background:'#fff'}).png().toBuffer(),left:col*380,top:rows.length*280});
    const label=col===0?'verbatim SVG':'published preview';
    layers.push({input:Buffer.from(`<svg width="380" height="30"><text x="4" y="12" font-size="10">${c.id}</text><text x="4" y="26" font-size="10">${label}</text></svg>`),left:col*380,top:rows.length*280+250});
  }
  rows.push({id:c.id,svgHash:hash(svg),previewHash:hash(preview)});
}
await sharp({create:{width:760,height:rows.length*280,channels:3,background:'#e8e6dc'}}).composite(layers).jpeg({quality:94}).toFile(path.join(out,'svg-preview-pairs.jpg'));
console.log(JSON.stringify(rows));
