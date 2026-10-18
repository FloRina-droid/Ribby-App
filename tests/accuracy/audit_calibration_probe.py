"""Verify that new test images/creators/observations never enter reference fitting."""
import hashlib
import json
from pathlib import Path
from dataset_utils import author_keys
ROOT=Path(__file__).resolve().parents[2]
read=lambda name:json.loads((ROOT/'reports'/name).read_text(encoding='utf-8'))
training=[r for sp in read('reference_manifest_v3.json') for r in sp['references']]
old=read('accuracy_holdout_v3.json');first=read('accuracy_test_manifest.json');probe=read('accuracy_calibration_probe.json')
known=training+old+first
for key in ('id','canonical_id','observation_id'):
    assert not ({r.get(key) for r in probe if r.get(key)}&{r.get(key) for r in known if r.get(key)}),key
authors=lambda rows:set().union(*(author_keys(r) for r in rows))
assert not authors(probe)&authors(known)
assert len({r.get('creator_id') for r in probe})==len(probe)
digest=lambda folder,r:hashlib.sha256((ROOT/folder/'image_refs'/(r['id']+'.bin')).read_bytes()).hexdigest()
known_hashes={digest('accuracy_work/v3/references',r) for r in training}
known_hashes|={digest('accuracy_work/v3/holdout',r) for r in old}
original='accuracy_test_data' if (ROOT/'accuracy_test_data/image_refs').exists() else 'accuracy_work/test_data'
known_hashes|={digest(original,r) for r in first}
probe_hashes={digest('accuracy_work/calibration/probe',r) for r in probe}
assert len(probe_hashes)==len(probe) and not probe_hashes&known_hashes
report={'pass':True,'new_photos':len(probe),'known_reference_or_previous_test_photos':len(known),
    'distinct_new_photographers':len(probe),'checks':['photo ID','canonical photo ID','observation ID','known creator names and IDs','identical file SHA256'],
    'species_counts':{sp:sum(r['scientific_name']==sp for r in probe) for sp in sorted({r['scientific_name'] for r in probe})}}
(ROOT/'reports/calibration_probe_audit_v4.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('New probe separation audit passed:',len(probe),'photos /',len(report['species_counts']),'species')
