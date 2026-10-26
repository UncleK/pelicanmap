// Explicitly reviewed comparisons; this is not a general media execution API.
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {cropPath} from './reviewed_video_crop.mjs';

const digest=b=>crypto.createHash('sha256').update(b).digest('hex');
export const PANELS={
  'https://x.com/chetaslua/status/2113503273361777086':{
    url:'https://video.twimg.com/amplify_video/2113502609416036352/vid/avc1/848x480/BgL8fXrUzL96hdQz.mp4?tag=29',
    sha256:'b41cb1175ead9b1f82a236325ef1e405dd5d022ed164639607e5fe801b9434e5',
    width:848,height:480,frames:300,fps:30,
    boxes:[[0,0,424,480],[424,0,424,480]],ranges:[[0,300]]},
  'https://x.com/abhinavflac/status/2113218148837257546':{
    url:'https://video.twimg.com/amplify_video/2113218040074850304/vid/avc1/1080x1208/PJn2hSECRUcsA9M9.mp4?tag=29',
    sha256:'a184dddfecf8d335c455c13b551980c299898f7ce1f6c0677093ca6ff2d86532',
    width:1080,height:1208,frames:231,fps:30,
    boxes:[[0,0,1080,608],[0,608,1080,600]],ranges:[[0,231]]},
  'https://x.com/sakeroux/status/2112473098201284875':{
    url:'https://video.twimg.com/amplify_video/2112472766100520960/vid/avc1/1280x720/I7rrItn3X_wK41PE.mp4?tag=14',
    sha256:'efd624190f6962fcea0e6bff2384952bfeba7bcf16de8e4a6955548bed616c08',
    width:1280,height:720,frames:960,fps:30,
    boxes:[[0,0,640,360],[640,0,640,360],[0,360,640,360],[640,360,640,360]],ranges:[[0,360],[360,960]]},
  'https://x.com/AgentSpaceAI/status/2113012455894868375':{
    url:'https://video.twimg.com/amplify_video/2112853138575441920/vid/avc1/1080x1080/Ng_uZHpg7GqggdIY.mp4?tag=29',
    sha256:'4b7ea39781cfd9cf908b80e47dd572cf664e7cfcd9c58f43a948aac852c7f2e4',
    width:1080,height:1080,frames:1624,fps:60,
    boxes:[[0,0,540,1080],[540,0,540,1080]],ranges:[[0,1624]]}
};

export function validateVideoPanel(c,m,root){
  const spec=PANELS[c.sourceUrl],s=m.reviewedVideoPanel;
  if(!spec || !s || m.url!==spec.url || s.sourceSha256!==spec.sha256 ||
     c.format!=='animation' || m!==c.media[0] || m.detailOnly ||
     !c.evidence.includes(c.sourceUrl) || !c.evidence.includes(m.url) ||
     !/^[a-f0-9]{64}$/.test(m.sha256||'') || !m.filename.endsWith('.mp4') ||
     s.method!=='ffmpeg-skill/crop.py+cut.py:lossless-preserve-color' ||
     !spec.boxes.some(box=>JSON.stringify(box)===JSON.stringify(s.box)) ||
     !spec.ranges.some(range=>JSON.stringify(range)===JSON.stringify(s.frames)) ||
     ['crop','hls','browserCapture','svgFromHardPrompts','svgFromTranscript','reviewedVideoSegment','reviewedVideoCrop'].some(k=>m[k]!==undefined))
    throw Error('Panel extraction requires the exact reviewed source, panel and frame range');
  cropPath(root,s.sourcePath);cropPath(root,s.capturePath);
  if(s.sourcePath===s.capturePath || !c.media.slice(1).some(x=>x.detailOnly===true &&
    x.url===spec.url && x.sha256===spec.sha256 && !x.reviewedVideoPanel && !x.crop && !x.reviewedVideoSegment && !x.reviewedVideoCrop))
    throw Error('Panel extraction must retain the complete original recording');
}

function run(binary,args){
  const r=spawnSync(binary,args,{encoding:'utf8',windowsHide:true,maxBuffer:8*1024*1024,timeout:120000});
  if(r.status!==0 || r.stderr.trim())throw Error('Panel verification failed: '+(r.error?.message||r.stderr));
  return r.stdout;
}
async function checked(root,value){
  const file=await fs.realpath(cropPath(root,value)),base=await fs.realpath(path.resolve(root,'pelican-archive/research'));
  if(!file.startsWith(base+path.sep) || !(await fs.stat(file)).isFile())throw Error('Panel path escapes research');
  return file;
}
function probe(file){
  return JSON.parse(run('ffprobe',['-v','error','-show_entries','format=duration:stream=codec_type,width,height,avg_frame_rate,nb_frames,pix_fmt','-of','json',file]));
}
function hashes(file,filter){
  const args=['-v','error','-nostdin','-i',file,'-map','0:v:0'];
  if(filter)args.push('-vf',filter);
  args.push('-fps_mode','passthrough','-f','framehash','-hash','sha256','-');
  return run(process.env.PELICAN_FFMPEG||'ffmpeg',args).split(/\r?\n/).filter(x=>x && !x.startsWith('#')).map(x=>{
    const p=x.split(',').map(x=>x.trim());return {pts:Number(p[2]),duration:Number(p[3]),size:Number(p[4]),hash:p[5]};
  });
}
export async function readReviewedVideoPanel(m,original,root){
  const s=m.reviewedVideoPanel,spec=Object.values(PANELS).find(x=>x.url===m.url);
  if(!spec || digest(original)!==spec.sha256)throw Error('Panel remote source hash mismatch');
  const source=await checked(root,s.sourcePath),capture=await checked(root,s.capturePath);
  const bytes=await fs.readFile(capture);
  if(digest(await fs.readFile(source))!==spec.sha256 || digest(bytes)!==m.sha256)
    throw Error('Panel source/output bytes changed');
  const before=probe(source),after=probe(capture),v=after.streams.find(x=>x.codec_type==='video'),sv=before.streams.find(x=>x.codec_type==='video');
  const [left,top,width,height]=s.box,[start,end]=s.frames;
  if(sv.width!==spec.width || sv.height!==spec.height || Number(sv.nb_frames)!==spec.frames ||
     v.width!==width || v.height!==height || Number(v.nb_frames)!==end-start || v.pix_fmt!==sv.pix_fmt ||
     Math.abs(Number(after.format.duration)-(end-start)/spec.fps)>0.1)
    throw Error('Panel dimensions, duration or frame count changed');
  const expected=hashes(source,`trim=start_frame=${start}:end_frame=${end},crop=${width}:${height}:${left}:${top},setpts=PTS-STARTPTS`);
  const actual=hashes(capture);
  const normalize=rows=>rows.map(x=>({...x,pts:x.pts-rows[0].pts}));
  if(expected.length!==end-start || JSON.stringify(normalize(expected))!==JSON.stringify(normalize(actual)))
    throw Error('Panel decoded pixels or relative frame timing changed');
  return {bytes,extraction:{kind:'reviewed-video-panel',source:m.url,sourceSha256:spec.sha256,
    box:{left,top,width,height},startFrame:start,endFrame:end,sourceFrames:spec.frames,
    sourceFps:spec.fps,method:s.method,decodedFrames:actual.length,
    decodedFrameHashesSha256:digest(Buffer.from(JSON.stringify(normalize(actual))))}};
}
