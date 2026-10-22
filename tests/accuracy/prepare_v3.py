"""Recreate the frozen V3 comparison from the shipped seed and source manifests."""
import json
import hashlib
import shutil
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import ribby_images as images

WORK=ROOT/'accuracy_work/v3';WORK.mkdir(parents=True,exist_ok=True)
images.install_reference_seed(WORK/'references',ROOT/'ribby_image_seed.zip')
metric=json.loads((ROOT/'image_metric.json').read_text(encoding='utf-8'))
for source,target in [('reference_manifest_v3.json','training_manifest.json'),('accuracy_holdout_v3.json','holdout_manifest.json'),('model_selection_v3.json','selection.json')]:
    raw=(ROOT/'reports'/source).read_bytes()
    key={'training_manifest.json':'training_manifest_sha256','selection.json':'selection_sha256'}.get(target)
    if key:
        # Preserve the frozen snapshot hash across Windows/Git line endings.
        lf=raw.replace(b'\r\n',b'\n').rstrip(b'\r\n')
        candidates=[raw]+[body+ending for body in (lf,lf.replace(b'\n',b'\r\n')) for ending in (b'\n',b'\r\n')]
        raw=next((value for value in candidates if hashlib.sha256(value).hexdigest()==metric[key]),None)
        if raw is None:raise ValueError('Snapshot differs from frozen metric: '+source)
    (WORK/target).write_bytes(raw)
manifest=json.loads((WORK/'holdout_manifest.json').read_text(encoding='utf-8'))
target=WORK/'holdout/image_refs';target.mkdir(parents=True,exist_ok=True)
for index,ref in enumerate(manifest):
    (target/(ref['id']+'.json')).write_text(json.dumps(ref,ensure_ascii=False),encoding='utf-8')
    images.reference_file(WORK/'holdout',ref['id'])
    if (index+1)%8==0:print('Prepared',index+1,'/112 independent test photos',flush=True)
print('Prepared frozen V3 corpus and holdout',flush=True)
