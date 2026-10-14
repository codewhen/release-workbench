"""Bounded child-workflow repetition; launched under normal process supervision."""
import argparse,json,os,sys,time
from pathlib import Path
from .config import Store,checked_path,workspace_root
from .engine import Engine,EVENT_PREFIX,Masker

def read_result(state,source):
    parts=source.split('.')[1:];value=state['steps']
    try:
        for part in parts:value=value[int(part)] if isinstance(value,list) else value[part]
    except (KeyError,IndexError,TypeError,ValueError):raise ValueError('Loop stop result is missing: '+source) from None
    if type(value) is not bool:raise ValueError('Loop stop result must be a Boolean true or false.')
    return value

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--config',required=True);parser.add_argument('--output',required=True);parser.add_argument('--iterations',type=int,required=True);parser.add_argument('--until');parser.add_argument('--delay',type=float,default=0);parser.add_argument('--secret-env',action='append',default=[]);parser.add_argument('--input',action='append',default=[]);args=parser.parse_args(argv)
    engine=None;summary={'status':'running','iterations':[],'limit':args.iterations,'stop_result':None};output=None;masker=None
    try:
        if not 1<=args.iterations<=1000 or not 0<=args.delay<=3600:raise ValueError('Use 1–1000 iterations and a delay of 0–3600 seconds.')
        store=Store(args.config);workflow=store.read()['workflow'];root=workspace_root(store.root,workflow);output=checked_path(root,args.output);output.mkdir(parents=True,exist_ok=True)
        secret_names=set(args.secret_env)|set(workflow.get('secret_env',[]))|{n for step in workflow['steps'] for n in step.get('secret_env',[])};masker=Masker([os.environ.get(n,'') for n in secret_names]);inputs={}
        workflow={**workflow,'secret_env':sorted(secret_names)}
        for item in args.input:
            key,value=item.split('=',1);inputs[key]=json.loads(value)
        for iteration in range(1,args.iterations+1):
            if iteration>1 and args.delay:time.sleep(args.delay)
            os.environ['WORKBENCH_LOOP_ITERATION']=str(iteration)
            print('LOOP: iteration '+str(iteration)+'/'+str(args.iterations),flush=True)
            engine=Engine(store.root,workflow,str(output/f'iteration-{iteration}'),inputs=inputs);engine.start();seen={}
            while engine.busy():
                state=engine.snapshot()
                for key,value in state['steps'].items():
                    event=(value['status'],value.get('stage',''))
                    if seen.get(key)!=event:print(masker.text(f'Iteration {iteration} · {key}: {event[0]} · {event[1]}'),flush=True);seen[key]=event
                time.sleep(.1)
            state=engine.snapshot();code=engine.exit_code();summary['iterations'].append(dict(iteration=iteration,status='passed' if code==0 else 'blocked' if code==2 else 'failed',report=str(engine.directory/'report.html'),summary=str(engine.directory/'summary.json')))
            if code:raise ValueError('Loop body failed or reached a blocked/manual gate in iteration '+str(iteration)+'. Inspect its saved report.')
            stop=read_result(state,args.until) if args.until else None;summary['stop_result']=stop
            print(EVENT_PREFIX+json.dumps(dict(done=iteration,total=args.iterations,stage=f'Iteration {iteration}/{args.iterations} complete')),flush=True)
            (output/'loop-summary.json').write_text(json.dumps(masker.object(summary),indent=2)+'\n')
            if stop is True:summary['status']='passed';break
        else:
            if args.until:raise ValueError('Loop reached its iteration limit without a true stop result.')
            summary['status']='passed'
        return 0
    except KeyboardInterrupt:
        if engine:
            engine.stop()
            while engine.busy():time.sleep(.1)
        summary['status']='cancelled';return 130
    except (ValueError,OSError) as error:
        summary.update(status='failed',error=str(error));print('LOOP FAILED: '+(masker.text(str(error)) if masker else str(error)),file=sys.stderr,flush=True);return 1
    finally:
        if output:(output/'loop-summary.json').write_text(json.dumps(masker.object(summary) if masker else summary,indent=2)+'\n')

if __name__=='__main__':raise SystemExit(main())
