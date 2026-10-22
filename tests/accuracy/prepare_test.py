"""Download the frozen 28-image evaluation set, retaining per-photo licenses."""
from pathlib import Path
import os
import sys
import json
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root))
import ribby_images
work=Path(os.environ.get('RIBBY_ACCURACY_WORKSPACE',str(root/'accuracy_work')))
target=work/'test_data';(target/'image_refs').mkdir(parents=True,exist_ok=True)
manifest=json.loads((root/'reports/accuracy_test_manifest.json').read_text(encoding='utf-8'))
for ref in manifest:
    (target/'image_refs'/f"{ref['id']}.json").write_text(json.dumps(ref,ensure_ascii=False),encoding='utf-8')
    ribby_images.reference_file(target,ref['id'])
(target/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False),encoding='utf-8')
print('Prepared',len(manifest),'frozen CC0/CC-BY test images')
