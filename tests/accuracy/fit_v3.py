"""Freeze the selected reference metric using training photographs only."""
import hashlib
import json
import re
import sys
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'accuracy_work/v3'
manifest=json.loads((WORK/'training_manifest.json').read_text(encoding='utf-8'))
selection=json.loads((WORK/'selection.json').read_text(encoding='utf-8'))
assert len(manifest)==14 and sum(len(s['references']) for s in manifest)==896
output={'version':3,'default':selection['selected']['model'],
    'reference_limit':selection['selected']['reference_limit'],
    'training_manifest_sha256':hashlib.sha256((WORK/'training_manifest.json').read_bytes()).hexdigest(),
    'selection_sha256':hashlib.sha256((WORK/'selection.json').read_bytes()).hexdigest(),
    'holdout_used_for_fit':False,'models':{}}
for model,key,dimensions in [('bioclip','bioclip-v1-fp16-22a18d2-v1',512),('dinov2','dinov2-small-q8-c2bb04a-cls-v1',384)]:
    chosen=next(r for r in selection['candidates'] if r['model']==model and r['method'] not in ('ridge','contrastive') and r['reference_limit'] in (16,32))
    config={**{k:chosen[k] for k in ('method','alpha')},'model_key':key,'dimensions':dimensions,
        'species':[s['sci'].casefold() for s in manifest], 'training_photos':896}
    if chosen['method']=='metric':
        classes=[np.array([json.loads((WORK/'references/image_vectors'/key/(r['id']+'.json')).read_text(encoding='utf-8'))['vector'] for r in s['references']]) for s in manifest]
        means=np.array([x.mean(axis=0) for x in classes]);center=means.mean(axis=0)
        x=np.concatenate(classes)-center;y=np.repeat(np.eye(14),64,axis=0)-1/14
        weights=np.linalg.solve(x.T@x+chosen['alpha']*np.eye(dimensions),x.T@y)
        config.update(center=np.round(center,10).tolist(),weights=np.round(weights.T,10).tolist())
    output['models'][model]=config
artifact=ROOT/'image_metric.json'
artifact.write_text(json.dumps(output,separators=(',',':'))+'\n',encoding='utf-8')
if '--embed' in sys.argv:
    app=ROOT/'ribby_app.html'
    replacement=('const IMAGE_RANKING = '+json.dumps(output,separators=(',',':'))+';').encode('utf-8')
    code,count=re.subn(rb'const IMAGE_RANKING = [^\r\n]*;',lambda match:replacement,app.read_bytes(),count=1)
    assert count==1,'No embedded ranking configuration found'
    app.write_bytes(code)
print(json.dumps({'frozen_metric_sha256':hashlib.sha256(artifact.read_bytes()).hexdigest(),'default':output['default'],
    'reference_limit':output['reference_limit'],'models':{k:v['method'] for k,v in output['models'].items()}}))
