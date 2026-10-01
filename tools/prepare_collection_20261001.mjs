// Curated source batch: original posts plus a version-pinned, licensed dataset.
// Fetch data only; do not install or execute any upstream project.
import fs from 'node:fs/promises';
import path from 'node:path';
import {ROOT} from './import_collection_batch.mjs';
const batch='2026-10-01-source-backfill';
const cases=[];
for(const file of ['collection-simon.json','collection-bbinwang.json','collection-recent.json']) {
  cases.push(...JSON.parse(await fs.readFile(path.join(ROOT,'deploy-build',file),'utf8')));
}
const revision='548f58a232c4aadf05f4798c2d69b8bd95e4b502';
const dataset='https://huggingface.co/datasets/sergiopaniego/pelican-svg-drawings';
const raw=dataset+'/raw/'+revision+'/';
const resolve=dataset+'/resolve/'+revision+'/';
const response=await fetch(raw+'data.jsonl',{headers:{'User-Agent':'PelicanMap-Collector/1.0'}});
if(!response.ok)throw Error('Dataset HTTP '+response.status);
const jsonl=await response.text();
const rows=jsonl.trim().split('\n').map(x=>JSON.parse(x));
if(rows.length!==139 || new Set(rows.map(x=>x.model)).size!==7)throw Error('Unexpected dataset revision');
const archiveDir=path.join(ROOT,'pelican-archive/research',batch);
await fs.mkdir(archiveDir,{recursive:true});
for(const [url,name] of [
  ['https://raw.githubusercontent.com/bbinwang/pelican-bicycle/b14acbb2ebe9d9be5f0dec3d35d8f4ae6fcaa432/LICENSE','bbinwang-LICENSE'],
  ['https://raw.githubusercontent.com/bbinwang/pelican-bicycle/b14acbb2ebe9d9be5f0dec3d35d8f4ae6fcaa432/README.md','bbinwang-README.md'],
  ['https://www.apache.org/licenses/LICENSE-2.0.txt','Apache-2.0.txt']
]) {
  const r=await fetch(url);if(!r.ok)throw Error('License/source archive missing');
  await fs.writeFile(path.join(archiveDir,name),await r.text());
}
await fs.writeFile(path.join(archiveDir,'hf-data.jsonl'),jsonl);
for(const name of ['README.md']) {
  const r=await fetch(raw+name);if(!r.ok)throw Error('Dataset evidence missing');
  await fs.writeFile(path.join(archiveDir,'hf-'+name),await r.text());
}
const commitsResponse=await fetch('https://huggingface.co/api/datasets/sergiopaniego/pelican-svg-drawings/commits/main');
const commits=await commitsResponse.json();
if(!commits.some(x=>x.id===revision && x.date.startsWith('2026-07-29')))throw Error('Unverified publication date');
await fs.writeFile(path.join(archiveDir,'hf-commits.json'),JSON.stringify(commits,null,2));
const held=[];
for(const row of rows) {
  if(row.task!=='pelican_bicycle' || !row.png || !row.svg) {held.push({id:row.id,reason:'No complete published render'});continue;}
  if(!/^png\/[A-Za-z0-9_.-]+\.png$/.test(row.png) || !/^svg\/[A-Za-z0-9_.-]+\.svg$/.test(row.svg))throw Error('Unreviewed dataset asset path');
  const modelSlug=row.model.toLowerCase().replace(/[^a-z0-9]+/g,'-');
  const number=String(row.sample+1).padStart(2,'0');
  const ident='hf-openenv-'+modelSlug+'-sample-'+number+'-2026-07-29';
  const filename='hf-'+modelSlug+'-'+number+'.png';
  cases.push({id:ident,sourceUrl:dataset+'/blob/'+revision+'/'+row.svg,date:'2026-07-29',dateBasis:'dataset-publication',model:row.model,author:'Sergio Paniego (@sergiopaniego)',format:'svg',variant:'sample-'+number,
    title:{zh:row.model+' · OpenEnv 独立样本 '+number,en:row.model+' · OpenEnv independent sample '+number},
    notes:{zh:'Sergio Paniego 公开的 OpenEnv 鹈鹕 SVG 数据集中，这个模型的第 '+number+' 个独立运行样本。模型标签、提供商和样本编号按逐行元数据保留，图像为原数据集发布的 PNG，而非本站重新生成。记录日期为数据集公开日期，不代表精确生成时刻；模型归属和环境评分没有经过本站独立认证，不把评分当作模型能力排名。',
      en:'Independent sample '+number+' for this model in Sergio Paniego’s public OpenEnv pelican SVG dataset. The model label, provider and sample number follow its per-row metadata. This is the PNG published by the dataset, not an image regenerated here. The date is the dataset publication date, not the exact generation time. Model provenance and environment scores are not independently authenticated here, and scores are not presented as capability rankings.'},
    prompt:'generate an SVG of a pelican riding a bicycle',
    rights:{zh:'原数据集标注 Apache-2.0；保留 Sergio Paniego 署名、固定版本与原始文件链接。',en:'The source dataset declares Apache-2.0; Sergio Paniego’s attribution, pinned revision and original file links are retained.'},
    sourceCodeUrl:dataset+'/blob/'+revision+'/'+row.svg,evidence:[dataset+'/blob/'+revision+'/README.md',dataset+'/blob/'+revision+'/data.jsonl',dataset+'/commit/'+revision],
    datasetSample:{id:row.id,sample:row.sample,provider:row.provider,access:row.access,gatePassed:row.gate_passed,judgeModel:row.judge_model,publicationDate:'2026-07-29',revision},
    media:[{url:resolve+row.png,filename,caption:{zh:'原始 PNG · OpenEnv 独立运行 '+number,en:'Original published PNG · Independent OpenEnv run '+number}}]});
}
for(const c of cases) {
  c.modelEn=c.model.replaceAll('（作者标注）',' (author-reported)').replaceAll('（底层模型未公开）',' (underlying model undisclosed)');
}
await fs.writeFile(path.join(archiveDir,'hf-held.json'),JSON.stringify(held,null,2));
await fs.writeFile(path.join(ROOT,'deploy-build/collection-reviewed.json'),JSON.stringify({reviewed:true,batch,cases},null,2));
console.log(JSON.stringify({batch,curated:cases.length-rows.length+held.length,dataset:rows.length-held.length,held,total:cases.length}));
