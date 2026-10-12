import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import psutil
from release_workbench.config import Store,parse_yaml,render_yaml,validate,input_value
from release_workbench.engine import Engine,PLATFORM


def command(key,code='print("done")',needs=(),**kwargs):return dict(id=key,name=key,kind='command',commands=[{'argv':['${python}','-c',code]}],needs=list(needs),**kwargs)
def workflow(steps,**kwargs):return dict(version=1,name='Example workflow',steps=steps,**kwargs)

class ConfigTests(unittest.TestCase):
 def test_yaml_preserves_comments_and_rejects_conflicting_edits(self):
  with tempfile.TemporaryDirectory() as temp:
   file=Path(temp)/'release-workbench.yaml';file.write_text('# human context\nversion: 1\nname: Example # keep name comment\nsteps: []\n')
   store=Store(file);old=store.read();value=old['workflow'];value['name']='Updated';new=store.save(value,old['revision'])
   self.assertIn('# human context',new['yaml']);self.assertIn('# keep name comment',new['yaml'])
   with self.assertRaises(ValueError):store.save(value,old['revision'])
 def test_invalid_graph_and_approval_cannot_run(self):
  self.assertTrue(validate(workflow([command('a',needs=['b']),command('b',needs=['a'])])))
  self.assertTrue(validate(workflow([command('a'),dict(id='review',name='Review',kind='manual',approval=True)])))
  self.assertTrue(validate(workflow([command('a',needs=['missing'])])))
 def test_unknown_properties_and_custom_yaml_are_rejected(self):
  self.assertTrue(validate(dict(version=1,name='Example',steps=[],unknown=True)))
  for text in ('x: !python/object hello','x: &loop [*loop]','x: &same []\ny: *same'):
   with self.assertRaises(ValueError):parse_yaml(text)
 def test_canvas_numeric_positions_round_trip(self):
  value=workflow([command('a',position={'x':0,'y':0})])
  self.assertEqual(parse_yaml(render_yaml(value)),value)
 def test_typed_inputs(self):
  for kind,value in [('usb_serial','--command'),('ipv4','127.0.0.1'),('pid','0'),('integer','2.4')]:
   with self.assertRaises(ValueError):input_value('device',value,dict(label='Device',type=kind))
  self.assertEqual(input_value('pid','123',dict(label='PID',type='pid')),123)
 def test_platform_commands_and_quoted_inputs(self):
  with tempfile.TemporaryDirectory() as temp:
   w=workflow([command('a',platform_commands={PLATFORM:[{'argv':['${python}','-c','print("native")','${input.path}']} ]},requires_inputs=['path'])],inputs={'path':{'label':'Path','type':'string'}})
   engine=Engine(Path(temp),w,inputs={'path':'a b; $(echo nope)'})
   self.assertEqual(engine.preview()[0]['commands'][0][-1],'a b; $(echo nope)')
 def test_non_json_yaml_types_and_duplicate_ids(self):
  with self.assertRaises(ValueError):parse_yaml('date: 2025-01-01')
  self.assertTrue(validate(workflow([command('a'),command('a')])))

class EngineTests(unittest.TestCase):
 def setUp(self):self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
 def tearDown(self):self.temp.cleanup()
 def engine(self,steps,**kwargs):return Engine(self.root,workflow(steps,**kwargs))
 def wait(self,e,timeout=10):
  until=time.monotonic()+timeout
  while e.busy():
   if time.monotonic()>until:e.stop();self.fail('Workflow did not finish')
   time.sleep(.02)
  return e.snapshot()
 def test_parallel_branches_and_join_wait_for_both(self):
  code='import time,pathlib;time.sleep(.4);pathlib.Path("{name}").write_text("done")'
  e=self.engine([command('left',code.format(name='left')),command('right',code.format(name='right')),command('join','import pathlib;assert pathlib.Path("left").exists() and pathlib.Path("right").exists()',needs=['left','right'])])
  e.start();s=self.wait(e);self.assertEqual(e.exit_code(),0)
  left=s['steps']['left']['attempts'][0];right=s['steps']['right']['attempts'][0]
  from datetime import datetime
  self.assertLess(abs((datetime.fromisoformat(left['started'])-datetime.fromisoformat(right['started'])).total_seconds()),.25)
 def test_resource_locks_and_exclusive_jobs_prevent_overlap(self):
  code='import pathlib,time; p=pathlib.Path("lock");assert not p.exists();p.write_text("held");time.sleep(.15);p.unlink()'
  for mode in ('resource','exclusive','interactive'):
   self.root.joinpath('lock').unlink(missing_ok=True)
   options={'resources':['device']} if mode=='resource' else {'exclusive':True} if mode=='exclusive' else {'mode':'interactive'}
   e=self.engine([command('first',code,**options),command('second',code,**options)])
   e.start();self.wait(e);self.assertEqual(e.exit_code(),0,mode)
 def test_concurrency_limit_one(self):
  code='import pathlib,time;p=pathlib.Path("busy");assert not p.exists();p.touch();time.sleep(.1);p.unlink()'
  e=self.engine([command('a',code),command('b',code)],concurrency=1);e.start();self.wait(e);self.assertEqual(e.exit_code(),0)
 def test_failure_blocks_descendant_but_independent_branch_finishes(self):
  e=self.engine([command('fail','raise SystemExit(7)'),command('blocked',needs=['fail']),command('independent')]);e.start();s=self.wait(e)
  self.assertEqual(s['steps']['blocked']['status'],'blocked');self.assertEqual(s['steps']['independent']['status'],'passed');self.assertEqual(e.exit_code(),1)
 def test_manual_gate_preserves_pending_work_and_requires_evidence(self):
  e=self.engine([dict(id='gate',name='Review',kind='manual'),command('after',needs=['gate'])]);e.start();s=self.wait(e)
  self.assertEqual(e.exit_code(),2);self.assertEqual(s['steps']['gate']['status'],'manual')
  with self.assertRaises(ValueError):e.record('gate','')
  e.record('gate','Evidence reviewed');self.wait(e);self.assertEqual(e.exit_code(),0)
 def test_background_profile_does_not_complete_manual_or_interactive_dependencies(self):
  e=self.engine([command('safe'),dict(id='gate',name='Gate',kind='manual'),command('after',needs=['gate']),command('pointer',mode='interactive')]);e.start('background');s=self.wait(e)
  self.assertEqual(e.selected,{'safe'});self.assertEqual(s['steps']['pointer']['status'],'pending');self.assertEqual(e.exit_code(),0)
 def test_selected_step_runs_unmet_ancestors_and_rerun_invalidates_descendants(self):
  e=self.engine([command('before'),command('after',needs=['before'])]);e.start(step='after');self.wait(e);e.start(step='before',rerun=True);s=self.wait(e)
  self.assertEqual(len(s['steps']['before']['attempts']),2);self.assertEqual(s['steps']['after']['status'],'pending')
 def test_disabled_required_steps_never_pass(self):
  e=self.engine([command('off',enabled=False),command('after',needs=['off'])]);e.start();s=self.wait(e);self.assertEqual(s['steps']['off']['status'],'disabled');self.assertEqual(s['steps']['after']['status'],'blocked');self.assertEqual(e.exit_code(),2)
 def test_missing_input_blocks_without_spawning(self):
  e=self.engine([command('a',requires_inputs=['device'])],inputs={'device':{'label':'Device','type':'usb_serial'}});e.start();s=self.wait(e);self.assertEqual(s['steps']['a']['status'],'blocked');self.assertFalse(s['steps']['a']['attempts'])
 def test_progress_events_and_log_parsers_are_distinct_from_estimates(self):
  e=self.engine([command('a')]);s=e.workflow['steps'][0]
  e.consume('a',s,'::workbench::{"done":3,"total":10,"stage":"Testing"}\n');self.assertEqual(e.state['steps']['a']['progress']['done'],3)
  s['progress']={'pattern':r'Finished (?P<done>\d+)/(?P<total>\d+)','mode':'groups'};e.consume('a',s,'Finished 5/10');self.assertEqual(e.state['steps']['a']['progress']['done'],5)
 def test_outputs_validate_and_populate_inputs(self):
  e=self.engine([command('prepare','import pathlib;pathlib.Path("output.json").write_text(\'{"pid":123}\')',outputs=[dict(path='output.json',key='pid',input='pid')]),command('measure','import sys;assert sys.argv[1]=="123"',needs=['prepare'],requires_inputs=['pid'])],inputs={'pid':{'label':'PID','type':'pid'}})
  e.workflow['steps'][1]['commands'][0]['argv'].append('${input.pid}')
  # Construct again so the configured fingerprint includes the command.
  e=Engine(self.root,e.workflow);e.start();self.wait(e);self.assertEqual(e.exit_code(),0);self.assertEqual(e.outputs['pid'],123)
 def test_stale_output_cannot_satisfy_preparation(self):
  self.root.joinpath('old.json').write_text('{"pid":123}');os.utime(self.root/'old.json',(1,1))
  e=self.engine([command('prepare',outputs=[dict(path='old.json',key='pid',input='pid')])],inputs={'pid':{'label':'PID','type':'pid'}});e.start();self.wait(e);self.assertEqual(e.exit_code(),1)
 def test_secrets_are_masked_in_saved_logs_commands_and_state(self):
  with patch.dict(os.environ,WB_TEST_SECRET='synthetic-secret-value'):
   e=self.engine([command('a','import os;print(os.environ["WB_TEST_SECRET"])')],secret_env=['WB_TEST_SECRET']);e.start();self.wait(e)
   for file in e.directory.iterdir():self.assertNotIn('synthetic-secret-value',file.read_text())
 def test_secret_environment_alias_is_masked(self):
  with patch.dict(os.environ,WB_ALIAS_SOURCE='synthetic-alias-secret'):
   e=self.engine([command('a','import os;print(os.environ["WB_ALIAS_TARGET"])',env={'WB_ALIAS_TARGET':'${env.WB_ALIAS_SOURCE}'},secret_env=['WB_ALIAS_TARGET'])]);e.start();self.wait(e)
   self.assertEqual(e.exit_code(),0)
   for file in e.directory.iterdir():self.assertNotIn('synthetic-alias-secret',file.read_text())
 def test_failed_job_keeps_partial_report_evidence(self):
  e=self.engine([command('a','import pathlib;pathlib.Path("partial.json").write_text("{}");raise SystemExit(1)',reports=['partial.json'])]);e.start();s=self.wait(e)
  self.assertEqual(e.exit_code(),1);self.assertTrue(s['steps']['a']['attempts'][0]['reports'])
 def test_workflow_and_step_environment_overrides_are_merged(self):
  e=self.engine([command('a','import os;assert os.environ["WB_SETTING"]=="step";assert os.environ["WB_GLOBAL"]=="global"',env={'WB_SETTING':'step'})],env={'WB_SETTING':'workflow','WB_GLOBAL':'global'});e.start();self.wait(e);self.assertEqual(e.exit_code(),0)
 def test_resume_requires_matching_workflow_and_source(self):
  e=self.engine([command('a')]);e.start();self.wait(e);resumed=Engine(self.root,e.workflow,resume=e.run_id);self.assertEqual(resumed.state['steps']['a']['status'],'passed')
  with self.assertRaises(ValueError):Engine(self.root,workflow([command('b')]),resume=e.run_id)
 def test_git_workspace_generated_reports_do_not_invalidate_source(self):
  subprocess.run(['git','init','-q',str(self.root)],check=True)
  self.root.joinpath('file.txt').write_text('source')
  e=self.engine([command('a')]);e.start();self.wait(e);e.start(step='a',rerun=True);self.wait(e);self.assertEqual(e.exit_code(),0)
  self.root.joinpath('file.txt').write_text('changed')
  with self.assertRaises(ValueError):e.start()
 def test_pause_blocks_new_jobs_then_resume(self):
  e=self.engine([command('a','import time;time.sleep(.3)'),command('b',needs=['a'])]);e.start()
  e.pause();time.sleep(.5);self.assertEqual(e.state['steps']['b']['status'],'queued');e.pause(False);self.wait(e);self.assertEqual(e.exit_code(),0)
 @unittest.skipIf(os.name=='nt','Windows forced process-tree stop has separate command coverage')
 def test_stop_single_job_reaps_detached_child_and_preserves_other_branch(self):
  code='import subprocess,pathlib,time;child=subprocess.Popen(["'+sys.executable+'","-c","import time;time.sleep(60)"],start_new_session=True);pathlib.Path("child.pid").write_text(str(child.pid));time.sleep(60)'
  e=self.engine([command('long',code),command('other','import time;time.sleep(.3)')]);e.start();until=time.monotonic()+5
  while not (self.root/'child.pid').exists():
   if time.monotonic()>until:self.fail('Child not started')
   time.sleep(.02)
  e.stop('long');s=self.wait(e,35);self.assertEqual(s['steps']['long']['status'],'cancelled');self.assertEqual(s['steps']['other']['status'],'passed')
  pid=int((self.root/'child.pid').read_text());self.assertTrue(not psutil.pid_exists(pid) or psutil.Process(pid).status()==psutil.STATUS_ZOMBIE)
 def test_timeout_is_failure_and_logs_are_preserved(self):
  e=self.engine([command('slow','import time;print("starting",flush=True);time.sleep(60)',timeout=.2)]);e.start();s=self.wait(e,35);self.assertEqual(e.exit_code(),1);self.assertIn('TIMEOUT',(e.directory/s['steps']['slow']['attempts'][0]['log']).read_text())
 def test_path_escape_and_shell_input_interpolation_are_rejected(self):
  e=self.engine([command('a',cwd='../')]);e.start();self.wait(e);self.assertEqual(e.exit_code(),2)
  w=workflow([dict(id='shell',name='Shell',kind='command',commands=[dict(shell='bash',script='echo ${input.value}')])],inputs={'value':{'label':'Value','type':'string'}})
  e=Engine(self.root,w,inputs={'value':'value'});e.start();self.wait(e);self.assertEqual(e.exit_code(),2)

class AdditionalBoundaryTests(unittest.TestCase):
 def test_secret_object_masking_handles_json_escaping_and_multiline_values(self):
  from release_workbench.engine import Masker
  secret='quoted"value\nsecond-line'
  masker=Masker([secret]);result=masker.object({'argv':[secret],'text':secret})
  self.assertNotIn('quoted',json.dumps(result));self.assertNotIn('second-line',json.dumps(result))
 def test_changed_inputs_cannot_reuse_completed_evidence(self):
  with tempfile.TemporaryDirectory() as temp:
   e=Engine(Path(temp),workflow([command('a')],inputs={'target':{'label':'Target','type':'string'}}));e.start()
   while e.busy():time.sleep(.02)
   with self.assertRaises(ValueError):e.set_inputs({'target':'new'})
 def test_explicit_shell_retains_native_environment_expansion(self):
  from release_workbench.engine import resolved_commands
  with tempfile.TemporaryDirectory() as temp:
   commands,_,_=resolved_commands(dict(name='shell',commands=[dict(shell='bash',script='echo ${HOME}')]),Path(temp),{})
   self.assertEqual(commands[0][-1],'echo ${HOME}')
 def test_windows_cancellation_uses_only_target_process_tree(self):
  from release_workbench.engine import cancel_tree
  from unittest.mock import Mock
  process=Mock(pid=123)
  with patch('release_workbench.engine.psutil.Process') as proc,patch('release_workbench.engine.os.name','nt'),patch('release_workbench.engine.subprocess.run') as run:
   proc.return_value.children.return_value=[];cancel_tree(process)
   run.assert_called_once_with(['taskkill','/PID','123','/T','/F'],capture_output=True,timeout=15)
