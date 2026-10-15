"""Version two keeps scope membership separate from dependency connections."""
from jsonschema import Draft202012Validator
GROUPS={'while','until','repeat','foreach','try'}
CONTROL={'switch','break','continue','wait','poll','declare','assign','update','merge','handle_error'}
def validate_flow(workflow,schema):
 errors=[f'{".".join(map(str,e.path))}: {e.message}' for e in Draft202012Validator(schema["oneOf"][1]).iter_errors(workflow)]
 if errors:return errors
 steps=workflow['steps'];by={s['id']:s for s in steps}
 if len(by)!=len(steps):errors.append('Step IDs must be unique across all scopes.')
 from .config import validate
 common={k:v for k,v in workflow.items() if k not in ('version','steps','profiles')};common.update(version=1,steps=[])
 errors.extend(validate(common))
 for name,ids in workflow.get('profiles',{}).items():
  if not set(ids)<=set(by):errors.append('Profile '+name+': unknown card IDs.')
 for s in steps:
  key=s['id'];parent=s.get('scope');kind=s['kind'];c=s.get('control',{})
  if parent and (parent not in by or by[parent]['kind'] not in GROUPS):errors.append(key+': scope must name a group.')
  if s.get('region','body') in ('catch','finally') and by.get(parent,{}).get('kind')!='try':errors.append(key+': Catch/Finally requires a Try group.')
  if s.get('region')=='condition' and by.get(parent,{}).get('kind') not in ('while','until'):errors.append(key+': Condition region requires While or Repeat until.')
  for d in s.get('needs',[]):
   if d not in by or (by[d].get('scope'),by[d].get('region','body'))!=(parent,s.get('region','body')):errors.append(key+': dependencies must stay in their group region; use group inputs/outputs.')
  if kind=='workflow' and (s.get('resources') or s.get('exclusive')):errors.append(key+': put locks on executable child cards, not the workflow container.')
  if kind in GROUPS:
   if s.get('resources') or s.get('exclusive') or s.get('mode')=='interactive':errors.append(key+': put execution locks on cards inside the group.')
   if kind in ('while','until') and not c.get('test'):errors.append(key+': configure the loop condition.')
   if kind=='foreach' and 'items' not in c:errors.append(key+': choose an array to process.')
   if kind=='repeat' and 'count' not in c:errors.append(key+': set the repeat count.')
  if kind in GROUPS|{'poll'} and c.get('test'):
   test=c['test']
   if not isinstance(test,dict) or not (test.get('source') or test.get('compute',{}).get('commands')):errors.append(key+': choose a condition value or probe commands.')
   source=test.get('source','').split('.') if isinstance(test.get('source',''),str) else []
   if len(source)>1 and source[0]=='steps':
    result=by.get(source[1])
    if result is None:errors.append(key+': condition result references a missing card.')
    elif kind=='while' and result.get('scope')==key and result.get('region','body')!='condition':errors.append(key+': return a value from Condition, not Body.')
   if test.get('operator','is_true') not in ('is_true','equals','not_equals','less_than','greater_than','contains'):errors.append(key+': invalid condition operator.')
  if kind=='poll' and not c.get('test'):errors.append(key+': configure a condition probe.')
  if kind in ('declare','assign','update') and not c.get('name'):errors.append(key+': choose a variable name.')
  if kind=='switch':
   ids=[v['id'] for v in c.get('cases',[])];
   if not c.get('source') or len(set(ids))!=len(ids) or 'default' in ids:errors.append(key+': choose a source and unique case IDs excluding default.')
  ancestors=[];p=parent
  while p and p in by:
   if p in ancestors:errors.append(key+': cyclic group membership.');break
   ancestors.append(p);p=by[p].get('scope')
  if len(ancestors)>16:errors.append(key+': maximum group depth is 16.')
  if kind in ('break','continue') and not any(by[p]['kind'] in GROUPS-{'try'} for p in ancestors):errors.append(key+': Break/Continue belongs inside a loop.')
  if kind=='break' and any(by[p]['kind']=='foreach' and by[p].get('control',{}).get('parallel',1)>1 for p in ancestors):errors.append(key+': use sequential For each when Break is required.')
  if s.get('approval') and parent:errors.append(key+': final approval gates belong in the main workflow after required groups.')
  if kind=='handle_error' and not any(by[p]['kind']=='try' for p in ancestors):errors.append(key+': Handle error belongs inside Try/Catch.')
  if s.get('retry') and kind=='condition' and not s.get('condition',{}).get('compute'):errors.append(key+': retry applies to executable probes, not pure comparisons.')
  if s.get('retry') and kind not in ('command','action','condition','poll'):errors.append(key+': retries apply only to executable cards.')
  if kind not in GROUPS|CONTROL:
   # Retain v1 field and command validation using a local scope-shaped graph.
   peers=[{k:v for k,v in x.items() if k not in ('scope','region','size','collapsed','region_sizes','control','retry')} for x in steps if (x.get('scope'),x.get('region','body'))==(parent,s.get('region','body'))]
   for x in peers:
    original=by[x['id']]
    if original['kind'] in GROUPS|CONTROL:
     x.clear();x.update(id=original['id'],name=original['name'],kind='condition' if original['kind']=='switch' else 'command',needs=original.get('needs',[]),required=original.get('required',True))
     if original['kind']=='switch':x['condition']={'source':'inputs.route_probe','operator':'is_true'}
     else:x['commands']=[{'argv':['placeholder']}]
    if x.get('when') and isinstance(x['when']['equals'],str):x['when']={**x['when'],'equals':True}
    condition=x.get('condition',{})
    if condition.get('source','').split('.')[0] in ('vars','loop','scope','error'):x['condition']={'source':'inputs.route_probe','operator':'is_true'}
   base={k:v for k,v in workflow.items() if k not in ('steps','version')};base.update(version=1,steps=peers,profiles={},inputs={**workflow.get('inputs',{}),'route_probe':{'label':'Validation placeholder','type':'boolean','default':False}})
   errors.extend(e for e in validate(base) if e.startswith(key+':'))
  when=s.get('when')
  if when and (when['step'] not in s.get('needs',[]) or by.get(when['step'],{}).get('kind') not in ('condition','switch')):errors.append(key+': route must depend on If or Switch.')
 def visit(key,path):
  if key in path:raise ValueError('Dependency cycle: '+' → '.join([*path,key]))
  for dep in by[key].get('needs',[]):
   if dep in by:visit(dep,[*path,key])
 try:
  for key in by:visit(key,[])
 except ValueError as e:errors.append(str(e))
 return list(dict.fromkeys(errors))
