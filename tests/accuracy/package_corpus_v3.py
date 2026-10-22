"""Validate provenance/split integrity and package exactly the frozen public corpus."""
import csv
import hashlib
import json
import shutil
import sys
import time
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import ribby_images as images
from dataset_utils import author_keys

WORK=ROOT/'accuracy_work/v3';DATA=WORK/'references'
for source,name in [('benchmark-manifest.json','reference_manifest_v2.json'),('fresh-test-vectors.json','accuracy_regression_vectors_v2.json')]:
    if not (ROOT/'reports'/name).exists():shutil.copy2(ROOT/'dev'/source,ROOT/'reports'/name)
training=json.loads((WORK/'training_manifest.json').read_text(encoding='utf-8'))
holdout=json.loads((WORK/'holdout_manifest.json').read_text(encoding='utf-8'))
old_test=json.loads((ROOT/'reports/accuracy_test_manifest.json').read_text(encoding='utf-8'))
refs=[r for sp in training for r in sp['references']]
assert len(training)==14 and all(len(sp['references'])==64 for sp in training)
assert len({r['id'] for r in refs})==896 and len(holdout)==112
for label,items in [('new',holdout),('previous',old_test)]:
    assert not ({r['canonical_id'] for r in refs}&{r['canonical_id'] for r in items}),label
    assert not ({r.get('observation_id') for r in refs if r.get('observation_id')}&{r.get('observation_id') for r in items if r.get('observation_id')}),label
    assert not (set().union(*(author_keys(r) for r in refs))&set().union(*(author_keys(r) for r in items))),label
train_hashes={hashlib.sha256((DATA/'image_refs'/(r['id']+'.bin')).read_bytes()).hexdigest() for r in refs}
test_hashes={hashlib.sha256((WORK/'holdout/image_refs'/(r['id']+'.bin')).read_bytes()).hexdigest() for r in holdout}
assert not train_hashes&test_hashes,'identical image bytes across training/holdout'
for ref in refs+holdout:
    assert images.license_info(ref['license_url']) and ref.get('creator') and ref.get('source_url')
    assert images.safe_url(ref['url'],images.IMAGE_HOSTS)
for key in images.VECTOR_MODELS:
    for species in training:
        enriched=images.with_precomputed_vectors(DATA,{'references':species['references']},key)
        assert all('features' in r for r in enriched['references']),key
for query in (DATA/'image_refs').glob('query_*.json'):
    value=json.loads(query.read_text(encoding='utf-8'));value['version']=images.CACHE_VERSION;value['fetched_at']=time.time()
    query.write_text(json.dumps(value,ensure_ascii=False),encoding='utf-8')
with (DATA/'BILDNACHWEISE.csv').open('w',encoding='utf-8-sig',newline='') as file:
    writer=csv.writer(file,delimiter=';');writer.writerow(['Art','Foto-ID','Urheber','Quelle','Originalseite','Lizenz','Lizenzlink','Bild-URL','Abrufzeit'])
    for ref in refs:writer.writerow([ref.get(k,'') for k in ('scientific_name','id','creator','provider','source_url','license','license_url','url','retrieved_at')])
summary={'version':3,'reference_photos':896,'vector_count':1792,'species':[{**{k:s[k] for k in ('id','sci','name_de')},'photos':len(s['references'])} for s in training],
    'new_holdout_photos':112,'previous_holdout_photos':28,'split_checks':['canonical photo ID','observation ID','connected creator names/IDs','identical image SHA256'],
    'sources':{provider:sum(r['provider']==provider for r in refs) for provider in sorted({r['provider'] for r in refs})},
    'licenses':{license:sum(r['license']==license for r in refs) for license in sorted({r['license'] for r in refs})}}
(DATA/'image_reference_report.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
for name,content in [('reference_corpus_v3.json',summary),('reference_manifest_v3.json',training),('accuracy_holdout_v3.json',holdout)]:
    (ROOT/'reports'/name).write_text(json.dumps(content,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
shutil.copy2(WORK/'selection.json',ROOT/'reports/model_selection_v3.json')
shutil.copytree(DATA,ROOT/'reference_data',dirs_exist_ok=True)
files=[DATA/'BILDNACHWEISE.csv',DATA/'image_reference_report.json',*(DATA/'image_refs').glob('query_*.json')]
for ref in refs:
    files.extend(DATA/'image_refs'/(ref['id']+suffix) for suffix in ('.json','.bin'))
    files.extend(DATA/'image_vectors'/key/(ref['id']+'.json') for key in images.VECTOR_MODELS)
assert len({p.relative_to(DATA).as_posix() for p in files})==len(files)
assert len(files)<5000 and sum(p.stat().st_size for p in files)<256*1024*1024
with zipfile.ZipFile(ROOT/'ribby_image_seed.zip','w',zipfile.ZIP_DEFLATED) as archive:
    for file in files:archive.write(file,file.relative_to(DATA).as_posix())
with zipfile.ZipFile(ROOT/'ribby_image_seed.zip') as archive:assert archive.testzip() is None
print(json.dumps({**summary,'seed_bytes':(ROOT/'ribby_image_seed.zip').stat().st_size},ensure_ascii=False))
