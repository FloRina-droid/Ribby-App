"""Bind calibration scope to the frozen photo bytes, without fitting parameters."""
import hashlib
import json
import re
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import ribby_images as images

calibration = json.loads((ROOT/'image_calibration.json').read_text(encoding='utf-8'))
manifest = json.loads((ROOT/'reports/reference_manifest_v3.json').read_text(encoding='utf-8'))
keys = list(images.VECTOR_MODELS)
hashes = {}
with images.reference_seed_archive(ROOT/'ribby_image_seed.zip') as archive:
    for species in manifest:
        for ref in species['references']:
            photo = archive.read('image_refs/'+ref['id']+'.bin')
            digest = hashlib.sha256(photo).hexdigest()
            for key in keys:
                vector = json.loads(archive.read('image_vectors/'+key+'/'+ref['id']+'.json'))
                assert vector['image_sha256'] == digest
            assert ref['id'] not in hashes
            hashes[ref['id']] = digest
assert len(hashes) == 896
payload = {'version':1, 'calibration_id':calibration['id'], 'images':hashes}
payload['id'] = 'reference-integrity-v1:'+hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
(ROOT/'image_reference_integrity.json').write_text(json.dumps(payload,indent=2)+'\n',encoding='utf-8')
app = ROOT/'ribby_app.html'
replacement = ('const IMAGE_REFERENCE_INTEGRITY = '+json.dumps(payload,separators=(',',':'))+';').encode()
code = app.read_bytes()
if b'const IMAGE_REFERENCE_INTEGRITY = ' in code:
    code, count = re.subn(rb'const IMAGE_REFERENCE_INTEGRITY = [^\r\n]*;', lambda _:replacement, code, count=1)
    assert count == 1
else:
    marker = b'function imageCosine('
    assert code.count(marker) == 1
    code = code.replace(marker, replacement+b'\n'+marker, 1)
app.write_bytes(code)
print(json.dumps({'pass':True,'photos':len(hashes),'id':payload['id'],'calibration_parameters_unchanged':True}))
