import json,tempfile,time,unittest
from pathlib import Path
from release_workbench.config import render_yaml,validate
from release_workbench.engine import Engine
from release_workbench.templates import make_template,starter_documents
class LoopTests(unittest.TestCase):
 def setup_loop(self,code='import json,os;print(json.dumps({"ready":int(os.environ["WORKBENCH_LOOP_ITERATION"])>=3}))',secret_env=None,**settings):
  temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);root=Path(temp.name)
  body={'version':1,'name':'body','steps':[{'id':'check','name':'check','kind':'command','capture':'json','commands':[{'argv':['${python}','-c',code]}]}]};(root/'body.yaml').write_text(render_yaml(body))
  w={'version':1,'name':'loop','steps':[{'id':'repeat','name':'repeat','kind':'loop','workflow':'body.yaml','loop':{'iterations':5,**settings},'timeout':10},{'id':'after','name':'after','kind':'command','needs':['repeat'],'commands':[{'argv':['${python}','-c','print("after loop")']}]}]};w['secret_env']=secret_env or [];return Engine(root,w)
 def finish(self,e):
  e.start();deadline=time.monotonic()+15
  while e.busy() and time.monotonic()<deadline:time.sleep(.02)
  self.assertFalse(e.busy());return e
 def test_fixed_count_and_following_card(self):
  e=self.finish(self.setup_loop(iterations=3));self.assertEqual(e.exit_code(),0);self.assertEqual(len(e.state['steps']['repeat']['result']['json']['iterations']),3);self.assertEqual(e.state['steps']['after']['status'],'passed')
 def test_until_true_stops_early(self):
  e=self.finish(self.setup_loop(until='steps.check.result.json.ready'));self.assertEqual(e.exit_code(),0);self.assertEqual(len(e.state['steps']['repeat']['result']['json']['iterations']),3)
 def test_limit_failure_retains_partial_evidence(self):
  e=self.finish(self.setup_loop('print("false")',until='steps.check.result.json'));self.assertEqual(e.exit_code(),1);self.assertEqual(e.state['steps']['after']['status'],'blocked');self.assertEqual(len(e.state['steps']['repeat']['result']['json']['iterations']),5);self.assertTrue(e.state['steps']['repeat']['attempts'][0]['reports'])
 def test_body_failure_and_non_boolean_stop_fail(self):
  for code in ['raise SystemExit(4)','print("1")']:
   e=self.finish(self.setup_loop(code,until='steps.check.result.json'));self.assertEqual(e.exit_code(),1)
 def test_cancel_stops_loop_and_blocks_next(self):
  e=self.setup_loop('import time;time.sleep(20);print("true")');e.start();deadline=time.monotonic()+5
  while not e.state['steps']['repeat']['attempts'] and time.monotonic()<deadline:time.sleep(.02)
  time.sleep(.3);e.stop('repeat')
  while e.busy() and time.monotonic()<deadline:time.sleep(.02)
  self.assertFalse(e.busy());self.assertEqual(e.state['steps']['repeat']['status'],'cancelled');self.assertEqual(e.state['steps']['after']['status'],'blocked')
 def test_loop_count_and_success_codes_are_validated(self):
  with self.assertRaises(ValueError):self.setup_loop(iterations=0)
  e=self.setup_loop();e.workflow['steps'][0]['success_codes']=[0,1];self.assertTrue(validate(e.workflow))
 def test_parent_secret_masking_is_inherited_by_body(self):
  from unittest.mock import patch
  with patch.dict('os.environ',{'LOOP_TEST_SECRET':'secret-loop-fixture'}):
   e=self.setup_loop('import json,os;print(json.dumps({"ready":True,"token":os.environ["LOOP_TEST_SECRET"]}))',iterations=1,secret_env=['LOOP_TEST_SECRET'])
   self.finish(e)
   self.assertEqual(e.exit_code(),0)
   for file in e.directory.rglob('*.json'):self.assertNotIn('secret-loop-fixture',file.read_text())
 def test_paired_starters_run(self):
  for template in ['loop-repeat','loop-until']:
   with tempfile.TemporaryDirectory() as directory:
    w=make_template(template,template);docs=starter_documents('release-workbench-demo.yaml',w,template)
    for name,value in docs.items():Path(directory,name).write_text(render_yaml(value))
    e=self.finish(Engine(Path(directory),w));self.assertEqual(e.exit_code(),0)
