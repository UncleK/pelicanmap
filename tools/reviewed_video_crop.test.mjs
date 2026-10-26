import test from 'node:test';
import assert from 'node:assert/strict';
import {validateCandidate,duplicateOf,ROOT} from './import_collection_batch.mjs';
import {COMPARISON_POST,COMPARISON_VIDEO,COMPARISON_SHA,DEEPSEEK_BOX,cropPath,verifyCropMetadata,readReviewedVideoCrop} from './reviewed_video_crop.mjs';

const sample=()=>({id:'test-deepseek-panel',sourceUrl:COMPARISON_POST,date:'2026-10-17',author:'Darren',model:'DeepSeek V4.1 Flash 1017',format:'animation',title:{zh:'鹈鹕',en:'Pelican'},notes:{zh:'网页录屏',en:'Web recording'},rights:{zh:'作者所有',en:'Creator owned'},generationMethod:'code-generated',codeGenerationEvidence:[COMPARISON_POST],unitType:'single-model-output',modelToMediaVerified:true,evidence:[COMPARISON_POST,COMPARISON_VIDEO],media:[{url:COMPARISON_VIDEO,filename:'panel.mp4',sha256:'a'.repeat(64),reviewedVideoCrop:{sourcePath:'pelican-archive/research/test/source.mp4',capturePath:'pelican-archive/research/test/crop.mp4',sourceSha256:COMPARISON_SHA,box:{...DEEPSEEK_BOX},method:'ffmpeg-skill/crop.py:lossless'}},{url:COMPARISON_VIDEO,filename:'complete.mp4',sha256:COMPARISON_SHA,detailOnly:true}]});

test('only the reviewed comparison and panel with a separate complete recording is allowed',()=>{
  assert.doesNotThrow(()=>validateCandidate(sample()));
  for(const mutate of [c=>c.sourceUrl+='?x=1',c=>c.format='video',c=>c.media.pop(),c=>c.media[0].url+='?x=1',c=>c.media[0].reviewedVideoCrop.box.left=0,c=>c.media[0].reviewedVideoCrop.box.width=638,c=>c.media[0].reviewedVideoCrop.sourceSha256='b'.repeat(64),c=>c.media[0].reviewedVideoCrop.method='invented',c=>c.media[1].sha256='b'.repeat(64),c=>c.media[0].browserCapture={}]){
    const c=sample();mutate(c);assert.throws(()=>validateCandidate(c));
  }
  for(const file of ['C:/source.mp4','pelican-archive/research/../source.mp4','pelican-archive/research-other/source.mp4'])assert.throws(()=>cropPath(ROOT,file));
});

test('crop metadata rejects missing frames, timing changes, audio or other source dimensions',()=>{
  const info=(w,h)=>({format:{duration:'5.000'},streams:[{codec_type:'video',width:w,height:h,avg_frame_rate:'20/1',nb_frames:'100',pix_fmt:'yuv420p'}]});
  const source=info(1280,864),crop=info(640,360);
  assert.doesNotThrow(()=>verifyCropMetadata(source,crop));
  for(const mutate of [x=>x.format.duration='4.95',x=>x.streams[0].nb_frames='99',x=>x.streams[0].avg_frame_rate='30/1',x=>x.streams[0].width=638,x=>x.streams.push({codec_type:'audio'}),x=>x.streams[0].pix_fmt='yuv444p']){
    const wrong=structuredClone(crop);mutate(wrong);assert.throws(()=>verifyCropMetadata(source,wrong));
  }
  assert.throws(()=>verifyCropMetadata(info(640,360),crop));
});

test('changed remote originals fail before local paths are opened',async()=>{
  await assert.rejects(readReviewedVideoCrop(sample().media[0],Buffer.from('changed source'),ROOT),/remote source hash/);
});

test('re-encoded copies of the same panel deduplicate while different panel selections do not',()=>{
  const a={source:COMPARISON_VIDEO,sha256:'a'.repeat(64),extraction:{kind:'reviewed-video-crop',sourceSha256:COMPARISON_SHA,box:{...DEEPSEEK_BOX}}};
  const b=structuredClone(a);b.sha256='b'.repeat(64);
  assert.equal(duplicateOf(sample(),[a],[{id:'prior-panel',media:[b]}]),'prior-panel');
  b.extraction.box.left=0;
  assert.equal(duplicateOf(sample(),[a],[{id:'other-panel',media:[b]}]),'');
});
