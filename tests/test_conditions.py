import json,tempfile,time,unittest
from pathlib import Path
from release_workbench.engine import Engine
from release_workbench.config import validate
from release_workbench.templates import make_template,TEMPLATES

class ConditionalWorkflowTests(unittest.TestCase):
 def run_workflow(self,w):
  temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);e=Engine(Path(temp.name),w);e.start()
  deadline=time.monotonic()+15
  while e.busy() and time.monotonic()<deadline:time.sleep(.02)
  self.assertFalse(e.busy());return e
 def computed(self,code):
  w=make_template('computed','branching');w['steps'][1]['condition']={'compute':{'commands':[{'argv':['${python}','-c',code]}]}};return w
 def test_computed_boolean_routes_and_logs_stderr(self):
  for value in (True,False):
   e=self.run_workflow(self.computed('import json,sys; print("diagnostic",file=sys.stderr); print(json.dumps('+str(value)+'))'))
   self.assertEqual(e.exit_code(),0);self.assertIs(e.state['steps']['choose']['result']['decision'],value)
   self.assertEqual(e.state['steps']['ready']['status'],'passed' if value else 'skipped')
   self.assertEqual(e.state['steps']['waiting']['status'],'skipped' if value else 'passed')
   self.assertIn('diagnostic',(e.directory/e.state['steps']['choose']['attempts'][0]['log']).read_text())
 def test_computed_invalid_values_and_failure_block_both_branches(self):
  for code in ['print("1")','print("null")','print("{}")','print('"true"')','print("not boolean")','print("false");raise SystemExit(1)']:
   with self.subTest(code=code):
    e=self.run_workflow(self.computed(code));self.assertEqual(e.exit_code(),1)
    for key in ['ready','waiting']:self.assertEqual(e.state['steps'][key]['status'],'blocked')
 def test_computed_ancestor_value_binding(self):
  w=self.computed('import json,sys;print(json.dumps(sys.argv[1]=="True"))');w['steps'][1]['condition']['compute']['commands'][0]['argv'].append('${steps.probe.result.json.ready}')
  e=self.run_workflow(w);self.assertTrue(e.state['steps']['choose']['result']['decision'])
  w['steps'][1]['condition']['compute']['commands'][0]['argv'][-1]='${steps.finish.result.json.ready}';self.assertTrue(validate(w))
 def test_computed_input_prompt_and_nonzero_rejection(self):
  w=self.computed('print("true")');w['inputs']={'flag':{'type':'string','label':'Flag'}};w['steps'][1]['condition']['compute']['commands'][0]['argv'].append('${input.flag}')
  with tempfile.TemporaryDirectory() as directory:
   e=Engine(Path(directory),w);self.assertEqual(e.input_requirements()['fields'][0]['key'],'flag')
  w['steps'][1]['success_codes']=[0,1];self.assertTrue(validate(w))
 def test_computed_timeout(self):
  w=self.computed('import time;time.sleep(20);print("true")');w['steps'][1]['timeout']=.2
  e=self.run_workflow(w);self.assertEqual(e.state['steps']['choose']['status'],'failed');self.assertIn('timeout',e.state['steps']['choose']['error'])
 def test_computed_cancel_blocks_both_branches(self):
  w=self.computed('import time;time.sleep(20);print("true")')
  with tempfile.TemporaryDirectory() as directory:
   e=Engine(Path(directory),w);e.start();deadline=time.monotonic()+5
   while e.state['steps']['choose']['status']!='running' and time.monotonic()<deadline:time.sleep(.02)
   self.assertEqual(e.state['steps']['choose']['status'],'running');e.stop('choose')
   while e.busy() and time.monotonic()<deadline:time.sleep(.02)
   self.assertEqual(e.state['steps']['choose']['status'],'cancelled')
   for key in ['ready','waiting']:self.assertEqual(e.state['steps'][key]['status'],'blocked')
 def test_computed_ssh_arguments_and_resource_lock(self):
  w=self.computed('');s=w['steps'][1];s['condition']['compute']['commands']=[{'argv':['ssh','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','host-alias','echo true']}];s['mode']='interactive';s['resources']=['remote-server']
  with tempfile.TemporaryDirectory() as directory:
   e=Engine(Path(directory),w);commands,_,_=e.prepare(s)
   self.assertEqual(commands[0],s['condition']['compute']['commands'][0]['argv']);self.assertEqual(e.resources(s),{'desktop','remote-server'})
 def test_computed_shell_does_not_interpolate_untrusted_results(self):
  w=self.computed('');w['steps'][1]['condition']['compute']['commands']=[{'shell':'sh','script':'echo ${steps.probe.result.json.ready}'}]
  e=self.run_workflow(w);self.assertEqual(e.state['steps']['choose']['status'],'blocked');self.assertIn('argv',e.state['steps']['choose']['error'])
 def test_computed_shell(self):
  import os
  if os.name=='nt':self.skipTest('Native Windows remains unverified')
  w=self.computed('');w['steps'][1]['condition']['compute']['commands']=[{'shell':'sh','script':'echo false'}]
  e=self.run_workflow(w);self.assertFalse(e.state['steps']['choose']['result']['decision'])
 def test_connected_compute_port_and_entry_fallback(self):
  for explicit in (True,False):
   for decision in (True,False):
    w=make_template('ports','branching');w['steps'][0]['commands'][0]['argv'][-1]='import json;print(json.dumps('+str(decision)+'))';w['steps'][1]['condition']={'input':{'step':'probe'} if explicit else {}}
    e=self.run_workflow(w);self.assertEqual(e.exit_code(),0);self.assertIs(e.state['steps']['choose']['result']['decision'],decision);self.assertEqual(e.state['steps']['choose']['result']['compute_source'],'probe')
 def test_compute_port_overrides_entry(self):
  w=make_template('override','branching');w['steps'][0]['commands'][0]['argv'][-1]='print("true")'
  w['steps'].insert(1,{'id':'compute','name':'Compute','kind':'command','capture':'json','commands':[{'argv':['${python}','-c','print("false")']}]})
  w['steps'][2]['needs']=['probe','compute'];w['steps'][2]['condition']={'input':{'step':'compute'}}
  e=self.run_workflow(w);self.assertFalse(e.state['steps']['choose']['result']['decision']);self.assertEqual(e.state['steps']['waiting']['status'],'passed')
 def test_connected_compute_field_and_invalid_output(self):
  w=make_template('field','branching');w['steps'][1]['condition']={'input':{'field':'ready'}};self.assertEqual(self.run_workflow(w).exit_code(),0)
  w['steps'][1]['condition']={'input':{}};e=self.run_workflow(w);self.assertEqual(e.exit_code(),1);self.assertEqual(e.state['steps']['waiting']['status'],'blocked')
 def test_input_port_validation(self):
  w=make_template('invalid','branching');w['steps'][1]['condition']={'input':{'step':'finish'}};self.assertTrue(validate(w))
  w['steps'][1]['condition']={'input':{}};w['steps'][1]['needs']=[];self.assertTrue(validate(w))
  w['steps'][1]['needs']=['probe','ready'];self.assertTrue(validate(w))
 def test_true_false_and_join(self):
  for value in (True,False):
   w=make_template('branch','branching');w['steps'][0]['commands'][0]['argv'][-1]='import json;print(json.dumps({"ready":'+str(value)+'}))'
   e=self.run_workflow(w);self.assertEqual(e.exit_code(),0)
   self.assertEqual(e.state['steps']['choose']['result']['decision'],value)
   self.assertEqual(e.state['steps']['ready']['status'],'passed' if value else 'skipped')
   self.assertEqual(e.state['steps']['waiting']['status'],'skipped' if value else 'passed')
   self.assertEqual(e.state['steps']['finish']['status'],'passed')
 def test_nonzero_probe_exit_code_can_branch(self):
  w=make_template('probe','branching');p=w['steps'][0];p.pop('capture');p['success_codes']=[0,1];p['commands'][0]['argv'][-1]='raise SystemExit(1)'
  w['steps'][1]['condition']={'source':'steps.probe.result.exit_code','operator':'equals','value':1}
  e=self.run_workflow(w);self.assertEqual(e.exit_code(),0);self.assertTrue(e.state['steps']['choose']['result']['decision'])
 def test_unexpected_failure_does_not_choose_false(self):
  w=make_template('failure','branching');w['steps'][0]['commands'][0]['argv'][-1]='raise SystemExit(2)'
  e=self.run_workflow(w);self.assertEqual(e.exit_code(),1);self.assertEqual(e.state['steps']['waiting']['status'],'blocked')
 def test_missing_or_invalid_json_fails(self):
  for code in ['print("not json")','print("{}")']:
   w=make_template('missing','branching');w['steps'][0]['commands'][0]['argv'][-1]=code
   e=self.run_workflow(w);self.assertEqual(e.exit_code(),1);self.assertNotEqual(e.state['steps']['waiting']['status'],'passed')
 def test_nested_json_and_numeric_comparison(self):
  w=make_template('nested','branching');w['steps'][0]['commands'][0]['argv'][-1]='import json;print(json.dumps(dict(data=dict(counts=[4]))))'
  w['steps'][1]['condition']={'source':'steps.probe.result.json.data.counts.0','operator':'greater_than','value':3}
  e=self.run_workflow(w);self.assertEqual(e.exit_code(),0);self.assertTrue(e.state['steps']['choose']['result']['decision'])
 def test_captured_text_comparison(self):
  w=make_template('text','branching');w['steps'][0]['capture']='text';w['steps'][0]['commands'][0]['argv'][-1]='print("READY")'
  w['steps'][1]['condition']={'source':'steps.probe.result.stdout','operator':'contains','value':'READY'}
  e=self.run_workflow(w);self.assertEqual(e.exit_code(),0)
 def test_skip_propagates_and_failed_branch_blocks_join(self):
  w=make_template('skip','branching');w['steps'][2]['commands'][0]['argv'][-1]='raise SystemExit(5)'
  e=self.run_workflow(w);self.assertEqual(e.exit_code(),1);self.assertEqual(e.state['steps']['finish']['status'],'blocked')
 def test_condition_references_must_be_ancestors_and_branches_depend_on_condition(self):
  w=make_template('validation','branching');w['steps'][1]['condition']['source']='steps.finish.result.exit_code';self.assertTrue(validate(w))
  w=make_template('validation','branching');w['steps'][2]['needs']=[];self.assertTrue(validate(w))
 def test_all_demo_templates_execute_without_external_packages(self):
  for template in ['branching','data-pipeline','backup','project-checks']:
   with self.subTest(template=template):
    w=make_template(template,template)
    for step in w['steps']:
     for c in step.get('commands',[]):compile(c['argv'][-1],'<starter>','exec')
    e=self.run_workflow(w);self.assertEqual(e.exit_code(),0)
 def test_shell_json_result(self):
  import os
  if os.name=='nt':self.skipTest('POSIX shell coverage; native Windows remains unverified')
  w=make_template('shell','branching');w['steps'][0]['commands']=[{'shell':'sh','script':"echo \'{\"ready\": true}\'"}]
  self.assertEqual(self.run_workflow(w).exit_code(),0)
 def test_capture_limit_is_a_failure(self):
  w=make_template('large','branching');w['steps'][0]['capture']='text';w['steps'][0]['commands'][0]['argv'][-1]='print("x"*1048577)'
  e=self.run_workflow(w);self.assertEqual(e.exit_code(),1);self.assertIn('1 MiB',e.state['steps']['probe']['error'])
 def test_child_workflow_runs_and_reports_are_local(self):
  from release_workbench.config import render_yaml
  temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);root=Path(temp.name)
  child={'version':1,'name':'child','steps':[{'id':'work','name':'work','kind':'command','commands':[{'argv':['${python}','-c','print("child done")']}]}]}
  (root/'child.yaml').write_text(render_yaml(child))
  w={'version':1,'name':'parent','steps':[{'id':'call','name':'Run child','kind':'workflow','workflow':'child.yaml'}]}
  e=Engine(root,w);e.start()
  while e.busy():time.sleep(.02)
  self.assertEqual(e.exit_code(),0);self.assertTrue(list((e.directory/'children').glob('call/*/summary.json')))
 def test_recursive_child_workflows_are_blocked(self):
  from release_workbench.config import render_yaml
  temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);root=Path(temp.name)
  w={'version':1,'name':'recursive','steps':[{'id':'call','name':'call','kind':'workflow','workflow':'child.yaml'}]}
  (root/'child.yaml').write_text(render_yaml(w));e=Engine(root,w);e.start()
  while e.busy():time.sleep(.02)
  self.assertEqual(e.exit_code(),2);self.assertIn('cycle',e.state['steps']['call']['error'])
 def test_required_approval_cannot_be_skipped(self):
  w=make_template('approval','branching');w['steps'].append({'id':'approve','name':'approve','kind':'manual','approval':True,'needs':['probe','choose','ready','waiting','finish']})
  e=self.run_workflow(w);self.assertEqual(e.exit_code(),2);self.assertEqual(e.state['steps']['approve']['status'],'blocked')
 def test_condition_order_does_not_require_file_topological_order(self):
  w=make_template('reverse','branching');w['steps'].reverse();e=self.run_workflow(w);self.assertEqual(e.exit_code(),0)
 def test_every_template_is_valid(self):
  for name in TEMPLATES:self.assertEqual(validate(make_template(name,name)),[])

if __name__=='__main__':unittest.main()
