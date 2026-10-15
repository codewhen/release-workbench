"""Structured v2 control flow; legacy execution supervises each leaf process.

Group membership is not an execution back-edge. Every iteration has a fresh scope
and evidence path; the coordinator below owns the budget and locks for all leaves.
"""
import copy,json,os,re,threading,time
from concurrent.futures import ThreadPoolExecutor,wait,FIRST_COMPLETED
from .engine import Engine,PASSED,SKIPPED,FAILED,stamp,fingerprint,source_fingerprint
from .flow_validation import GROUPS

class FlowSignal(Exception):
 def __init__(self,kind,context=None):self.kind=kind;self.context=context;super().__init__(kind)
class FlowFailure(Exception):
 def __init__(self,message,context=None):self.context=context;super().__init__(message)
class FlowBlocked(FlowFailure):pass

class Coordinator:
 def __init__(self,limit):self.limit=limit;self.cv=threading.Condition();self.active={};self.exclusive_waiting=0;self.paused=False
 def acquire(self,key,resources,exclusive,checkpoint):
  with self.cv:
   if exclusive:self.exclusive_waiting+=1
   try:
    while True:
     checkpoint();held=set().union(*(v[0] for v in self.active.values())) if self.active else set()
     if not any(v[1] for v in self.active.values()) and not resources&held and len(self.active)<self.limit and (not self.active if exclusive else not self.exclusive_waiting):
      self.active[key]=(resources,exclusive);return
     self.cv.wait(.05)
   finally:
    if exclusive:self.exclusive_waiting-=1
 def release(self,key):
  with self.cv:self.active.pop(key,None);self.cv.notify_all()

class FlowEngine(Engine):
 def __init__(self,*args,**kwargs):
  super().__init__(*args,**kwargs);self.coordinator=Coordinator(self.workflow.get('concurrency',4));self.leaves={};self.cancelled=set();self.manual_events={};self.manual_notes={};self.manual_decisions={};self.children={};self.interactive=False;self.deadlines={}
  self.by={s['id']:s for s in self.workflow['steps']};self.state['version']=2;self.state.setdefault('executions',{});self.state.setdefault('variables',{})
 def selection(self,profile='all',step=None):
  if step:
   s=self.by[step]
   while s.get('scope'):s=self.by[s['scope']]
   chosen=self.ancestors(s['id'])
  elif profile=='all':chosen={s['id'] for s in self.workflow['steps'] if not s.get('scope')}
  elif profile=='background':
   def compatible(k):return self.by[k].get('mode','background')=='background' and self.by[k]['kind']!='manual' and all(compatible(s['id']) for s in self.workflow['steps'] if s.get('scope')==k)
   roots={s['id'] for s in self.workflow['steps'] if not s.get('scope') and compatible(s['id'])}
   chosen={k for k in roots if self.ancestors(k)<=roots}
  else:
   chosen=super().selection(profile)
   chosen={k for k in chosen if not self.by[k].get('scope')}
   if profile=='background':
    def compatible(k):return self.by[k].get('mode','background')=='background' and self.by[k]['kind']!='manual' and all(compatible(s['id']) for s in self.workflow['steps'] if s.get('scope')==k)
    chosen={k for k in chosen if compatible(k)}
  result=set(chosen)
  for s in self.workflow['steps']:
   p=s.get('scope');seen=set()
   while p and p not in seen:
    if p in chosen:result.add(s['id']);break
    seen.add(p);p=self.by[p].get('scope')
  return result
 def preview(self,step=None,profile='all'):
  return [dict(id=s['id'],name=s['name'],kind=s['kind'],scope=s.get('scope'),region=s.get('region','body'),needs=s.get('needs',[]),control=self.masker.object(s.get('control',{})),commands=self.masker.object(s.get('commands',[]))) for s in self.workflow['steps'] if s['id'] in self.selection(profile,step)]
 def start(self,profile='all',step=None,rerun=False):
  with self.lock:
   if self.busy():raise ValueError('Workflow is already running.')
   current=dict(workflow=fingerprint(self.workflow),source=source_fingerprint(self.root,self.workflow,self.output),platform=self.signature['platform'])
   if current!=self.signature:raise ValueError('Source changed. Start a new run.')
   self.selected=self.selection(profile,step)
   if not rerun and any(self.state['steps'][k]['status']=='cancelled' and self.state['steps'][k]['attempts'] for k in self.selected):raise ValueError('Interrupted work requires explicit retry (rerun) or a new run.')
   self.stopped=False;self.paused=False;self.cancelled.clear();self.deadlines.clear();self.state['selection']=sorted(self.selected)
   if rerun:
    affected=set(self.selected)
    if step:
     target=self.by[step]
     while target.get('scope'):target=self.by[target['scope']]
     roots={s['id'] for s in self.workflow['steps'] if not s.get('scope') and target['id'] in self.ancestors(s['id'])}
     affected=set(roots)
     for s in self.workflow['steps']:
      owner=s
      while owner.get('scope'):owner=self.by[owner['scope']]
      if owner['id'] in roots:affected.add(s['id'])
    for k in affected:self.state['steps'][k].update(status='pending',error='')
   self.state['starts']=self.state.get('starts',0)+1
   self.thread=threading.Thread(target=self.schedule,daemon=True);self.thread.start()
 def is_cancelled(self,path):return any(path==k or path.startswith(k+'/') or '/' not in k and self.state['executions'].get(path,{}).get('step')==k for k in self.cancelled)
 def checkpoint(self,path):
  if self.stopped or self.is_cancelled(path):raise FlowSignal('cancelled')
  if any((path==k or path.startswith(k+'/')) and time.monotonic()>=deadline for k,deadline in self.deadlines.items()):raise FlowFailure('Configured group timeout exceeded.')
  while self.paused or self.coordinator.paused:
   if self.stopped or self.is_cancelled(path):raise FlowSignal('cancelled')
   time.sleep(.05)
 def sleep(self,seconds,path):
  end=time.monotonic()+seconds
  while time.monotonic()<end:self.checkpoint(path);time.sleep(min(.05,end-time.monotonic()))
 def ref(self,source,ctx):
  parts=source.split('.');families={'vars':ctx['vars'],'steps':ctx['steps'],'inputs':self.inputs(),'input':self.inputs(),'loop':ctx.get('loop',{}),'scope':ctx.get('scope',{}),'error':ctx.get('error',{}),'env':os.environ}
  if parts[0] not in families:raise FlowFailure('Unknown value source: '+source)
  value=families[parts.pop(0)]
  try:
   for p in parts:value=value[int(p)] if isinstance(value,list) else value[p]
  except (KeyError,IndexError,ValueError,TypeError):raise FlowFailure('Missing scoped value: '+source) from None
  return copy.deepcopy(value)
 def resolve(self,value,ctx):
  if isinstance(value,dict):return {k:self.resolve(v,ctx) for k,v in value.items()}
  if isinstance(value,list):return [self.resolve(v,ctx) for v in value]
  if not isinstance(value,str):return value
  pattern=r'\$\{((?:vars|steps|inputs|input|loop|error|scope)\.[^}]+)\}'
  m=re.fullmatch(pattern,value)
  if m:return self.ref(m[1],ctx)
  return re.sub(pattern,lambda m:str(self.ref(m[1],ctx)),value)
 def test(self,test,ctx,path,retry=None):
  if test.get('compute'):
   probe={'id':'probe','name':'Condition probe','kind':'command',**test['compute'],'capture':'json'}
   probe['retry']=retry or {'attempts':1}
   result=self.leaf(probe,ctx,path+'/probe')['json'];value=result
  else:
   value=self.ref(test['source'],ctx);op=test.get('operator','is_true');expected=self.resolve(test.get('value'),ctx)
   if op=='is_true':
    if type(value) is not bool:raise FlowFailure('Condition must be Boolean true or false.')
    return value
   if op in ('equals','not_equals'):
    equal=type(value) is type(expected) and value==expected;return equal if op=='equals' else not equal
   if op in ('less_than','greater_than'):
    if any(type(v) not in (int,float) for v in (value,expected)):raise FlowFailure('Numeric condition needs numbers.')
    return value<expected if op=='less_than' else value>expected
   if op=='contains':return expected in value
   raise FlowFailure('Unknown condition operator.')
  if type(value) is not bool:raise FlowFailure('Condition probe must return JSON true or false.')
  return value
 def schedule(self):
  ctx={'vars':{},'steps':{},'loop':{}}
  try:
   ctx=self.region(None,'body',ctx,'root/run-'+str(self.state.get('starts',1)),resume=True);self.state['variables']=self.masker.object(ctx['vars'])
  except FlowSignal:pass
  except FlowFailure:pass
  except Exception as e:self.state['error']=self.masker.text(str(e))
  finally:
   with self.lock:
    for k in self.selected:
     if self.state['steps'][k]['status'] in ('queued','running','stopping','pending'):
      # An unentered loop body or Catch is skipped, not a request for user input.
      parent=next((s.get('scope') for s in self.workflow['steps'] if s['id']==k),None)
      ancestor=None
      while parent:
       ancestor=self.state['steps'].get(parent,{}).get('status')
       if ancestor not in ('queued','running','stopping','pending'):break
       parent=next((s.get('scope') for s in self.workflow['steps'] if s['id']==parent),None)
      status='cancelled' if self.stopped or ancestor=='cancelled' else 'skipped' if ancestor in ('passed','recorded','skipped') else 'blocked'
      self.state['steps'][k].update(status=status,error=None if status=='skipped' else 'Not reached; inspect enclosing scope.',stage='Control branch was not entered.' if status=='skipped' else 'Not reached.')
    self.save()
 def region(self,parent,region,ctx,path,resume=False):
  nodes=[s for s in self.workflow['steps'] if s.get('scope')==parent and s.get('region','body')==region and (parent is not None or s['id'] in self.selected)]
  results={};contexts={};pending={s['id']:s for s in nodes};active={};signal=None;failed=[]
  if resume:
   for k in list(pending):
    old=self.state['steps'][k]
    if old['status'] in PASSED:
     results[k]=old;contexts[k]=copy.deepcopy(old.get('scope_context',ctx));pending.pop(k)
  def skipped(s,status,error=''):
   value={'status':status,'result':{},'error':error};results[s['id']]=value;self.state['steps'][s['id']].update(value)
  with ThreadPoolExecutor(max_workers=64) as pool:
   while pending or active:
    try:self.checkpoint(path)
    except FlowSignal as e:signal=e;local=e.context or local.kind
    for key,s in list(pending.items()):
     if signal:skipped(s,'skipped' if signal in ('break','continue') else 'cancelled');pending.pop(key);continue
     if not all(d in results for d in s.get('needs',[])):continue
     deps=[results[d]['status'] for d in s.get('needs',[])]
     if any(d in FAILED for d in deps):skipped(s,'blocked','A prerequisite failed.');pending.pop(key);continue
     if not s.get('enabled',True):skipped(s,'disabled','Disabled required work cannot pass.');pending.pop(key);continue
     when=s.get('when');skip=when and results[when['step']].get('result',{}).get('decision')!=when['equals']
     if skip or (s.get('join','all')=='all' and 'skipped' in deps) or (s.get('join')=='any' and deps and not any(d in PASSED for d in deps)):
      skipped(s,'blocked' if s.get('approval') else 'skipped');pending.pop(key);continue
     branch=copy.deepcopy(ctx);parents=[contexts[d] for d in s.get('needs',[]) if d in contexts]
     for d in s.get('needs',[]):branch['steps'][d]=results[d]
     if len(parents)==1:branch['vars']=copy.deepcopy(parents[0]['vars']);branch['handled']=parents[0].get('handled',False)
     elif parents:
      branch['vars']={k:copy.deepcopy(v) for k,v in parents[0]['vars'].items() if all(k in p['vars'] and p['vars'][k]==v for p in parents)}
     for p in parents:branch['steps'].update(p['steps'])
     future=pool.submit(self.node,s,branch,path+'/'+key);active[future]=key;pending.pop(key)
    if not active:
     if pending:raise FlowFailure('Unresolved dependencies in '+path)
     break
    done,_=wait(active,timeout=.05,return_when=FIRST_COMPLETED)
    for f in done:
     key=active.pop(f)
     try:value,out=f.result();results[key]=value;contexts[key]=out
     except FlowSignal as e:
      if e.kind=='cancelled' and parent is None and not self.stopped:
       results[key]={'status':'cancelled','result':{}};contexts[key]=e.context or copy.deepcopy(ctx);continue
      if signal is None:
       signal=e.kind;ctx=e.context or ctx
       for other in active.values():self.cancelled.add(path+'/'+other)
      results[key]={'status':'passed' if e.kind in ('break','continue') else 'cancelled','result':{}}
     except Exception as e:results[key]={'status':'blocked' if isinstance(e,FlowBlocked) else 'failed','error':str(e)};contexts[key]=getattr(e,'context',None) or copy.deepcopy(ctx);failed.append(e)
  if signal:raise FlowSignal(signal,ctx)
  out=copy.deepcopy(ctx)
  for key,v in results.items():out['steps'][key]=v
  terminals=[k for k in contexts if not any(k in s.get('needs',[]) for s in nodes)]
  if len(terminals)==1:out=contexts[terminals[0]]
  elif terminals:
   allctx=[contexts[k] for k in terminals];out['vars']={k:copy.deepcopy(v) for k,v in allctx[0]['vars'].items() if all(p['vars'].get(k)==v for p in allctx)};out['handled']=any(p.get('handled') for p in allctx)
  for key,v in results.items():out['steps'][key]=v
  if failed or any(r['status'] in FAILED for r in results.values()):raise (FlowBlocked if failed and all(isinstance(e,FlowBlocked) for e in failed) else FlowFailure)('; '.join(map(str,failed)) or 'A card failed or was blocked in '+path,out)
  return out
 def node(self,s,ctx,path):
  before_variables=copy.deepcopy(ctx['vars'])
  key=s['id'];start=time.monotonic();status='passed';error='';result={};control=s.get('control',{});log=key[:60]+'-'+fingerprint(path)[:16]+'.log'
  with self.lock:
   value=self.state['steps'][key];value.update(status='running',stage=path,execution_id=path,error='');self.running[path]={'started':start,'resources':set(),'exclusive':False};self.state['executions'][path]={'step':key,'status':'running','started':stamp()};self.save()
  try:
   kind=s['kind']
   if kind=='wait' or kind=='manual' and 'timeout' in s:self.deadlines[path]=start+s.get('timeout',3600)
   self.checkpoint(path)
   if kind in GROUPS:
    result=self.group(s,ctx,path)
   elif kind in ('declare','assign','update'):
    name=control['name'];v=self.resolve(control.get('value'),ctx)
    if kind=='declare' and name in ctx['vars']:raise FlowFailure('Variable already declared: '+name)
    if kind!='declare' and name not in ctx['vars']:raise FlowFailure('Declare the variable before updating: '+name)
    if kind=='update':
     old=ctx['vars'][name];op=control.get('operator','add')
     if op=='add':v=old+v
     elif op=='subtract':v=old-v
     elif op=='multiply':v=old*v
     elif op=='append':v=[*old,v]
    ctx['vars'][name]=v;result={'json':{name:v}}
   elif kind=='merge':
    objects=self.resolve(control.get('value',[]),ctx);merged={}
    for obj in objects:
     if not isinstance(obj,dict):raise FlowFailure('Merge outputs requires objects.')
     for k,v in obj.items():
      if k in merged and control.get('conflicts','error')=='error':raise FlowFailure('Duplicate output key: '+k)
      if k not in merged or control.get('conflicts')=='last':merged[k]=v
    result={'json':merged}
   elif kind=='switch':
    v=self.ref(control['source'],ctx);result={'decision':next((case['id'] for case in control.get('cases',[]) if type(self.resolve(case['value'],ctx)) is type(v) and self.resolve(case['value'],ctx)==v),'default')}
   elif kind in ('break','continue'):raise FlowSignal(kind,ctx)
   elif kind=='handle_error':ctx['handled']=True;result={'json':{'handled':True}}
   elif kind=='wait':self.sleep(control.get('delay',1),path)
   elif kind=='poll':
    n=0;deadline=start+control.get('timeout',1800) if control.get('timeout',1800) is not None else float('inf')
    if deadline!=float('inf'):self.deadlines[path]=deadline
    while True:
     self.checkpoint(path)
     if time.monotonic()>=deadline:raise FlowFailure('Poll timeout exceeded.')
     n+=1;decision=self.test(control['test'],ctx,path+f'/poll-{n}',s.get('retry'));self.event(path,iteration=n,decision=decision)
     if decision:break
     if control.get('limit',100) is not None and n>=control.get('limit',100):raise FlowFailure('Poll iteration limit exceeded.')
     self.sleep(control.get('delay',1),path)
    result={'json':{'polls':n,'ready':True}}
   elif kind=='workflow':result=self.child_workflow(s,ctx,path)
   elif kind=='manual':
    if not self.interactive:raise FlowBlocked('Manual evidence required in '+path)
    event=threading.Event();value['note']='';self.manual_events[path]=(event,key);value.update(status='manual',stage=path);self.save()
    while not event.wait(.05):self.checkpoint(path)
    result={'json':{'evidence':self.manual_notes.get(path,value.get('note','')),**({'decision':self.manual_decisions[path]} if path in self.manual_decisions else {})}};self.manual_events.pop(path,None);status='recorded'
   elif kind=='condition' and not s.get('condition',{}).get('compute'):
    test=s['condition']
    if 'input' in test:
     source=test['input'].get('step') or s.get('needs',[])[-1];data=ctx['steps'][source]['result'];v=data.get('decision',data.get('json'))
     for part in test['input'].get('field','').split('.') if test['input'].get('field') else []:v=v[part]
     if type(v) is not bool:raise FlowFailure('If input must be Boolean.')
     result={'decision':v}
    else:result={'decision':self.test(test,ctx,path)}
   else:result=self.leaf(s,ctx,path)
  except FlowSignal as e:
   status='passed' if e.kind in ('break','continue') else 'cancelled';error=e.kind if status=='cancelled' else '';result={'control':e.kind};raise
  except Exception as e:status='blocked' if isinstance(e,FlowBlocked) else 'failed';error=self.masker.text(str(e));raise (FlowBlocked(error,ctx) if isinstance(e,FlowBlocked) else FlowFailure(error,ctx)) from e
  finally:
   with self.lock:
    elapsed=round(time.monotonic()-start,3);record={'status':status,'result':self.masker.object(result),'error':error,'seconds':elapsed,'execution_id':path,'scope_context':self.masker.object(ctx),'variables_before':self.masker.object(before_variables),'variables_after':self.masker.object(ctx['vars'])}
    (self.directory/log).write_text(json.dumps(self.masker.object(record),indent=2)+'\n');attempt={'status':status,'seconds':elapsed,'started':stamp(),'commands':[],'reports':[],'log':log}
    reports=[r['report'] for r in self.state['executions'][path].get('leaf_attempts',[]) if r.get('report')]
    if result.get('report'):reports.append(result['report'])
    for report in dict.fromkeys(reports):
     if (self.root/report).is_file():attempt['reports'].append({'path':report,'sha256':self.file_hash(self.root/report)})
    value.update(record);value['attempts'].append(attempt);self.state['executions'][path].update(record);self.running.pop(path,None);self.save()
  out=copy.deepcopy(ctx);out['steps'][key]={'status':status,'result':result};return {'status':status,'result':result},out
 def event(self,path,**values):
  with self.lock:
   self.state['executions'][path].setdefault('events',[]).append({'at':stamp(),**self.masker.object(values)})
   self.state['executions'][path].update(self.masker.object(values));key=self.state['executions'][path]['step'];self.state['steps'][key]['stage']=path+' · '+json.dumps(values);self.save()
 def group(self,s,ctx,path):
  kind=s['kind'];c=s.get('control',{});start=time.monotonic();local=copy.deepcopy(ctx);history=[]
  if c.get('timeout',1800) is not None:self.deadlines[path]=start+c.get('timeout',1800)
  local['scope']={'inputs':self.resolve(c.get('inputs',{}),ctx)};local['steps']={}
  def region(name,context,suffix):return self.region(s['id'],name,context,path+'/'+suffix)
  if kind=='try':
   signal=None;failure=None
   try:local=region('body',local,'try')
   except FlowSignal as e:signal=e;local=e.context or local
   except FlowFailure as e:
    failure=e;local=e.context or local;local['error']={'message':str(e)};local['handled']=False
    try:local=region('catch',local,'catch')
    except (FlowSignal,FlowFailure) as catch:failure=catch
    if local.get('handled'):failure=None
   finally:
    if not self.stopped and (signal is None or signal.kind!='cancelled') and not any(path==k or path.startswith(k+'/') for k in self.cancelled):local=region('finally',local,'finally')
   if failure:raise failure
   if signal:signal.context=local;raise signal
  else:
   items=self.resolve(c.get('items',[]),ctx) if kind=='foreach' else None
   if kind=='foreach' and not isinstance(items,list):raise FlowFailure('For each needs an array.')
   def iteration(i,item=None):
    self.checkpoint(path)
    context=copy.deepcopy(local);context['loop']={'iteration':i+1,'index':i,'item':item}
    try:return region('body',context,f'iteration-{i+1}/body')
    except FlowSignal as e:
     if kind=='foreach' and c.get('parallel',1)>1 and e.kind=='continue':return e.context or context
     raise
   if kind=='foreach' and c.get('parallel',1)>1:
    if c.get('limit',100) is not None and len(items)>c.get('limit',100):raise FlowFailure('Collection exceeds the configured iteration limit.')
    with ThreadPoolExecutor(max_workers=c['parallel']) as pool:
     history=[r for r in pool.map(lambda pair:iteration(*pair),enumerate(items))]
   else:
    i=0
    while True:
     self.checkpoint(path)
     timeout=c.get('timeout',1800)
     if timeout is not None and time.monotonic()-start>=timeout:raise FlowFailure('Group timeout exceeded.')
     if kind=='repeat' and i>=c.get('count',3) or kind=='foreach' and i>=len(items):break
     local['loop']={'iteration':i+1,'index':i,'item':items[i] if items is not None else None}
     if kind=='while':
      local=region('condition',local,f'iteration-{i+1}/condition');decision=self.test(c['test'],{**local,'steps':{**ctx['steps'],**local['steps']}},path+f'/condition-{i+1}');self.event(path,iteration=i+1,decision=decision)
      if not decision:break
     limit=c.get('limit',100)
     if limit is not None and i>=limit:raise FlowFailure('Group iteration limit exceeded.')
     try:local=iteration(i,items[i] if items is not None else None)
     except FlowSignal as e:
      local=e.context or local
      if e.kind=='break':break
      if e.kind!='continue':raise
     i+=1;history.append(copy.deepcopy(local) if kind=='foreach' else {'iteration':i});self.event(path,iteration=i)
     if kind=='until':
      local=region('condition',local,f'iteration-{i}/condition');decision=self.test(c['test'],{**local,'steps':{**ctx['steps'],**local['steps']}},path+f'/condition-{i}');self.event(path,iteration=i,decision=decision)
      if decision:break
     self.sleep(c.get('delay',0),path)
  exports={'items':[self.resolve(c.get('outputs',{}),context) for context in history]} if kind=='foreach' else self.resolve(c.get('outputs',{}),{**local,'steps':{**ctx['steps'],**local['steps']}})
  return {'json':exports,'iterations':len(history),'handled':local.get('handled',False)}
 def child_workflow(self,s,ctx,path):
  from .config import Store,workspace_root
  file=self.check_child_workflow(s['workflow']);config=Store(file).read()['workflow']
  bindings=self.resolve(s.get('workflow_inputs',{}),ctx)
  config={**config,'version':2,'workspace':'.'}
  child=FlowEngine(self.root,config,str((self.directory/'children'/path).relative_to(self.root)),inputs=bindings);child.coordinator=self.coordinator;child.secret_names|=self.secret_names;child.masker.add(self.masker.values);self.children[path]=child
  try:
   child.start()
   while child.busy():
    try:self.checkpoint(path)
    except (FlowFailure,FlowSignal):
     child.stop(force=True)
     while child.busy():time.sleep(.03)
     raise
    if child.paused!=self.paused:child.pause(self.paused)
    time.sleep(.03)
   code=child.exit_code()
   if code==130:raise FlowSignal('cancelled')
   if code==2:raise FlowBlocked('Child workflow requires evidence or has blocked work. '+path)
   if code:raise FlowFailure('Child workflow failed: '+path)
   return {'json':child.state.get('outputs',{}),'report':str((child.directory/'report.html').relative_to(self.root))}
  finally:self.children.pop(path,None)
 def leaf(self,s,ctx,path):
  key=s['id'];retry=s.get('retry',{});last=None
  for n in range(retry.get('attempts',1)):
   self.checkpoint(path);self.coordinator.acquire(path,self.resources(s),s.get('exclusive',False),lambda:self.checkpoint(path))
   try:
    step={k:v for k,v in s.items() if k not in ('scope','region','control','retry','collapsed','size','when','needs')};step['id']='task';step['needs']=[]
    # Never interpolate dynamic data into shell source; use argv or environment.
    collections=[step.get('commands',[]),*step.get('platform_commands',{}).values()]
    compute=step.get('condition',{}).get('compute',{});collections.extend([compute.get('commands',[]),*compute.get('platform_commands',{}).values()])
    for commands in collections:
     for command in commands:
      if 'script' in command and re.search(r'\$\{(?:vars|steps|loop|error|scope|input|inputs)\.',command['script']):raise FlowFailure('Use argv or environment bindings for dynamic shell data.')
    step=self.resolve(step,ctx)
    text=lambda v:v if isinstance(v,str) else json.dumps(v,allow_nan=False)
    for command in step.get('commands',[]):
     if 'argv' in command:command['argv']=[text(v) for v in command['argv']]
    for commands in step.get('platform_commands',{}).values():
     for command in commands:
      if 'argv' in command:command['argv']=[text(v) for v in command['argv']]
    if step.get('condition',{}).get('compute'):
     compute=step['condition']['compute']
     for commands in [compute.get('commands',[]),*compute.get('platform_commands',{}).values()]:
      for command in commands:
       if 'argv' in command:command['argv']=[text(v) for v in command['argv']]
    if step.get('env'):step['env']={k:text(v) for k,v in step['env'].items()}
    if step.get('action',{}).get('type')=='run_script':step['action']['arguments']=[text(v) for v in step['action'].get('arguments',[])]
    w={'version':1,'name':s['name'],'steps':[step],'env':self.workflow.get('env',{}),'secret_env':list(self.secret_names),'inputs':self.workflow.get('inputs',{})}
    runner=Engine(self.root,w,str((self.directory/'leaves'/path/f'attempt-{n+1}').relative_to(self.root)));self.leaves[path]=runner;runner.set_inputs(self.inputs());runner.start()
    timeout_error=None
    while runner.busy():
     try:self.checkpoint(path)
     except FlowFailure as e:timeout_error=e;runner.stop(force=True)
     except FlowSignal:runner.stop()
     if self.stopped or any(path==k or path.startswith(k+'/') for k in self.cancelled):runner.stop()
     time.sleep(.03)
    state=runner.snapshot()['steps']['task'];self.leaves.pop(path,None)
    self.outputs.update(runner.outputs)
    with self.lock:
     self.state['executions'].setdefault(path,{}).setdefault('leaf_attempts',[]).append({'status':state['status'],'report':str((runner.directory/'report.html').relative_to(self.root))})
    if timeout_error:raise timeout_error
    if state['status']=='cancelled':raise FlowSignal('cancelled')
    if state['status'] in PASSED:return {**state.get('result',{}),'report':str((runner.directory/'report.html').relative_to(self.root))}
    last=state.get('error') or 'Executable card failed.'
    if retry.get('exit_codes') and state.get('exit_code') not in retry['exit_codes']:break
   finally:self.coordinator.release(path)
   if n+1<retry.get('attempts',1):self.sleep(retry.get('delay',1)*retry.get('backoff',1)**n,path)
  raise FlowFailure(last or 'Executable card failed.')
 def manual_returns_condition(self,key):
  return any(s['kind'] in ('while','until') and s.get('control',{}).get('test',{}).get('source')=='steps.'+key+'.result.json.decision' for s in self.workflow['steps'])
 def record(self,key,note,decision=None):
  if not note.strip():raise ValueError('Record evidence before continuing.')
  candidates=[(p,e,k) for p,(e,k) in self.manual_events.items() if p==key or k==key]
  if len(candidates)!=1:raise ValueError('Choose a unique active manual execution.')
  p,event,k=candidates[0]
  if self.manual_returns_condition(k) and type(decision) is not bool:raise ValueError('Choose True or False for the condition result.')
  if decision is not None and type(decision) is not bool:raise ValueError('Condition result must be Boolean true or false.')
  if decision is not None:self.manual_decisions[p]=decision
  self.manual_notes[p]=self.masker.text(note);self.state['steps'][k]['note']=self.manual_notes[p];event.set()
 def stop(self,key=None,force=False):
  with self.lock:
   if key is None:self.stopped=True;self.paused=False;self.coordinator.paused=False
   else:
    matches=[p for p,v in self.state['executions'].items() if v.get('step')==key and v.get('status')=='running'];self.cancelled.update(matches or [key])
   for path in self.running:
    if key is None or any(path==k or path.startswith(k+'/') for k in self.cancelled):
     current=self.state['executions'].get(path,{}).get('step')
     if current:self.state['steps'][current].update(status='stopping',stage='Stop requested; cleaning up active work')
   for path,child in list(self.children.items()):
    if key is None or any(path==k or path.startswith(k+'/') for k in self.cancelled):child.stop(force=force)
   for path,runner in list(self.leaves.items()):
    if key is None or any(path==k or path.startswith(k+'/') for k in self.cancelled):runner.stop(force=force)
   self.save()
 def pause(self,paused=True):
  with self.lock:self.paused=paused;self.coordinator.paused=paused;self.save()
 def snapshot(self):
  with self.lock:
   result=copy.deepcopy(self.state);result['manual_executions']=[{'id':p,'step':k,'decision_required':self.manual_returns_condition(k)} for p,(e,k) in self.manual_events.items()];result.update(active=list({v.get('step') for p,v in self.state['executions'].items() if p in self.running}),busy=self.busy(),paused=self.paused)
   for p,(event,key) in self.manual_events.items():result['steps'][key].update(status='manual',execution_id=p)
   for key,value in result['steps'].items():
    value['timing']={'percent':100 if value['status'] in PASSED|FAILED|SKIPPED else None,'estimated':False,'indeterminate':value['status'] in ('running','manual'),'elapsed':round(time.monotonic()-self.running[value['execution_id']]['started'],1) if value.get('execution_id') in self.running else value.get('seconds',0),'eta':None,'expected':None}
    if value.get('attempts'):value['tail']=(self.directory/value['attempts'][-1]['log']).read_text()[-20000:]
    for path,runner in list(self.leaves.items()):
     if self.state['executions'].get(path,{}).get('step')==key:value['tail']=runner.snapshot()['steps']['task'].get('tail','')
   roots=[s for s in self.workflow['steps'] if not s.get('scope')];done=sum(result['steps'][s['id']]['status'] in PASSED|SKIPPED for s in roots);result['completion']={'done':done,'total':len(roots),'percent':round(100*done/max(1,len(roots)))}
   return self.masker.object(result)
 def exit_code(self):
  values=[self.state['steps'][k]['status'] for k in self.selected if not self.by[k].get('scope')]
  if self.stopped or 'cancelled' in values:return 130
  if 'failed' in values:return 1
  return 0 if all(v in PASSED|SKIPPED for v in values) else 2
