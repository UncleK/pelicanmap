// Explicitly reviewed comparisons; this is not a general media execution API.
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {cropPath} from './reviewed_video_crop.mjs';

const digest=b=>crypto.createHash('sha256').update(b).digest('hex');
export const PANELS={
  "https://x.com/leo114119/status/2118344638583255484":{"url":"https://video.twimg.com/amplify_video/2118344212668461056/vid/avc1/1080x1504/exX-LzByM5MNCFoH.mp4?tag=29","sha256":"9defc5970bc354b8fb31ce14f42982578fa462bba368833a2a3e1960176eb6a3","width":1080,"height":1504,"frames":462,"fps":30,"boxes":[[0,0,1080,754],[0,762,1080,742]],"ranges":[[0,462]]},
  "https://x.com/noclipepe/status/2118102232780480804":{"url":"https://video.twimg.com/amplify_video/2118100251852615680/vid/avc1/1200x1200/y9VXW4s3SeSlN_c5.mp4?tag=29","sha256":"931c297f41c1d820da5753acb011f9f249fff0e02a71b004ea0c8bb17c5b1bf5","width":1200,"height":1200,"frames":858,"fps":30,"boxes":[[52,86,530,532],[616,86,530,532],[52,632,530,534],[616,632,530,534]],"ranges":[[30,90]]},
  "https://x.com/bangbuilds/status/2117994190667997406/video/1":{"url":"https://video.twimg.com/amplify_video/2117993451765841920/vid/avc1/1838x1080/Q1ovM12OsMvPoLRw.mp4?tag=29","sha256":"1bf79e7a77cf4e4bba8acc2fa2eb057360ffb2d2f92b07813e84c928096611a2","width":1838,"height":1080,"frames":383,"fps":30.0,"boxes":[[784,214,1024,696]],"ranges":[[0,383]]},
  "https://x.com/bangbuilds/status/2117994190667997406/video/2":{"url":"https://video.twimg.com/amplify_video/2117993467049893889/vid/avc1/1894x1080/ePas7zaxbOwiwKdn.mp4?tag=29","sha256":"adba0648ed3d6921619e7151cf4982ec3283fac65900e8587ad9ed9ea256a113","width":1894,"height":1080,"frames":311,"fps":30.0,"boxes":[[978,296,888,618]],"ranges":[[0,311]]},
  "https://x.com/xueyu1125/status/2117951147239682360":{"url":"https://video.twimg.com/amplify_video/2117950927961485312/vid/avc1/1326x1068/TnBMnA7Xk_2Eiu7C.mp4?tag=29","sha256":"d4d0062beabf95f62dfb3da6c3ef7aa01764d1668aad91dfda4900a93d135506","width":1326,"height":1068,"frames":586,"fps":30.0,"boxes":[[0,0,674,440],[714,0,612,440],[0,554,680,400],[716,554,610,400]],"ranges":[[0,586]]},
  "https://x.com/china_stonerao/status/2117198598073192595":{"url":"https://video.twimg.com/amplify_video/2117198391939932160/vid/avc1/856x720/XYVvdVBQ9_JQXhzR.mp4?tag=14","sha256":"e3fffddcac14bc4552f8904d5f8c192c068e178ec51e35a89ce5f768cf23525a","width":856,"height":720,"frames":176,"fps":30,"boxes":[[0,0,428,360],[428,0,428,360],[0,360,428,360],[428,360,428,360]],"ranges":[[0,176]]},
  "https://x.com/Delroy715/status/2117259793669013728":{"url":"https://video.twimg.com/amplify_video/2117259526965698560/vid/avc1/1920x1080/2QuoHZ1j3lpx2m_9.mp4?tag=29","sha256":"ea3fad0005d4ce3dc7c030d67312dad5bf0463011173dceb5a2857c9cbe2a335","width":1920,"height":1080,"frames":300,"fps":30,"boxes":[[0,212,960,540]],"ranges":[[0,300]]},
  "https://x.com/evals_ag/status/2117148447983935908":{"url":"https://video.twimg.com/amplify_video/2117148361501626368/vid/avc1/1920x1080/xBKEuVpHiPbwuLY9.mp4?tag=29","sha256":"7f76bdce39da9094722548ee4c1de03edcf13e708f0347bc2ff75849480557d4","width":1920,"height":1080,"frames":360,"fps":30,"boxes":[[0,0,960,540],[960,0,960,540],[0,540,960,540],[960,540,960,540]],"ranges":[[0,360]]},
  "https://x.com/evals_ag/status/2117160278395936772":{"url":"https://video.twimg.com/amplify_video/2117159971846844416/vid/avc1/1920x1080/NsCgB1-uuhUy9UAV.mp4?tag=29","sha256":"b3be887e7cab11f2598d7c7a1c2978940551f144b90b6cc84201474b80213cd3","width":1920,"height":1080,"frames":360,"fps":30,"boxes":[[0,0,960,540],[960,0,960,540],[0,540,960,540],[960,540,960,540]],"ranges":[[0,360]]},
  "https://x.com/evals_ag/status/2117281079975711172":{"url":"https://video.twimg.com/amplify_video/2117280987050889217/vid/avc1/1920x1080/CsLtG1Jo-ZiSo-Z2.mp4?tag=29","sha256":"16af6bff38edb9b7b13a7dece26480067be72e3c91eaf39f0e0c0c8bb0d59e64","width":1920,"height":1080,"frames":360,"fps":30,"boxes":[[0,0,960,540],[960,0,960,540],[0,540,960,540],[960,540,960,540]],"ranges":[[0,360]]},
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
    boxes:[[0,0,540,1080],[540,0,540,1080]],ranges:[[0,1624]]},
  "https://x.com/xiangxiang103/status/2114902354449547443":{"url":"https://video.twimg.com/amplify_video/2114902215869747200/vid/avc1/1550x1296/wn1-5wRNiVnuA6Cb.mp4?tag=29","sha256":"52603f854e693567feb7f469fa97ec7f126e6411830bafb63ec00c439585465f","width":1550,"height":1296,"frames":384,"fps":24,"boxes":[[40,188,720,480],[790,188,720,480],[40,776,720,480],[790,776,720,480]],"ranges":[[0,384]]},
  "https://x.com/hiwise_aigc/status/2115130734944129251":{"url":"https://video.twimg.com/amplify_video/2115129317734916096/vid/avc1/1080x1920/kqjwczlAxE6FAW6S.mp4?tag=29","sha256":"b3ac84df65eff412af8f07e14a1c75945b19b3f57b262b52a1827937e1961041","width":1080,"height":1920,"frames":928,"fps":60,"boxes":[[0,288,1080,680],[0,1276,1080,644]],"ranges":[[0,928]]},
  "https://x.com/trypalomino/status/2115120801351627229":{"url":"https://video.twimg.com/amplify_video/2115120766144442368/vid/avc1/2160x2160/yTFKL3lOtbItEqyq.mp4?tag=29","sha256":"29add64d18c2dca65416dd7173150e091f12764c3b955996fdc19096bb75cff0","width":2160,"height":2160,"frames":360,"fps":30,"boxes":[[0,0,1080,1080],[1080,0,1080,1080],[0,1080,1080,1080],[1080,1080,1080,1080]],"ranges":[[0,360]]},
  "https://x.com/YxzRainy/status/2114972070996226190":{"url":"https://video.twimg.com/amplify_video/2114972041233543168/vid/avc1/1080x1440/Lc-YHQidf4H_6JsZ.mp4?tag=29","sha256":"002b4202fa22f31092bc55c2054a09edb12ba64e5b6755dbd0d3d3628a4b6a05","width":1080,"height":1440,"frames":414,"fps":60,"boxes":[[0,0,1080,720],[0,720,1080,720]],"ranges":[[0,414]]},
  "https://x.com/YxzRainy/status/2115048659343782307":{"url":"https://video.twimg.com/amplify_video/2115048557342490624/vid/avc1/1816x3228/KfU8HOtcPIYkR49I.mp4?tag=29","sha256":"866b6582d55c675ca610808a881a937ae534bce1d6249033ca83088302c1c2ae","width":1816,"height":3228,"frames":1657,"fps":60,"boxes":[[0,1076,1816,1076]],"ranges":[[0,1657]]},
  "https://x.com/gibbsfree8660/status/2114913998265061392":{"url":"https://video.twimg.com/tweet_video/HVmvBE3XwAAvMJb.mp4","sha256":"fb8ac4d544277b220bbc736d666d103e7964d3623a5e7ae02b9901334234e4dd","width":1200,"height":674,"frames":180,"fps":20,"boxes":[[104,270,396,190],[606,206,584,328]],"ranges":[[0,180]]}
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
