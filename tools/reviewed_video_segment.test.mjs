import test from 'node:test';
import assert from 'node:assert/strict';
import {validateCandidate,duplicateOf,makeRecord,ROOT} from './import_collection_batch.mjs';
import {SATURN_ARTICLE,SATURN_VIDEO,segmentPath,verifySegmentMetadata,readReviewedVideoSegment} from './reviewed_video_segment.mjs';

const sample=()=>({id:'test-saturn-2026-10-13',sourceUrl:SATURN_ARTICLE,date:'2026-10-13',model:'Gemini 4 (suspected routing)',author:'Publisher',format:'animation',unitType:'single-model-output',modelToMediaVerified:true,generationMethod:'code-generated',codeGenerationEvidence:[SATURN_ARTICLE],title:{zh:'土星环',en:'Saturn rings'},notes:{zh:'来源型号未认证',en:'Unverified source label'},rights:{zh:'原作者所有',en:'Creator owned'},evidence:[SATURN_ARTICLE,SATURN_VIDEO],media:[{url:SATURN_VIDEO,filename:'segment.mp4',sha256:'a'.repeat(64),reviewedVideoSegment:{capturePath:'pelican-archive/research/test/segment.mp4',sourcePath:'pelican-archive/research/test/source.mp4',sourceSha256:'b'.repeat(64),start:47.3,end:67.2,sourceDuration:181.834,method:'ffmpeg-skill/cut.py:accurate'}},{url:SATURN_VIDEO,filename:'complete.mp4',sha256:'b'.repeat(64),detailOnly:true}]});

test('reviewed segment permits only the exact reviewed article and recording, with separate original',()=>{
  assert.doesNotThrow(()=>validateCandidate(sample()));
  for(const change of [{sourceUrl:SATURN_ARTICLE+'?x=1'},{format:'video'},{evidence:[SATURN_VIDEO]},{media:[sample().media[0]]}])
    assert.throws(()=>validateCandidate({...sample(),...change}));
  for(const url of [SATURN_VIDEO+'?v=1',SATURN_VIDEO+'#x',SATURN_VIDEO.replace('https:','http:'),SATURN_VIDEO.replace('cdn.techgogogo.com','cdn.techgogogo.com:444'),SATURN_VIDEO.replace('cdn.techgogogo.com','user:pass@cdn.techgogogo.com'),SATURN_VIDEO.replace('report.mp4','other.mp4')]){
    const c=sample();c.media[0].url=url;c.evidence.push(url);assert.throws(()=>validateCandidate(c));
  }
  for(const change of [{sha256:'c'.repeat(64)},{url:SATURN_VIDEO+'?x=1'},{reviewedVideoSegment:sample().media[0].reviewedVideoSegment}]){
    const c=sample();Object.assign(c.media[1],change);assert.throws(()=>validateCandidate(c));
  }
});

test('segment refuses invalid intervals, provenance and mixed derivations',()=>{
  for(const change of [{start:-1},{start:68},{end:47.3},{end:182},{end:NaN},{sourceDuration:Infinity},{sourceSha256:'not-a-hash'},{method:'invented-motion'},{capturePath:'pelican-archive/research/../source.mp4'},{sourcePath:'C:/outside/source.mp4'},{capturePath:sample().media[0].reviewedVideoSegment.sourcePath}]){
    const c=sample();Object.assign(c.media[0].reviewedVideoSegment,change);assert.throws(()=>validateCandidate(c));
  }
  for(const key of ['crop','hls','browserCapture','svgFromTranscript','svgFromHardPrompts']){
    const c=sample();c.media[0][key]={};assert.throws(()=>validateCandidate(c));
  }
  assert.throws(()=>segmentPath(ROOT,'pelican-archive/research-other/source.mp4'));
});

test('segment metadata preserves exact source interval, picture and audio shape',()=>{
  const s=sample().media[0].reviewedVideoSegment;
  const source={format:{duration:'181.834'},streams:[{codec_type:'video',width:1920,height:1080,avg_frame_rate:'30/1'},{codec_type:'audio',channels:2,sample_rate:'44100'}]};
  const clip=structuredClone(source);clip.format.duration='19.923';
  assert.doesNotThrow(()=>verifySegmentMetadata(s,source,clip));
  for(const mutate of [x=>x.format.duration='19',x=>x.streams.pop(),x=>x.streams[0].width=960,x=>x.streams[0].avg_frame_rate='60/1',x=>x.streams[1].sample_rate='48000']){
    const wrong=structuredClone(clip);mutate(wrong);assert.throws(()=>verifySegmentMetadata(s,source,wrong));
  }
  const wrongSource=structuredClone(source);wrongSource.format.duration='200';assert.throws(()=>verifySegmentMetadata(s,wrongSource,clip));
});

test('pinned remote recording is checked before reading any local segment',async()=>{
  await assert.rejects(readReviewedVideoSegment(sample().media[0],Buffer.from('changed remote recording'),ROOT),/remote source hash/);
});

test('a suspected model and unnamed creator retain bilingual source attribution and segment provenance',()=>{
  const c=sample();c.modelEn='Gemini 4 (suspected routing; source label)';c.authorEn='Publisher (creator undisclosed)';
  const record=makeRecord(c,[{src:'/segment.mp4',source:SATURN_VIDEO,sha256:'a'.repeat(64),extraction:{kind:'reviewed-video-segment',sourceSha256:'b'.repeat(64),start:47.3,end:67.2}},{src:'/original.mp4',source:SATURN_VIDEO,sha256:'b'.repeat(64)}],'2026-10-14');
  assert.equal(record.i18n.en.author,c.authorEn);assert.equal(record.i18n.en.model,c.modelEn);
  assert.equal(record.modelClaimStatus,'source-reported-not-independently-authenticated');
  assert.equal(record.media[0].extraction.kind,'reviewed-video-segment');assert.equal(record.media[1].detailOnly,true);
  assert.equal(record.demoUrl,'');
});

test('re-encoding the same reviewed interval does not create a new work',()=>{
  const c=sample(),extraction={kind:'reviewed-video-segment',sourceSha256:'b'.repeat(64),start:47.3,end:67.2};
  const assets=[{source:SATURN_VIDEO,sha256:'a'.repeat(64),extraction},{source:SATURN_VIDEO,sha256:'b'.repeat(64)}];
  const existing={id:'existing-saturn',media:[{source:SATURN_VIDEO,sha256:'c'.repeat(64),extraction},{source:SATURN_VIDEO,sha256:'b'.repeat(64)}]};
  assert.equal(duplicateOf(c,assets,[existing]),existing.id);
  const other=structuredClone(existing);other.media[0].extraction.start=80;other.media[0].extraction.end=90;
  assert.equal(duplicateOf(c,assets,[other]),'');
  assert.equal(duplicateOf(c,assets,[{id:'original',media:[{source:SATURN_VIDEO,sha256:'b'.repeat(64)}]}]),'original');
});
