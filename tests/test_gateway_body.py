import ast,io,os,unittest
from pathlib import Path
class GatewayBodyTests(unittest.TestCase):
 def body(self,payload):
  source=Path(os.environ.get('RIBBY_GATEWAY_TEST_SOURCE',str(Path(__file__).resolve().parents[1]/'toolbox'/'ribby_gateway.py')))
  if not source.exists(): source=source.parents[1]/'ribby_gateway.py'
  tree=ast.parse(source.read_text(encoding='utf-8'));node=next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=='SizedRequestBody');ns={};exec(compile(ast.Module(body=[node],type_ignores=[]),'gateway','exec'),ns)
  stream=io.BytesIO(payload);return stream,ns['SizedRequestBody'](stream,len(payload))
 def test_body_streams_exact_bytes_in_bounded_chunks(self):
  payload=b'x'*150000;stream,body=self.body(payload);self.assertEqual(len(body),len(payload));self.assertEqual(stream.tell(),0);chunks=list(body);self.assertEqual(b''.join(chunks),payload);self.assertLessEqual(max(map(len,chunks)),65536)
 def test_requests_retains_length_without_chunked_encoding(self):
  try: import requests
  except ImportError: self.skipTest('requests belongs to the optional Toolbox gateway runtime')
  payload=b'x'*150000;stream,body=self.body(payload);prepared=requests.Request('POST','http://app/api/images/features',data=body).prepare()
  self.assertEqual(stream.tell(),0);self.assertEqual(prepared.headers['Content-Length'],str(len(payload)));self.assertNotIn('Transfer-Encoding',prepared.headers);self.assertEqual(b''.join(prepared.body),payload)
if __name__=='__main__':unittest.main()
