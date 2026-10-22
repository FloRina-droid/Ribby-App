"""Fit temperature scaling without reading any independent probe outcomes.

Nested photographer-grouped validation evaluates the complete calibration
pipeline. The frozen V3 ranking/metric parameters are not tuned here.
"""
import hashlib
import json
import math
import re
import sys
from pathlib import Path
import numpy as np
from dataset_utils import author_name

ROOT=Path(__file__).resolve().parents[2];WORK=ROOT/'accuracy_work/calibration'
WORK.mkdir(parents=True,exist_ok=True)
manifest=json.loads((ROOT/'reports/reference_manifest_v3.json').read_text(encoding='utf-8'))
metric=json.loads((ROOT/'image_metric.json').read_text(encoding='utf-8'))
parents={}
def find(x):
    parents.setdefault(x,x)
    if parents[x]!=x:parents[x]=find(parents[x])
    return parents[x]
refs=[];labels=[]
for c,sp in enumerate(manifest):
    for ref in sp['references']:
        name='name:'+author_name(ref);find(name)
        if ref.get('creator_id'):
            a,b=find(name),find('inat:'+str(ref['creator_id']));parents[max(a,b)]=min(a,b)
        refs.append(ref);labels.append(c)
labels=np.array(labels);groups=[find('name:'+author_name(r)) for r in refs]
outer=np.array([int(hashlib.sha256(('ribby-calibration-outer:'+g).encode()).hexdigest()[:8],16)%5 for g in groups])
inner=np.array([int(hashlib.sha256(('ribby-calibration-inner:'+g).encode()).hexdigest()[:8],16)%3 for g in groups])
normalize=lambda x:x/np.maximum(np.linalg.norm(x,axis=-1,keepdims=True),1e-12)

def probabilities(scores,temperature):
    z=(scores-scores.max(axis=1,keepdims=True))/temperature
    exp=np.exp(z);return exp/exp.sum(axis=1,keepdims=True)

def fit_temperature(scores,target):
    def loss(log_temperature):
        p=probabilities(scores,math.exp(log_temperature))
        return float(-np.log(np.maximum(p[np.arange(len(target)),target],1e-15)).mean())
    # One positive parameter, bounded away from underflow/extreme predictions.
    lo,hi=math.log(.005),math.log(2.)
    ratio=(math.sqrt(5)-1)/2
    for _ in range(70):
        a,b=hi-ratio*(hi-lo),lo+ratio*(hi-lo)
        if loss(a)<loss(b):hi=b
        else:lo=a
    return math.exp((lo+hi)/2)

def metrics(scores,target,probs):
    predicted=scores.argmax(axis=1);correct=(predicted==target).astype(float)
    raw=scores.max(axis=1);confidence=probs[np.arange(len(target)),predicted]
    def top(p):
        ece=0;bins=[]
        for index in range(10):
            selected=(p>=index/10)&(p<((index+1)/10) if index<9 else p<=1)
            n=int(selected.sum())
            if not n:continue
            avg=float(p[selected].mean());acc=float(correct[selected].mean())
            ece+=n/len(target)*abs(avg-acc)
            bins.append(dict(lower=index/10,upper=(index+1)/10,n=n,mean=avg,accuracy=acc))
        clipped=np.clip(p,1e-12,1-1e-12)
        return dict(mean=float(p.mean()),brier=float(((p-correct)**2).mean()),
            binary_logloss=float(-(correct*np.log(clipped)+(1-correct)*np.log(1-clipped)).mean()),ece10=ece,bins=bins)
    return dict(n=len(target),correct=int(correct.sum()),raw_as_chance=top(raw),calibrated=top(confidence),
        multiclass_logloss=float(-np.log(np.maximum(probs[np.arange(len(target)),target],1e-15)).mean()))

def get_scores(features,train_indices,test_indices):
    train=features[train_indices];y=labels[train_indices]
    means=np.array([train[y==c].mean(axis=0) for c in range(14)])
    center=means.mean(axis=0);balance=np.sqrt(len(y)/(14*np.bincount(y,minlength=14)[y]))
    x=(train-center)*balance[:,None];targets=(np.eye(14)[y]-1/14)*balance[:,None]
    weights=np.linalg.solve(x.T@x+np.eye(features.shape[1]),x.T@targets)
    query=normalize((features[test_indices]-center)@weights)
    result={}
    for limit in (8,16,32):
        prototypes=np.array([features[train_indices[y==c][:limit]].mean(axis=0) for c in range(14)])
        result[limit]=(1+query@normalize((prototypes-center)@weights).T)/2
    return result

output={'version':1,'method':'temperature-scaling','metric_sha256':hashlib.sha256((ROOT/'image_metric.json').read_bytes()).hexdigest(),
    'metric_training_sha256':metric['training_manifest_sha256'],'training_photos':len(refs),
    'scope':'Closed set of the 14 trained species; exact public reference sets; no private photos',
    'species':[s['sci'].casefold() for s in manifest],'reference_sets':{str(n):{s['sci'].casefold():[r['id'] for r in s['references'][:n]] for s in manifest} for n in (8,16,32)},'models':{}}
report={'design':'Nested five outer / three inner photographer-grouped folds; frozen V3 alpha=1; probe and previous holdouts never used for fitting',
    'metric_sha256':output['metric_sha256'],'models':{}}
for model in ('bioclip','dinov2'):
    config=metric['models'][model];assert config['method']=='metric' and config['alpha']==1
    key=config['model_key'];features=np.array([json.loads((ROOT/'accuracy_work/v3/references/image_vectors'/key/(r['id']+'.json')).read_text(encoding='utf-8'))['vector'] for r in refs])
    oof={n:np.zeros((len(refs),14)) for n in (8,16,32)}
    nested_probs={n:np.zeros((len(refs),14)) for n in (8,16,32)}
    nested_temperatures={n:[] for n in (8,16,32)}
    for fold in range(5):
        training=np.flatnonzero(outer!=fold);testing=np.flatnonzero(outer==fold)
        assert set(groups[i] for i in training).isdisjoint(groups[i] for i in testing)
        outer_scores=get_scores(features,training,testing)
        inner_scores={n:np.zeros((len(refs),14)) for n in (8,16,32)}
        for f in range(3):
            tr=np.flatnonzero((outer!=fold)&(inner!=f));te=np.flatnonzero((outer!=fold)&(inner==f))
            assert len(tr) and len(te)
            assert set(groups[i] for i in tr).isdisjoint(groups[i] for i in testing)
            assert set(groups[i] for i in tr).isdisjoint(groups[i] for i in te)
            scores=get_scores(features,tr,te)
            for n in (8,16,32):inner_scores[n][te]=scores[n]
        for n in (8,16,32):
            temperature=fit_temperature(inner_scores[n][training],labels[training])
            nested_temperatures[n].append(temperature)
            oof[n][testing]=outer_scores[n]
            nested_probs[n][testing]=probabilities(outer_scores[n],temperature)
        print('CALIBRATION',model,'outer fold',fold+1,'/5',flush=True)
    profiles={};rows={}
    for n in (8,16,32):
        temperature=fit_temperature(oof[n],labels)
        profiles[str(n)]={'temperature':temperature,'samples':len(refs),'species_count':14,'model_key':key}
        rows[str(n)]={**metrics(oof[n],labels,nested_probs[n]),'final_temperature':temperature,'nested_temperatures':nested_temperatures[n]}
    output['models'][model]={'model_key':key,'profiles':profiles}
    report['models'][model]=rows
    np.savez_compressed(WORK/(model+'_oof.npz'),labels=labels,outer=outer,**{f'scores_{n}':oof[n] for n in (8,16,32)})
    print('NESTED RESULT',model,json.dumps({n:{'raw_brier':r['raw_as_chance']['brier'],'calibrated_brier':r['calibrated']['brier'],'temperature':r['final_temperature']} for n,r in rows.items()}),flush=True)
canonical=json.dumps(output,sort_keys=True,separators=(',',':')).encode()
output['id']='temperature-v1:'+hashlib.sha256(canonical).hexdigest()
(ROOT/'image_calibration.json').write_text(json.dumps(output,separators=(',',':'))+'\n',encoding='utf-8')
if '--embed' in sys.argv:
    app=ROOT/'ribby_app.html'
    replacement=('const IMAGE_CALIBRATION = '+json.dumps(output,separators=(',',':'))+';').encode('utf-8')
    code,count=re.subn(rb'const IMAGE_CALIBRATION = [^\r\n]*;',lambda match:replacement,app.read_bytes(),count=1)
    assert count==1
    app.write_bytes(code)
(ROOT/'reports/calibration_training_v4.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('Calibration frozen:',output['id'],flush=True)
