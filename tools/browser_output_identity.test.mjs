import {test} from 'node:test';
import assert from 'node:assert/strict';
import {duplicateOf,validateCandidate} from './import_collection_batch.mjs';
import fs from 'node:fs';
const pinned=JSON.parse(fs.readFileSync(new URL('./reviewed_source_assets.json',import.meta.url))).find(x=>x.url==='https://wallabytoken.com/blog/p/pelican-bicycle');
const b={id:'review-fixture-kimi',sourceUrl:pinned.url,author:'Fixture',model:'Kimi K3.1 Pro',date:'2026-10-24',format:'animation',title:{zh:'测试',en:'Fixture'},notes:{zh:'测试',en:'Fixture'},rights:{zh:'测试',en:'Fixture'},unitType:'single-model-output',modelToMediaVerified:true,generationMethod:'code-generated',codeGenerationEvidence:[pinned.url],evidence:[pinned.url],media:[{url:pinned.url,filename:'fixture.jpeg',reviewedSourceAsset:{path:pinned.path,sha256:pinned.sha256},browserCapture:{capturePath:'pelican-archive/research/fixture/frame.jpeg',sha256:'1'.repeat(64),sourceHtmlSha256:pinned.sha256,outputSelector:'#pbB-scene'}}]};
const html=b.media[0].browserCapture.sourceHtmlSha256;
const frame=(selector)=>({sha256:'b'.repeat(64),source:b.sourceUrl,extraction:{kind:'browser-rendered-frame',sourceSha256:html,outputSelector:selector}});
test('two reviewed model modules in one HTML are independent outputs',()=>{
 validateCandidate(b);
 assert.equal(duplicateOf(b,[frame('#pbB-scene')],[{id:'other',media:[frame('#pbA-scene')]}]),'');
 assert.equal(duplicateOf(b,[frame('#pbB-scene')],[{id:'same',media:[frame('#pbB-scene')]}]),'same');
});
test('selectors cannot be invented to multiply a source output',()=>{
 for(const selector of ['#other','#pbA-scene']){
  const c=structuredClone(b);c.media[0].browserCapture.outputSelector=selector;
  assert.throws(()=>validateCandidate(c));
 }
 const c=structuredClone(b);c.media[0].browserCapture.sourceHtmlSha256='0'.repeat(64);
 assert.throws(()=>validateCandidate(c));
});
test('the earlier capture without a selector still deduplicates its exact reviewed model module',()=>{
 const old={id:'earlier-deepseek',sourceUrl:pinned.url,model:'DeepSeek V4.1 Flash 1017',media:[frame(undefined)]};
 const a=structuredClone(b);a.model='DeepSeek V4.1 Flash 1017';a.media[0].browserCapture.outputSelector='#pbA-scene';
 assert.equal(duplicateOf(a,[frame('#pbA-scene')],[old]),old.id);
 assert.equal(duplicateOf(b,[frame('#pbB-scene')],[old]),'');
});
