"""One packaged CLI for setup, browser editing, local execution and CI."""
import argparse
import json
import shlex
from pathlib import Path
import sys
import time
from .config import Store,assert_valid,parse_yaml,render_yaml
from .engine import Engine
from .server import serve

from .templates import TEMPLATES,make_template

def starter(name='My workflow',release=False):return make_template(name,'release' if release else 'tests')

def wizard(path,template=None,name=None):
    if path.exists():raise ValueError('Workflow already exists. Use the browser editor or another --config path.')
    interactive=not (template and name)
    name=name or input('Workflow name [My workflow]: ').strip() or 'My workflow'
    template=template or input('Template: '+', '.join(TEMPLATES)+' [tests]: ').strip() or 'tests'
    workflow=make_template(name,template)
    if template=='blank':workflow['steps']=[]
    else:
        if interactive and template in ('tests','release'):
            command=input('Test command [python -m unittest discover -v]: ').strip()
            if command:workflow['steps'][0]['commands']=[{'argv':shlex.split(command)}]
        print('Edit more steps and advanced settings in the browser or YAML.')
    path.write_text(render_yaml(workflow));print(f'Created {path}. Next: release-workbench serve --config {path}')

def main(argv=None):
    parser=argparse.ArgumentParser(description='Visual workflows, parallel jobs and release evidence on your own machine.')
    parser.add_argument('--version',action='version',version='0.6.0')
    sub=parser.add_subparsers(dest='action',required=True)
    for command in ('init','validate','serve','run','report'):
        child=sub.add_parser(command);child.add_argument('--config',default='release-workbench.yaml');child.add_argument('--output',default='.workbench')
        if command=='init':child.add_argument('--template',choices=list(TEMPLATES));child.add_argument('--name')
        if command in ('serve','run'):child.add_argument('--resume');child.add_argument('--input',action='append',default=[],metavar='KEY=JSON_OR_STRING')
        if command=='serve':child.add_argument('--port',type=int,default=3103);child.add_argument('--no-open',action='store_true')
        if command=='run':child.add_argument('--profile',default='all');child.add_argument('--step');child.add_argument('--non-interactive',action='store_true');child.add_argument('--rerun',action='store_true')
        if command=='report':child.add_argument('--run',required=True)
    args=parser.parse_args(argv)
    try:
        path=Path(args.config).resolve()
        if args.action=='init':wizard(path,args.template,args.name);return 0
        if args.action=='serve':
            if args.input:raise ValueError('Enter browser inputs after opening the workbench; --input is for CLI run.')
            serve(path,args.port,args.no_open,args.output,args.resume);return 0
        store=Store(path);record=store.read()
        if args.action=='validate':print(f'Valid: {record["workflow"]["name"]} · {len(record["workflow"]["steps"])} steps');return 0
        if args.action=='report':
            from .config import checked_path
            report=checked_path(checked_path(store.root,args.output),args.run)/'report.html'
            if not report.is_file():raise ValueError('Run report not found.')
            print(report);return 0
        inputs={}
        for item in args.input:
            key,value=item.split('=',1)
            try:inputs[key]=json.loads(value)
            except ValueError:inputs[key]=value
        engine=Engine(store.root,record['workflow'],args.output,args.resume,inputs)
        engine.start(args.profile,args.step,args.rerun);seen={}
        try:
            while engine.busy():
                state=engine.snapshot()
                for key,value in state['steps'].items():
                    event=(value['status'],value.get('stage',''))
                    if key in engine.selected and seen.get(key)!=event:print(f'{key}: {event[0]} · {event[1]}',flush=True);seen[key]=event
                time.sleep(.1)
        except KeyboardInterrupt:
            engine.stop()
            while engine.busy():time.sleep(.1)
        state=engine.snapshot()
        for key in engine.selected:
            value=state['steps'][key];print(f'{key}: {value["status"]}'+(' · '+value['error'] if value.get('error') else ''))
        print(f'Report: {engine.directory/"report.html"}\nJSON: {engine.directory/"summary.json"}')
        return engine.exit_code()
    except (ValueError,OSError,KeyError) as error:print('ERROR: '+str(error),file=sys.stderr);return 2

if __name__=='__main__':sys.exit(main())
