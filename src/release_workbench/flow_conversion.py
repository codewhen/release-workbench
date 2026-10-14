"""Explicit, validated draft conversion of a legacy child-workflow Loop."""
import copy,re
from pathlib import Path
from .config import Store,assert_valid,workspace_root,checked_path

def convert_loop(root,workflow,key):
 root=Path(root).resolve()
 value=copy.deepcopy(workflow);step=next((s for s in value['steps'] if s['id']==key),None)
 if not step or step['kind']!='loop':raise ValueError('Choose a legacy Loop card.')
 child=Store(checked_path(root,step['workflow'])).read()['workflow']
 if workspace_root(checked_path(root,step['workflow']).parent,child)!=root:raise ValueError('Child workspace differs from its parent.')
 if any(s.get('approval') or s.get('outputs') or s.get('scope') for s in child['steps']):raise ValueError('This child needs manual conversion of approvals, input outputs or existing groups.')
 mapping={s['id']:key+'-'+s['id'] for s in child['steps']};known={s['id'] for s in value['steps']}
 if known&set(mapping.values()):raise ValueError('Converted IDs conflict with existing cards.')
 bindings={name:step.get('workflow_inputs',{}).get(name,spec.get('default')) for name,spec in child.get('inputs',{}).items()}
 if any(v is None for v in bindings.values()):raise ValueError('Bind every child input before conversion.')
 def rewrite(v):
  if isinstance(v,dict):return {k:rewrite(x) for k,x in v.items()}
  if isinstance(v,list):return [rewrite(x) for x in v]
  if not isinstance(v,str):return v
  full=re.fullmatch(r'\$\{input\.([^}]+)\}',v)
  if full and full[1] in bindings:return bindings[full[1]]
  for old,new in mapping.items():v=v.replace('steps.'+old+'.','steps.'+new+'.')
  for name,binding in bindings.items():v=v.replace('${input.'+name+'}',str(binding))
  return v
 children=[]
 for s in child['steps']:
  n=rewrite(s);n.update(id=mapping[s['id']],scope=key,region='body',needs=[mapping[d] for d in s.get('needs',[])],position={'x':40+len(children)%2*300,'y':100+len(children)//2*230})
  n.pop('requires_inputs',None)
  if n.get('when'):n['when']['step']=mapping[s['when']['step']]
  if n.get('condition',{}).get('input',{}).get('step'):n['condition']['input']['step']=mapping[s['condition']['input']['step']]
  n['env']={**child.get('env',{}),**n.get('env',{})};children.append(n)
 until=step['loop'].get('until');step['kind']='until' if until else 'repeat';step['control']={'limit':step['loop']['iterations'],'timeout':step.get('timeout',3600),'delay':step['loop'].get('delay',0),'outputs':{}}
 if until:step['control']['test']={'source':rewrite(until),'operator':'is_true'}
 else:step['control']['count']=step['loop']['iterations']
 for f in ('workflow','workflow_inputs','loop','resources','exclusive'):step.pop(f,None)
 step['mode']='background';step['size']={'width':840,'height':max(560,350+(len(children)//2)*230)};value['version']=2;value['steps']+=children
 value['secret_env']=sorted(set(value.get('secret_env',[]))|set(child.get('secret_env',[])))
 assert_valid(value);return value
