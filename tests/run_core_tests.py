"""Run core tests and retain a machine-readable result for the release report."""
import hashlib
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern='test_images.py')
result=unittest.TextTestRunner(verbosity=1).run(suite)
report={'finished_at':datetime.now(timezone.utc).isoformat(),'tests':result.testsRun,'passed':result.testsRun-len(result.failures)-len(result.errors),'failures':[str(t) for t,_ in result.failures],'errors':[str(t) for t,_ in result.errors],'pass':result.wasSuccessful(),'sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ('ribby_app.html','ribby_server.py','ribby_images.py')}}
(ROOT/'reports/system_core_tests.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
sys.exit(0 if result.wasSuccessful() else 1)
