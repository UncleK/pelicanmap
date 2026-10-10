import test from 'node:test';
import assert from 'node:assert/strict';
import {safeName,validateImageExtension,validateSvg,extractTranscriptSvg,extractHardPromptsSvg,validateCandidate,canonicalUrl,duplicateOf,makeRecord,faithfulCrop} from './import_collection_batch.mjs';
import sharp from 'sharp';
import {validateHlsSpec,verifyHlsTrack,verifyHlsMaster} from './reviewed_hls.mjs';

const sample=()=>({id:'test-pelican-2026-07-29',sourceUrl:'https://example.com/source',date:'2026-07-29',model:'Source-model-label',author:'Author',format:'svg',unitType:'single-model-output',modelToMediaVerified:true,generationMethod:'code-generated',codeGenerationEvidence:['https://example.com/source'],
  title:{zh:'真实输出',en:'Actual output'},notes:{zh:'按来源记录',en:'As attributed by the source'},rights:{zh:'权利归原作者',en:'Rights remain with the author'},
  evidence:['https://example.com/source'],media:[{url:'https://static.simonwillison.net/test.svg',filename:'test.svg',caption:{zh:'原始输出',en:'Original output'}}]});
const asset={src:'/media/collected/test/test.svg',source:'https://static.simonwillison.net/test.svg',sha256:'a'.repeat(64)};

test('faithful crops preserve exact source pixels and reject an altered source',async()=>{
  const original=await sharp({create:{width:30,height:20,channels:3,background:'#ff7722'}}).png().toBuffer();
  const {createHash}=await import('node:crypto');
  const sha256=createHash('sha256').update(original).digest('hex');
  const spec={sourceSha256:sha256,crop:{left:5,top:2,width:12,height:13}};
  const result=await faithfulCrop(original,spec);
  assert.deepEqual(result.box,[5,2,17,15]);
  assert.deepEqual(await sharp(result.bytes).raw().toBuffer(),await sharp(original).extract(spec.crop).raw().toBuffer());
  await assert.rejects(faithfulCrop(original,{...spec,sourceSha256:'0'.repeat(64)}),/source hash/);
  await assert.rejects(faithfulCrop(original,{...spec,crop:{left:25,top:2,width:12,height:13}}),/outside/);
  const candidate=sample();candidate.format='image';candidate.media=[{url:candidate.media[0].url,filename:'crop.png',crop:spec.crop,sourceSha256:sha256,sha256:'a'.repeat(64)}];
  assert.throws(()=>validateCandidate(candidate),/complete source/);
});

function reviewedHls() {
  const base='https://video.twimg.com/amplify_video/123456/';
  const part=url=>({url:base+url,sha256:'a'.repeat(64)});
  const hls={master:part('pl/master.m3u8'),video:{playlist:part('pl/avc1/video.m3u8'),init:part('vid/init.mp4'),segments:[part('vid/1.m4s'),part('vid/2.m4s')]},audio:{playlist:part('pl/mp4a/audio.m3u8'),init:part('aud/init.mp4'),segments:[part('aud/1.m4s')]}};
  const media={url:hls.master.url,filename:'original.mp4',sha256:'b'.repeat(64),hls};
  const evidence=[hls.master.url,...[hls.video,hls.audio].flatMap(t=>[t.playlist.url,t.init.url,...t.segments.map(x=>x.url)])];
  return {media,evidence};
}
const hlsMaster=Buffer.from('#EXTM3U\n#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="audio",URI="/amplify_video/123456/pl/mp4a/audio.m3u8"\n#EXT-X-STREAM-INF:BANDWIDTH=1234,AUDIO="audio"\n/amplify_video/123456/pl/avc1/video.m3u8\n');
const hlsVideo=Buffer.from('#EXTM3U\n#EXT-X-MAP:URI="/amplify_video/123456/vid/init.mp4"\n#EXTINF:1.0,\n/amplify_video/123456/vid/1.m4s\n#EXTINF:2.0,\n/amplify_video/123456/vid/2.m4s\n#EXT-X-ENDLIST\n');
test('reviewed HLS binds all hashed original parts to one public video and evidence',()=>{
  const {media,evidence}=reviewedHls();
  assert.doesNotThrow(()=>validateHlsSpec(media,evidence));
  assert.doesNotThrow(()=>validateCandidate({...sample(),format:'animation',evidence:[...sample().evidence,...evidence],media:[media]}));
  for(const change of [{filename:'../bad.mp4'},{filename:'init.webm'},{sha256:undefined},{url:'https://video.twimg.com/amplify_video/999/pl/master.m3u8'}])
    assert.throws(()=>validateHlsSpec({...media,...change},evidence));
  assert.throws(()=>validateHlsSpec(media,evidence.slice(1)));
  for(const url of ['http://video.twimg.com/amplify_video/123456/vid/1.m4s','https://evil.example/amplify_video/123456/vid/1.m4s','https://user:pass@video.twimg.com/amplify_video/123456/vid/1.m4s','https://video.twimg.com:444/amplify_video/123456/vid/1.m4s','https://video.twimg.com/amplify_video/999/vid/1.m4s']) {
    const copy=structuredClone(media);copy.hls.video.segments[0].url=url;
    assert.throws(()=>validateHlsSpec(copy,[...evidence,url]));
  }
  const empty=structuredClone(media);empty.hls.video.segments=[];
  assert.throws(()=>validateHlsSpec(empty,evidence));
});
test('HLS must include every ordered fragment and complete ENDLIST',()=>{
  const {media}=reviewedHls();
  assert.deepEqual(verifyHlsTrack(hlsVideo,media.hls.video),{duration:3,segments:2});
  for(const playlist of [hlsVideo.toString().replace('#EXT-X-ENDLIST',''),hlsVideo.toString().replace('vid/2.m4s','vid/3.m4s'),hlsVideo.toString().replace('#EXTINF:2.0,',''),hlsVideo.toString().replace('#EXTINF:1.0,','#EXTINF:NaN,'),hlsVideo.toString().replace('vid/init.mp4','vid/other.mp4')])
    assert.throws(()=>verifyHlsTrack(Buffer.from(playlist),media.hls.video));
  const reordered=structuredClone(media.hls.video);reordered.segments.reverse();
  assert.throws(()=>verifyHlsTrack(hlsVideo,reordered));
});
test('HLS rejects encryption, byte ranges, gaps, discontinuities and cross-video paths',()=>{
  const {media}=reviewedHls();
  for(const tag of ['#EXT-X-KEY:METHOD=AES-128,URI="secret"','#EXT-X-BYTERANGE:1@0','#EXT-X-GAP','#EXT-X-DISCONTINUITY','#EXT-X-PART:URI="partial.m4s"'])
    assert.throws(()=>verifyHlsTrack(Buffer.from(hlsVideo.toString().replace('#EXT-X-ENDLIST',tag+'\n#EXT-X-ENDLIST')),media.hls.video));
  assert.throws(()=>verifyHlsTrack(Buffer.from(hlsVideo.toString().replace('vid/1.m4s','../other/1.m4s')),media.hls.video));
  assert.throws(()=>verifyHlsTrack(Buffer.from(hlsVideo.toString().replace('123456/vid/1.m4s','777/vid/1.m4s')),media.hls.video));
});
test('HLS master associates exact video and audio rather than guessed URLs',()=>{
  const {media}=reviewedHls();
  assert.doesNotThrow(()=>verifyHlsMaster(hlsMaster,media.hls));
  const missing=structuredClone(media.hls);delete missing.audio;
  assert.throws(()=>verifyHlsMaster(hlsMaster,missing));
  const wrong=structuredClone(media.hls);wrong.audio.playlist.url=wrong.audio.playlist.url.replace('audio.m3u8','other.m3u8');
  assert.throws(()=>verifyHlsMaster(hlsMaster,wrong));
  assert.throws(()=>verifyHlsMaster(Buffer.from(hlsMaster.toString().replace('video.m3u8','other.m3u8')),media.hls));
});

test('intake requires source-reviewed code generation, not a media-type guess',()=>{
  for(const change of [{generationMethod:undefined},{generationMethod:'direct-text-to-video'},
    {codeGenerationEvidence:[]},{codeGenerationEvidence:['file:///private']},{model:'Veo 2'},{model:'Sora'}])
    assert.throws(()=>validateCandidate({...sample(),...change}));
  const record=makeRecord(sample(),[asset],'2026-10-03');
  assert.equal(record.generationMethod,'code-generated');
  assert.deepEqual(record.codeGenerationEvidence,sample().codeGenerationEvidence);
});

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

test('historical repository previews require pinned provenance and raster hashes',()=>{
  const sourceUrl='https://github.com/denamwangi/pelicans',url='https://github.com/user-attachments/assets/1da8d4fd-478f-4be2-a707-61be7ea695a1';
  const c={...sample(),sourceUrl,evidence:[sourceUrl,url,sourceUrl+'/commit/'+'a'.repeat(40)],media:[{url,filename:'preview.png',sha256:'b'.repeat(64)}]};
  assert.doesNotThrow(()=>validateCandidate(c));
  for(const change of [{sourceUrl:'https://example.com/source'},{evidence:[sourceUrl,url]},
    {media:[{...c.media[0],sha256:undefined}]},{media:[{...c.media[0],filename:'code.svg'}]},
    {media:[{...c.media[0],url:'https://github.com/denamwangi/pelicans/archive/main.zip'}]}])assert.throws(()=>validateCandidate({...c,...change}));
});

test('historical author PNG intake does not authorize arbitrary hosts or code mirrors',()=>{
  const sourceUrl='https://nezhar.com/blog/gpt-5-model-price-comparison-via-pelicans-on-bicycle/',url='https://nezhar.com/images/gpt-5-pelicans.png';
  const c={...sample(),sourceUrl,evidence:[sourceUrl,url],media:[{url,filename:'preview.png',sha256:'c'.repeat(64)}]};
  assert.doesNotThrow(()=>validateCandidate(c));
  for(const change of [{sourceUrl:'https://nezhar.com/'},{evidence:[sourceUrl]},
    {media:[{...c.media[0],url:'https://nezhar.com/images/pelican-gpt-5.svg',filename:'code.svg'}]},
    {media:[{...c.media[0],sha256:undefined}]}])assert.throws(()=>validateCandidate({...c,...change}));
});

test('provisional model positions never become imported artwork dates or release facts',()=>{
  for(const change of [{modelTimeline:{releaseDate:'2026-07-29'}},{modelSortDate:'2026-07'},{modelReleaseDate:'2026-07-29'},{dateBasis:'model-position'},{dateBasis:'estimated-model-release'}])assert.throws(()=>validateCandidate({...sample(),...change}));
  const record=makeRecord(sample(),[asset],'2026-10-02');
  assert.equal(record.date,sample().date);
  assert.equal(record.model,sample().model);
  assert.equal(record.sourceUrl,sample().sourceUrl);
  assert.equal(record.modelTimeline,undefined);
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

test('Gist preview attachments retain original bytes and need reviewed source plus hash',()=>{
  const sourceUrl='https://gist.github.com/SerJaimeLannister/f6de26bd0d0817e0563e8c1398eac655';
  const url='https://gist.github.com/user-attachments/assets/fcd1c614-fa9e-46e6-be8b-fac31d2867e0';
  const c={...sample(),sourceUrl,format:'image',evidence:[sourceUrl,url],media:[{url,filename:'preview.png',sha256:'a'.repeat(64)}]};
  assert.doesNotThrow(()=>validateCandidate(c));
  for(const change of [{sourceUrl:'https://example.com/repost'},{evidence:[sourceUrl]},
    {media:[{...c.media[0],sha256:undefined}]},{media:[{...c.media[0],filename:'preview.svg'}]},
    {media:[{...c.media[0],url:'https://gist.github.com/SerJaimeLannister/raw/preview.png'}]}])assert.throws(()=>validateCandidate({...c,...change}));
});

test('author-hosted DiffusionGemma preview is not a blanket download-host permission',()=>{
  const sourceUrl='https://gist.github.com/peterc/7672e74ec1437945e5fca5ce2c1c95a8';
  const url='https://peterc.org/misc/pelican.png';
  const c={...sample(),sourceUrl,format:'image',evidence:[sourceUrl,url],media:[{url,filename:'preview.png',sha256:'a'.repeat(64)}]};
  assert.doesNotThrow(()=>validateCandidate(c));
  for(const change of [{sourceUrl:'https://example.com/repost'},{evidence:[sourceUrl]},
    {media:[{...c.media[0],sha256:undefined}]},{media:[{...c.media[0],url:'https://peterc.org/misc/other.png'}]}])assert.throws(()=>validateCandidate({...c,...change}));
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
