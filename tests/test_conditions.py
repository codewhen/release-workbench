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
