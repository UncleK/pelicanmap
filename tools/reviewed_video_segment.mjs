// A reviewed temporal excerpt keeps its complete public recording separately.
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {spawnSync} from 'node:child_process';

export const SATURN_ARTICLE='https://www.techgogogo.com/2026/10/13/gemini-4-suspected-benchmark-report/';
export const SATURN_VIDEO='https://cdn.techgogogo.com/videos/gemini-4-suspected-benchmark-report.mp4';
const hash=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const validHash=value=>typeof value==='string' && /^[a-f0-9]{64}$/.test(value);

export function segmentPath(root,value){
  if(typeof value!=='string' || !/^pelican-archive\/research\/[a-zA-Z0-9_.\/-]+\.mp4$/.test(value) || value.includes('..'))
    throw Error('Reviewed segment paths must be relative MP4 files within pelican-archive/research');
  const file=path.resolve(root,value),base=path.resolve(root,'pelican-archive/research');
  const relative=path.relative(base,file);
  if(!relative || relative.startsWith('..') || path.isAbsolute(relative))throw Error('Reviewed segment path escapes research');
  return file;
}

export function validateVideoSegment(c,m,root){
  const s=m.reviewedVideoSegment;
  if(c.sourceUrl!==SATURN_ARTICLE || m.url!==SATURN_VIDEO || c.format!=='animation' ||
    !c.evidence.includes(SATURN_ARTICLE) || !c.evidence.includes(SATURN_VIDEO) || !m.filename.endsWith('.mp4') || !validHash(m.sha256))
    throw Error('Reviewed Saturn recording requires the exact article, original video URL, animation format and pinned hash');
  if(!s){
    if(m.detailOnly!==true || !c.media[0].reviewedVideoSegment ||
      m.sha256!==c.media[0].reviewedVideoSegment.sourceSha256)
      throw Error('Complete reviewed recording must be the hashed detailOnly source of the primary segment');
    return;
  }
  if(m!==c.media[0] || m.detailOnly || !validHash(s.sourceSha256) ||
    !['ffmpeg-skill/cut.py:copy','ffmpeg-skill/cut.py:accurate','ffmpeg-skill/cut.py:hybrid'].includes(s.method) ||
    ![s.start,s.end,s.sourceDuration].every(Number.isFinite) || s.start<0 || s.end<=s.start || s.end>s.sourceDuration ||
    ['crop','hls','browserCapture','svgFromHardPrompts','svgFromTranscript'].some(key=>m[key]!==undefined))
    throw Error('Invalid reviewed video segment bounds, method, hashes or mixed derivation');
  segmentPath(root,s.capturePath);segmentPath(root,s.sourcePath);
  if(s.capturePath===s.sourcePath || !c.media.slice(1).some(x=>x.url===m.url && x.sha256===s.sourceSha256 && x.detailOnly===true && !x.reviewedVideoSegment))
    throw Error('Reviewed segment must retain its complete original recording separately');
}

async function checkedFile(root,value){
  const file=segmentPath(root,value),real=await fs.realpath(file),base=await fs.realpath(path.resolve(root,'pelican-archive/research'));
  const rel=path.relative(base,real);
  if(!rel || rel.startsWith('..') || path.isAbsolute(rel) || !(await fs.stat(real)).isFile())throw Error('Reviewed segment file escapes research or is not a file');
  return real;
}

function probe(file){
  const result=spawnSync('ffprobe',['-v','error','-show_entries','format=duration:stream=codec_type,width,height,avg_frame_rate,channels,sample_rate','-of','json',file],{encoding:'utf8',windowsHide:true});
  if(result.status!==0)throw Error('Reviewed segment probe failed: '+result.stderr);
  const info=JSON.parse(result.stdout);
  if(!(Number(info.format?.duration)>0) || !info.streams?.some(x=>x.codec_type==='video'))throw Error('Reviewed recording has no valid video');
  return info;
}

export function verifySegmentMetadata(s,source,clip){
  if(Math.abs(Number(source.format.duration)-s.sourceDuration)>0.05 || Math.abs(Number(clip.format.duration)-(s.end-s.start))>0.05)
    throw Error('Reviewed segment duration does not match its source and selected interval');
  const shape=info=>info.streams.filter(x=>['video','audio'].includes(x.codec_type)).map(x=>
    x.codec_type==='video'?['video',x.width,x.height,x.avg_frame_rate]:['audio',x.channels,x.sample_rate]);
  if(JSON.stringify(shape(source))!==JSON.stringify(shape(clip)))throw Error('Reviewed segment must preserve source dimensions, frame rate and audio tracks');
}

export async function readReviewedVideoSegment(m,original,root){
  const s=m.reviewedVideoSegment;
  if(hash(original)!==s.sourceSha256)throw Error('Reviewed segment remote source hash mismatch');
  const sourceFile=await checkedFile(root,s.sourcePath),clipFile=await checkedFile(root,s.capturePath);
  if(hash(await fs.readFile(sourceFile))!==s.sourceSha256)throw Error('Reviewed segment local source hash mismatch');
  const bytes=await fs.readFile(clipFile);
  if(bytes.length<100 || bytes.length>100*1024*1024 || hash(bytes)!==m.sha256 || bytes.toString('ascii',4,8)!=='ftyp')
    throw Error('Reviewed segment bytes or hash mismatch');
  verifySegmentMetadata(s,probe(sourceFile),probe(clipFile));
  const decode=spawnSync(process.env.PELICAN_FFMPEG || 'ffmpeg',['-v','error','-i',clipFile,'-f','null','-'],{encoding:'utf8',windowsHide:true});
  if(decode.status!==0 || decode.stderr.trim())throw Error('Reviewed segment full decode failed: '+decode.stderr);
  return {bytes,extraction:{kind:'reviewed-video-segment',source:m.url,sourceSha256:s.sourceSha256,
    start:s.start,end:s.end,sourceDuration:s.sourceDuration,method:s.method,segmentSha256:m.sha256}};
}
