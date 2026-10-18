"""Build a larger licensed corpus and a photographer-disjoint frozen holdout.

Existing 28 test photographs and their known creators remain excluded from new
references. No images from the new holdout are used to select the ranking rule.
"""
import hashlib
import json
import re
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import ribby_images as images
from dataset_utils import author_name, author_keys

WORK = ROOT / 'accuracy_work' / 'v3'
DATA = WORK / 'references'
TEST = WORK / 'holdout'
API_CACHE = WORK / 'api'
for folder in (DATA / 'image_refs', TEST / 'image_refs', API_CACHE):
    folder.mkdir(parents=True, exist_ok=True)

def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

catalog = json.loads((ROOT / 'image_reference_catalog.json').read_text(encoding='utf-8'))
old_test = json.loads((ROOT / 'reports/accuracy_test_manifest.json').read_text(encoding='utf-8'))
old = {}
baseline_path=ROOT/'reports/reference_manifest_v2.json'
baseline={s['id']:s['references'] for s in json.loads(baseline_path.read_text(encoding='utf-8'))} if baseline_path.exists() else None
for sp in catalog:
    key = hashlib.sha256(sp['sci'].casefold().encode()).hexdigest()
    old[sp['id']] = baseline[sp['id']] if baseline else json.loads((ROOT / 'reference_data/image_refs' / f'query_{key}.json').read_text(encoding='utf-8'))['references']
old_refs = [r for refs in old.values() for r in refs]
known = old_refs + old_test
known_ids = {images.photo_identity(r) for r in known}
known_obs = {r.get('observation_id') for r in known if r.get('observation_id')}
known_authors = set().union(*(author_keys(r) for r in known))

def candidates(sp, page):
    cache = API_CACHE / f"{sp['id']}_{page}.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding='utf-8'))
    taxon_id = next(r['taxon_id'] for r in old[sp['id']] if r.get('taxon_id'))
    params = dict(taxon_id=taxon_id, quality_grade='research', photos='true',
                  photo_license='cc0,cc-by', captive='false', per_page=100,
                  order_by='created_at', order='desc', page=page)
    response = images.fetch_json('https://api.inaturalist.org/v1/observations?' + urlencode(params))
    result = []
    for obs in response.get('results', []):
        if images.taxon_key(obs.get('taxon', {}).get('name')) != images.taxon_key(sp['sci']):
            continue
        if obs.get('quality_grade') != 'research':
            continue
        for photo in obs.get('photos', []):
            lic = images.license_info(photo.get('license_code'))
            url = photo.get('url', '').replace('/square.', '/medium.')
            creator = images.plain(photo.get('attribution'))
            photo_id = photo.get('id')
            if not lic or not creator or not str(photo_id).isdigit() or not images.safe_url(url, images.IMAGE_HOSTS):
                continue
            identity = 'inat:' + str(photo_id)
            result.append({**lic, 'id': hashlib.sha256(identity.encode()).hexdigest()[:32],
                'canonical_id': identity, 'species_id': sp['id'], 'scientific_name': sp['sci'],
                'creator': creator, 'creator_id': obs.get('user', {}).get('id'),
                'observation_id': obs['id'], 'provider': 'iNaturalist', 'taxon_id': taxon_id,
                'taxon_verified': 'research-grade-exact-taxon', 'title': sp['sci'],
                'source_url': f'https://www.inaturalist.org/photos/{photo_id}',
                'url': url, 'original_url': url.replace('/medium.', '/original.'), 'retrieved_at': time.time()})
            break
    write(cache, result)
    return result

def download(folder, ref):
    meta = folder / 'image_refs' / (ref['id'] + '.json')
    write(meta, ref)
    for attempt in range(3):
        try:
            images.reference_file(folder, ref['id'])
            return True
        except Exception as error:
            if attempt == 2:
                print('DOWNLOAD SKIP', ref['id'], str(error), flush=True)
    return False

# Freeze a genuinely new holdout first, keeping its photographers out of training.
holdout_file = WORK / 'holdout_manifest.json'
if holdout_file.exists():
    holdout = json.loads(holdout_file.read_text(encoding='utf-8'))
else:
    holdout = []
    banned_authors = set(known_authors)
    for sp in catalog:
        selected = []
        for page in (5, 6, 7, 8, 9, 10, 3, 4, 2, 1):
            for ref in candidates(sp, page):
                if images.photo_identity(ref) in known_ids or ref['observation_id'] in known_obs or author_keys(ref) & banned_authors:
                    continue
                if not download(TEST, ref):
                    continue
                selected.append(ref)
                banned_authors.update(author_keys(ref))
                known_ids.add(images.photo_identity(ref)); known_obs.add(ref['observation_id'])
                if len(selected) == 8:
                    break
            if len(selected) == 8:
                break
        if len(selected) != 8:
            raise RuntimeError(f"Only {len(selected)} independent holdout photos for {sp['sci']}")
        holdout.extend(selected)
        print('HOLDOUT', sp['sci'], len(selected), flush=True)
    write(holdout_file, holdout)
write(TEST / 'manifest.json', holdout)
blocked = old_test + holdout
blocked_authors = set().union(*(author_keys(r) for r in blocked))
blocked_ids = {images.photo_identity(r) for r in blocked}
blocked_obs = {r.get('observation_id') for r in blocked if r.get('observation_id')}
training, downloads = [], []
for sp in catalog:
    selected = list(old[sp['id']])
    identities = {images.photo_identity(r) for r in selected}
    observations = {r.get('observation_id') for r in selected if r.get('observation_id')}
    creator_counts = {}
    for ref in selected:
        name = author_name(ref); creator_counts[name] = creator_counts.get(name, 0) + 1
    for page in range(1, 11):
        for ref in candidates(sp, page):
            identity = images.photo_identity(ref)
            if identity in identities or identity in blocked_ids or ref['observation_id'] in observations or ref['observation_id'] in blocked_obs or author_keys(ref) & blocked_authors:
                continue
            name = author_name(ref)
            if creator_counts.get(name, 0) >= 3:
                continue
            # Download before accepting an item so frozen manifests are complete.
            if not download(DATA, ref):
                continue
            selected.append(ref); identities.add(identity); observations.add(ref['observation_id'])
            creator_counts[name] = creator_counts.get(name, 0) + 1
            if len(selected) == 64:
                break
        if len(selected) == 64:
            break
    if len(selected) != 64:
        raise RuntimeError(f"Only {len(selected)} references for {sp['sci']}")
    for ref in selected:
        for suffix in ('.json', '.bin'):
            source = ROOT / 'reference_data/image_refs' / (ref['id'] + suffix)
            target = DATA / 'image_refs' / source.name
            if source.exists() and not target.exists():
                shutil.copy2(source, target)
        for folder in (ROOT / 'reference_data/image_vectors').iterdir():
            source = folder / (ref['id'] + '.json')
            if source.exists():
                target = DATA / 'image_vectors' / folder.name / source.name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
    # Round robin authors; the whole 64-item corpus remains available for selection.
    selected = images.diverse_photos(selected, 64)
    key = hashlib.sha256(sp['sci'].casefold().encode()).hexdigest()
    write(DATA / 'image_refs' / f'query_{key}.json', dict(references=selected, warnings=[],
        fetched_at=time.time(), version=images.CACHE_VERSION,
        creators=len({author_name(r) for r in selected})))
    training.append({**sp, 'references': selected})
    write(WORK / 'training_manifest.json', training)
    print('REFERENCES', sp['sci'], len(selected), 'creators', len(creator_counts), flush=True)

refs = [r for sp in training for r in sp['references']]
assert len({r['id'] for r in refs}) == 896
assert not ({images.photo_identity(r) for r in refs} & blocked_ids)
assert not ({r.get('observation_id') for r in refs if r.get('observation_id')} & blocked_obs)
assert not (set().union(*(author_keys(r) for r in refs)) & blocked_authors)
write(WORK / 'dataset_summary.json', dict(reference_photos=len(refs), new_holdout=len(holdout),
    previous_holdout=len(old_test), licenses=sorted({r['license'] for r in refs + holdout}),
    disjoint_by=['canonical_photo_id', 'observation_id', 'normalized_creator_name', 'inaturalist_creator_id']))
print('EXPANSION COMPLETE', len(refs), 'references;', len(holdout), 'new test photos', flush=True)
