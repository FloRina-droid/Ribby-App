"""Reproduce Git-sized seed parts and their integrity manifest (stdlib only)."""
import argparse
import hashlib
import json
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--seed', type=Path, default=Path('ribby_image_seed.zip'))
args = parser.parse_args()
seed = args.seed.resolve()
parts = []
digest = hashlib.sha256()
with seed.open('rb') as source:
    while block := source.read(48 * 1024 * 1024):
        name = f'{seed.name}.part{len(parts) + 1:03d}'
        part = seed.with_name(name)
        part.write_bytes(block)
        parts.append({'name': name, 'bytes': len(block), 'sha256': hashlib.sha256(block).hexdigest()})
        digest.update(block)
if not parts:
    raise ValueError('Seed ist leer')
expected = {part['name'] for part in parts}
extra = {p.name for p in seed.parent.glob(seed.name + '.part*')} - expected
if extra:
    raise ValueError('Unerwartete alte Teile vorhanden; vor Veröffentlichung prüfen: ' + ', '.join(sorted(extra)))
manifest = {'version': 1, 'bytes': sum(p['bytes'] for p in parts), 'sha256': digest.hexdigest(), 'parts': parts}
seed.with_name(seed.name + '.manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
print(json.dumps(manifest))
