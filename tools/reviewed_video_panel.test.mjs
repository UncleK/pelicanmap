import test from 'node:test';
import assert from 'node:assert/strict';
import {PANELS,validateVideoPanel,readReviewedVideoPanel} from './reviewed_video_panel.mjs';
import {duplicateOf,ROOT} from './import_collection_batch.mjs';

function sample(){
  const sourceUrl='https://x.com/sakeroux/status/2112473098201284875',spec=PANELS[sourceUrl];
  return {id:'test-panel',sourceUrl,format:'animation',evidence:[sourceUrl,spec.url],
    media:[{url:spec.url,filename:'panel.mp4',sha256:'a'.repeat(64),reviewedVideoPanel:{
      sourcePath:'pelican-archive/research/test/original.mp4',capturePath:'pelican-archive/research/test/panel.mp4',
      sourceSha256:spec.sha256,box:[...spec.boxes[0]],frames:[...spec.ranges[0]],method:'ffmpeg-skill/crop.py+cut.py:lossless-preserve-color'}},
      {url:spec.url,filename:'original.mp4',sha256:spec.sha256,detailOnly:true}]};
}
test('unreviewed source, altered panel, traversal and missing original are refused',()=>{
  const good=sample();assert.doesNotThrow(()=>validateVideoPanel(good,good.media[0],ROOT));
  for(const mutate of [c=>c.sourceUrl+='?other=1',c=>c.media.pop(),c=>c.media[1].detailOnly=false,
    c=>c.media[0].url+='?other=1',c=>c.media[0].reviewedVideoPanel.box[0]=2,
    c=>c.media[0].reviewedVideoPanel.frames[1]=359,c=>c.media[0].reviewedVideoPanel.sourceSha256='b'.repeat(64),
    c=>c.media[0].reviewedVideoPanel.capturePath='pelican-archive/research/../other.mp4',
    c=>c.media[0].reviewedVideoPanel.method='invented',c=>c.media[0].reviewedVideoSegment={}]){
    const wrong=sample();mutate(wrong);assert.throws(()=>validateVideoPanel(wrong,wrong.media[0],ROOT));
  }
});
test('October 23 comparisons accept only the complete reviewed panels and original attachment',()=>{
  for(const sourceUrl of ['https://x.com/chetaslua/status/2113503273361777086','https://x.com/abhinavflac/status/2113218148837257546']){
    const spec=PANELS[sourceUrl];
    for(const box of spec.boxes){
      const c=sample();c.sourceUrl=sourceUrl;c.evidence=[sourceUrl,spec.url];
      c.media[0].url=spec.url;c.media[1].url=spec.url;c.media[1].sha256=spec.sha256;
      Object.assign(c.media[0].reviewedVideoPanel,{sourceSha256:spec.sha256,box:[...box],frames:[...spec.ranges[0]]});
      assert.doesNotThrow(()=>validateVideoPanel(c,c.media[0],ROOT));
      for(const mutate of [x=>x.media[0].reviewedVideoPanel.box[1]+=2,x=>x.media[0].reviewedVideoPanel.frames[1]--,x=>x.media.pop(),x=>x.media[0].url+='&other=1']){
        const bad=structuredClone(c);mutate(bad);assert.throws(()=>validateVideoPanel(bad,bad.media[0],ROOT));
      }
    }
  }
});
test('changed remote source fails before local files are accessed',async()=>{
  await assert.rejects(readReviewedVideoPanel(sample().media[0],Buffer.from('changed original'),ROOT),/remote source hash/);
});
test('deduplication distinguishes real panel and prompt outputs sharing the original',()=>{
  const c=sample(),s=c.media[0].reviewedVideoPanel;
  const asset={source:c.media[0].url,sha256:'a'.repeat(64),extraction:{kind:'reviewed-video-panel',sourceSha256:s.sourceSha256,
    box:{left:0,top:0,width:640,height:360},startFrame:0,endFrame:360}};
  const prior=structuredClone(asset);prior.sha256='b'.repeat(64);
  assert.equal(duplicateOf(c,[asset],[{id:'same-output',media:[prior]}]),'same-output');
  prior.extraction.box.left=640;assert.equal(duplicateOf(c,[asset],[{id:'other-panel',media:[prior]}]),'');
  prior.extraction.box.left=0;prior.extraction.startFrame=360;prior.extraction.endFrame=960;
  assert.equal(duplicateOf(c,[asset],[{id:'other-prompt',media:[prior]}]),'');
});
