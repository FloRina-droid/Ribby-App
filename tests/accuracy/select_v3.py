"""Photographer-grouped selection; never opens holdout labels or vectors."""
import hashlib
import json
import os
import re
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / 'accuracy_work/v3'
manifest_path = WORK / 'training_manifest.json'
if os.environ.get('RIBBY_V3_BASELINE') == '1':
    manifest_path = ROOT / 'reports/reference_manifest_v2.json'
    if not manifest_path.exists():manifest_path=ROOT/'dev/benchmark-manifest.json'
manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
assert len(manifest) == 14
data_dir = ROOT / 'reference_data' if os.environ.get('RIBBY_V3_BASELINE') == '1' else WORK / 'references'

def normalize(v):
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)

def author_name(ref):
    name = re.sub(r'^\s*(?:\(c\)|©)\s*', '', ref.get('creator', '').casefold())
    return re.sub(r'\W+', '', re.sub(r',?\s*(?:some rights reserved|no rights reserved).*$', '', name))

# Connect name and numeric iNaturalist IDs before assigning folds, including
# Commons mirrors that have no numeric author ID.
parents = {}
def find(x):
    parents.setdefault(x, x)
    if parents[x] != x:
        parents[x] = find(parents[x])
    return parents[x]
def union(a, b):
    a, b = find(a), find(b)
    parents[max(a,b)] = min(a,b)
refs, labels = [], []
for i, species in enumerate(manifest):
    for ref in species['references']:
        name = 'name:' + author_name(ref)
        find(name)
        if ref.get('creator_id'):
            union(name, 'inat:' + str(ref['creator_id']))
        refs.append(ref); labels.append(i)
labels = np.array(labels)
folds = np.array([int(hashlib.sha256(('ribby-v3-group:' + find('name:' + author_name(r))).encode()).hexdigest()[:8],16)%5 for r in refs])
methods = [('centroid', 0), ('centered', .5), ('centered', 1), ('contrastive', .01), ('contrastive', .1), ('contrastive', 1), ('nearest', 0), ('weighted2', 0), ('top3', 0)]
methods += [(name, alpha) for name in ('ridge', 'metric') for alpha in (.01, .1, 1, 10)]
results = []
for model, key in [('bioclip','bioclip-v1-fp16-22a18d2-v1'),('dinov2','dinov2-small-q8-c2bb04a-cls-v1')]:
    features = np.array([json.loads((data_dir/'image_vectors'/key/(r['id']+'.json')).read_text(encoding='utf-8'))['vector'] for r in refs])
    for limit in (16, 32, 64):
        tally = {(m,a):[0,0,0] for m,a in methods}
        for fold in range(5):
            test_indices = np.flatnonzero(folds == fold)
            classes = [np.flatnonzero((labels == c)&(folds != fold))[:limit] for c in range(14)]
            assert all(len(c) for c in classes)
            means = np.array([features[c].mean(axis=0) for c in classes])
            centroids = normalize(means)
            queries = features[test_indices]
            train_indices = np.flatnonzero(folds != fold)
            train_features = features[train_indices]
            train_labels = labels[train_indices]
            projection_center = np.array([train_features[train_labels==c].mean(axis=0) for c in range(14)]).mean(axis=0)
            balance = np.sqrt(len(train_indices)/(14*np.bincount(train_labels)[train_labels]))
            x = (train_features-projection_center)*balance[:,None]
            y = (np.eye(14)[train_labels] - 1/14)*balance[:,None]
            ridge_weights = {}
            for alpha in (.01,.1,1,10):
                ridge_weights[alpha] = np.linalg.solve(x.T@x+alpha*np.eye(x.shape[1]),x.T@y)
            for method, alpha in methods:
                if method == 'centroid':
                    scores = queries @ centroids.T
                elif method == 'centered':
                    center = means.mean(axis=0) * alpha
                    scores = normalize(queries-center) @ normalize(means-center).T
                elif method == 'contrastive':
                    center = means.mean(axis=0)
                    centered = normalize(means-center)
                    gram = centered @ centered.T
                    weights = normalize(np.linalg.solve(gram + alpha*np.eye(14),centered))
                    scores = normalize(queries-center) @ weights.T
                elif method == 'ridge':
                    weights = normalize(ridge_weights[alpha].T)
                    scores = normalize(queries-projection_center) @ weights.T
                elif method == 'metric':
                    weights = ridge_weights[alpha]
                    scores = normalize((queries-projection_center)@weights) @ normalize((means-projection_center)@weights).T
                else:
                    count = 1 if method=='nearest' else 2 if method=='weighted2' else 3
                    values = [np.sort(queries @ features[c].T,axis=1)[:,-min(count,len(c)):] for c in classes]
                    if method=='weighted2':
                        scores = np.array([v[:,-1]*.6+v[:,0]*.4 for v in values]).T
                    else:
                        scores = np.array([v.mean(axis=1) for v in values]).T
                ranks = np.argsort(-scores,axis=1)
                target = labels[test_indices]
                counts = tally[(method,alpha)]
                counts[0] += int(np.sum(ranks[:,0] == target))
                counts[1] += int(np.sum(np.any(ranks[:,:3] == target[:,None],axis=1)))
                counts[2] += len(target)
        for (method,alpha),(top1,top3,n) in tally.items():
            results.append(dict(model=model,method=method,alpha=alpha,reference_limit=limit,correct=top1,top3_correct=top3,n=n,top1=top1/n,top3=top3/n))
results.sort(key=lambda r:(-r['top1'],-r['top3'],r['reference_limit'],r['alpha']))
deployable = [r for r in results if r['method'] not in ('ridge','contrastive') and r['reference_limit'] in (16,32)]
selection = dict(design='Five folds grouped by connected photographer names and iNaturalist IDs; holdout unopened',
    constraints='Existing 8/16/32 reference controls remain unchanged; choose a method that still compares the selected reference photographs',
    selected=deployable[0], exploratory_best=results[0], candidates=results)
output = WORK / ('baseline_selection.json' if os.environ.get('RIBBY_V3_BASELINE') == '1' else 'selection.json')
output.parent.mkdir(parents=True,exist_ok=True)
output.write_text(json.dumps(selection,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(selected=selection['selected'], best_ten=results[:10]),indent=2))
