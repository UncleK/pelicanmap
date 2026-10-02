import test from 'node:test';
import assert from 'node:assert/strict';
import {safeName,validateImageExtension,validateSvg,extractTranscriptSvg,extractHardPromptsSvg,validateCandidate,canonicalUrl,duplicateOf,makeRecord} from './import_collection_batch.mjs';
import sharp from 'sharp';

const sample=()=>({id:'test-pelican-2026-07-29',sourceUrl:'https://example.com/source',date:'2026-07-29',model:'Source-model-label',author:'Author',format:'svg',unitType:'single-model-output',modelToMediaVerified:true,
  title:{zh:'真实输出',en:'Actual output'},notes:{zh:'按来源记录',en:'As attributed by the source'},rights:{zh:'权利归原作者',en:'Rights remain with the author'},
  evidence:['https://example.com/source'],media:[{url:'https://static.simonwillison.net/test.svg',filename:'test.svg',caption:{zh:'原始输出',en:'Original output'}}]});
const asset={src:'/media/collected/test/test.svg',source:'https://static.simonwillison.net/test.svg',sha256:'a'.repeat(64)};

test('files cannot escape the batch archive',()=>{
  assert.equal(safeName('model-sample-01.svg'),'model-sample-01.svg');
  for(const name of ['../test.svg','a/test.png','C:/test.png','.svg','test.html'])assert.throws(()=>safeName(name));
});
test('decoded image formats determine filenames, not CDN query hints',async()=>{
  const bytes=await sharp({create:{width:16,height:16,channels:3,background:'#168ab2'}}).png().toBuffer();
  const metadata=await sharp(bytes).metadata();
  assert.doesNotThrow(()=>validateImageExtension('reddit-preview.png',metadata));
  for(const filename of ['reddit-preview.webp','reddit-preview.jpg','reddit-preview.gif','reddit-preview.mp4'])assert.throws(()=>validateImageExtension(filename,metadata));
  assert.doesNotThrow(()=>validateImageExtension('source.JPG',{format:'jpeg'}));
  assert.doesNotThrow(()=>validateImageExtension('source.jpeg',{format:'jpeg'}));
  assert.doesNotThrow(()=>validateImageExtension('source.svg',{format:'svg'}));
});
test('only self-contained SVG drawings are accepted',()=>{
  const plain='<svg xmlns="http://www.w3.org/2000/svg"><defs><circle id="a"/></defs><use href="#a"/></svg>';
  assert.equal(validateSvg(Buffer.from(plain)),plain);
  for(const svg of ['<svg><script>alert(1)</script></svg>','<svg onload="f()"></svg>','<svg><image href="x"/></svg>','<svg><use href="https://evil.example/x"/></svg>','<!DOCTYPE svg><svg></svg>','<svg style="fill:url(https://evil.example/x)"></svg>','<svg>'])assert.throws(()=>validateSvg(Buffer.from(svg)));
});

test('static SVG extraction preserves the exact response, excluding reasoning examples',()=>{
  const svg='<svg xmlns="http://www.w3.org/2000/svg"><circle cx="20" cy="20" r="10"/></svg>';
  assert.equal(extractTranscriptSvg(Buffer.from('## Reasoning\n<svg></svg>\n## Response\n```svg\n'+svg+'\n```')).toString(),svg);
  for(const value of ['no drawing','<svg></svg><svg></svg>','<svg><animate/></svg>','<svg><script/></svg>'])assert.throws(()=>extractTranscriptSvg(Buffer.from(value)));
});
test('source checks, actual publication dates and bilingual metadata are mandatory',()=>{
  assert.doesNotThrow(()=>validateCandidate(sample()));
  for(const change of [{date:'2026-02-30'},{author:''},{model:''},{evidence:[]},{title:{zh:'仅中文'}},{media:[]},{media:[{url:'https://evil.example/a.svg',filename:'test.svg'}]}])assert.throws(()=>validateCandidate({...sample(),...change}));
});
test('forum uploads are limited to reviewed original images with pinned hashes',()=>{
  const url='https://cdn3.ldstatic.com/original/4X/f/6/5/'+'f'.repeat(40)+'.png';
  const c={...sample(),sourceUrl:'https://linux.do/t/topic/1244131/18',evidence:['https://linux.do/t/topic/1244131/18',url],media:[{url,filename:'forum.png',sha256:'a'.repeat(64)}]};
  assert.doesNotThrow(()=>validateCandidate(c));
  for(const change of [{sourceUrl:'https://example.com/claimed-source'},{evidence:[c.sourceUrl]},
    {media:[{...c.media[0],sha256:undefined}]},{media:[{...c.media[0],url:url.replace('/original/','/optimized/')}]}])assert.throws(()=>validateCandidate({...c,...change}));
});
test('source and media tracking links do not defeat deduplication',()=>{
  assert.equal(canonicalUrl('https://twitter.com/author/status/1?s=20'),'https://x.com/author/status/1');
  assert.equal(canonicalUrl('https://v.redd.it/a.mp4?source=fallback'),'https://v.redd.it/a.mp4');
  const old={id:'old',sourceUrl:'https://example.com/source',author:'Author',model:'Source-model-label',date:'2026-07-29',media:[asset]};
  assert.equal(duplicateOf(sample(),[asset],[old]),'old');
  assert.equal(duplicateOf({...sample(),sourceUrl:'https://example.com/repost'},[{...asset,source:'https://static.simonwillison.net/reupload.svg'}],[old]),'old');
  assert.equal(duplicateOf(sample(),[{...asset,sha256:'b'.repeat(64),source:'https://static.simonwillison.net/independent.svg'}],[old]),'');
});

test('raytracer archival accepts reviewed PNGs, not executable scene code',()=>{
  const sourceUrl='https://blog.nawaz.org/posts/2025/Oct/pelican-on-a-bike-raytracer-edition/';
  const url='https://blog.nawaz.org/images/pelican/opus4.png';
  const c={...sample(),sourceUrl,format:'3d',evidence:[sourceUrl,url],media:[{url,filename:'opus4.png',sha256:'a'.repeat(64)}]};
  assert.doesNotThrow(()=>validateCandidate(c));
  for(const change of [{sourceUrl:'https://example.com/repost'},{evidence:[sourceUrl]},
    {media:[{...c.media[0],sha256:undefined}]},{media:[{...c.media[0],url:url.replace('.png','.pov')}]},
    {media:[{...c.media[0],url:url.replace('/images/pelican/','/uploads/')}]}])assert.throws(()=>validateCandidate({...c,...change}));
});
test('ordinary imported outputs never become playable and preserve evidence',()=>{
  const r=makeRecord(sample(),[asset],'2026-10-01');
  assert.equal(r.kind,'timeline');assert.equal(r.demoUrl,'');assert.equal(r.date,'2026-07-29');
  assert.equal(r.thumbnail,asset.src);assert.equal(r.media[0].sha256,asset.sha256);
  assert.equal(r.media[0].captionEn,'Original output');
  assert.equal(r.i18n.en.title,'Actual output');assert.equal(r.ingestion.sourceChecked,true);
  assert.deepEqual(r.ingestion.evidence,sample().evidence);
});

test('single-output mapping and detail-only full originals are required',()=>{
  for (const change of [{format:'unclassified'},{unitType:'collection'},
    {modelToMediaVerified:false},{media:[...sample().media,...sample().media]}]) {
    assert.throws(()=>validateCandidate({...sample(),...change}));
  }
  assert.doesNotThrow(()=>validateCandidate({...sample(),media:[...sample().media,{...sample().media[0],detailOnly:true}]}));
  for(const svg of ['<svg><animateTransform/></svg>','<svg><set/></svg>',
    '<svg><style>@keyframes ride {}</style></svg>','<svg style="animation:ride 1s"></svg>']) {
    assert.throws(()=>validateSvg(Buffer.from(svg)));
  }
});

test('all dates and media classifications preserve one reviewed output, not a playable claim',()=>{
  for(const format of ['svg','image','animation','3d','game','video','audio','other']) {
    const c={...sample(),format,date:'2024-10-25'};
    assert.doesNotThrow(()=>validateCandidate(c));
    const record=makeRecord(c,[asset],'2026-10-01');
    assert.equal(record.format,format);assert.ok(record.formatLabel);
    assert.equal(record.demoUrl,'');assert.equal(record.reviewedModelNames.length,1);
  }
  const year={...sample(),date:'2024',datePrecision:'year',dateBasis:'source-described-year'};
  assert.doesNotThrow(()=>validateCandidate(year));
  assert.equal(makeRecord(year,[asset],'2026-10-01').datePrecision,'year');
  const animated=Buffer.from('<svg><circle r="10"><animate attributeName="r" from="1" to="10" dur="2s"/></circle></svg>');
  assert.doesNotThrow(()=>validateSvg(animated,{allowAnimation:true}));
  assert.equal(extractTranscriptSvg(animated,{allowAnimation:true}).toString(),animated.toString());
  assert.throws(()=>validateSvg(Buffer.from('<svg><script/></svg>'),{allowAnimation:true}));
  assert.throws(()=>validateCandidate({...sample(),media:[{...sample().media[0],allowAnimation:true}]}));
  assert.throws(()=>validateCandidate({...sample(),format:'video',media:[{...sample().media[0],frameTime:-1}]}));
});

test('documented month precision is accepted without inventing a day',()=>{
  const month={...sample(),date:'2025-03',datePrecision:'month',dateBasis:'source-described-month'};
  assert.doesNotThrow(()=>validateCandidate(month));
  assert.equal(makeRecord(month,[asset],'2026-10-01').date,'2025-03');
  for(const change of [{date:'2025-13'},{date:'2025-03',datePrecision:undefined},
    {date:'2025-03',dateBasis:'source-publication'},{date:'2025'}]) {
    assert.throws(()=>validateCandidate({...month,...change}));
  }
});

test('explicit response selection excludes earlier reasoning and other outputs',()=>{
  const first='<svg><circle r="4"/></svg>',second='<svg><rect width="5"/></svg>';
  const text=Buffer.from('## Reasoning\n<svg></svg>\n### Response:\n'+first+'\n## Prompt\nexample <svg></svg>\n## Response\n'+second);
  assert.equal(extractTranscriptSvg(text,{responseIndex:0}).toString(),first);
  assert.equal(extractTranscriptSvg(text,{responseIndex:1}).toString(),second);
  assert.throws(()=>extractTranscriptSvg(text,{responseIndex:2}));
  assert.throws(()=>extractTranscriptSvg(text,{responseIndex:0,svgIndex:1}));
});

test('Hard Prompts extracts only the reviewed model/run and decodes once',()=>{
  const panel=(model,run,svg)=>'<div class="iteration-content" data-model="'+model+'" data-iteration="'+run+'"><pre><code>'+svg+'</code></pre></div>';
  const page=Buffer.from(panel('gpt-5',1,'&lt;svg&gt;&lt;circle r="4"/&gt;&lt;/svg&gt;')+panel('gpt-5',2,'&lt;svg&gt;&lt;rect width="5"/&gt;&lt;/svg&gt;'));
  assert.equal(extractHardPromptsSvg(page,'gpt-5',2).toString(),'<svg><rect width="5"/></svg>');
  for(const [model,run] of [['gpt-5',3],['gpt-5.*',1],['gpt-5',0]])assert.throws(()=>extractHardPromptsSvg(page,model,run));
  const c={...sample(),model:'gpt-5',media:[{url:'https://hardprompts.ai/topics/pelican-bicycle-svg.html',filename:'gpt.svg',svgFromHardPrompts:true,sourceModel:'gpt-5',sourceRun:2,sha256:'a'.repeat(64)}]};
  assert.doesNotThrow(()=>validateCandidate(c));
  assert.throws(()=>validateCandidate({...c,media:[{...c.media[0],sourceModel:'grok-4'}]}));
  assert.throws(()=>validateCandidate({...c,media:[{...c.media[0],url:'https://hardprompts.ai/other.html'}]}));
});

test('one page or transcript URL does not merge different extracted outputs',()=>{
  const base={...asset,source:'https://hardprompts.ai/topics/pelican-bicycle-svg.html',extraction:{kind:'source-html-code',sourceSha256:'c'.repeat(64),model:'gpt-5',run:1}};
  const old={...sample(),id:'old',media:[base]};
  assert.equal(duplicateOf(sample(),[{...base,sha256:'b'.repeat(64),extraction:{...base.extraction,run:2}}],[old]),'');
  assert.equal(duplicateOf(sample(),[{...base,sha256:'b'.repeat(64),extraction:{...base.extraction,model:'grok-4'}}],[old]),'');
  assert.equal(duplicateOf(sample(),[{...base,sha256:'b'.repeat(64)}],[old]),'');
  assert.equal(duplicateOf(sample(),[base],[old]),'old');
  assert.equal(duplicateOf(sample(),[{...base,sha256:'b'.repeat(64)}],[{...old,media:[{...base,sha256:undefined}]}]),'old');
  assert.equal(duplicateOf(sample(),[{...base,sha256:'b'.repeat(64),extraction:undefined}],[old]),'');
});

test('a reused media URL with changed bytes is not the same dated work',()=>{
  const old={...sample(),id:'old',media:[asset]};
  assert.equal(duplicateOf({...sample(),date:'2026-07-30'},[{...asset,sha256:'b'.repeat(64)}],[old]),'');
});

test('source response timestamps are preserved without inventing a publication day',()=>{
  const c={...sample(),dateBasis:'source-reported-response-timestamp',sourceResponseTimestamp:'2026-07-29T12:00:00Z'};
  const record=makeRecord(c,[asset],'2026-10-01');
  assert.equal(record.dateBasis,c.dateBasis);
  assert.equal(record.sourceResponseTimestamp,c.sourceResponseTimestamp);
  assert.equal(record.sourcePublicationDate,undefined);
});
