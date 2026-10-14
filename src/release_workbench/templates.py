"""Small, local starters shared by browser and CLI; no paid or hosted tools."""
TEMPLATES={
 'loop-repeat':'Repeat a workflow three times', 'loop-until':'Loop until ready (bounded)',
 'computed-if':'If(a) with a computed Boolean',
 'no-code':'No-code data and file automation', 'no-code-tests':'No-code Python test workflow',
 'blank':'Blank workflow', 'tests':'Test starter', 'release':'Release with approval',
 'branching':'If / Else with a branch join', 'data-pipeline':'CSV processing pipeline',
 'backup':'Safe demonstration file backup', 'project-checks':'Project inventory and conditional checks',
}
def command(id,name,code,needs=(),**extra):
 return dict(id=id,name=name,kind='command',needs=list(needs),mode='background',commands=[{'argv':['${python}','-c',code]}],**extra)
def branching(name='If / Else starter',probe=None):
 return dict(version=1,name=name,concurrency=4,inputs={},steps=[
  command('probe','Read program result',probe or 'import json;print(json.dumps({"ready":True,"count":3}))',capture='json'),
  dict(id='choose',name='If ready',kind='condition',needs=['probe'],condition={'source':'steps.probe.result.json.ready','operator':'is_true'}),
  command('ready','True: process ready data','print("Ready path selected")',needs=['choose'],when={'step':'choose','equals':True}),
  command('waiting','False: defer processing','print("Waiting path selected")',needs=['choose'],when={'step':'choose','equals':False}),
  command('finish','Join the chosen path','print("Chosen path completed")',needs=['ready','waiting'],join='any'),
 ])
def _make_template(name,template):
 if template not in TEMPLATES:raise ValueError('Choose a supported starter template.')
 if template in ('loop-repeat','loop-until'):
  loop={'iterations':3 if template=='loop-repeat' else 5}
  if template=='loop-until':loop['until']='steps.check.result.json.ready';loop['delay']=.1
  return dict(version=1,name=name,steps=[dict(id='repeat',name='Repeat body workflow',kind='loop',workflow='workflow-workbench-loop-body.yaml',loop=loop,timeout=60)])
 if template=='no-code-tests':
  return dict(version=1,name=name,concurrency=4,inputs={},steps=[dict(id='tests',name='Run Python tests',kind='action',action={'type':'run_tests','runner':'unittest','target':'.'})])
 if template=='no-code':
  return dict(version=1,name=name,concurrency=4,inputs={},steps=[
   dict(id='values',name='Set starting values',kind='action',action={'type':'set_values','values':{'amount':3,'message':'Sample automation'}}),
   dict(id='calculate',name='Calculate double',kind='action',needs=['values'],action={'type':'calculate','left':'${steps.values.result.json.amount}','right':2,'operator':'multiply'}),
   dict(id='choose',name='If the result is positive',kind='condition',needs=['calculate'],condition={'source':'steps.calculate.result.json.value','operator':'greater_than','value':0}),
   dict(id='save',name='True: save sample JSON',kind='action',needs=['choose'],when={'step':'choose','equals':True},action={'type':'write_file','path':'.workbench/demo/no-code.json','content':'${steps.calculate.result.json}','format':'json','create_directories':True,'overwrite':True}),
   dict(id='review',name='False: review values',kind='manual',needs=['choose'],when={'step':'choose','equals':False},description='Inspect the result and record why it is not positive.'),
   dict(id='read',name='Read the saved result',kind='action',needs=['save'],action={'type':'read_json','path':'.workbench/demo/no-code.json'})])
 if template=='computed-if':
  w=branching(name);w['steps'].pop(0);w['steps'][0].update(name='If(a): compute readiness',needs=[],condition={'compute':{'commands':[{'argv':['${python}','-c','import json; print(json.dumps(2 + 2 == 4))']}]}});return w
 if template=='branching':return branching(name)
 if template=='project-checks':
  w=branching(name,'import json,pathlib;p=list(pathlib.Path(".").glob("*.py"));print(json.dumps({"ready":bool(p),"python_files":len(p)}))')
  w['steps'][0]['name']='Inspect this project';w['steps'][2]['name']='True: check Python syntax'
  w['steps'][2]['commands']=[{'argv':['${python}','-c','import ast,pathlib;files=list(pathlib.Path(".").glob("*.py"));[ast.parse(p.read_text(),filename=str(p)) for p in files];print("Parsed",len(files),"Python files")']}]
  w['steps'][3]['name']='False: no Python files';w['steps'][3]['commands']=[{'argv':['${python}','-c','print("No root Python files. Add checks for your project language.")']}]
  return w
 steps=[]
 if template in ('tests','release'):
  steps=[command('test','Run tests','import unittest;runner=unittest.TextTestRunner(verbosity=2);result=runner.run(unittest.defaultTestLoader.discover("."));raise SystemExit(not result.wasSuccessful())')]
  if template=='release':steps.append(dict(id='release-review',name='Review release evidence',kind='manual',description='Record tested source, package hashes and the release decision.',needs=['test'],approval=True))
 if template=='data-pipeline':
  steps=[command('prepare','Create sample CSV','from pathlib import Path;p=Path(".workbench/demo");p.mkdir(parents=True,exist_ok=True);(p/"input.csv").write_text("name,amount\\nAlpha,10\\nBeta,20\\n")',reports=['.workbench/demo/input.csv']),
   command('transform','Read CSV and calculate total','import csv,json;from pathlib import Path;rows=list(csv.DictReader(Path(".workbench/demo/input.csv").open()));data={"rows":len(rows),"total":sum(int(r["amount"]) for r in rows)};Path(".workbench/demo/result.json").write_text(json.dumps(data));print(json.dumps(data))',needs=['prepare'],capture='json',reports=['.workbench/demo/result.json']),
   dict(id='check',name='If data is present',kind='condition',needs=['transform'],condition={'source':'steps.transform.result.json.rows','operator':'greater_than','value':0}),
   command('publish','True: prepare summary','print("Sample data processed; inspect result.json in evidence")',needs=['check'],when={'step':'check','equals':True})]
 if template=='backup':
  steps=[command('prepare','Create a demonstration source file','from pathlib import Path;p=Path(".workbench/demo");p.mkdir(parents=True,exist_ok=True);(p/"source.txt").write_text("Example backup content\\n")'),
   command('copy','Copy the demo file','import shutil;shutil.copy2(".workbench/demo/source.txt",".workbench/demo/backup.txt")',needs=['prepare'],reports=['.workbench/demo/backup.txt']),
   command('verify','Verify backup bytes','from pathlib import Path;import hashlib,json;a=Path(".workbench/demo/source.txt").read_bytes();b=Path(".workbench/demo/backup.txt").read_bytes();assert a==b;print(json.dumps({"verified":True,"sha256":hashlib.sha256(b).hexdigest()}))',needs=['copy'],capture='json')]
 return dict(version=1,name=name,concurrency=4,inputs={},steps=steps)

def make_template(name,template):
 workflow=_make_template(name,template);steps=workflow['steps'];by_id={s['id']:s for s in steps};depth={};rows={}
 def level(id):
  if id not in depth:depth[id]=max([-1]+[level(parent) for parent in by_id[id].get('needs',[])])+1
  return depth[id]
 for step in steps:
  column=level(step['id']);row=rows.get(column,0);rows[column]=row+1;step['position']={'x':column*310,'y':row*180}
 return workflow

def starter_documents(filename,workflow,template):
 """Paired starter documents; callers create every file exclusively."""
 from pathlib import Path
 if template not in ('loop-repeat','loop-until'):return {filename:workflow}
 body_name=Path(filename).stem+'-body.yaml'
 workflow['steps'][0]['workflow']=body_name
 body=dict(version=1,name=workflow['name']+' · body',steps=[command('check','Compute readiness','import json,os;iteration=int(os.environ.get("WORKBENCH_LOOP_ITERATION","1"));print(json.dumps({"iteration":iteration,"ready":iteration>=3}))',capture='json')])
 return {filename:workflow,body_name:body}
