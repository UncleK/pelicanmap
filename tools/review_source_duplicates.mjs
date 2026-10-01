// Read-only artwork comparison evidence: render known local SVGs, never scripts.
import fs from 'node:fs/promises';
import path from 'node:path';
import {createRequire} from 'node:module';
const require = createRequire(import.meta.url);
const sharp = require('sharp');
const root = path.resolve(import.meta.dirname, '..');
const {items} = JSON.parse(await fs.readFile(path.join(root, 'site/catalog.json'), 'utf8'));
const pairs = [];
const extra = process.argv.includes('--extra');
const june = process.argv.includes('--june');
const talk = process.argv.includes('--talk');
for (const model of ['claude-opus-5.5', 'fable-5.1']) {
  for (const effort of ['low','medium','high','xhigh','max']) {
    const a = items.find(x => x.originalId === `zoo:${model}-${effort}`);
    const stem = model === 'fable-5.1' ? 'claude-fable-5-1' : 'claude-opus-5-5';
    const b = items.find(x => x.id === `simon-grid-2026-09-22-${stem}-${effort}`);
    if (a && b) pairs.push([a,b]);
  }
}
if (extra) {
  pairs.length=0;
  for (const [originalId,stem] of [
    ['zoo:claude-fable-5.1-2026-09-16','claude-fable-5-1'],
    ['zoo:claude-opus-5-2026-09-16','claude-opus-5'],
    ['x-2072068898648949184','claude-sonnet-5']
  ]) {
    const old=items.find(x=>x.originalId===originalId);
    if (!old) throw new Error('Missing '+originalId);
    for (const effort of ['low','medium','high','xhigh','max']) {
      const crop=items.find(x=>x.id===`simon-grid-2026-09-22-${stem}-${effort}`);
      if(crop)pairs.push([old,crop]);
    }
  }
}
if (june) {
  pairs.length=0;
  const candidates=[
    ['amazon-nova-lite', /origin-us-amazon-nova-lite/],
    ['amazon-nova-micro', /origin-us-amazon-nova-micro/],
    ['amazon-nova-pro', /origin-us-amazon-nova-pro/],
    ['llama-3-3-70b', /zoo-pelican-bicycle-llama/],
    ['deepseek-r1', /zoo-r1-peli|x-1881421983994487214/],
    ['claude-3-7-sonnet', /zoo-pelican-claude-3-7/],
    ['gpt-4-5', /zoo-pelican-gpt45|x-1895210413148803551|x-1895212134885401013/],
    ['gemini-2-5-pro-2025-03', /zoo-gemini-2-5-pro-pelican|x-1904581889672753429|x-1904637065889014116/],
    ['gpt-4-1-2025-04', /zoo-gpt-4-1-pelican/],
    ['gemini-2-5-pro-preview-05-06', /x-simon-gemini25pro-2025-05-07/],
    ['o1-pro', /simon-source-1902509366244471291-o1-pro-high/]
  ];
  for(const [stem,pattern] of candidates) {
    const panel=items.find(x=>x.id.startsWith('simon-june-slides-'+stem));
    if(!panel)throw new Error('Missing June panel '+stem);
    for(const old of items.filter(x=>pattern.test(x.id)))pairs.push([old,panel]);
  }
}
if(talk){
  pairs.length=0;
  for(const [original,pattern] of [
    ['zoo:5-minutes-llms.017',/zoo-gemini-3-pelican-(low|high)/],
    ['zoo:5-minutes-llms.019',/gemma.*4.*26|gemma-4-pelican/],
    ['zoo:5-minutes-llms.025',/qwen.*3-6.*35|qwen36-35/]
  ]){
    const panel=items.find(x=>x.originalId===original);
    if(!panel)throw new Error('Missing '+original);
    for(const old of items.filter(x=>x.id!==panel.id && pattern.test(x.id) && x.media.length===1))pairs.push([old,panel]);
  }
}
const overlays = [];
for (let row=0;row<pairs.length;row++) {
  for (let col=0;col<2;col++) {
    const item=pairs[row][col];
    const src=item.media.find(x=>x.src.endsWith('.svg'))?.src || item.media[0].src;
    const input=path.join(root,'pelican-web',src.replace(/^\//,''));
    const png=await sharp(input).flatten({background:'#faf8f1'}).resize(440,250,{fit:'contain',background:'#faf8f1'}).png().toBuffer();
    overlays.push({input:png,left:col*460,top:row*280});
  }
}
const out=path.join(root,`deploy-build/source-duplicate-review${talk?'-talk':june?'-june':extra?'-extra':''}.png`);
await sharp({create:{width:920,height:pairs.length*280,channels:3,background:'#ddd8c8'}}).composite(overlays).png().toFile(out);
if(extra)for(let i=0;i<3;i++)await sharp(out).extract({left:0,top:i*1400,width:920,height:1400}).png().toFile(out.replace('.png',`-${i+1}.png`));
if(june)for(let i=0;i<Math.ceil(pairs.length/5);i++)await sharp(out).extract({left:0,top:i*1400,width:920,height:Math.min(1400,(pairs.length-i*5)*280)}).png().toFile(out.replace('.png',`-${i+1}.png`));
if(talk)for(let i=0;i<Math.ceil(pairs.length/5);i++)await sharp(out).extract({left:0,top:i*1400,width:920,height:Math.min(1400,(pairs.length-i*5)*280)}).png().toFile(out.replace('.png',`-${i+1}.png`));
console.log(JSON.stringify({image:out,rows:pairs.map(pair=>pair.map(x=>({id:x.id,date:x.date,source:x.sourceUrl,media:x.thumbnail})))}));
