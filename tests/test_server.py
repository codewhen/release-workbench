import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from release_workbench.config import render_yaml
from release_workbench.server import App,make_server
from test_engine import workflow,command

class ServerTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name).resolve();self.file=self.root/'release-workbench.yaml';self.file.write_text(render_yaml(workflow([command('test')])));self.app=App(self.file);self.server=make_server(self.app,0);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.url=f'http://127.0.0.1:{self.server.server_port}'
 def tearDown(self):self.app.engine.stop();self.server.shutdown();self.server.server_close();self.thread.join();self.temp.cleanup()
 def request(self,path,data=None,token=True,headers=None):
  payload=json.dumps(data).encode() if data is not None else None
  request=Request(self.url+path,data=payload,headers={'Content-Type':'application/json',**({'X-Workbench-Token':self.server.token} if token else {}),**(headers or {})})
  return urlopen(request,timeout=5)
 def test_csrf_origin_and_host_protection(self):
  for headers,token in [({},False),({'Origin':'https://untrusted.example'},True),({'Host':'untrusted.example'},True)]:
   with self.assertRaises(HTTPError) as error:self.request('/api/run',{},token,headers)
   self.assertEqual(error.exception.code,403);error.exception.close()
 def test_preview_never_executes_and_invalid_save_is_atomic(self):
  old=self.app.config();steps=old['workflow'];steps['steps'][0]['commands'][0]['argv'][-1]='raise SystemExit(8)'
  self.request('/api/preview',{});self.assertFalse(self.app.engine.state['steps']['test']['attempts'])
  with self.assertRaises(HTTPError) as error:self.request('/api/save',{'workflow':{'version':2},'revision':old['revision']})
  error.exception.close()
  self.assertEqual(self.app.config()['revision'],old['revision'])
 def test_external_edits_and_active_workflow_block_saving(self):
  old=self.app.config();self.file.write_text(self.file.read_text()+'\n# external edit\n')
  with self.assertRaises(HTTPError) as error:self.request('/api/save',{'workflow':old['workflow'],'revision':old['revision']})
  error.exception.close()
 def test_report_paths_do_not_allow_escape_or_unconfigured_files(self):
  self.root.joinpath('private.txt').write_text('private')
  for path in ('/files/private.txt','/files/../outside.txt'):
   with self.assertRaises(HTTPError) as error:self.request(path)
   error.exception.close()
 def test_report_html_is_sandboxed(self):
  relative=self.app.engine.directory.relative_to(self.root).as_posix()+'/report.html'
  response=self.request('/files/'+relative)
  self.assertEqual(response.headers['Content-Security-Policy'],'sandbox');self.assertTrue(response.read())
 def test_browser_saves_the_same_configuration_as_yaml(self):
  old=self.app.config();new=old['workflow'];new['name']='Configured in browser'
  saved=json.load(self.request('/api/save',{'workflow':new,'revision':old['revision']}))
  self.assertEqual(saved['workflow'],self.app.config()['workflow']);self.assertEqual(saved['workflow']['name'],'Configured in browser')

 def test_library_actions_are_authenticated_and_workflow_scoped(self):
  with self.assertRaises(HTTPError) as error:self.request('/api/library/create',{'project':'invalid','name':'Other','filename':'other.yaml'},token=False)
  self.assertEqual(error.exception.code,403);error.exception.close()
  catalog=json.load(self.request('/api/library'));project=catalog['projects'][0]['id']
  created=json.load(self.request('/api/library/create',{'project':project,'name':'Other','filename':'release-workbench-other.yaml'}))
  other=json.load(self.request('/api/config?workflow='+created['id']))
  self.assertEqual(other['workflow']['name'],'Other');self.assertEqual(self.app.config()['workflow']['name'],'Example workflow')
  with self.assertRaises(HTTPError) as error:self.request('/api/config?workflow=unknown')
  error.exception.close()
 def test_library_report_routes_use_selected_workflow(self):
  catalog=json.load(self.request('/api/library'));created=json.load(self.request('/api/library/create',{'project':catalog['projects'][0]['id'],'name':'Other','filename':'release-workbench-other.yaml'}))
  state=json.load(self.request('/api/state?workflow='+created['id']));relative=state['directory']+'/report.html'
  response=self.request('/files/'+relative+'?workflow='+created['id']);self.assertTrue(response.read())
