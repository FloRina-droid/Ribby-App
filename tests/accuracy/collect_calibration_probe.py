"""Freeze up to 70 new photos, retaining strict photographer separation."""
import hashlib
import json
import sys
import time
from pathlib import Path
from urllib.parse import urlencode

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import ribby_images as images
from dataset_utils import author_keys

WORK=ROOT/'accuracy_work/calibration';DATA=WORK/'probe';API=WORK/'api'
(DATA/'image_refs').mkdir(parents=True,exist_ok=True);API.mkdir(parents=True,exist_ok=True)
catalog=json.loads((ROOT/'image_reference_catalog.json').read_text(encoding='utf-8'))
train=json.loads((ROOT/'reports/reference_manifest_v3.json').read_text(encoding='utf-8'))
known=[r for sp in train for r in sp['references']]
for filename in ('accuracy_test_manifest.json','accuracy_holdout_v3.json'):
    known+=json.loads((ROOT/'reports'/filename).read_text(encoding='utf-8'))
output=WORK/'probe_manifest.json'
rows=json.loads(output.read_text(encoding='utf-8')) if output.exists() else []
blocked=known+rows
ids={r['canonical_id'] for r in blocked};obs={r.get('observation_id') for r in blocked if r.get('observation_id')}
authors=set().union(*(author_keys(r) for r in blocked))

def candidates(sp,page):
    old=ROOT/'accuracy_work/v3/api'/f"{sp['id']}_{page}.json"
    cache=API/f"{sp['id']}_{page}.json"
    if cache.exists():return json.loads(cache.read_text(encoding='utf-8'))
    if old.exists():return json.loads(old.read_text(encoding='utf-8'))
    taxon=next(r['taxon_id'] for r in known if r['scientific_name']==sp['sci'] and r.get('taxon_id'))
    params=dict(taxon_id=taxon,quality_grade='research',photos='true',photo_license='cc0,cc-by',captive='false',per_page=100,order_by='created_at',order='desc',page=page)
    data=images.fetch_json('https://api.inaturalist.org/v1/observations?'+urlencode(params));result=[]
    for observation in data.get('results',[]):
        if observation.get('quality_grade')!='research' or images.taxon_key(observation.get('taxon',{}).get('name'))!=images.taxon_key(sp['sci']):continue
        for photo in observation.get('photos',[]):
            lic=images.license_info(photo.get('license_code'));url=photo.get('url','').replace('/square.','/medium.')
            creator=images.plain(photo.get('attribution'));photo_id=photo.get('id')
            if not lic or not creator or not str(photo_id).isdigit() or not images.safe_url(url,images.IMAGE_HOSTS):continue
            identity='inat:'+str(photo_id)
            result.append({**lic,'id':hashlib.sha256(identity.encode()).hexdigest()[:32],'canonical_id':identity,
                'species_id':sp['id'],'scientific_name':sp['sci'],'creator':creator,'creator_id':observation.get('user',{}).get('id'),
                'observation_id':observation['id'],'provider':'iNaturalist','taxon_id':taxon,'taxon_verified':'research-grade-exact-taxon',
                'title':sp['sci'],'source_url':f'https://www.inaturalist.org/photos/{photo_id}','url':url,
                'original_url':url.replace('/medium.','/original.'),'retrieved_at':time.time()})
            break
    cache.write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8');return result

for sp in catalog:
    selected=[r for r in rows if r['species_id']==sp['id']]
    if len(selected)==5:continue
    for page in (5,6,7,8,9,10,3,4,2,1,*range(11,21)):
        for ref in candidates(sp,page):
            if ref['canonical_id'] in ids or ref['observation_id'] in obs or author_keys(ref)&authors:continue
            if not images.license_info(ref.get('license_url')) or not images.safe_url(ref.get('url'),images.IMAGE_HOSTS):continue
            (DATA/'image_refs'/(ref['id']+'.json')).write_text(json.dumps(ref,ensure_ascii=False),encoding='utf-8')
            try:images.reference_file(DATA,ref['id'])
            except Exception as error:print('SKIP',ref['id'],str(error),flush=True);continue
            selected.append(ref);rows.append(ref);ids.add(ref['canonical_id']);obs.add(ref['observation_id']);authors.update(author_keys(ref))
            if len(selected)==5:break
        if len(selected)==5:break
    if len(selected)<3:raise RuntimeError(f"Only {len(selected)} new independent photos for {sp['sci']}")
    output.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('NEW PROBE',sp['sci'],len(selected),flush=True)
assert 42<=len(rows)<=70
(ROOT/'reports/accuracy_calibration_probe.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Frozen new calibration probe:',len(rows),'photos; no labels used for fitting',flush=True)
