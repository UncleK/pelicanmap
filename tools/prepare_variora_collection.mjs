import fs from 'node:fs/promises';
import path from 'node:path';
import {ROOT} from './import_collection_batch.mjs';
const cases=JSON.parse(await fs.readFile(path.join(ROOT,'deploy-build/collection-variora.json'),'utf8'));
for(const c of cases) {
  // These are published screenshots of SVG/HTML animations, not interactive mirrors.
  c.format='animation';
  c.modelEn=c.model.replaceAll('（上游标注）',' (upstream-reported)');
}
await fs.writeFile(path.join(ROOT,'deploy-build/collection-variora-reviewed.json'),JSON.stringify({reviewed:true,batch:'2026-10-01-variora-backfill',cases},null,2));
console.log(JSON.stringify({reviewed:cases.length}));
