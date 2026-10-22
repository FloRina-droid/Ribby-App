"""Verify the complete multipart release and normal server startup without a ZIP."""
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import ribby_images as images

manifest = json.loads((ROOT/'ribby_image_seed.zip.manifest.json').read_text(encoding='utf-8'))
assert len(manifest['parts']) == 3 and all(p['bytes'] < 50 * 1024 * 1024 for p in manifest['parts'])
work = ROOT/'dev'
work.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix='seed-release-', dir=work) as temporary:
    bundle = Path(temporary).resolve()
    assert bundle.is_relative_to(work.resolve())
    for name in ['ribby_server.py', 'ribby_images.py', 'ribby_app.html', 'ribby_image_seed.zip.manifest.json']:
        shutil.copyfile(ROOT/name, bundle/name)
    for part in manifest['parts']:
        source, destination = ROOT/part['name'], bundle/part['name']
        try:
            os.link(source, destination)
        except OSError:
            shutil.copyfile(source, destination)
    assert not (bundle/'ribby_image_seed.zip').exists()
    data = bundle/'data'
    # Start the actual shipping server, not a test replacement for its seed loader.
    with socket.socket() as available:
        available.bind(('127.0.0.1', 0))
        port = available.getsockname()[1]
    env = {**os.environ, 'RIBBY_DATA_DIR': str(data), 'RIBBY_HOST': '127.0.0.1', 'RIBBY_PORT': str(port),
           'RIBBY_ADMIN_EMAIL': 'release@ribby.test', 'RIBBY_ADMIN_PASSWORD': 'ReleaseTestOnly2026!'}
    env.pop('RIBBY_DISABLE_SEED', None)
    with (bundle/'startup.log').open('w', encoding='utf-8') as log:
        process = subprocess.Popen([sys.executable, '-u', str(bundle/'ribby_server.py')], cwd=bundle,
                                   env=env, stdout=log, stderr=log, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        try:
            deadline = time.monotonic() + 45
            while True:
                if process.poll() is not None:
                    raise AssertionError('Release server exited: ' + (bundle/'startup.log').read_text(encoding='utf-8'))
                try:
                    with urlopen(f'http://127.0.0.1:{port}/api/ping', timeout=1) as response:
                        assert json.load(response)['imageRecognition']
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise
                    time.sleep(.2)
            with urlopen(f'http://127.0.0.1:{port}/', timeout=5) as response:
                assert response.read().decode('utf-8') == (ROOT/'ribby_app.html').read_text(encoding='utf-8')
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
    count = 0
    with images.reference_seed_archive(bundle/'ribby_image_seed.zip') as archive:
        assert archive.testzip() is None
        for entry in archive.infolist():
            path = data/entry.filename
            assert path.read_bytes() == archive.read(entry), entry.filename
            count += 1
    photos = len(list((data/'image_refs').glob('*.bin')))
    vectors = len(list((data/'image_vectors').rglob('*.json')))
    assert (photos, vectors) == (896, 1792)
    assert images.install_reference_seed(data, bundle/'ribby_image_seed.zip') == 0
    # All shipped vectors still pass photo-digest, dimension, model and norm checks.
    usable = 0
    for model in images.VECTOR_MODELS:
        for query in (data/'image_refs').glob('query_*.json'):
            refs = json.loads(query.read_text(encoding='utf-8'))
            result = images.with_precomputed_vectors(data, refs, model)
            usable += sum('features' in ref for ref in result['references'])
    assert usable == 1792
report = {'pass': True, 'parts': len(manifest['parts']), 'bytes': manifest['bytes'],
          'archive_sha256': manifest['sha256'], 'complete_file_comparisons': count,
          'photos': photos, 'usable_vectors': usable, 'normal_server_start_without_full_zip': True,
          'repeat_install_copies': 0, 'no_joined_archive_created': True,
          'backend_sha256': hashlib.sha256((ROOT/'ribby_images.py').read_bytes()).hexdigest()}
(ROOT/'reports/release_seed_v5.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
print(json.dumps(report))
