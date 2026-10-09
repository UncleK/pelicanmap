// Import an explicitly reviewed batch. This is not an unattended web crawler.
// Preserve original assets, archive evidence, and never execute upstream code.
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {createRequire} from 'node:module';
import {spawnSync} from 'node:child_process';
import {pathToFileURL} from 'node:url';
import {validateHlsSpec,assembleReviewedHls} from './reviewed_hls.mjs';

export const ROOT = path.resolve(import.meta.dirname, '..');
const require = createRequire(import.meta.url);
const sharp = require('sharp');
const hosts = new Set(['static.simonwillison.net','raw.githubusercontent.com','gist.githubusercontent.com','gist.github.com','github.com','nezhar.com','peterc.org','huggingface.co','pbs.twimg.com','video.twimg.com','v.redd.it','i.redd.it','preview.redd.it','hardprompts.ai','cdn3.ldstatic.com','blog.nawaz.org']);
const digest = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const localized = value => typeof value === 'string' ? {zh:value,en:value} : value;

export function safeName(name) {
  if (!/^[a-zA-Z0-9][a-zA-Z0-9._-]*\.(?:svg|png|jpe?g|webp|gif|mp4|webm|mp3|m4a|wav|ogg|flac)$/i.test(name)) throw Error('Unsafe asset filename');
  return name;
}

export function validateImageExtension(filename, metadata) {
  const expected = {'.svg':'svg','.png':'png','.jpg':'jpeg','.jpeg':'jpeg','.webp':'webp','.gif':'gif'}[path.extname(filename).toLowerCase()];
  if (!expected || metadata.format !== expected) throw Error('Image bytes do not match filename: '+filename);
}

export function validateSvg(bytes,{allowAnimation=false}={}) {
  const text = bytes.toString('utf8');
  if (!/<svg\b[^>]*>[\s\S]*<\/svg>\s*$/i.test(text) || /<!DOCTYPE|<!ENTITY|<script\b|<foreignObject\b|\son\w+\s*=|<image\b|@import/i.test(text)) throw Error('Unsafe or incomplete SVG');
  if (!allowAnimation && /<(?:animate\w*|set)\b|@keyframes|\banimation\s*:/i.test(text)) throw Error('Animated SVG must be reviewed and labelled animation');
  for (const match of text.matchAll(/(?:href|src)\s*=\s*(['"])(.*?)\1/gi)) {
    if (!match[2].startsWith('#')) throw Error('External SVG reference');
  }
  for (const match of text.matchAll(/url\s*\((.*?)\)/gi)) {
    if (!match[1].trim().replace(/^['"]|['"]$/g,'').startsWith('#')) throw Error('External SVG style');
  }
  return text;
}

export function extractTranscriptSvg(bytes,selection={}) {
  const text=bytes.toString('utf8');
  const headings=[...text.matchAll(/^#{2,3} Response:?\s*$/gm)];
  let response=text;
  if(headings.length) {
    const index=selection.responseIndex ?? headings.length-1;
    if(!Number.isInteger(index) || index<0 || index>=headings.length)throw Error('Invalid reviewed response index');
    const start=headings[index].index+headings[index][0].length;
    const tail=text.slice(start),next=tail.search(/^#{1,3}\s+[^\n]+$/m);
    response=next<0?tail:tail.slice(0,next);
  } else if(selection.responseIndex!==undefined)throw Error('Selected response heading is missing');
  const blocks=[...response.matchAll(/<svg\b[\s\S]*?<\/svg\s*>/gi)];
  const svgIndex=selection.svgIndex ?? 0;
  if((selection.svgIndex===undefined && blocks.length!==1) || !Number.isInteger(svgIndex) || svgIndex<0 || svgIndex>=blocks.length)throw Error('Transcript must contain one complete reviewed response SVG');
  const svg=Buffer.from(blocks[svgIndex][0]);
  validateSvg(svg,{allowAnimation:selection.allowAnimation===true});
  return svg;
}

export function extractHardPromptsSvg(bytes,model,run) {
  if(!/^[a-z0-9.-]+$/.test(model) || !/^[1-9]\d*$/.test(String(run)))throw Error('Invalid reviewed Hard Prompts selector');
  const text=bytes.toString('utf8');
  const entries=[...text.matchAll(/<div\b[^>]*class="iteration-content"[^>]*>/g)];
  const matches=entries.filter(x=>new RegExp('data-model="'+model.replace(/[.]/g,'\\.')+'"').test(x[0]) && new RegExp('data-iteration="'+run+'"').test(x[0]));
  if(matches.length!==1)throw Error('Missing or ambiguous source model/run panel');
  const entry=matches[0],next=entries.find(x=>x.index>entry.index);
  const section=text.slice(entry.index,next?.index ?? text.length);
  const codes=[...section.matchAll(/<pre>\s*<code\b[^>]*>([\s\S]*?)<\/code>\s*<\/pre>/g)];
  if(codes.length!==1)throw Error('Missing or ambiguous published response code');
  const decoded=codes[0][1].replace(/&(#x[0-9a-f]+|#\d+|amp|lt|gt|quot|apos);/gi,(_,entity)=>{
    const known={amp:'&',lt:'<',gt:'>',quot:'"',apos:"'"};
    if(known[entity])return known[entity];
    return String.fromCodePoint(entity.startsWith('#x')?parseInt(entity.slice(2),16):parseInt(entity.slice(1),10));
  }).trim();
  return extractTranscriptSvg(Buffer.from(decoded));
}

export function validateCandidate(c) {
  if(c.generationMethod!=='code-generated' || /^(?:veo(?:[ -]?\d+(?:\.\d+)?)?|sora(?:[ -]?\d+(?:\.\d+)?)?)(?:\s|$)/i.test(c.model || ''))throw Error('Only source-reviewed LLM code-generated works; direct text-to-video is outside the collection scope');
  if(!c.codeGenerationEvidence?.length || !c.codeGenerationEvidence.every(x=>typeof x==='string' && x.startsWith('https://')))throw Error('Code-generation source evidence is required; media format alone is not evidence');
  for(const key of ['modelTimeline','modelSortDate','modelReleaseDate'])if(Object.hasOwn(c,key))throw Error('Model positions are derived centrally; keep release estimates out of artwork facts');
  if(['model-release','estimated-model-release','inferred-model-release','model-position','estimated-position'].includes(c.dateBasis))throw Error('A model position cannot be an artwork date');
  if (!/^[a-z0-9][a-z0-9-]+$/.test(c.id || '')) throw Error('Invalid case id');
  const monthOnly=/^\d{4}-(?:0[1-9]|1[0-2])$/.test(c.date || '') && c.datePrecision==='month' && c.dateBasis==='source-described-month';
  const yearOnly=/^\d{4}$/.test(c.date || '') && c.datePrecision==='year' && c.dateBasis==='source-described-year';
  const fullDay=/^\d{4}-\d{2}-\d{2}$/.test(c.date || '') && Number.isFinite(Date.parse(c.date+'T00:00:00Z')) && new Date(c.date+'T00:00:00Z').toISOString().slice(0,10)===c.date;
  if (!monthOnly && !yearOnly && !fullDay) throw Error('Invalid source date; documented months/years need explicit precision/evidence');
  if (new URL(c.sourceUrl).protocol !== 'https:' || !c.author || !c.model) throw Error('Missing provenance');
  for (const key of ['title','notes','rights']) {
    const value = localized(c[key]);
    if (!value?.zh || !value?.en) throw Error('Missing bilingual '+key);
  }
  if (!['svg','image','animation','3d','game','video','audio','other'].includes(c.format) || !c.media?.length) throw Error('Classify the actual output and provide reviewed media; unknown types use other');
  if(c.media.some(m=>m.allowAnimation===true) && c.format!=='animation')throw Error('Animated SVG must be labelled animation');
  if(c.unitType!=='single-model-output' || c.modelToMediaVerified!==true) throw Error('Review one model-to-output mapping before importing');
  if(c.media.length>1 && !c.media.slice(1).every(x=>x.detailOnly===true)) throw Error('Split comparison outputs; complete source images must be detailOnly');
  if (!c.evidence?.length || c.evidence.some(x=>!x.startsWith('https://'))) throw Error('Missing source-check evidence');
  for (const m of c.media) {
    safeName(m.filename);
    if(m.hls)validateHlsSpec(m,c.evidence);
    if (!hosts.has(new URL(m.url).hostname) || !m.url.startsWith('https://')) throw Error('Unreviewed media host');
    if(new URL(m.url).hostname==='github.com' &&
      (!/^https:\/\/github\.com\/[^/?#]+\/[^/?#]+(?:\/blob\/[a-f0-9]{40}\/README\.md)?$/.test(c.sourceUrl) ||
       !/^\/user-attachments\/assets\/[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}$/.test(new URL(m.url).pathname) ||
       !/\.(png|jpe?g|webp)$/i.test(m.filename) || !/^[a-f0-9]{64}$/.test(m.sha256||'') ||
       !c.evidence.includes(m.url) || !c.evidence.some(x=>/^https:\/\/github\.com\/[^/]+\/[^/]+\/(?:commit|blob)\/[a-f0-9]{40}(?:\/|$)/.test(x))))
      throw Error('Repository preview requires a pinned public source, original raster attachment and reviewed hash');
    if(new URL(m.url).hostname==='nezhar.com' &&
      (c.sourceUrl!=='https://nezhar.com/blog/gpt-5-model-price-comparison-via-pelicans-on-bicycle/' ||
       m.url!=='https://nezhar.com/images/gpt-5-pelicans.png' || !m.filename.endsWith('.png') ||
       !/^[a-f0-9]{64}$/.test(m.sha256||'') || !c.evidence.includes(m.url)))
      throw Error('Author preview requires the reviewed GPT-5 article, exact raster URL and pinned hash');
    if(new URL(m.url).hostname==='gist.github.com' &&
      (!/^https:\/\/gist\.github\.com\/[^/?#]+\/[a-f0-9]{32}(?:\?permalink_comment_id=\d+)?$/.test(c.sourceUrl) ||
       !/^\/user-attachments\/assets\/[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}$/.test(new URL(m.url).pathname) ||
       !m.filename.endsWith('.png') || !/^[a-f0-9]{64}$/.test(m.sha256||'') || !c.evidence.includes(m.url)))
      throw Error('Gist previews need a reviewed original Gist, published attachment and pinned PNG hash');
    if(new URL(m.url).hostname==='peterc.org' &&
      (c.sourceUrl!=='https://gist.github.com/peterc/7672e74ec1437945e5fca5ce2c1c95a8' ||
       m.url!=='https://peterc.org/misc/pelican.png' || !m.filename.endsWith('.png') ||
       !/^[a-f0-9]{64}$/.test(m.sha256||'') || !c.evidence.includes(m.url)))
      throw Error('Author preview needs the reviewed DiffusionGemma Gist, exact image URL and pinned PNG hash');
    if(new URL(m.url).hostname==='cdn3.ldstatic.com' &&
      (!/^https:\/\/linux\.do\/t\/topic\/\d+(?:\/\d+)?$/.test(c.sourceUrl) ||
       !/^\/original\/4X\/[a-f0-9]\/[a-f0-9]\/[a-f0-9]\/[a-f0-9]{40}\.(png|jpe?g|webp|gif)$/.test(new URL(m.url).pathname) ||
       !/^[a-f0-9]{64}$/.test(m.sha256||'') || !c.evidence.includes(m.url)))
      throw Error('Forum media needs a reviewed topic, original upload, source link and pinned hash');
    if(new URL(m.url).hostname==='gist.githubusercontent.com' && !/^\/[^/]+\/[a-f0-9]{32}\/raw\/[a-f0-9]{40}\//.test(new URL(m.url).pathname))throw Error('Gist media needs a pinned version');
    if(new URL(m.url).hostname==='blog.nawaz.org' &&
      (c.sourceUrl!=='https://blog.nawaz.org/posts/2025/Oct/pelican-on-a-bike-raytracer-edition/' ||
       !/^\/images\/pelican\/[a-z0-9.-]+\.png$/.test(new URL(m.url).pathname) ||
       !/^[a-f0-9]{64}$/.test(m.sha256||'') || !c.evidence.includes(m.url)))
      throw Error('Raytracer media needs the reviewed original article, image path, source link and pinned hash');
    if(m.svgFromTranscript && !m.filename.endsWith('.svg'))throw Error('Transcript extraction must produce an SVG');
    if(new URL(m.url).hostname==='hardprompts.ai' && (!/^\/topics\/pelican-bicycle-svg(?:\.html)?$/.test(new URL(m.url).pathname) || !m.svgFromHardPrompts || !/^[a-f0-9]{64}$/.test(m.sha256 || '') || m.sourceModel!==c.model || !/^[1-9]\d*$/.test(String(m.sourceRun))))throw Error('Hard Prompts requires an explicitly reviewed, hashed model/run panel');
    for(const key of ['responseIndex','svgIndex'])if(m[key]!==undefined && (!m.svgFromTranscript || !Number.isInteger(m[key]) || m[key]<0))throw Error('Invalid reviewed transcript selection');
    if(m.frameTime!==undefined && (!Number.isFinite(m.frameTime) || m.frameTime<0 || !/\.(mp4|webm)$/i.test(m.filename)))throw Error('Invalid reviewed video frame time');
  }
}

export function canonicalUrl(url) {
  const u = new URL(url);
  if (['twitter.com','www.twitter.com','www.x.com'].includes(u.hostname)) u.hostname='x.com';
  for (const name of ['s','t','source','utm_source','utm_medium','utm_campaign']) u.searchParams.delete(name);
  u.hash='';
  return u.href.replace(/\/$/,'');
}

export function duplicateOf(c, assets, existing) {
  const sameAsset=(a,m)=>{
    if(m.sha256 && a.sha256)return m.sha256===a.sha256;
    if(!m.source || canonicalUrl(m.source)!==canonicalUrl(a.source))return false;
    // A source page/transcript may publish many independent outputs. Its URL
    // is not an image identity; compare the reviewed extraction selector.
    if(a.extraction || m.extraction) {
      if(!a.extraction || !m.extraction || a.extraction.kind!==m.extraction.kind)return false;
      if(a.extraction.kind==='source-html-code')return a.extraction.model===m.extraction.model && String(a.extraction.run)===String(m.extraction.run) && a.extraction.sourceSha256===m.extraction.sourceSha256;
      return a.extraction.responseIndex===m.extraction.responseIndex && a.extraction.svgIndex===m.extraction.svgIndex && a.extraction.sourceSha256===m.extraction.sourceSha256;
    }
    return true;
  };
  for (const x of existing) {
    if (x.id===c.id) return x.id;
    if (assets.every(a=>(x.media || []).some(m=>sameAsset(a,m)))) return x.id;
  }
  return '';
}

export function makeRecord(c, assets, updated) {
  validateCandidate(c);
  const title=localized(c.title),notes=localized(c.notes),rights=localized(c.rights);
  const media=assets.map((a,i)=>({src:a.src,source:a.source,sha256:a.sha256,...(a.extraction?{extraction:a.extraction}:{}),...(a.posterProvenance?{posterProvenance:a.posterProvenance}:{}),...(c.media[i].detailOnly?{detailOnly:true}:{}),caption:localized(c.media[i].caption || {zh:'原始输出',en:'Original output'}).zh,captionEn:localized(c.media[i].caption || {zh:'原始输出',en:'Original output'}).en,poster:a.poster || ''}));
  const recordPath='/specimens/'+c.id+'/';
  return {id:c.id,originalId:c.id,kind:'timeline',title:title.zh,model:c.model,author:c.author,date:c.date,month:c.date.slice(0,7),
    notes:notes.zh,source:'community',sourceLabel:'社区记录',sourceUrl:c.sourceUrl,format:c.format,
    formatLabel:{svg:'静态 SVG',image:'图像',animation:'动画','3d':'三维作品',game:'游戏 / 交互',video:'视频',audio:'音频',other:'其他媒体'}[c.format],originalForm:c.format,
    originalLevel:c.variant || '',promptCategory:c.promptCategory || 'classic',promptStatus:c.prompt || '来源未完整提供逐条提示词，请查看原始链接',dateBasis:c.dateBasis || 'source-publication',
    mediaStatus:'local',mediaNote:'',media,thumbnail:assets[0].poster || assets[0].src,demoUrl:'',externalUrl:c.externalUrl || '',sourceCodeUrl:c.sourceCodeUrl || '',
    path:recordPath,url:'https://pelicanmap.aveniqa.com'+recordPath,markdown:recordPath+'index.md',updated,rights:rights.zh,
    i18n:{en:{title:title.en,model:c.modelEn || c.model,notes:notes.en,rights:rights.en,promptStatus:c.prompt || 'The source does not provide the complete per-run prompt; see the original link',promptCategory:'Source-documented test'}},
    ingestion:{sourceChecked:true,imagesChecked:true,sourceVerification:'source-checked',evidence:c.evidence},
    unitType:c.unitType,reviewedModelNames:[c.model],modelClaimStatus:'source-reported-not-independently-authenticated',generationMethod:c.generationMethod,codeGenerationEvidence:c.codeGenerationEvidence,
    ...(c.datePrecision?{datePrecision:c.datePrecision}:{}),...(c.generationConditions?{generationConditions:c.generationConditions}:{}),
    ...(c.authorDefault===true?{authorDefault:true}:{}),
    ...(c.parentId?{parentId:c.parentId}:{}),...(c.representativeOf?{representativeOf:c.representativeOf}:{}),...(c.modelRunGroup?{modelRunGroup:c.modelRunGroup}:{}),
    ...(c.datasetSample ? {datasetSample:c.datasetSample}: {}),...(c.sourcePublicationDate ? {sourcePublicationDate:c.sourcePublicationDate}: {}),...(c.sourceResponseTimestamp?{sourceResponseTimestamp:c.sourceResponseTimestamp}:{})};
}

async function writeOriginal(file,bytes) {
  await fs.mkdir(path.dirname(file),{recursive:true});
  try {await fs.writeFile(file,bytes,{flag:'wx'});}
  catch(e) {if(e.code!=='EEXIST')throw e; if(digest(await fs.readFile(file))!==digest(bytes))throw Error('Refusing to replace original '+file);}
}

async function download(url) {
  if (!hosts.has(new URL(url).hostname)) throw Error('Unreviewed download host');
  const r=await fetch(url,{headers:{'User-Agent':'PelicanMap-Collector/1.0'},signal:AbortSignal.timeout(60000)});
  if(!r.ok)throw Error('Media HTTP '+r.status+' '+url+([401,403,429].includes(r.status)?' — use the authorized signed-in Chrome public read-only fallback; do not bypass challenges or execute upstream code':''));
  if(Number(r.headers.get('content-length'))>100*1024*1024)throw Error('Oversize media');
  const bytes=Buffer.from(await r.arrayBuffer());
  if(bytes.length<100 || bytes.length>100*1024*1024)throw Error('Invalid media size');
  return bytes;
}

async function archiveAsset(m,mediaDir,relativeDir,format,evidence) {
  const hls=m.hls ? await assembleReviewedHls(m,evidence,path.join(mediaDir,m.filename+'-hls')) : null;
  const original=hls ? hls.bytes : await download(m.url);
  const bytes=m.svgFromHardPrompts ? extractHardPromptsSvg(original,m.sourceModel,m.sourceRun) : m.svgFromTranscript ? extractTranscriptSvg(original,{...m,allowAnimation:format==='animation'}) : original,sha256=digest(bytes);
  if(m.sha256 && sha256!==m.sha256.toLowerCase())throw Error('Source hash mismatch');
  const file=path.join(mediaDir,safeName(m.filename));
  const ext=path.extname(file).toLowerCase();
  if(ext==='.svg')validateSvg(bytes,{allowAnimation:format==='animation'});
  let poster='',posterProvenance;
  if(['.mp4','.webm'].includes(ext)) {
    if(ext==='.mp4' && bytes.toString('ascii',4,8)!=='ftyp')throw Error('Not an MP4');
    await writeOriginal(file,bytes);
    const probe=spawnSync('ffprobe',['-v','error','-show_entries','format=duration:stream=codec_type,width,height','-of','json',file],{encoding:'utf8',windowsHide:true});
    if(probe.status!==0)throw Error('Invalid video '+probe.stderr);
    const info=JSON.parse(probe.stdout);
    if(!info.streams.some(x=>x.codec_type==='video' && x.width>10 && x.height>10) || !(Number(info.format.duration)>0))throw Error('Missing video track');
    let posterName=m.filename.replace(/\.[^.]+$/,'-poster.jpg'),posterFile=path.join(mediaDir,posterName);
    let savedPoster=false;
    if(m.frameTime!==undefined && m.frameTime>=Number(info.format.duration))throw Error('Reviewed frame is outside video duration');
    if(m.posterUrl && m.frameTime===undefined) {
      try{
        const preview=await download(m.posterUrl),previewMeta=await sharp(preview).metadata();
        if(!['png','jpeg','webp'].includes(previewMeta.format))throw Error('Upstream video preview must be a raster image');
        posterName=m.filename.replace(/\.[^.]+$/,'-poster.'+(previewMeta.format==='jpeg'?'jpg':previewMeta.format));
        posterFile=path.join(mediaDir,posterName);
        await writeOriginal(posterFile,preview);savedPoster=true;posterProvenance={kind:'upstream-preview',source:m.posterUrl};
      }
      catch(e){if(!e.message.startsWith('Media HTTP'))throw e;}
    }
    if(!savedPoster) {
      const ffmpeg=process.env.PELICAN_FFMPEG || 'ffmpeg';
      // A reviewed frame overrides an upstream blank opening poster. Never
      // overwrite an original or an earlier poster when rerunning a batch.
      try{await fs.access(posterFile);throw Error('Refusing to replace existing poster');}catch(e){if(e.code!=='ENOENT')throw e;}
      const frameTime=m.frameTime ?? Math.min(1,Number(info.format.duration)/2);
      const result=spawnSync(ffmpeg,['-v','error','-n','-ss',String(frameTime),'-i',file,'-frames:v','1','-vf','scale=960:-1',posterFile],{encoding:'utf8',windowsHide:true});
      if(result.status!==0)throw Error('Poster extraction failed '+result.stderr);
      posterProvenance={kind:'original-video-frame',source:m.url,sourceSha256:sha256,frameTime};
    }
    const metadata=await sharp(posterFile).metadata();
    validateImageExtension(posterName,metadata);
    const stats=await sharp(posterFile).stats();
    if(!metadata.width || !metadata.height || stats.channels.every(x=>x.stdev<0.5))throw Error('Blank or invalid video poster; review another real frame');
    posterProvenance.sha256=digest(await fs.readFile(posterFile));
    poster=relativeDir+'/'+posterName;
  } else if(['.mp3','.m4a','.wav','.ogg','.flac'].includes(ext)) {
    await writeOriginal(file,bytes);
    const probe=spawnSync('ffprobe',['-v','error','-show_entries','format=duration:stream=codec_type','-of','json',file],{encoding:'utf8',windowsHide:true});
    if(probe.status!==0)throw Error('Invalid audio '+probe.stderr);
    const info=JSON.parse(probe.stdout);
    if(!info.streams.some(x=>x.codec_type==='audio') || !(Number(info.format.duration)>0))throw Error('Missing audio track');
  } else {
    const image=sharp(bytes,{limitInputPixels:40000000});
    const meta=await image.metadata();
    validateImageExtension(m.filename,meta);
    let display=image;
    if(m.posterUrl) {
      const preview=await download(m.posterUrl),previewMeta=await sharp(preview).metadata();
      if(!['png','jpeg','webp'].includes(previewMeta.format))throw Error('Upstream preview must be a raster image');
      const posterName=m.filename.replace(/\.[^.]+$/,'-poster.'+(previewMeta.format==='jpeg'?'jpg':previewMeta.format));
      await writeOriginal(path.join(mediaDir,posterName),preview);
      poster=relativeDir+'/'+posterName;display=sharp(preview);
      posterProvenance={kind:'upstream-preview',source:m.posterUrl,sha256:digest(preview)};
    }
    const stats=await display.stats();
    if(!meta.width || !meta.height || meta.width<10 || meta.height<10 || stats.channels.every(x=>x.stdev<0.5))throw Error('Blank or invalid image');
    await writeOriginal(file,bytes);
  }
  const extraction=hls ? {...hls.extraction,sources:hls.extraction.sources.map(x=>({...x,src:relativeDir+'/'+m.filename+'-hls/'+x.filename}))} : m.svgFromHardPrompts?{kind:'source-html-code',sourceSha256:digest(original),model:m.sourceModel,run:m.sourceRun}:m.svgFromTranscript?{kind:'transcript-response',sourceSha256:digest(original),responseIndex:m.responseIndex ?? 'last',svgIndex:m.svgIndex ?? 0}:null;
  return {src:relativeDir+'/'+m.filename,source:m.url,sha256,poster,bytes:bytes.length,...(posterProvenance?{posterProvenance}:{}),...(extraction?{extraction}:{})};
}

export async function importBatch(manifestPath) {
  const manifest=JSON.parse(await fs.readFile(manifestPath,'utf8'));
  if(manifest.reviewed!==true || !/^[a-z0-9-]+$/.test(manifest.batch || ''))throw Error('Batch must be explicitly reviewed');
  const cases=manifest.cases;
  if(!Array.isArray(cases))throw Error('Missing reviewed cases');
  cases.forEach(validateCandidate);
  const additionsPath=path.join(ROOT,'site/additions.json');
  const additions=JSON.parse(await fs.readFile(additionsPath,'utf8'));
  const catalog=JSON.parse(await fs.readFile(path.join(ROOT,'site/catalog.json'),'utf8')).items;
  const existing=[...catalog,...additions];
  // Compare exact source bytes, not just source URLs; re-uploads are not new outputs.
  for(const x of existing)for(const m of x.media || []) {
    if(!m.sha256 && m.src.startsWith('/media/')) {
      try{m.sha256=digest(await fs.readFile(path.join(ROOT,'pelican-web',m.src.slice(1))));}catch(e){if(e.code!=='ENOENT')throw e;}
    }
  }
  const relativeDir='/media/collected/'+manifest.batch,mediaDir=path.join(ROOT,'pelican-web',relativeDir.slice(1));
  const policy=JSON.parse(await fs.readFile(path.join(ROOT,'site/collecting-policy.json'),'utf8'));
  const audit={batch:manifest.batch,checkedAt:new Date().toISOString(),policyVersion:policy.version,reviewer:'maintaining-agent',requiresPerBatchUserApproval:policy.publicationAuthority.requiresPerBatchUserApproval,modelPositionDerivation:'tools/model_chronology.py; never overwrite artwork date or verified release facts',before:catalog.length,added:[],duplicates:[],failed:[]};
  // Bounded concurrent archival; commit and deduplicate in manifest order.
  // Large batches have no artwork cap and do not race additions writes.
  const prepared=new Array(cases.length);
  let cursor=0;
  await Promise.all(Array.from({length:Math.min(4,cases.length)},async()=>{
    while(cursor<cases.length) {
      const index=cursor++,c=cases[index];
      if(existing.some(x=>x.id===c.id)){prepared[index]={existing:c.id};continue;}
      try {
        const assets=[];
        for(const m of c.media)assets.push(await archiveAsset(m,mediaDir,relativeDir,c.format,c.evidence));
        prepared[index]={assets};
      }catch(e){prepared[index]={error:e.message};}
    }
  }));
  for(const [index,c] of cases.entries()) {
    if(existing.some(x=>x.id===c.id)){audit.duplicates.push({id:c.id,existing:c.id});continue;}
    try {
      if(prepared[index].error)throw Error(prepared[index].error);
      const assets=prepared[index].assets;
      const duplicate=duplicateOf(c,assets,existing);
      if(duplicate){audit.duplicates.push({id:c.id,existing:duplicate});continue;}
      const collectedDate=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Shanghai'}).format(new Date());
      const record=makeRecord(c,assets,collectedDate);
      additions.push(record);existing.push(record);audit.added.push({id:c.id,sourceUrl:c.sourceUrl,assets});
    } catch(e){audit.failed.push({id:c.id,error:e.message});}
    if((audit.added.length+audit.duplicates.length+audit.failed.length)%20===0) console.log(JSON.stringify({processed:audit.added.length+audit.duplicates.length+audit.failed.length,total:cases.length}));
  }
  await fs.writeFile(additionsPath,JSON.stringify(additions,null,2)+'\n');
  const archiveDir=path.join(ROOT,'pelican-archive/research',manifest.batch);
  await fs.mkdir(archiveDir,{recursive:true});
  await writeOriginal(path.join(archiveDir,'reviewed-manifest.json'),Buffer.from(JSON.stringify(manifest,null,2)));
  await fs.writeFile(path.join(archiveDir,'import-audit.json'),JSON.stringify(audit,null,2)+'\n');
  await writeOriginal(path.join(archiveDir,'import-'+audit.checkedAt.replace(/[:.]/g,'-')+'.json'),Buffer.from(JSON.stringify(audit,null,2)));
  console.log(JSON.stringify({batch:audit.batch,added:audit.added.length,duplicates:audit.duplicates.length,failed:audit.failed,records:additions.length}));
  return audit;
}

if(process.argv[1] && import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href) {
  const audit=await importBatch(path.resolve(process.argv[2]));
  if(audit.failed.length)process.exitCode=1;
}
