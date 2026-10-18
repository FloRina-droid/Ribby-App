import os
import sys
import json
import re
from pathlib import Path
from urllib.parse import urlparse

root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root))
work=Path(os.environ.get('RIBBY_ACCURACY_WORKSPACE',str(root/'accuracy_work')))
work.mkdir(parents=True,exist_ok=True)
data_dir=Path(os.environ.get('RIBBY_ACCURACY_DATA_DIR',str(root/'ribby_data')))
os.environ['RIBBY_DATA_DIR']=str(work/'server_data')
os.environ['RIBBY_DISABLE_SEED']='1'
import ribby_server as server

class Handler(server.RibbyHandler):
    def send_common_headers(self):
        super().send_common_headers()
        self.send_header('Cross-Origin-Opener-Policy','same-origin')
        self.send_header('Cross-Origin-Embedder-Policy','require-corp')
    def do_GET(self):
        path=urlparse(self.path).path
        if path=='/benchmark-manifest':
            catalog=json.loads((root/'image_reference_catalog.json').read_text(encoding='utf-8'))
            rows=[]
            for species in catalog:
                import hashlib
                key=hashlib.sha256(species['sci'].casefold().encode()).hexdigest()
                data=json.loads((data_dir/'image_refs'/f'query_{key}.json').read_text(encoding='utf-8'))
                refs=[r for r in data['references'] if (data_dir/'image_refs'/f"{r['id']}.bin").exists()]
                rows.append({**species,'references':refs})
            self.send_json(rows);return
        if path.startswith('/benchmark-image/'):
            ref_id=path.split('/')[-1]
            if not re.fullmatch('[a-f0-9]{32}',ref_id):self.send_json({},400);return
            data=data_dir/'image_refs'/f'{ref_id}.bin'
            if not data.exists():self.send_json({},404);return
            self.send_file(data,server.ribby_images.image_mime(data.read_bytes()));return
        super().do_GET()

print('Benchmark server: http://127.0.0.1:7434',flush=True)
server.ThreadingHTTPServer(('127.0.0.1',7434),Handler).serve_forever()
