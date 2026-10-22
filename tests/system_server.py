"""Isolated full-catalog test server; never reads the user's Ribby database."""
import json
import os
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
DATA=Path(os.environ.get('RIBBY_SYSTEM_DATA',str(ROOT/'dev/system_data'))).resolve()
os.environ['RIBBY_DATA_DIR']=str(DATA)
os.environ['RIBBY_ADMIN_EMAIL']='admin@ribby.test'
os.environ['RIBBY_ADMIN_PASSWORD']='SystemTestOnly2026!'
import ribby_server as server

server.ensure_default_admin()
for identifier in ('field','other'):
    server.save_item(DATA/'users',{'id':identifier,'name':identifier,'email':identifier+'@ribby.test','password':server.hash_pw('SystemTestOnly2026!'),'role':'user'})
for species in json.loads((ROOT/'image_reference_catalog.json').read_text(encoding='utf-8')):
    server.save_item(DATA/'species',species)
copied=server.ribby_images.install_reference_seed(DATA,ROOT/'ribby_image_seed.zip')
# Freeze only the isolated test corpus; production keeps its normal source refresh.
for query in (DATA/'image_refs').glob('query_*.json'):
    payload=json.loads(query.read_text(encoding='utf-8'));payload['fetched_at']=time.time();query.write_text(json.dumps(payload,ensure_ascii=False),encoding='utf-8')
class QuietHandler(server.RibbyHandler):
    def log_message(self,*args):pass
print(f'Isolated system server http://127.0.0.1:7436; public seed files installed: {copied}',flush=True)
server.ThreadingHTTPServer(('127.0.0.1',7436),QuietHandler).serve_forever()
