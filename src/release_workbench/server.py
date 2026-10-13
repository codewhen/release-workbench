"""Local editor API. Configuration edits never execute commands."""
from __future__ import annotations
import difflib
import json
import mimetypes
from pathlib import Path
import secrets
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import unquote,urlparse,parse_qs
import webbrowser
from .config import SCHEMA,Store,assert_valid,checked_path,parse_yaml,render_yaml
from .engine import Engine,resolved_commands
from .library import Library

class App:
    def __init__(self,config,output='.workbench',resume=None):
        self.store=Store(config);self.output=output;self.lock=threading.RLock();self.engine=Engine(self.store.root,self.store.read()['workflow'],output,resume)
    def config(self):return self.store.read()
    def idle(self):
        if self.engine.busy():raise ValueError('Stop the workflow and wait for cleanup before editing configuration.')
    def save(self,value,revision):
        with self.lock:
            self.idle();record=self.store.save(value,revision);self.engine=Engine(self.store.root,record['workflow'],self.output);return record
    def fresh(self):
        with self.lock:
            self.idle();self.engine=Engine(self.store.root,self.store.read()['workflow'],self.output,inputs=self.engine.initial_inputs);return self.engine.snapshot()
    def detect(self):
        with self.lock:
            self.idle();workflow=self.store.read()['workflow'];hook=workflow.get('detect')
            if not hook:raise ValueError('No detection hook configured.')
            commands,cwd,env=resolved_commands(dict(name='Input detection',commands=hook['commands']),self.store.root,self.engine.inputs())
            import os
            values={};warnings=[]
            for command in commands:
                result=subprocess.run(command,cwd=cwd,env=dict(os.environ,**env),capture_output=True,text=True,timeout=hook.get('timeout',30),check=True)
                data=json.loads(result.stdout)
                if not isinstance(data,dict):raise ValueError('Detection must return a JSON object.')
                warnings.extend(data.get('warnings',[]))
                for key,options in data.items():
                    if key!='warnings' and key in workflow.get('inputs',{}):
                        if not isinstance(options,list) or any(not isinstance(v,dict) or 'value' not in v or 'label' not in v for v in options):raise ValueError('Detection candidates need value and label fields.')
                        values[key]=options
            return dict(candidates=values,warnings=warnings)
    def allowed_file(self,relative):
        file=checked_path(self.store.root,relative)
        if file.is_relative_to(self.engine.output):return file
        workflow=self.store.read()['workflow']
        for directory in workflow.get('report_paths',[]):
            if file.is_relative_to(checked_path(self.store.root,directory)):return file
        for step in workflow['steps']:
            for pattern in step.get('reports',[]):
                if file in self.engine.matches(pattern):return file
        raise ValueError('File is outside configured report locations.')

def make_server(app,port=3103):
    library=app if isinstance(app,Library) else Library(app.store.path,app.output,initial_app=app)
    token=secrets.token_urlsafe(32);static=Path(__file__).with_name('static')
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def send(self,value,code=200,kind='application/json'):
            data=json.dumps(value).encode() if isinstance(value,(dict,list)) else value.encode() if isinstance(value,str) else value
            self.send_response(code);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(data)
        def trusted(self):return self.headers.get('Host') in (f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}')
        def do_GET(self):
            if not self.trusted():return self.send({'error':'Invalid local host.'},403)
            route=unquote(urlparse(self.path).path)
            try:
                if route=='/api/schema':return self.send(SCHEMA)
                if route=='/api/library':
                    with library.lock:return self.send(library.catalog())
                if route.startswith(('/api/','/files/')):
                    with library.lock:app=library.get(parse_qs(urlparse(self.path).query).get('workflow',[None])[0])
                if route=='/api/config':return self.send(app.config())
                if route=='/api/schema':return self.send(SCHEMA)
                if route=='/api/state':
                    result=app.engine.snapshot();result['directory']=str(app.engine.directory.relative_to(app.store.root));return self.send(result)
                if route.startswith('/files/'):
                    file=app.allowed_file(route[7:])
                    if not file.is_file():return self.send({'error':'File not found.'},404)
                    # Report HTML renders inside an opaque sandbox with scripts disabled.
                    self.send_response(200);self.send_header('Content-Type',('text/html' if file.suffix=='.html' else 'text/plain')+'; charset=utf-8');self.send_header('Content-Length',str(file.stat().st_size));self.send_header('Content-Security-Policy',"sandbox");self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(file.read_bytes());return
                file=checked_path(static,'index.html' if route=='/' else route.lstrip('/'))
                if not file.is_file():return self.send({'error':'Not found.'},404)
                content=file.read_bytes()
                if file.name=='index.html':content=content.replace(b'__TOKEN__',token.encode())
                return self.send(content,kind=mimetypes.guess_type(file.name)[0] or 'application/octet-stream')
            except (ValueError,OSError) as error:self.send({'error':str(error)},400)
        def do_POST(self):
            origin=self.headers.get('Origin')
            if not self.trusted() or self.headers.get('X-Workbench-Token')!=token or origin and origin not in (f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}'):
                return self.send({'error':'Local authenticated request required.'},403)
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=2*1024*1024:raise ValueError('Invalid request size.')
                data=json.loads(self.rfile.read(length))
                if not isinstance(data,dict):raise ValueError('Expected an object.')
                with library.lock:
                    route=urlparse(self.path).path
                    if route=='/api/library/register':return self.send(library.register(data.get('project'),data.get('config')))
                    if route=='/api/library/create':return self.send(library.create(data['project'],data['name'],data['filename'],data.get('template','blank')))
                    app=library.get(parse_qs(urlparse(self.path).query).get('workflow',[None])[0])
                    if route=='/api/render':return self.send({'yaml':render_yaml(data['workflow'],app.config()['yaml'])})
                    if route=='/api/validate':
                        value=parse_yaml(data['yaml']) if 'yaml' in data else data['workflow'];assert_valid(value)
                        record=app.config();text=data.get('yaml') or render_yaml(value,record['yaml'])
                        return self.send(dict(workflow=value,yaml=text,diff=''.join(difflib.unified_diff(record['yaml'].splitlines(True),text.splitlines(True),fromfile='Saved',tofile='Draft'))))
                    if route=='/api/save':return self.send(app.save(data.get('yaml',data.get('workflow')),data['revision']))
                    if route=='/api/new-run':return self.send(app.fresh())
                    if route=='/api/detect':return self.send(app.detect())
                    if route=='/api/inputs':app.engine.set_inputs(data['inputs'])
                    elif route=='/api/preview':return self.send(app.engine.preview(data.get('step'),data.get('profile','all')))
                    elif route=='/api/run':
                        if app.store.read()['workflow']!=app.engine.workflow:raise ValueError('Workflow changed on disk. Reload and start a new run.')
                        library.ensure_can_run(app)
                        app.engine.start(data.get('profile','all'),data.get('step'),data.get('rerun',False))
                    elif route=='/api/record':
                        library.ensure_can_run(app);app.engine.record(data['step'],data['note'])
                    elif route=='/api/stop':app.engine.stop(data.get('step'))
                    elif route=='/api/pause':app.engine.pause(data.get('paused',True))
                    else:raise ValueError('Unknown action.')
                return self.send({'ok':True})
            except (ValueError,KeyError,OSError,TypeError,subprocess.SubprocessError) as error:return self.send({'error':str(error)},400)
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler);server.token=token;server.library=library;return server

def serve(config,port=3103,no_open=False,output='.workbench',resume=None):
    library=Library(config,output,resume);server=make_server(library,port)
    url=f'http://127.0.0.1:{server.server_port}'+(f'?workflow={library.identity(library.primary)}' if resume else '')
    print(f'Release Workbench: {url}\nInitial project: {library.root}\nWorkflow library: {library.registry}',flush=True)
    if not no_open:webbrowser.open(url)
    try:server.serve_forever()
    except KeyboardInterrupt:
        library.shutdown()
    finally:server.server_close()
