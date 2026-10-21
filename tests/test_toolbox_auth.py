import os,tempfile,json,threading,unittest,sys
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from http.server import ThreadingHTTPServer
ROOT=Path(__file__).resolve().parents[1]
class ToolboxAuthTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory();cls.data=Path(cls.temp.name);cls.key='a'*64;(cls.data/'key').write_text(cls.key)
  os.environ.update(RIBBY_DATA_DIR=str(cls.data/'data'),RIBBY_DISABLE_SEED='1',RIBBY_TOOLBOX_AUTH='1',RIBBY_TOOLBOX_SECRET_FILE=str(cls.data/'key'))
  sys.path.insert(0,str(ROOT));import ribby_server;cls.mod=ribby_server
  (ribby_server.DATA_DIR/'users'/'admin.json').write_text(json.dumps({'id':'admin','name':'Existing Admin','email':'admin@ribby.app','role':'admin','password':'never-expose'}))
  cls.http=ThreadingHTTPServer(('127.0.0.1',0),ribby_server.RibbyHandler);cls.thread=threading.Thread(target=cls.http.serve_forever,daemon=True);cls.thread.start();cls.base='http://127.0.0.1:'+str(cls.http.server_port)
 @classmethod
 def tearDownClass(cls):cls.http.shutdown();cls.http.server_close();cls.temp.cleanup()
 def call(self,path,headers=None,method='GET'):
  req=Request(self.base+path,headers=headers or {},method=method,data=b'{}' if method=='POST' else None)
  try:
   with urlopen(req) as r:return r.status,r.read()
  except HTTPError as e:return e.code,e.read()
 def test_direct_access_and_old_bearer_are_denied(self):
  for headers in [{},{'Authorization':'Bearer '+'b'*64},{'X-Ribby-Toolbox-Key':'wrong'}]:
   for path in ['/','/api/species','/api/auth/toolbox','/api/me']:self.assertEqual(self.call(path,headers)[0],401)
 def test_valid_bridge_returns_existing_account_without_password_or_token(self):
  status,body=self.call('/api/auth/toolbox',{'X-Ribby-Toolbox-Key':self.key});self.assertEqual(status,200);d=json.loads(body);self.assertTrue(d['toolbox']);self.assertEqual(d['user']['id'],'admin');self.assertNotIn('password',d['user']);self.assertNotIn('token',d)
 def test_trusted_page_enables_toolbox_mode_and_uses_original_logo(self):
  status,body=self.call('/',{'X-Ribby-Toolbox-Key':self.key});self.assertEqual(status,200);self.assertIn(b'window.RIBBY_TOOLBOX_AUTH=true;',body);self.assertIn(b'<link rel="icon" type="image/jpeg" href="data:image/jpeg;base64,',body)
 def test_standalone_page_keeps_normal_login_mode(self):
  os.environ['RIBBY_TOOLBOX_AUTH']='0'
  try:
   status,body=self.call('/');self.assertEqual(status,200);self.assertNotIn(b'window.RIBBY_TOOLBOX_AUTH=true;',body)
  finally:os.environ['RIBBY_TOOLBOX_AUTH']='1'
 def test_password_login_disabled_in_toolbox_mode(self):self.assertEqual(self.call('/api/auth/login',{'X-Ribby-Toolbox-Key':self.key},'POST')[0],403)
 def test_missing_key_fails_closed(self):
  p=self.data/'key';p.unlink()
  try:self.assertEqual(self.call('/api/me',{'X-Ribby-Toolbox-Key':self.key})[0],401)
  finally:p.write_text(self.key)
if __name__=='__main__':unittest.main()
