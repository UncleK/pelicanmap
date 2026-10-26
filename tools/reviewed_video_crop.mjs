// Only the reviewed DeepSeek panel of this public comparison is admitted.
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {spawnSync} from 'node:child_process';

export const COMPARISON_POST='https://x.com/dtzy_88/status/2111356355315646601';
export const COMPARISON_VIDEO='https://video.twimg.com/tweet_video/HU0KRrObcAAtlTO.mp4';
export const COMPARISON_SHA='dd522cf9c018ed2fe1ecd2654ab451914d92005ee4c5b1448b91e9000483c76b';
export const DEEPSEEK_BOX={left:640,top:504,width:640,height:360};
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const isHash=s=>typeof s==='string' && /^[a-f0-9]{64}$/.test(s);
const sameBox=(a,b)=>['left','top','width','height'].every(k=>a?.[k]===b[k]);

export function cropPath(root,value){
  if(typeof value!=='string' || !/^pelican-archive\/research\/[a-zA-Z0-9_.\/-]+\.mp4$/.test(value) || value.includes('..'))
    throw Error('Reviewed crop must be an MP4 within research');
  const file=path.resolve(root,value),rel=path.relative(path.resolve(root,'pelican-archive/research'),file);
  if(!rel || rel.startsWith('..') || path.isAbsolute(rel))throw Error('Reviewed crop path escapes research');
  return file;
}

export function validateVideoCrop(c,m,root){
  const s=m.reviewedVideoCrop;
  if(c.sourceUrl!==COMPARISON_POST || m.url!==COMPARISON_VIDEO || c.format!=='animation' ||
     !c.evidence.includes(COMPARISON_POST) || !c.evidence.includes(COMPARISON_VIDEO) ||
     m!==c.media[0] || m.detailOnly || !m.filename.endsWith('.mp4') || !isHash(m.sha256) ||
     !s || s.sourceSha256!==COMPARISON_SHA || s.method!=='ffmpeg-skill/crop.py:lossless' ||
     !sameBox(s.box,DEEPSEEK_BOX) ||
     ['crop','hls','browserCapture','svgFromHardPrompts','svgFromTranscript','reviewedVideoSegment'].some(k=>m[k]!==undefined))
    throw Error('Video crop requires the exact reviewed comparison and DeepSeek panel');
  cropPath(root,s.sourcePath);cropPath(root,s.capturePath);
  if(s.capturePath===s.sourcePath || !c.media.slice(1).some(x=>x.url===m.url && x.sha256===s.sourceSha256 &&
      x.detailOnly===true && !x.reviewedVideoCrop && !x.reviewedVideoSegment && !x.crop))
    throw Error('Reviewed video crop must retain its complete original comparison');
}

async function checkedPath(root,value){
  const file=await fs.realpath(cropPath(root,value)),base=await fs.realpath(path.resolve(root,'pelican-archive/research'));
  const rel=path.relative(base,file);
  if(!rel || rel.startsWith('..') || path.isAbsolute(rel) || !(await fs.stat(file)).isFile())
    throw Error('Reviewed crop resolves outside research or is not a file');
  return file;
}

function run(binary,args){
  const r=spawnSync(binary,args,{encoding:'utf8',windowsHide:true,maxBuffer:4*1024*1024,timeout:60000});
  if(r.status!==0 || r.stderr.trim())throw Error('Video crop verification failed: '+(r.error?.message || r.stderr));
  return r.stdout;
}

function probe(file){
  return JSON.parse(run('ffprobe',['-v','error','-show_entries','format=duration:stream=codec_type,width,height,avg_frame_rate,nb_frames,pix_fmt','-of','json',file]));
}

export function verifyCropMetadata(source,crop){
  const shape=(info,w,h)=>info.streams?.length===1 && info.streams[0].codec_type==='video' &&
    info.streams[0].width===w && info.streams[0].height===h && info.streams[0].avg_frame_rate==='20/1' &&
    Number(info.streams[0].nb_frames)===100 && info.streams[0].pix_fmt==='yuv420p' && Number(info.format?.duration)===5;
  if(!shape(source,1280,864) || !shape(crop,640,360))
    throw Error('Video crop must retain all 100 frames, timing and pixel format of the reviewed silent recording');
}

function frameHashes(file,box){
  // Read-only decoded-pixel evidence; this does not render or alter a file.
  const args=['-v','error','-nostdin','-i',file,'-map','0:v:0'];
  if(box)args.push('-vf',`crop=${box.width}:${box.height}:${box.left}:${box.top}`);
  args.push('-f','framehash','-hash','sha256','-');
  return run(process.env.PELICAN_FFMPEG || 'ffmpeg',args).split(/\r?\n/).filter(x=>x && !x.startsWith('#')).map(x=>x.trim());
}

export async function readReviewedVideoCrop(m,original,root){
  const s=m.reviewedVideoCrop;
  if(hash(original)!==COMPARISON_SHA || s.sourceSha256!==COMPARISON_SHA)throw Error('Video crop remote source hash mismatch');
  const source=await checkedPath(root,s.sourcePath),crop=await checkedPath(root,s.capturePath);
  if(hash(await fs.readFile(source))!==COMPARISON_SHA)throw Error('Video crop local source hash mismatch');
  const bytes=await fs.readFile(crop);
  if(bytes.length<100 || bytes.length>100*1024*1024 || hash(bytes)!==m.sha256 || bytes.toString('ascii',4,8)!=='ftyp')
    throw Error('Video crop output bytes/hash mismatch');
  verifyCropMetadata(probe(source),probe(crop));
  const expected=frameHashes(source,DEEPSEEK_BOX),actual=frameHashes(crop);
  if(expected.length!==100 || JSON.stringify(expected)!==JSON.stringify(actual))
    throw Error('Video crop changed decoded pixels, frames or timing');
  return {bytes,extraction:{kind:'reviewed-video-crop',source:m.url,sourceSha256:COMPARISON_SHA,
    box:DEEPSEEK_BOX,method:s.method,decodedFrames:100,decodedFrameHashesSha256:hash(Buffer.from(actual.join('\n')))}};
}
