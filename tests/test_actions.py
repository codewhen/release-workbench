import json,tempfile,time,unittest
from pathlib import Path
from release_workbench.engine import Engine
from release_workbench.actions import run_action,test_command
from release_workbench.config import validate
from release_workbench.templates import make_template

class ActionTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
 def run_workflow(self,steps,inputs=None):
  e=Engine(self.root,dict(version=1,name='No code',steps=steps,inputs=inputs or {}));e.start();deadline=time.monotonic()+12
  while e.busy() and time.monotonic()<deadline:time.sleep(.02)
  self.assertFalse(e.busy());return e
 def action(self,id,type,**values):return dict(id=id,name=id,kind='action',action={'type':type,**values})
 def test_values_calculation_and_json_files(self):
  w=make_template('No code','no-code');e=self.run_workflow(w['steps']);self.assertEqual(e.exit_code(),0)
  self.assertEqual(e.state['steps']['calculate']['result']['json']['value'],6);self.assertEqual(e.state['steps']['read']['result']['json'],{'value':6})
  self.assertEqual(e.state['steps']['review']['status'],'skipped');self.assertTrue(e.state['steps']['save']['attempts'][0]['reports'])
 def test_true_boolean_binding_is_preserved(self):
  a=self.action('a','set_values',values={'ready':True});b=self.action('b','set_values',values={'flag':'${steps.a.result.json.ready}'});b['needs']=['a']
  e=self.run_workflow([a,b]);self.assertIs(e.state['steps']['b']['result']['json']['flag'],True)
 def test_division_by_zero_fails(self):
  e=self.run_workflow([self.action('a','calculate',left=2,right=0,operator='divide')]);self.assertEqual(e.exit_code(),1);self.assertIn('zero',e.state['steps']['a']['error'])
 def test_non_numeric_calculation_fails(self):
  e=self.run_workflow([self.action('a','calculate',left='text',right=2,operator='add')]);self.assertEqual(e.exit_code(),1)
 def test_missing_binding_fails(self):
  a=self.action('a','set_values',values={});b=self.action('b','set_values',values={'value':'${steps.a.result.json.missing}'});b['needs']=['a']
  e=self.run_workflow([a,b]);self.assertEqual(e.exit_code(),1);self.assertIn('Missing action',e.state['steps']['b']['error'])
 def test_write_does_not_overwrite_by_default(self):
  self.root.joinpath('file.txt').write_text('original');e=self.run_workflow([self.action('a','write_file',path='file.txt',content='replacement')]);self.assertEqual(e.exit_code(),1);self.assertEqual(self.root.joinpath('file.txt').read_text(),'original')
 def test_file_paths_and_symlinks_cannot_escape(self):
  with self.assertRaises(ValueError):run_action({'type':'read_json','path':'../outside.json'},self.root,lambda x:x)
  self.root.joinpath('escape').symlink_to(self.root.parent)
  with self.assertRaises(ValueError):run_action({'type':'write_file','path':'escape/outside.txt','content':'x'},self.root,lambda x:x)
 def test_file_existence_is_data(self):
  e=self.run_workflow([self.action('a','file_exists',path='missing.txt')]);self.assertEqual(e.exit_code(),0);self.assertIs(e.state['steps']['a']['result']['json']['exists'],False)
 def test_empty_unittest_discovery_fails(self):
  e=self.run_workflow([self.action('a','run_tests',runner='unittest',target='.')]);self.assertEqual(e.exit_code(),1)
 def test_unittest_runner_runs_actual_tests(self):
  self.root.joinpath('test_sample.py').write_text('import unittest\nclass TestSample(unittest.TestCase):\n def test_sum(self):self.assertEqual(2+2,4)\n')
  e=self.run_workflow([self.action('a','run_tests',runner='unittest',target='.')]);self.assertEqual(e.exit_code(),0)
 def test_bindings_must_be_ancestors(self):
  a=self.action('a','set_values',values={'value':'${steps.b.result.json.value}'});b=self.action('b','set_values',values={'value':1});self.assertTrue(validate(dict(version=1,name='invalid',steps=[a,b])))
 def test_runner_arguments_are_not_shell_expressions(self):
  self.assertEqual(test_command({'runner':'go','target':'./...'},self.root,'.'),['go','test','./...'])
  with self.assertRaises(ValueError):test_command({'runner':'gradle','target':'test; echo fail'},self.root,'.')
 def test_script_card_passes_arguments_without_shell_parsing(self):
  self.root.joinpath('check.py').write_text('import json,sys;print(json.dumps({"argument":sys.argv[1]}))')
  step=self.action('script','run_script',language='python',path='check.py',arguments=['hello world; not a shell operator']);step['capture']='json'
  e=self.run_workflow([step]);self.assertEqual(e.exit_code(),0);self.assertEqual(e.state['steps']['script']['result']['json']['argument'],'hello world; not a shell operator')
 def test_action_input_requirements_block_before_file_write(self):
  step=self.action('save','write_file',path='result.txt',content='${input.message}')
  e=self.run_workflow([step],inputs={'message':{'type':'string','label':'Message'}});self.assertEqual(e.exit_code(),2);self.assertFalse(self.root.joinpath('result.txt').exists())
 def test_test_cards_cannot_treat_nonzero_exit_codes_as_success(self):
  step=self.action('tests','run_tests',runner='unittest',target='.');step['success_codes']=[0,1]
  self.assertTrue(validate(dict(version=1,name='invalid',steps=[step])))
 def test_json_size_limit(self):
  self.root.joinpath('large.json').write_text(' '*1048577)
  e=self.run_workflow([self.action('a','read_json',path='large.json')]);self.assertEqual(e.exit_code(),1);self.assertIn('1 MiB',e.state['steps']['a']['error'])

if __name__=='__main__':unittest.main()
