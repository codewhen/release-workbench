"""Dependency scheduler, resource ownership, process supervision and evidence."""
from __future__ import annotations
from datetime import datetime,timezone
import copy
import hashlib
import html
import json
import os
from pathlib import Path
import platform
import re
import shlex
import signal
import statistics
import subprocess
import sys
import threading
import time
import uuid
import psutil
from .config import assert_valid,checked_path,input_value,Store

PASSED={'passed','recorded'}
SKIPPED={'skipped'}
FAILED={'failed','cancelled','blocked','disabled'}
PLATFORM={'Darwin':'macos','Windows':'windows','Linux':'linux'}.get(platform.system(),platform.system().lower())
EVENT_PREFIX='::workbench::'

def stamp():return datetime.now(timezone.utc).isoformat()
def fingerprint(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def source_fingerprint(root,workflow,output=None):
    records={}
    def git(*args):return subprocess.run(['git',*args],cwd=root,capture_output=True,timeout=15).stdout
    try:
        head=git('rev-parse','HEAD').decode().strip()
        files=set(git('diff','--name-only','-z','HEAD').decode().split('\0'))|set(git('ls-files','--others','--exclude-standard','-z').decode().split('\0'))
        for name in sorted(files-{''}):
            file=checked_path(root,name)
            if output and file.is_relative_to(output):continue
            records[name]=hashlib.sha256(file.read_bytes()).hexdigest() if file.is_file() else 'deleted'
    except (OSError,subprocess.SubprocessError):head=''
    for pattern in workflow.get('source_paths',[]):
        checked_path(root,pattern)
        for file in sorted(root.glob(pattern)):
            resolved=checked_path(root,str(file.relative_to(root)))
            if resolved.is_file() and not (output and resolved.is_relative_to(output)):records[file.relative_to(root).as_posix()]=hashlib.sha256(resolved.read_bytes()).hexdigest()
    return dict(head=head,dirty=records)

class Masker:
    def __init__(self,values):self.values=[];self.add(values)
    def add(self,values):self.values=sorted(set(self.values)|{part for v in values if v for part in [str(v),*str(v).splitlines()] if part},key=len,reverse=True)
    def text(self,value):
        for secret in self.values:value=value.replace(secret,'[REDACTED]')
        return value
    def object(self,value):
        if isinstance(value,str):return self.text(value)
        if isinstance(value,list):return [self.object(v) for v in value]
        if isinstance(value,dict):return {self.text(str(k)):self.object(v) for k,v in value.items()}
        return value

def cancel_tree(process,grace=30):
    try:root=psutil.Process(process.pid);children=root.children(recursive=True)
    except psutil.NoSuchProcess:process.wait();return
    targets=[*children,root]
    if os.name=='nt':
        subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True,timeout=15)
    else:
        # Descendants may have created separate sessions; signal each process,
        # leaf first, so Python runners get a chance to restore device settings.
        for child in targets:
            try:child.send_signal(signal.SIGINT)
            except psutil.NoSuchProcess:pass
        _,alive=psutil.wait_procs(targets,timeout=grace)
        for child in alive:
            try:child.kill()
            except psutil.NoSuchProcess:pass
    process.wait(timeout=15)

def resolved_commands(step,root,inputs):
    values={'python':sys.executable,'workspace':str(root),'platform':PLATFORM}
    values.update({f'input.{key}':value for key,value in inputs.items()})
    values.update({f'env.{key}':value for key,value in os.environ.items()})
    def expand(text,shell=False):
        def replacement(match):
            key=match[1]
            if shell and key not in values and not key.startswith(('input.','env.')) and key not in ('workspace','python','platform'):return match[0]
            if key not in values or values[key] in ('',None):raise ValueError(f'Missing value for ${{{key}}}.')
            return str(values[key])
        return re.sub(r'\$\{([^}]+)\}',replacement,str(text))
    commands=step.get('platform_commands',{}).get(PLATFORM,step.get('commands',[]))
    if step.get('platform_commands') and PLATFORM not in step['platform_commands'] and not step.get('commands'):
        raise ValueError(f'{step["name"]}: no commands for {PLATFORM}.')
    result=[]
    for command in commands:
        if 'argv' in command:result.append([expand(part) for part in command['argv']])
        else:
            executable=command['shell'];flag={'bash':'-c','sh':'-c','powershell':'-Command','cmd':'/c'}[executable]
            # Shell scripts cannot interpolate user input; use environment refs.
            if re.search(r'\$\{input\.',command['script']):raise ValueError('Pass inputs as argv or environment values, not shell interpolation.')
            result.append([executable,flag,expand(command['script'],shell=True)])
    cwd=checked_path(root,expand(step.get('cwd','.')))
    env={key:expand(value) for key,value in step.get('env',{}).items()}
    return result,cwd,env

class Engine:
    def __init__(self,root,workflow,output='.workbench',resume=None,inputs=None):
        self.root=Path(root).resolve();self.workflow=copy.deepcopy(assert_valid(workflow))
        self.output=checked_path(self.root,output);self.output.mkdir(parents=True,exist_ok=True)
        self.lock=threading.RLock();self.running={};self.events={};self.thread=None
        self.paused=False;self.stopped=False;self.selected=set();self.outputs={}
        secret_names=set(workflow.get('secret_env',[]))
        for step in workflow['steps']:secret_names.update(step.get('secret_env',[]))
        self.secret_names=secret_names
        self.masker=Masker([os.environ.get(name,'') for name in secret_names])
        self.initial_inputs={key:input_value(key,spec.get('default',''),{**spec,'required':False}) for key,spec in workflow.get('inputs',{}).items()}
        self.set_inputs(inputs or {},persist=False)
        self.signature=dict(workflow=fingerprint(workflow),source=source_fingerprint(self.root,workflow,self.output),platform=PLATFORM)
        self.history={}
        for file in sorted(self.output.glob('*/summary.json'))[-30:]:
            try:
                previous=json.loads(file.read_text())
                if previous.get('platform')!=PLATFORM or previous.get('signature',{}).get('workflow')!=self.signature['workflow']:continue
                for key,step in previous['steps'].items():
                    for attempt in step['attempts']:
                        if attempt['status']=='passed':self.history.setdefault(key,[]).append(attempt['seconds'])
            except (ValueError,KeyError,OSError,TypeError):continue
        self.run_id=resume or datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'-'+uuid.uuid4().hex[:8]
        if not re.fullmatch(r'[A-Za-z0-9_-]+',self.run_id):raise ValueError('Invalid run ID.')
        self.directory=checked_path(self.output,self.run_id)
        self.state=dict(version=1,run_id=self.run_id,name=workflow['name'],platform=PLATFORM,started=stamp(),signature=self.signature,inputs=self.initial_inputs,outputs={},selection=[],steps={s['id']:dict(status='pending',attempts=[],note='',error='',seconds=0) for s in workflow['steps']})
        if resume:
            old=json.loads((self.directory/'summary.json').read_text())
            if old['signature']!=self.signature:raise ValueError('Source or workflow changed. Start a new run; previous evidence is preserved.')
            if inputs and any(old['inputs'].get(k)!=v for k,v in inputs.items()):raise ValueError('Inputs changed. Start a new run.')
            self.state=old;self.initial_inputs=old['inputs'];self.outputs=old.get('outputs',{})
            for value in self.state['steps'].values():
                if value['status'] in ('running','stopping','queued'):
                    value.update(status='cancelled',error='Server exited during execution. Inspect remaining processes before rerunning.')
                    if value['attempts']:value['attempts'][-1]['status']='cancelled'
        else:self.directory.mkdir()
        self.save()
    def busy(self):return bool(self.thread and self.thread.is_alive()) or bool(self.running)
    def set_inputs(self,values,persist=True):
        with self.lock:
            if persist and self.busy():raise ValueError('Wait for running jobs before changing inputs.')
            specs=self.workflow.get('inputs',{})
            if set(values)-set(specs):raise ValueError('Unknown input field.')
            validated={key:input_value(key,value,{**specs[key],'required':False}) for key,value in values.items()}
            if persist and any(self.inputs().get(k)!=v for k,v in validated.items()) and any(v['attempts'] or v['status']=='recorded' for v in self.state['steps'].values()):
                raise ValueError('Inputs changed after collecting evidence. Create a new run before changing them.')
            self.initial_inputs.update(validated)
            if persist:
                self.state['inputs']=dict(self.initial_inputs);self.save()
    def inputs(self):return {**self.initial_inputs,**self.outputs}
    def ancestors(self,key):
        by_id={s['id']:s for s in self.workflow['steps']}
        if key not in by_id:raise ValueError('Unknown step '+key)
        result={key}
        for dep in by_id[key].get('needs',[]):result|=self.ancestors(dep)
        return result
    def selection(self,profile='all',step=None):
        if step:return self.ancestors(step)
        if profile=='all':return {s['id'] for s in self.workflow['steps']}
        if profile=='background':
            background={s['id'] for s in self.workflow['steps'] if s['kind'] in ('command','condition','workflow','action') and s.get('mode','background')=='background'}
            completed={key for key,value in self.state['steps'].items() if value['status'] in PASSED}
            return {key for key in background if self.ancestors(key)<=background|completed}
        if profile not in self.workflow.get('profiles',{}):raise ValueError('Unknown profile '+profile)
        result=set()
        for key in self.workflow['profiles'][profile]:result|=self.ancestors(key)
        return result
    def preview(self,step=None,profile='all'):
        selection=self.selection(profile,step);result=[]
        for s in self.workflow['steps']:
            if s['id'] not in selection:continue
            record=dict(id=s['id'],name=s['name'],kind=s['kind'],needs=s.get('needs',[]),resources=s.get('resources',[]),exclusive=s.get('exclusive',False))
            try:
                commands,cwd,_=self.prepare(s);record.update(commands=self.masker.object(commands),cwd=str(cwd))
            except ValueError as error:record['error']=str(error)
            result.append(record)
        return result
    def check_child_workflow(self,path,seen=()):
        path=checked_path(self.root,str(path))
        if path in seen or len(seen)>=16:raise ValueError('Child workflows contain a cycle or exceed 16 levels.')
        workflow=Store(path).read()['workflow']
        for child in workflow['steps']:
            if child['kind']=='workflow':self.check_child_workflow(checked_path(path.parent,child['workflow']),(*seen,path))
        return path
    def prepare(self,step):
        if step.get('action',{}).get('type')=='run_tests':
            from .actions import test_command
            step={**step,'commands':[{'argv':test_command(step['action'],self.root,step.get('cwd','.'))}]}
        if step['kind']=='workflow':
            path=self.check_child_workflow(step['workflow'])
            if path.parent!=self.root:raise ValueError('Run workflow cards currently require a YAML file in this project root. Use a command for another project.')
            step={**step,'commands':[{'argv':[sys.executable,'-m','release_workbench.cli','run','--config',str(path),'--output',str(self.directory/'children'/step['id']),'--non-interactive']}]}
        values=self.inputs()
        references=set(re.findall(r'\$\{input\.([^}]+)\}',json.dumps(step)))&set(self.workflow.get('inputs',{}))
        for key in set(step.get('requires_inputs',[]))|references|{k for k,v in self.workflow.get('inputs',{}).items() if v.get('required')}:
            values[key]=input_value(key,values.get(key,''),{**self.workflow['inputs'][key],'required':True})
        if step.get('action',{}).get('type')=='run_script':
            action=self.resolve_action(step['action'],os.environ)
            if not isinstance(action['path'],str):raise ValueError('Script path must be text.')
            file=checked_path(self.root,action['path'])
            if not file.is_file():raise ValueError('Script file not found: '+action['path'])
            program=[sys.executable] if action['language']=='python' else ['bash'] if action['language']=='bash' else ['powershell' if os.name=='nt' else 'pwsh','-NoProfile','-File']
            step={**step,'commands':[{'argv':[*program,str(file),*(str(v) for v in action.get('arguments',[]))]}]}
        if step.get('condition',{}).get('compute'):
            computation=copy.deepcopy(step['condition']['compute'])
            chosen=computation.get('platform_commands',{}).get(PLATFORM,computation.get('commands',[]))
            if not chosen:raise ValueError('Compute a needs commands for '+PLATFORM+'.')
            for commands in [chosen]:
                for command in commands:
                    if 'argv' in command:command['argv']=[str(v) for v in self.resolve_action(command['argv'],{**os.environ,**self.workflow.get('env',{}),**step.get('env',{})})]
                    elif re.search(r'\$\{(?:steps|input)\.',command['script']):raise ValueError('Pass computed inputs and earlier results as argv, not shell interpolation.')
            step={**step,'commands':chosen};step.pop('platform_commands',None)
        merged={**step,'env':{**self.workflow.get('env',{}),**step.get('env',{})}}
        return resolved_commands(merged,self.root,values)
    def input_requirements(self,profile='all',step=None,values=None):
        """Describe required user fields without running or changing evidence.

        A selected ancestor may provide an input through a validated JSON output;
        those generated values need not be entered before that producer runs.
        """
        with self.lock:
            selected=self.selection(profile,step);specs=self.workflow.get('inputs',{})
            values=values or {}
            if set(values)-set(specs):raise ValueError('Unknown input field.')
            available={**self.inputs(),**values};missing={}
            for current in self.workflow['steps']:
                if current['id'] not in selected or not current.get('enabled',True):continue
                ancestors=self.ancestors(current['id'])-{current['id']}
                produced={out['input'] for parent in self.workflow['steps'] if parent['id'] in selected&ancestors for out in parent.get('outputs',[])}
                settings=dict(condition=current.get('condition',{}),action=current.get('action',{}),commands=current.get('platform_commands',{}).get(PLATFORM,current.get('commands',[])),env={**self.workflow.get('env',{}),**current.get('env',{})},cwd=current.get('cwd','.'),resources=current.get('resources',[]))
                references=set(re.findall(r'\$\{input\.([^}]+)\}',json.dumps(settings)))&set(specs)
                if current.get('when') and self.state['steps'][current['when']['step']]['status'] not in PASSED:continue
                if current.get('when') and self.state['steps'][current['when']['step']].get('result',{}).get('decision') is not current['when']['equals']:continue
                if current.get('condition',{}).get('source','').startswith('inputs.'):
                    references.add(current['condition']['source'].split('.')[1])
                needed=set(current.get('requires_inputs',[]))|references|{key for key,spec in specs.items() if spec.get('required')}
                for key in sorted(needed-produced):
                    try:input_value(key,available.get(key,''),{**specs[key],'required':True})
                    except ValueError as error:missing.setdefault(key,dict(key=key,spec=specs[key],message=str(error),step=current['id']))
            return self.masker.object(dict(fields=list(missing.values())))

    def resources(self,step):
        values=self.inputs()
        result={re.sub(r'\$\{input\.([^}]+)\}',lambda m:str(values.get(m[1],'')),r) for r in step.get('resources',[])}
        if step.get('mode')=='interactive':result.add('desktop')
        return result
    def start(self,profile='all',step=None,rerun=False):
        with self.lock:
            if self.busy():raise ValueError('Workflow is already running or paused. Resume or stop it first.')
            current=dict(workflow=fingerprint(self.workflow),source=source_fingerprint(self.root,self.workflow,self.output),platform=PLATFORM)
            if current!=self.signature:raise ValueError('Source changed. Start a new run before executing.')
            self.selected=self.selection(profile,step);self.paused=False;self.stopped=False
            if rerun:
                downstream={s['id'] for s in self.workflow['steps'] if step in self.ancestors(s['id'])} if step else set(self.selected)
                for key in downstream:
                    self.state['steps'][key].update(status='pending',note='',error='');self.state['steps'][key].pop('result',None)
            for key in self.selected:
                value=self.state['steps'][key]
                if value['status'] not in PASSED:value.update(status='queued',error='')
            self.state['selection']=sorted(self.selected);self.save()
            self.thread=threading.Thread(target=self.schedule,daemon=True);self.thread.start()
    def dependency_state(self,step):
        deps=[self.state['steps'][d]['status'] for d in step.get('needs',[])]
        if any(d in FAILED for d in deps):return 'blocked'
        if not all(d in PASSED|SKIPPED for d in deps):return 'waiting'
        when=step.get('when')
        if when:
            parent=self.state['steps'][when['step']]
            if parent['status']=='skipped' or parent.get('result',{}).get('decision') is not when['equals']:return 'skipped'
        if step.get('join','all')=='any':return 'ready' if any(d in PASSED for d in deps) else 'skipped'
        return 'skipped' if any(d in SKIPPED for d in deps) else 'ready'
    def evaluate_condition(self,step):
        condition=step['condition']
        if 'input' in condition:
            source=condition['input'].get('step') or step.get('needs',[])[-1]
            result=self.state['steps'][source].get('result',{})
            if 'decision' in result:value=result['decision']
            elif 'json' in result:value=result['json']
            elif 'stdout' in result:
                try:value=json.loads(result['stdout'])
                except (ValueError,TypeError):raise ValueError('Compute source must return JSON true or false.') from None
            else:raise ValueError('No captured result from '+source+'. Enable JSON output capture on that card.')
            field=condition['input'].get('field','')
            try:
                for part in field.split('.') if field else []:value=value[int(part)] if isinstance(value,list) else value[part]
            except (KeyError,IndexError,TypeError,ValueError):raise ValueError('Compute Boolean field is missing: '+field) from None
            if type(value) is not bool:raise ValueError('Compute source must return a Boolean true or false; configure a Boolean JSON field for an object.')
            return value
        parts=condition['source'].split('.')
        value=self.inputs() if parts[0]=='inputs' else self.state['steps']
        try:
            for part in parts[1:]:value=value[int(part)] if isinstance(value,list) else value[part]
        except (KeyError,IndexError,TypeError,ValueError):raise ValueError('Condition source is missing: '+condition['source'])
        op=condition['operator'];expected=condition.get('value')
        if op=='is_true':return value is True
        if op in ('equals','not_equals'):
            same=type(value)==type(expected) or isinstance(value,(int,float)) and not isinstance(value,bool) and isinstance(expected,(int,float)) and not isinstance(expected,bool)
            equal=same and value==expected
            return equal if op=='equals' else not equal
        if op in ('greater_than','less_than'):
            if any(isinstance(v,bool) or not isinstance(v,(int,float)) for v in (value,expected)):raise ValueError('Numeric comparison requires numbers.')
            return value>expected if op=='greater_than' else value<expected
        if op=='contains':
            if not isinstance(value,(str,list,dict)) or isinstance(value,str) and not isinstance(expected,str):raise ValueError('Contains requires compatible text, array or object values.')
            return expected in value
        raise ValueError('Unknown condition operator.')
    def record_condition(self,step):
        key=step['id'];value=self.state['steps'][key]
        try:decision=self.evaluate_condition(step);status='passed';error=''
        except ValueError as exc:decision=None;status='failed';error=str(exc)
        result={'decision':decision}
        if 'input' in step['condition']:result['compute_source']=step['condition']['input'].get('step') or step.get('needs',[])[-1]
        value.update(status=status,result=result,error=error,stage='If: '+str(decision))
        log=f'{key}-{len(value["attempts"])+1}.log'
        (self.directory/log).write_text(self.masker.text(json.dumps({'condition':step['condition'],'decision':decision,'error':error},indent=2)))
        value['attempts'].append(dict(status=status,seconds=0,started=stamp(),commands=[],reports=[],log=log))

    def schedule(self):
        steps=self.workflow['steps']
        while True:
            with self.lock:
                progressed=False;held=set().union(*(v['resources'] for v in self.running.values())) if self.running else set()
                exclusive_running=any(v['exclusive'] for v in self.running.values())
                for s in steps:
                    key=s['id'];value=self.state['steps'][key]
                    if key not in self.selected or value['status']!='queued':continue
                    deps=[self.state['steps'][d]['status'] for d in s.get('needs',[])]
                    if not s.get('enabled',True):value.update(status='disabled',error='Disabled steps do not count as passing.');progressed=True;continue
                    dependency=self.dependency_state(s)
                    if dependency=='blocked':value.update(status='blocked',error='A prerequisite failed, was disabled or cancelled.');progressed=True;continue
                    if self.stopped:value.update(status='cancelled',error='Scheduling stopped.');progressed=True;continue
                    if dependency=='waiting':continue
                    if dependency=='skipped':
                        value.update(status='blocked' if s.get('approval') else 'skipped',error='Approval cannot be skipped; use an explicit branch join.' if s.get('approval') else '',stage='Branch not selected');progressed=True;continue
                    if s['kind']=='condition' and not s.get('condition',{}).get('compute'):
                        if self.paused or exclusive_running or s.get('exclusive') and self.running:continue
                        self.record_condition(s);progressed=True;continue
                    if s['kind']=='manual':value.update(status='manual',error='Record evidence to continue.');progressed=True;continue
                    if self.paused or exclusive_running:continue
                    if len(self.running)>=self.workflow.get('concurrency',4):break
                    resources=self.resources(s)
                    if resources&held:continue
                    if s.get('exclusive') and self.running:break  # Drain running jobs; no starvation.
                    try:commands,cwd,env=self.prepare(s)
                    except ValueError as error:value.update(status='blocked',error=str(error));progressed=True;continue
                    cancel=threading.Event();self.events[key]=cancel
                    self.running[key]=dict(resources=resources,exclusive=s.get('exclusive',False),started=time.monotonic())
                    value.update(status='running',error='',seconds=0,progress=None,stage='Starting')
                    self.save();threading.Thread(target=self.execute_action if s['kind']=='action' and s['action']['type'] not in ('run_tests','run_script') else self.execute,args=(s,commands,cwd,env,cancel),daemon=True).start()
                    held|=resources;progressed=True
                    if s.get('exclusive'):break
                if progressed:self.save()
                if not self.running:
                    # A paused scheduler stays alive; manual gates return control.
                    if (not self.paused or self.stopped) and not progressed:return
            time.sleep(.05)
    def resolve_action(self,value,env):
        if isinstance(value,dict):return {key:self.resolve_action(item,env) for key,item in value.items()}
        if isinstance(value,list):return [self.resolve_action(item,env) for item in value]
        if not isinstance(value,str):return value
        def reference(match):
            family,path=match.group(1),match.group(2);parts=path.split('.')
            data=self.state['steps'] if family=='steps' else self.inputs() if family=='input' else env
            try:
                for part in parts:data=data[int(part)] if isinstance(data,list) else data[part]
                return data
            except (KeyError,IndexError,TypeError,ValueError):raise ValueError('Missing action value: '+match.group(0))
        pattern=r'\$\{(steps|input|env)\.([^}]+)\}'
        full=re.fullmatch(pattern,value)
        if full:return reference(full)
        return re.sub(pattern,lambda match:str(reference(match)),value)
    def execute_action(self,step,commands,cwd,extra_env,cancel):
        from .actions import run_action
        key=step['id'];start=time.monotonic();wall=time.time();error='';status='passed';reports=[]
        with self.lock:
            self.masker.add([extra_env.get(name,'') for name in self.secret_names]);value=self.state['steps'][key]
            attempt=dict(started=stamp(),status='running',seconds=0,commands=[],log=f'{key}-{len(value["attempts"])+1}.log',reports=[])
            value['attempts'].append(attempt);value['stage']='Action: '+step['action']['type'];self.save()
        try:
            if cancel.is_set():raise InterruptedError('Action cancelled before starting.')
            env={**os.environ,**extra_env}
            data,files=run_action(step['action'],self.root,lambda item:self.resolve_action(item,env))
            reports=[dict(path=file.relative_to(self.root).as_posix(),sha256=self.file_hash(file)) for file in files]+self.collect(step,wall)
            self.collect_outputs(step,wall)
            if cancel.is_set():raise InterruptedError('Action cancelled; inspect partial file evidence.')
            if time.monotonic()-start>step.get('timeout',3600):raise ValueError('Configured timeout exceeded.')
            result={'exit_code':0,'json':data}
            with self.lock:value['result']=result;attempt['result']=self.masker.object(result)
        except InterruptedError as exc:status='cancelled';error=str(exc)
        except Exception as exc:status='failed';error=self.masker.text(str(exc))
        with self.lock:
            elapsed=round(time.monotonic()-start,3)
            (self.directory/attempt['log']).write_text(self.masker.text(json.dumps({'action':step['action'],'result':value.get('result'),'error':error},indent=2)))
            value.update(status=status,seconds=elapsed,error=error,exit_code=0 if status=='passed' else 130 if status=='cancelled' else 1)
            attempt.update(status=status,seconds=elapsed,error=error,exit_code=value['exit_code'],reports=reports)
            if status=='passed':self.history.setdefault(key,[]).append(elapsed)
            self.running.pop(key,None);self.events.pop(key,None);self.save()

    def execute(self,step,commands,cwd,extra_env,cancel):
        key=step['id'];start=time.monotonic();wall=time.time();code=0;error='';process=None
        computed=bool(step.get('condition',{}).get('compute'))
        with self.lock:
            self.masker.add([extra_env.get(name,'') for name in self.secret_names])
            value=self.state['steps'][key];attempt=dict(started=stamp(),status='running',seconds=0,commands=self.masker.object(commands),log=f'{key}-{len(value["attempts"])+1}.log',reports=[])
            value['attempts'].append(attempt);self.save()
        try:
            with (self.directory/attempt['log']).open('w',buffering=1,encoding='utf-8') as log:
                def write(text):log.write(self.masker.text(text));log.flush()
                write('Source: '+json.dumps(self.signature['source'])+'\n')
                for n,command in enumerate(commands,1):
                    if cancel.is_set():code=130;break
                    with self.lock:value['stage']=f'Command {n}/{len(commands)}: '+self.masker.text(shlex.join(command))[:500]
                    write(f'STAGE {n}/{len(commands)}: {step["name"]}\nCOMMAND: {shlex.join(command)}\nDIRECTORY: {cwd}\n')
                    env={**os.environ,'PYTHONUNBUFFERED':'1',**self.workflow.get('env',{}),**extra_env}
                    process=subprocess.Popen(command,cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE if computed else subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=os.name!='nt')
                    captured=bytearray();capture_overflow=False
                    # Read lines on a separate thread so cancellation/timeouts never depend on output.
                    def read_output(stream,capture=True):
                        nonlocal capture_overflow
                        buffer=b''
                        while True:
                            chunk=stream.read1(8192)
                            if not chunk:break
                            if capture:
                                if len(captured)+len(chunk)<=1048576:captured.extend(chunk)
                                else:capture_overflow=True
                            buffer+=chunk
                            while b'\n' in buffer:
                                line,buffer=buffer.split(b'\n',1);text=line.decode('utf-8',errors='replace')+'\n';write(text);self.consume(key,step,text)
                            if len(buffer)>65536:
                                # Preserve the tail that might contain a split secret.
                                keep=max([len(v.encode()) for v in self.masker.values]+[1]);cut=max(0,len(buffer)-keep)
                                if cut:
                                    safe=self.masker.text(buffer.decode('utf-8',errors='replace')).encode()
                                    write(safe[:-keep].decode('utf-8',errors='replace'));buffer=safe[-keep:]
                        if buffer:write(buffer.decode('utf-8',errors='replace'))
                    reader=threading.Thread(target=read_output,args=(process.stdout,),daemon=True);reader.start()
                    stderr_reader=threading.Thread(target=read_output,args=(process.stderr,False),daemon=True) if computed else None
                    if stderr_reader:stderr_reader.start()
                    deadline=start+step.get('timeout',3600);heartbeat=time.monotonic()+30
                    while process.poll() is None:
                        if cancel.wait(.1):
                            write('STOP: waiting for process/device cleanup.\n');cancel_tree(process);code=130;break
                        if time.monotonic()>=deadline:
                            write('TIMEOUT: waiting for cleanup.\n');cancel_tree(process);code=1;error='Configured timeout exceeded.';break
                        if time.monotonic()>=heartbeat:write('STILL RUNNING: '+step['name']+'\n');heartbeat=time.monotonic()+30
                    else:code=process.returncode
                    reader.join(timeout=35)
                    process.stdout.close()
                    if stderr_reader:
                        stderr_reader.join(timeout=35);process.stderr.close()
                        if stderr_reader.is_alive():raise RuntimeError('Diagnostic reader did not finish after process exit.')
                    if reader.is_alive():raise RuntimeError('Output reader did not finish after process exit.')
                    if code not in step.get('success_codes',[0]) or error:
                        if not error:error=f'Command exited {code}. Inspect the saved attempt log.'
                        break
                    write(f'DONE {n}/{len(commands)}; remaining: {len(commands)-n}\n')
                accepted=code in step.get('success_codes',[0]) and not error and not cancel.is_set()
                if accepted:
                    result={'exit_code':code}
                    if step.get('capture') or computed:
                        if capture_overflow:raise ValueError('Captured result exceeds 1 MiB. Write larger data to a report file.')
                        result['stdout']=captured.decode('utf-8',errors='replace').strip()
                        if step.get('capture')=='json' or computed:result['json']=json.loads(result['stdout'],parse_constant=lambda value:(_ for _ in ()).throw(ValueError('Invalid JSON constant: '+value)))
                    if computed:
                        if type(result['json']) is not bool:raise ValueError('Compute a must print JSON true or false to stdout, not a string, number or object.')
                        result['decision']=result['json']
                        write('IF(a): '+str(result['decision']).lower()+'; selected '+('True' if result['decision'] else 'False')+' branch\n')
                        with self.lock:value['stage']='If: '+str(result['decision'])
                    with self.lock:value['result']=result;attempt['result']=self.masker.object(result)
                    reports=self.collect(step,wall)
                    attempt['reports']=reports
                    self.collect_outputs(step,wall)
                    write('SUMMARY: '+str(self.directory/'summary.json')+'\n')
        except Exception as exc:
            code=1;error=self.masker.text(str(exc))
            if process and process.poll() is None:
                try:cancel_tree(process)
                except Exception as cleanup:error+='; cleanup: '+str(cleanup)
            with (self.directory/attempt['log']).open('a') as log:log.write('ERROR: '+error+'\n')
        if code and not attempt['reports']:
            try:attempt['reports']=self.collect(step,wall)
            except Exception as exc:
                with (self.directory/attempt['log']).open('a') as log:log.write('REPORT COLLECTION: '+self.masker.text(str(exc))+'\n')
        with self.lock:
            status='cancelled' if cancel.is_set() or code==130 else 'passed' if code in step.get('success_codes',[0]) and not error else 'failed'
            elapsed=round(time.monotonic()-start,3);value.update(status=status,seconds=elapsed,error=error,exit_code=code)
            attempt.update(status=status,seconds=elapsed,exit_code=code,error=error)
            if status=='passed':self.history.setdefault(key,[]).append(elapsed)
            self.running.pop(key,None);self.events.pop(key,None);self.save()
    def collect_outputs(self,step,wall):
        for output in step.get('outputs',[]):
            matches=self.matches(output['path'],wall if output.get('fresh',True) else None)
            if not matches:raise ValueError('Missing output: '+output['path'])
            data=json.loads(max(matches,key=lambda p:p.stat().st_mtime).read_text())
            for part in output['key'].split('.'):data=data[int(part)] if isinstance(data,list) else data[part]
            target=output['input'];data=input_value(target,data,{**self.workflow['inputs'][target],'required':True})
            with self.lock:self.outputs[target]=data;self.state['outputs']=self.outputs

    def consume(self,key,step,line):
        with self.lock:
            value=self.state['steps'][key]
            if line.startswith(EVENT_PREFIX):
                try:
                    event=json.loads(line[len(EVENT_PREFIX):]);done=float(event['done']);total=float(event['total'])
                    if total>0 and 0<=done<=total:value['progress']=dict(done=done,total=total,estimated=False)
                    if event.get('stage'):value['stage']=str(event['stage'])[:500]
                except (ValueError,KeyError,TypeError):pass
            elif re.match(r'^(STAGE|Verified:|STILL WAITING:)',line):value['stage']=line.strip()[:500]
            parser=step.get('progress')
            if parser:
                match=re.search(parser['pattern'],line)
                if match:
                    try:
                        mode=parser.get('mode','count');previous=value.get('progress') or {'done':0}
                        done=float(match['done'])+parser.get('offset',0) if mode in ('groups','index') else previous['done']+1
                        total=float(match['total']) if mode=='groups' else parser['total']
                        if total>0 and 0<=done<=total:value['progress']=dict(done=done,total=total,estimated=False)
                    except (ValueError,KeyError,IndexError):pass
    def matches(self,pattern,since=None):
        expanded,_,_=resolved_commands(dict(name='Report path',commands=[{'argv':[pattern]}]),self.root,self.inputs())
        pattern=expanded[0][0]
        checked_path(self.root,pattern)
        return [p for p in self.root.glob(pattern) if p.is_file() and checked_path(self.root,str(p.relative_to(self.root))).is_file() and (since is None or p.stat().st_mtime>=since)]
    @staticmethod
    def file_hash(file):
        with file.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
    def collect(self,step,since):
        results=[]
        for pattern in step.get('reports',[]):
            for file in self.matches(pattern,since):
                results.append(dict(path=file.relative_to(self.root).as_posix(),sha256=self.file_hash(file)))
        return results
    def record(self,key,note):
        with self.lock:
            if source_fingerprint(self.root,self.workflow,self.output)!=self.signature['source']:raise ValueError('Source changed. Start a new run before recording evidence.')
            s=next((s for s in self.workflow['steps'] if s['id']==key),None)
            if not s or s['kind']!='manual':raise ValueError('Select a manual gate.')
            if not note.strip():raise ValueError('Record evidence before completing this gate.')
            if not s.get('enabled',True):raise ValueError('Disabled gates cannot pass.')
            if self.dependency_state(s)!='ready':raise ValueError('Complete prerequisites before recording this gate.')
            value=self.state['steps'][key];evidence=self.masker.text(note[:10000])
            attempt=dict(started=stamp(),status='recorded',seconds=0,commands=[],reports=[],log=f'{key}-{len(value["attempts"])+1}.log')
            (self.directory/attempt['log']).write_text('Manual attestation '+stamp()+'\n'+evidence+'\n')
            value['attempts'].append(attempt)
            value.update(status='recorded',note=evidence,error='');self.save()
            if self.selected and not self.busy() and not self.stopped:
                self.thread=threading.Thread(target=self.schedule,daemon=True);self.thread.start()
    def stop(self,key=None):
        with self.lock:
            if key is None:self.stopped=True;self.paused=False
            elif key not in self.state['steps']:raise ValueError('Unknown step.')
            for current,event in self.events.items():
                if key is None or key==current:event.set();self.state['steps'][current]['status']='stopping'
            if key and key not in self.running and self.state['steps'][key]['status']=='queued':self.state['steps'][key].update(status='cancelled',error='Stopped before starting.')
            self.save()
    def pause(self,paused=True):
        with self.lock:self.paused=paused;self.save()
    def save(self):
        data=self.masker.object(self.state)
        target=self.directory/'summary.json';temp=target.with_suffix('.tmp');temp.write_text(json.dumps(data,indent=2)+'\n');os.replace(temp,target)
        sections=[]
        for s in self.workflow['steps']:
            value=data['steps'][s['id']];links=''.join(f'<li>{html.escape(a["status"])}: <a href="{a["log"]}">Attempt {n+1}</a></li>' for n,a in enumerate(value['attempts']))
            sections.append(f'<section><h2>{html.escape(s["name"])}</h2><p>{value["status"]} · {value["seconds"]}s</p><pre>{html.escape(value.get("error","")+"\n"+value["note"])}</pre><ul>{links}</ul></section>')
        report='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Workflow report</title><style>body{font:16px/1.6 system-ui;max-width:900px;margin:40px auto;padding:20px;color:#182a30}section{border-top:1px solid #cad5d8;padding:20px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere}a{color:#165c73}</style><h1>'+html.escape(data['name'])+'</h1><p>'+html.escape(self.run_id)+' · '+PLATFORM+'</p><p>Results apply to the recorded source, workflow and selection. Pending, disabled and blocked work is not passing evidence. Manual records are operator attestations.</p><a href="summary.json">JSON evidence</a>'+''.join(sections)+'</html>'
        (self.directory/'report.html').write_text(report)
    def snapshot(self):
        with self.lock:
            result=copy.deepcopy(self.state);result.update(active=list(self.running),busy=self.busy(),paused=self.paused)
            for s in self.workflow['steps']:
                value=result['steps'][s['id']];elapsed=time.monotonic()-self.running[s['id']]['started'] if s['id'] in self.running else value['seconds']
                expected=statistics.median(self.history.get(s['id'],[])[-10:]) if self.history.get(s['id']) else s.get('expected_seconds',60)
                actual=value.get('progress');finished=value['status'] in PASSED|FAILED|SKIPPED
                percent=100 if finished else min(99,round(100*actual['done']/actual['total'])) if actual else min(95,round(100*elapsed/expected)) if s['id'] in self.running else 0
                value['timing']=dict(percent=percent,estimated=not actual and not finished and value['status'] in ('running','stopping'),elapsed=round(elapsed,1),eta=None if s['kind']=='manual' or value['status']=='stopping' or elapsed>=expected and not finished else 0 if finished else round(expected-elapsed),expected=expected)
                attempts=value['attempts']
                if attempts:
                    log=self.directory/attempts[-1]['log']
                    if log.exists():
                        with log.open('rb') as f:f.seek(max(0,log.stat().st_size-20000));value['tail']=f.read().decode(errors='replace')
            done=sum(v['status'] in PASSED|SKIPPED for v in result['steps'].values());result['completion']=dict(done=done,total=len(self.workflow['steps']),percent=round(100*done/max(1,len(self.workflow['steps']))))
            return self.masker.object(result)
    def exit_code(self):
        values=[self.state['steps'][key]['status'] for key in self.selected]
        if any(v=='cancelled' for v in values):return 130
        if any(v=='failed' for v in values):return 1
        if any(v not in PASSED|SKIPPED for v in values):return 2
        return 0
