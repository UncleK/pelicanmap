// Exact public responses already obtained during source review, including
// browser-observed WebP responses whose direct download returns HTTP 403.
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {readFileSync} from 'node:fs';
const reviews=JSON.parse(readFileSync(new URL('./reviewed_source_assets.json',import.meta.url),'utf8'));
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');

export function reviewedSourceAsset(m){
  if(!m.reviewedSourceAsset)return null;
  const row=reviews.find(x=>x.url===m.url);
  if(!row || m.reviewedSourceAsset.path!==row.path || m.reviewedSourceAsset.sha256!==row.sha256)
    throw Error('Public source cache must match an exact reviewed URL, path and SHA-256');
  return row;
}
export function validateReviewedSourceAsset(c,m){
  const row=reviewedSourceAsset(m);
  if(!row)return false;
  if(!row.bindings.some(x=>x.sourceUrl===c.sourceUrl && x.model===c.model) ||
     !c.evidence.includes(m.url) || !c.evidence.includes(c.sourceUrl))
    throw Error('Reviewed public asset is not bound to this source and model');
  return true;
}
export function verifyReviewedSourceBytes(row,bytes){
  if(bytes.length!==row.bytes || sha(bytes)!==row.sha256)throw Error('Reviewed public response bytes changed');
  return bytes;
}
export async function readReviewedSourceAsset(m,root){
  const row=reviewedSourceAsset(m);
  if(!row)throw Error('Missing reviewed source asset');
  const base=await fs.realpath(path.join(root,'pelican-archive/research'));
  const file=await fs.realpath(path.resolve(root,row.path));
  const rel=path.relative(base,file);
  if(!rel || rel.startsWith('..') || path.isAbsolute(rel))throw Error('Reviewed source cache escapes research');
  return verifyReviewedSourceBytes(row,await fs.readFile(file));
}
