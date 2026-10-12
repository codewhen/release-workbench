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
from .config import assert_valid,checked_path,input_value

PASSED={'passed','recorded'}
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
            background={s['id'] for s in self.workflow['steps'] if s['kind']=='command' and s.get('mode','background')=='background'}
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
    def prepare(self,step):
        values=self.inputs()
        for key in set(step.get('requires_inputs',[]))|{k for k,v in self.workflow.get('inputs',{}).items() if v.get('required')}:
            values[key]=input_value(key,values.get(key,''),{**self.workflow['inputs'][key],'required':True})
        merged={**step,'env':{**self.workflow.get('env',{}),**step.get('env',{})}}
        return resolved_commands(merged,self.root,values)
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
                for key in downstream:self.state['steps'][key].update(status='pending',note='',error='')
            for key in self.selected:
                value=self.state['steps'][key]
                if value['status'] not in PASSED:value.update(status='queued',error='')
            self.state['selection']=sorted(self.selected);self.save()
            self.thread=threading.Thread(target=self.schedule,daemon=True);self.thread.start()
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
                    if any(d in FAILED for d in deps):value.update(status='blocked',error='A prerequisite failed, was disabled or cancelled.');progressed=True;continue
                    if self.stopped:value.update(status='cancelled',error='Scheduling stopped.');progressed=True;continue
                    if not all(d in PASSED for d in deps):continue
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
                    self.save();threading.Thread(target=self.execute,args=(s,commands,cwd,env,cancel),daemon=True).start()
                    held|=resources;progressed=True
                    if s.get('exclusive'):break
                if progressed:self.save()
                if not self.running:
                    # A paused scheduler stays alive; manual gates return control.
                    if not self.paused or self.stopped:return
            time.sleep(.05)
    def execute(self,step,commands,cwd,extra_env,cancel):
        key=step['id'];start=time.monotonic();wall=time.time();code=0;error='';process=None
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
                    process=subprocess.Popen(command,cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=os.name!='nt')
                    # Read lines on a separate thread so cancellation/timeouts never depend on output.
                    def read_output():
                        buffer=b''
                        while True:
                            chunk=process.stdout.read1(8192)
                            if not chunk:break
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
                    reader=threading.Thread(target=read_output,daemon=True);reader.start()
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
                    if reader.is_alive():raise RuntimeError('Output reader did not finish after process exit.')
                    if code:
                        if not error:error=f'Command exited {code}. Inspect the saved attempt log.'
                        break
                    write(f'DONE {n}/{len(commands)}; remaining: {len(commands)-n}\n')
                if code==0:
                    reports=self.collect(step,wall)
                    attempt['reports']=reports
                    for output in step.get('outputs',[]):
                        matches=self.matches(output['path'],wall if output.get('fresh',True) else None)
                        if not matches:raise ValueError('Missing output: '+output['path'])
                        data=json.loads(max(matches,key=lambda p:p.stat().st_mtime).read_text())
                        for part in output['key'].split('.'):data=data[int(part)] if isinstance(data,list) else data[part]
                        target=output['input'];data=input_value(target,data,{**self.workflow['inputs'][target],'required':True})
                        with self.lock:self.outputs[target]=data;self.state['outputs']=self.outputs
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
            status='cancelled' if cancel.is_set() or code==130 else 'passed' if code==0 else 'failed'
            elapsed=round(time.monotonic()-start,3);value.update(status=status,seconds=elapsed,error=error,exit_code=code)
            attempt.update(status=status,seconds=elapsed,exit_code=code,error=error)
            if status=='passed':self.history.setdefault(key,[]).append(elapsed)
            self.running.pop(key,None);self.events.pop(key,None);self.save()
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
            if any(self.state['steps'][dep]['status'] not in PASSED for dep in s.get('needs',[])):raise ValueError('Complete prerequisites before recording this gate.')
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
                actual=value.get('progress');finished=value['status'] in PASSED|FAILED
                percent=100 if finished else min(99,round(100*actual['done']/actual['total'])) if actual else min(95,round(100*elapsed/expected)) if s['id'] in self.running else 0
                value['timing']=dict(percent=percent,estimated=not actual and not finished and value['status'] in ('running','stopping'),elapsed=round(elapsed,1),eta=None if s['kind']=='manual' or value['status']=='stopping' or elapsed>=expected and not finished else 0 if finished else round(expected-elapsed),expected=expected)
                attempts=value['attempts']
                if attempts:
                    log=self.directory/attempts[-1]['log']
                    if log.exists():
                        with log.open('rb') as f:f.seek(max(0,log.stat().st_size-20000));value['tail']=f.read().decode(errors='replace')
            done=sum(v['status'] in PASSED for v in result['steps'].values());result['completion']=dict(done=done,total=len(self.workflow['steps']),percent=round(100*done/max(1,len(self.workflow['steps']))))
            return self.masker.object(result)
    def exit_code(self):
        values=[self.state['steps'][key]['status'] for key in self.selected]
        if any(v=='cancelled' for v in values):return 130
        if any(v=='failed' for v in values):return 1
        if any(v not in PASSED for v in values):return 2
        return 0
