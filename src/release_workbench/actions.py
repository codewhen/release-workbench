"""Bounded local actions configured as data, without evaluating program text."""
import json,math,os,tempfile
from pathlib import Path
from .config import checked_path

LIMIT=1048576

def run_action(action,root,resolve):
 action=resolve(action);kind=action['type']
 if kind=='set_values':return action['values'],[]
 if kind=='calculate':
  left,right=action['left'],action['right']
  if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in (left,right)):raise ValueError('Calculate needs two finite numbers.')
  op=action['operator']
  if op=='add':value=left+right
  elif op=='subtract':value=left-right
  elif op=='multiply':value=left*right
  elif op=='divide':
   if right==0:raise ValueError('Cannot divide by zero.')
   value=left/right
  else:raise ValueError('Unknown calculation operator.')
  if not math.isfinite(value):raise ValueError('Calculation result is not finite.')
  return {'value':value},[]
 if kind in ('file_exists','read_json','write_file') and not isinstance(action.get('path'),str):raise ValueError('File path must be text.')
 if kind=='file_exists':
  file=checked_path(root,action['path']);return {'exists':file.is_file(),'path':file.relative_to(root).as_posix()},[]
 if kind=='read_json':
  file=checked_path(root,action['path'])
  if file.stat().st_size>LIMIT:raise ValueError('JSON input exceeds 1 MiB.')
  data=file.read_bytes()
  if len(data)>LIMIT:raise ValueError('JSON input exceeds 1 MiB.')
  return json.loads(data,parse_constant=lambda x:(_ for _ in ()).throw(ValueError('Invalid JSON constant: '+x))),[]
 if kind=='write_file':
  file=checked_path(root,action['path']);content=action['content']
  if action.get('format','text')=='json':content=json.dumps(content,indent=2,allow_nan=False)+'\n'
  elif not isinstance(content,str):raise ValueError('Text file content must be text; use JSON format for structured values.')
  data=content.encode('utf-8')
  if len(data)>LIMIT:raise ValueError('File content exceeds 1 MiB.')
  if action.get('create_directories'):file.parent.mkdir(parents=True,exist_ok=True)
  if action.get('overwrite',False):
   fd,temp=tempfile.mkstemp(prefix='.workbench-write-',dir=file.parent)
   try:
    with os.fdopen(fd,'wb') as stream:stream.write(data)
    os.replace(temp,file)
   finally:
    if Path(temp).exists():Path(temp).unlink()
  else:
   with file.open('xb') as stream:stream.write(data)
  return {'path':file.relative_to(root).as_posix(),'bytes':len(data),'written':True},[file]
 raise ValueError('Unknown built-in action.')


def test_command(action,root,cwd):
 runner=action['runner'];target=action.get('target','')
 if runner=='unittest':return ['${python}',str(Path(__file__).with_name('test_runner.py')),target or '.']
 if runner=='pytest':return ['${python}','-m','pytest',target or '.']
 if runner=='go':return ['go','test',target or './...']
 if runner=='flutter':return ['flutter','test',target or 'test']
 if runner=='npm':return ['npm','test']+(['--',target] if target else [])
 if runner=='gradle':
  import re
  task=target or 'test'
  if not re.fullmatch(r'[A-Za-z0-9_:]+',task):raise ValueError('Enter a Gradle task name, such as :app:testDebugUnitTest.')
  folder=checked_path(root,cwd)
  if os.name=='nt':return ['cmd','/c','gradlew.bat',task]
  return [str(folder/'gradlew'),task]
 raise ValueError('Unknown test runner.')
