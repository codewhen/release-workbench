import tempfile,time,unittest,json
from pathlib import Path
from release_workbench.engine import Engine
from release_workbench.config import validate

def card(key,kind,needs=(),scope=None,region='body',**control):
 return dict(id=key,name=key,kind=kind,needs=list(needs),**({'scope':scope,'region':region} if scope else {}),control=control)
def cmd(key,script,needs=(),scope=None,region='body',**extra):
 return dict(id=key,name=key,kind='command',commands=[{'argv':['${python}','-c',script]}],needs=list(needs),**({'scope':scope,'region':region} if scope else {}),**extra)
class FlowTests(unittest.TestCase):
 def setUp(self):self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
 def tearDown(self):self.temp.cleanup()
 def runflow(self,steps,**extra):
  w=dict(version=2,name='Structured flow',steps=steps,**extra);self.assertEqual(validate(w),[]);e=Engine(self.root,w);e.start();self.finish(e);return e
 def finish(self,e,timeout=15):
  deadline=time.monotonic()+timeout
  while e.busy():
   if time.monotonic()>deadline:e.stop(force=True);self.fail('Flow did not stop')
   time.sleep(.02)
 def test_while_zero_iterations_and_fill_independent(self):
  e=self.runflow([card('n','declare',name='n',value=0),card('loop','while',['n'],test={'source':'vars.n','operator':'greater_than','value':0}),cmd('body','raise Exception("must not run")',scope='loop')]);self.assertEqual(e.exit_code(),0)
 def test_while_recomputes_variable_and_exports(self):
  e=self.runflow([card('n','declare',name='n',value=0),card('loop','while',['n'],test={'source':'vars.n','operator':'less_than','value':3},outputs={'count':'${vars.n}'}),card('inc','update',scope='loop',name='n',value=1)]);self.assertEqual(e.exit_code(),0);self.assertEqual(e.state['steps']['loop']['result']['json']['count'],3)
 def test_repeat_until_executes_first(self):
  e=self.runflow([card('n','declare',name='n',value=0),card('loop','until',['n'],test={'source':'vars.n','operator':'greater_than','value':1},outputs={'n':'${vars.n}'}),card('inc','update',scope='loop',name='n',value=1)]);self.assertEqual(e.state['steps']['loop']['result']['json']['n'],2)
 def test_break_keeps_variable_changes(self):
  e=self.runflow([card('n','declare',name='n',value=0),card('loop','repeat',['n'],count=9,outputs={'n':'${vars.n}'}),card('inc','update',scope='loop',name='n',value=1),card('stop','break',['inc'],scope='loop'),cmd('never','raise Exception()',needs=['stop'],scope='loop')]);self.assertEqual(e.exit_code(),0);self.assertEqual(e.state['steps']['loop']['result']['json']['n'],1)
 def test_continue_skips_tail(self):
  e=self.runflow([card('loop','repeat',count=3),card('next','continue',scope='loop'),cmd('never','raise Exception()',needs=['next'],scope='loop')]);self.assertEqual(e.exit_code(),0)
 def test_nested_repeat(self):
  e=self.runflow([card('outer','repeat',count=2),card('inner','repeat',scope='outer',count=2),cmd('body','print("ok")',scope='inner')]);self.assertEqual(e.exit_code(),0);self.assertEqual(len(e.state['steps']['body']['attempts']),4)
 def test_limit_exhaustion_fails(self):
  e=self.runflow([card('loop','while',test={'compute':{'commands':[{'argv':['${python}','-c','print("true")']}]}},limit=2),card('wait','wait',scope='loop',delay=0)]);self.assertEqual(e.exit_code(),1)
 def test_foreach_outputs_do_not_overwrite_parent(self):
  e=self.runflow([card('n','declare',name='n',value=1),card('loop','foreach',['n'],items=['a','b'],parallel=2),cmd('body','print("${loop.item}")',scope='loop')]);self.assertEqual(e.exit_code(),0);self.assertEqual(e.state['variables']['n'],1)
 def test_switch_first_matching_and_default(self):
  steps=[card('v','declare',name='v',value='x'),card('choose','switch',['v'],source='vars.v',cases=[{'id':'yes','value':'x'}])]
  steps+=[dict(cmd('chosen','print("chosen")',needs=['choose']),when={'step':'choose','equals':'yes'}),dict(cmd('other','raise Exception()',needs=['choose']),when={'step':'choose','equals':'default'})]
  e=self.runflow(steps);self.assertEqual(e.exit_code(),0);self.assertEqual(e.state['steps']['other']['status'],'skipped')
 def test_try_catch_requires_explicit_handling_and_finally(self):
  steps=[card('guard','try'),cmd('bad','raise Exception("expected")',scope='guard'),card('handled','handle_error',scope='guard',region='catch'),cmd('cleanup','from pathlib import Path;Path("clean").write_text("yes")',scope='guard',region='finally')]
  e=self.runflow(steps);self.assertEqual(e.exit_code(),0);self.assertTrue((self.root/'clean').exists());self.assertEqual(e.state['steps']['bad']['status'],'failed')
 def test_unhandled_catch_fails(self):
  e=self.runflow([card('guard','try'),cmd('bad','raise Exception()',scope='guard'),card('wait','wait',scope='guard',region='catch',delay=0)]);self.assertEqual(e.exit_code(),1)
 def test_retry_records_failed_and_successful_attempts(self):
  script='from pathlib import Path;p=Path("attempt");n=int(p.read_text())+1 if p.exists() else 1;p.write_text(str(n));exit(0 if n==2 else 1)'
  e=self.runflow([cmd('flaky',script,retry={'attempts':2,'delay':0})]);self.assertEqual(e.exit_code(),0);self.assertEqual(len(next(v for v in e.state['executions'].values() if v.get('step')=='flaky')['leaf_attempts']),2)
 def test_unlimited_stop_no_finally_launched(self):
  w=dict(version=2,name='Unlimited',steps=[card('guard','try'),card('loop','while',scope='guard',test={'compute':{'commands':[{'argv':['${python}','-c','print("true")']}]}},limit=None,timeout=None),card('pause','wait',scope='loop',delay=1),cmd('cleanup','from pathlib import Path;Path("clean").write_text("bad")',scope='guard',region='finally')]);e=Engine(self.root,w);e.start();time.sleep(.5);e.stop(force=True);self.finish(e);self.assertEqual(e.exit_code(),130);self.assertFalse((self.root/'clean').exists())
 def test_manual_noninteractive_blocks(self):
  e=self.runflow([card('loop','repeat',count=1),dict(id='gate',name='Gate',kind='manual',scope='loop')]);self.assertEqual(e.exit_code(),2)
 def test_cross_scope_edge_and_membership_cycle_rejected(self):
  w=dict(version=2,name='Bad',steps=[card('loop','repeat',count=2),card('a','wait',scope='loop',delay=0),card('b','wait',['a'],delay=0)]);self.assertTrue(validate(w))
 def test_merge_duplicate_requires_policy(self):
  e=self.runflow([card('merge','merge',value=[{'a':1},{'a':2}])]);self.assertEqual(e.exit_code(),1)
 def test_shared_budget_for_parallel_foreach(self):
  e=self.runflow([card('loop','foreach',items=[1,2,3],parallel=3),cmd('work','import time;time.sleep(.12)',scope='loop')],concurrency=1);self.assertEqual(e.exit_code(),0);self.assertEqual(len(e.state['steps']['work']['attempts']),3)
 def test_all_v2_starters_validate_and_run(self):
  from release_workbench.templates import make_template
  for name in ['visual-while','visual-foreach','visual-poll','visual-retry','visual-recovery']:
   w=make_template(name,name);self.assertEqual(validate(w),[],name);e=Engine(self.root,w);e.start();self.finish(e);self.assertEqual(e.exit_code(),0,name)
 def test_manual_browser_evidence_resumes_group(self):
  w=dict(version=2,name='Manual',steps=[card('loop','repeat',count=1),dict(id='gate',name='Gate',kind='manual',scope='loop')]);e=Engine(self.root,w);e.interactive=True;e.start();deadline=time.monotonic()+5
  while not e.manual_events and time.monotonic()<deadline:time.sleep(.02)
  self.assertTrue(e.manual_events);e.record('gate','checked');self.finish(e);self.assertEqual(e.exit_code(),0)
 def test_group_timeout_stops_active_process(self):
  e=self.runflow([card('loop','repeat',count=1,timeout=.2),cmd('long','import time;time.sleep(20)',scope='loop')]);self.assertEqual(e.exit_code(),1)
 def test_failed_finally_propagates(self):
  e=self.runflow([card('guard','try'),card('ok','wait',scope='guard',delay=0),cmd('bad','raise Exception()',scope='guard',region='finally')]);self.assertEqual(e.exit_code(),1)
 def test_secrets_masked_in_scoped_evidence(self):
  import os
  from unittest.mock import patch
  with patch.dict(os.environ,{'FLOW_TEST_SECRET':'private-token-abcdef'}):
   e=self.runflow([cmd('secret','import os;print(os.environ["FLOW_TEST_SECRET"])',capture='text')],secret_env=['FLOW_TEST_SECRET']);self.assertEqual(e.exit_code(),0)
   for f in e.directory.rglob('*'):
    if f.is_file():self.assertNotIn('private-token-abcdef',f.read_text(errors='ignore'),str(f))
 def test_background_profile_selects_compatible_groups_only(self):
  w=dict(version=2,name='Background',steps=[card('loop','repeat',count=1),card('wait','wait',scope='loop',delay=0),dict(id='gate',name='Gate',kind='manual')]);e=Engine(self.root,w);e.start('background');self.finish(e);self.assertEqual(e.exit_code(),0);self.assertEqual(e.state['steps']['gate']['status'],'pending')
 def test_break_cancels_active_parallel_body(self):
  e=self.runflow([card('loop','repeat',count=10),card('break','break',scope='loop'),card('long','wait',scope='loop',delay=30)]);self.assertEqual(e.exit_code(),0)
 def test_parallel_foreach_publishes_each_item(self):
  e=self.runflow([card('loop','foreach',items=[2,4],parallel=2,outputs={'item':'${loop.item}'})]);self.assertEqual(e.state['steps']['loop']['result']['json']['items'],[{'item':2},{'item':4}])
 def test_selected_rerun_keeps_completed_prerequisite(self):
  e=self.runflow([cmd('setup','from pathlib import Path;p=Path("once");assert not p.exists();p.write_text("one")'),card('work','wait',['setup'],delay=0)]);e.start(step='work',rerun=True);self.finish(e);self.assertEqual(e.exit_code(),0);self.assertEqual(len(e.state['steps']['setup']['attempts']),1)
 def test_repeated_manual_evidence_is_separate(self):
  w=dict(version=2,name='Manual iterations',steps=[card('loop','repeat',count=2),dict(id='gate',name='Gate',kind='manual',scope='loop')]);e=Engine(self.root,w);e.interactive=True;e.start()
  for index in range(2):
   deadline=time.monotonic()+5
   while not any(f'iteration-{index+1}/' in p for p in e.manual_events) and time.monotonic()<deadline:time.sleep(.01)
   p=next(p for p in e.manual_events if f'iteration-{index+1}/' in p);e.record(p,'evidence '+str(index))
  self.finish(e);self.assertEqual(e.exit_code(),0);self.assertEqual(len(e.state['steps']['gate']['attempts']),2)
 def test_resume_does_not_repeat_successful_side_effect(self):
  e=self.runflow([cmd('once','from pathlib import Path;p=Path("once");assert not p.exists();p.write_text("one")')]);again=Engine(self.root,e.workflow,resume=e.run_id);again.start();self.finish(again);self.assertEqual(again.exit_code(),0)
 def test_resource_lock_shared_across_nested_groups(self):
  script='from pathlib import Path;import time;p=Path("lock");f=p.open("x");f.close();time.sleep(.05);p.unlink()'
  e=self.runflow([card('left','repeat',count=2),card('right','repeat',count=2),cmd('a',script,scope='left',resources=['shared']),cmd('b',script,scope='right',resources=['shared'])],concurrency=4);self.assertEqual(e.exit_code(),0)
 def test_child_workflow_shares_coordinator_and_bindings(self):
  from release_workbench.config import render_yaml
  child=dict(version=1,name='Child',inputs={'text':{'label':'Text','type':'string'}},steps=[cmd('print','print("${input.text}")')]);(self.root/'child.yaml').write_text(render_yaml(child))
  e=self.runflow([dict(id='call',name='Call child',kind='workflow',workflow='child.yaml',workflow_inputs={'text':'hello'})],concurrency=1);self.assertEqual(e.exit_code(),0)
 def test_loop_conversion_is_explicit_and_keeps_original_unchanged(self):
  from release_workbench.flow_conversion import convert_loop
  from release_workbench.config import render_yaml
  (self.root/'child.yaml').write_text(render_yaml(dict(version=1,name='Body',steps=[cmd('probe','print("true")',capture='json')])))
  original=dict(version=1,name='Legacy',steps=[dict(id='loop',name='Loop',kind='loop',workflow='child.yaml',loop={'iterations':3,'until':'steps.probe.result.json'})]);converted=convert_loop(self.root,original,'loop');self.assertEqual(original['version'],1);self.assertEqual(converted['steps'][0]['kind'],'until');e=Engine(self.root,converted);e.start();self.finish(e);self.assertEqual(e.exit_code(),0)
 def test_rerun_preserves_attempt_logs(self):
  e=self.runflow([card('wait','wait',delay=0)]);first=e.state['steps']['wait']['attempts'][0]['log'];text=(e.directory/first).read_text();e.start(step='wait',rerun=True);self.finish(e);self.assertNotEqual(first,e.state['steps']['wait']['attempts'][1]['log']);self.assertEqual((e.directory/first).read_text(),text)
 def test_condition_region_is_recomputed(self):
  probe=cmd('check','import json,sys;print(json.dumps(int(sys.argv[1])<3))',scope='loop',region='condition',capture='json');probe['commands'][0]['argv'].append('${vars.n}')
  e=self.runflow([card('n','declare',name='n',value=0),card('loop','while',['n'],test={'source':'steps.check.result.json','operator':'is_true'},outputs={'n':'${vars.n}'}),probe,card('inc','update',scope='loop',name='n',value=1)]);self.assertEqual(e.exit_code(),0);self.assertEqual(len(e.state['steps']['check']['attempts']),4)
 def test_invalid_boolean_condition_fails(self):
  e=self.runflow([card('n','declare',name='n',value='yes'),card('loop','while',['n'],test={'source':'vars.n','operator':'is_true'})]);self.assertEqual(e.exit_code(),1)
 def test_exclusive_job_waits_for_all_other_leaves(self):
  normal='from pathlib import Path;import time,sys;p=Path("ordinary-"+sys.argv[1]);p.write_text("active");time.sleep(.15);p.unlink()'
  left=cmd('left',normal);left['commands'][0]['argv'].append('left');right=cmd('right',normal);right['commands'][0]['argv'].append('right')
  exclusive=cmd('exclusive','from pathlib import Path;import time;assert not list(Path(".").glob("ordinary-*"));time.sleep(.1);assert not list(Path(".").glob("ordinary-*"))',exclusive=True)
  e=self.runflow([left,exclusive,right],concurrency=3);self.assertEqual(e.exit_code(),0)
 def test_if_can_compare_a_scoped_variable(self):
  e=self.runflow([card('ready','declare',name='ready',value=True),dict(id='choose',name='Choose',kind='condition',needs=['ready'],condition={'source':'vars.ready','operator':'is_true'})]);self.assertEqual(e.exit_code(),0);self.assertTrue(e.state['steps']['choose']['result']['decision'])
 def test_if_can_read_group_published_boolean(self):
  e=self.runflow([card('group','repeat',count=1,outputs={'ready':True}),dict(id='choose',name='Choose',kind='condition',needs=['group'],condition={'input':{'step':'group','field':'ready'}})]);self.assertEqual(e.exit_code(),0)
 def test_final_approval_requires_group_dependencies(self):
  w=dict(version=2,name='Approval',steps=[card('group','repeat',count=1),dict(id='approval',name='Approve',kind='manual',approval=True)]);self.assertTrue(validate(w));w['steps'][1]['needs']=['group'];self.assertEqual(validate(w),[])
 def test_dynamic_shell_data_is_not_interpolated(self):
  step=dict(id='shell',name='Shell',kind='command',commands=[{'shell':'sh','script':'echo ${vars.value}'}],needs=['value'])
  e=self.runflow([card('value','declare',name='value',value='$(touch injected)'),step]);self.assertEqual(e.exit_code(),1);self.assertFalse((self.root/'injected').exists())
 def test_wait_obeys_step_timeout(self):
  step=card('wait','wait',delay=5);step['timeout']=1;e=self.runflow([step]);self.assertEqual(e.exit_code(),1)
 def test_catch_retains_successful_variable_updates(self):
  e=self.runflow([card('n','declare',name='n',value=0),card('guard','try',['n'],outputs={'n':'${vars.n}'}),card('inc','update',scope='guard',name='n',value=1),cmd('bad','raise Exception()',needs=['inc'],scope='guard'),card('handled','handle_error',scope='guard',region='catch')]);self.assertEqual(e.exit_code(),0);self.assertEqual(e.state['steps']['guard']['result']['json']['n'],1)
 def test_group_inputs_are_explicit(self):
  e=self.runflow([cmd('outer','import json;print(json.dumps({"ready":True}))',capture='json'),card('loop','repeat',['outer'],count=1,inputs={'outer':'${steps.outer.result}'},outputs={'ready':'${scope.inputs.outer.json.ready}'})]);self.assertEqual(e.exit_code(),0);self.assertTrue(e.state['steps']['loop']['result']['json']['ready'])
 def test_foreach_accepts_an_earlier_card_array(self):
  e=self.runflow([cmd('items','print("[1,2,3]")',capture='json'),card('loop','foreach',['items'],items='${steps.items.result.json}',outputs={'item':'${loop.item}'})]);self.assertEqual(e.exit_code(),0);self.assertEqual(len(e.state['steps']['loop']['result']['json']['items']),3)
 def test_parallel_foreach_obeys_limit(self):
  e=self.runflow([card('loop','foreach',items=[1,2,3],parallel=2,limit=2)]);self.assertEqual(e.exit_code(),1)
 def test_parallel_foreach_continue_only_skips_current_item(self):
  e=self.runflow([card('loop','foreach',items=[1,2],parallel=2,outputs={'item':'${loop.item}'}),card('next','continue',scope='loop')]);self.assertEqual(e.exit_code(),0);self.assertEqual(len(e.state['steps']['loop']['result']['json']['items']),2)
 def test_stop_while_paused(self):
  e=Engine(self.root,dict(version=2,name='Pause',steps=[card('wait','wait',delay=20)]));e.start();time.sleep(.1);e.pause();e.stop(force=True);self.finish(e);self.assertEqual(e.exit_code(),130)
 def test_selected_stop_keeps_independent_work_running(self):
  e=Engine(self.root,dict(version=2,name='Selected stop',steps=[card('first','wait',delay=20),card('second','wait',delay=.2)]));e.start();time.sleep(.05);e.stop('first',force=True);self.finish(e);self.assertEqual(e.state['steps']['first']['status'],'cancelled');self.assertEqual(e.state['steps']['second']['status'],'passed')
 def test_selected_stop_does_not_launch_finally(self):
  e=Engine(self.root,dict(version=2,name='Selected cleanup',steps=[card('guard','try'),card('work','wait',scope='guard',delay=20),cmd('cleanup','from pathlib import Path;Path("should-not-exist").write_text("bad")',scope='guard',region='finally')]));e.start();time.sleep(.05);e.stop('work',force=True);self.finish(e);self.assertFalse((self.root/'should-not-exist').exists());self.assertEqual(e.exit_code(),130)
 def test_selected_stop_before_dispatch(self):
  e=Engine(self.root,dict(version=2,name='Early selected stop',steps=[card('first','wait',delay=20),card('second','wait',delay=.1)]));e.start();e.stop('first',force=True);self.finish(e);self.assertEqual(e.state['steps']['first']['status'],'cancelled');self.assertEqual(e.state['steps']['second']['status'],'passed')
