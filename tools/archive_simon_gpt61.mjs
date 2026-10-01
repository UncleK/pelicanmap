// Archive original published output and render static previews without executing it.
import fs from 'node:fs/promises';
import path from 'node:path';
import {createRequire} from 'node:module';
const require = createRequire(import.meta.url);
const sharp = require('sharp');
const root = path.resolve(import.meta.dirname, '..');
const headers = {'User-Agent':'PelicanMap-Maintainer/1.0'};
const response = await fetch('https://api.github.com/gists/4aa871683dae5c566129a6028fbc7f21', {headers});
if (!response.ok) throw Error(`Gist: ${response.status}`);
const gist = await response.json();
if (gist.owner.login !== 'simonw' || !gist.created_at.startsWith('2026-09-29')) throw Error('Unexpected provenance');
const archive = path.join(root,'deploy-build/research-simon-gpt61');
await fs.mkdir(archive,{recursive:true});
await fs.writeFile(path.join(archive,'gist.json'),JSON.stringify(gist,null,2));
const sections = gist.files['pelicans.md'].content.split(/(?=^# 2026-)/m).filter(x=>x.startsWith('# '));
const levels = [];
for (const section of sections) {
  if (!section.includes('Model: **gpt-6.1-sol**') || !section.includes('Generate an SVG of a pelican riding a bicycle')) throw Error('Unexpected model or prompt');
  const level = section.match(/^- reasoning_effort: (\w+)/m)?.[1];
  const svg = section.match(/```svg\s*\n([\s\S]*?)\n```/)?.[1];
  if (!['low','medium','high','xhigh','max'].includes(level) || !svg || /<script|<foreignObject|(?:href|src)\s*=\s*["']https?:/i.test(svg)) throw Error('Unsafe or missing output');
  await fs.writeFile(path.join(archive,`${level}.svg`),svg);
  const output = path.join(root,'pelican-web/media/recovered',`simon-gpt61-sol-${level}.png`);
  await sharp(Buffer.from(svg),{density:144}).resize({width:1200,withoutEnlargement:true}).png().toFile(output);
  levels.push({level,output,bytes:(await fs.stat(output)).size});
}
if (levels.length !== 5) throw Error('Missing reasoning levels');
console.log(JSON.stringify({source:gist.html_url,raw:gist.files['pelicans.md'].raw_url,levels}));
// Forum attachments remain original GIFs/JPEGs; make small first-frame card covers.
for (const name of ['linuxdo-noobiehwang-gpt61-high-01.gif','linuxdo-noobiehwang-gpt61-high-02.gif','linuxdo-boris20190-gpt61-xhigh.jpg']) {
  const file=path.join(root,'pelican-web/media/recovered',name);
  const metadata=await sharp(file).metadata();
  if (!metadata.width || !metadata.height) throw Error('Invalid forum attachment');
  await sharp(file).resize({width:960,withoutEnlargement:true}).webp({quality:86}).toFile(file.replace(/\.(gif|jpg)$/,'-cover.webp'));
  console.log(JSON.stringify({name,width:metadata.width,height:metadata.height,frames:metadata.pages||1}));
}
