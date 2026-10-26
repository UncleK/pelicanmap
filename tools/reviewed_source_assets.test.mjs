import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {existsSync} from 'node:fs';
import {reviewedSourceAsset,validateReviewedSourceAsset,verifyReviewedSourceBytes,readReviewedSourceAsset} from './reviewed_source_assets.mjs';
const root=path.resolve(import.meta.dirname,'..');
const rows=JSON.parse(await fs.readFile(new URL('./reviewed_source_assets.json',import.meta.url)));
const row=rows.find(x=>x.url.includes('zdmimg'));
const m={url:row.url,reviewedSourceAsset:{path:row.path,sha256:row.sha256}};
const c={...row.bindings[0],evidence:[row.bindings[0].sourceUrl,row.url]};
test('browser-observed public bytes retain their exact response hash',{skip:!existsSync(path.join(root,row.path))},async()=>{
 const bytes=await readReviewedSourceAsset(m,root);
 assert.equal(bytes.toString('ascii',0,4),'RIFF');
 assert.equal(validateReviewedSourceAsset(c,m),true);
 assert.throws(()=>verifyReviewedSourceBytes(row,Buffer.concat([bytes,Buffer.from('changed')])));
});
test('cannot borrow another output, model, source URL, cache path or digest',()=>{
 for(const changed of [{...c,model:'Other model'},{...c,sourceUrl:'https://example.com/other'},{...c,evidence:[]}])
  assert.throws(()=>validateReviewedSourceAsset(changed,m));
 for(const changed of [{...m,url:m.url+'?other=1'},{...m,reviewedSourceAsset:{...m.reviewedSourceAsset,path:'../outside.webp'}},{...m,reviewedSourceAsset:{...m.reviewedSourceAsset,sha256:'0'.repeat(64)}}])
  assert.throws(()=>reviewedSourceAsset(changed));
});
test('unreviewed asset does not acquire a cache exemption',()=>{
 assert.equal(reviewedSourceAsset({url:'https://example.com/image.webp'}),null);
 assert.throws(()=>reviewedSourceAsset({url:'https://example.com/image.webp',reviewedSourceAsset:{path:row.path,sha256:row.sha256}}));
});
