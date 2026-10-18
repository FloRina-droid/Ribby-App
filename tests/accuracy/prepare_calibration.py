"""Download the frozen independent V4 probe; do not fit or tune anything."""
import hashlib
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import ribby_images as images
WORK=ROOT/'accuracy_work/calibration';target=WORK/'probe/image_refs';target.mkdir(parents=True,exist_ok=True)
raw=(ROOT/'reports/accuracy_calibration_probe.json').read_bytes()
refs=json.loads(raw.decode('utf-8'));(WORK/'probe_manifest.json').write_bytes(raw)
for index,ref in enumerate(refs):
    assert images.license_info(ref['license_url'])
    (target/(ref['id']+'.json')).write_text(json.dumps(ref,ensure_ascii=False),encoding='utf-8')
    images.reference_file(WORK/'probe',ref['id'])
print('Prepared',len(refs),'frozen licensed probe photos')
