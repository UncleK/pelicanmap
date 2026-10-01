import fs from 'node:fs/promises';
import path from 'node:path';
import {ROOT} from './import_collection_batch.mjs';
const manifests=await Promise.all(['collection-reviewed.json','collection-variora-reviewed.json'].map(async name=>JSON.parse(await fs.readFile(path.join(ROOT,'deploy-build',name),'utf8'))));
const ids=new Set(manifests.flatMap(m=>m.cases.map(c=>c.id)));
const byId=new Map(manifests.flatMap(m=>m.cases.map(c=>[c.id,c])));
const file=path.join(ROOT,'site/additions.json');
const records=JSON.parse(await fs.readFile(file,'utf8'));
for(const x of records)if(ids.has(x.id)) {
  x.updated='2026-10-01';
  x.media.forEach((m,i)=>{m.captionEn=byId.get(x.id).media[i].caption.en;});
  if(x.id.startsWith('hf-openenv-') || x.id.startsWith('github-bbinwang-')) {
    x.licenseUrl='/media/collected/2026-10-01-source-backfill/ATTRIBUTION.txt';
    x.licenseFiles=x.id.startsWith('hf-')?['/media/collected/2026-10-01-source-backfill/apache-2.0.txt']:['/media/collected/2026-10-01-source-backfill/bbinwang-MIT.txt'];
  } else if(x.id.startsWith('variora-')) {
    x.licenseUrl='/media/collected/2026-10-01-variora-backfill/ATTRIBUTION.txt';
    x.licenseFiles=['/media/collected/2026-10-01-variora-backfill/Variora-MIT.txt'];
  }
}
await fs.writeFile(file,JSON.stringify(records,null,2)+'\n');
console.log(JSON.stringify({newRecords:records.filter(x=>ids.has(x.id)).length,allAdditions:records.length,withPublicLicense:records.filter(x=>ids.has(x.id)&&x.licenseUrl).length}));
