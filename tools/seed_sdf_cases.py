"""Explicitly selected, visually reviewed source previews for the first import."""
import json
from pathlib import Path
from submit_ingest import submit
ROOT=Path(__file__).resolve().parents[1]
CASES=[
 ('gpt-5-6-sol-high-run-01','gpt-5.6-sol','Sol · 高推理强度的 SDF 三维鹈鹕','Sol · SDF pelican at high reasoning effort','用 SDF 光线步进渲染立体鹈鹕和青绿色自行车，保留鸟喙、辐条与投影。适合与同一仓库的其他模型并排观察。','A ray-marched SDF pelican on a teal bicycle, with a pouch beak, spokes and ground shadows. Compare the geometry with other runs from the same repository.'),
 ('claude-fable-5-max-run-01','claude-fable-5','Fable · 公路骑行的 SDF 三维场景','Fable · An SDF ride along a roadway','同一 SDF 提示词下的 max 推理强度版本：鹈鹕骑着宽胎自行车，场景加入道路与远景。','A max-effort response to the same SDF prompt: a pelican on a fat-tire bicycle, with a roadway and distant scenery.'),
 ('deepseek-v4-pro-low-run-01','deepseek/deepseek-v4-pro','DeepSeek V4 Pro · 偏暗的 SDF 骑行场景','DeepSeek V4 Pro · A dimly lit SDF scene','low 推理强度版本。原始预览明显偏暗，鸟与自行车的结构难以辨认；保留实际画面，作为同题不同实现的对照。','A low-effort run. The original preview is dark and the bird and bicycle are difficult to distinguish; the actual image is preserved as a comparison of different implementations of the same task.')
]
if __name__=='__main__':
    jobs=[]
    for ident,model,zh,en,nzh,nen in CASES:
        payload={'sourceUrl':f'https://github.com/AzatJalilov/PelicanSdf/blob/main/data/results/{ident}.json','date':'2026-07-18','model':model,'author':'AzatJalilov / Pelican SDF','format':'3d','title':{'zh':zh,'en':en},'notes':{'zh':nzh,'en':nen},'media':[f'https://raw.githubusercontent.com/AzatJalilov/PelicanSdf/main/assets/thumbnails/{ident}.jpg']}
        result=submit(payload);jobs.append(result);print(json.dumps(result))
    (ROOT/'deploy-build/ingest-jobs.json').write_text(json.dumps(jobs),encoding='utf8')
