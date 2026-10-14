"""Local project/workflow catalog. Opening a workflow never starts its commands."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import threading
from .config import workspace_root,Store,checked_path,render_yaml
from .engine import fingerprint

class Library:
    def __init__(self,config,output='.workbench',resume=None,initial_app=None):
        self.primary=Path(config).resolve()
        self.root=self.primary.parent
        if not self.root.is_dir():raise ValueError('The initial project folder must exist.')
        self.output=output
        self.lock=threading.RLock()
        self.registry=checked_path(self.root,output)/'library.json'
        self.projects={str(self.root)}
        self.files={str(self.primary)} if self.primary.is_file() else set()
        self.apps={}
        if self.registry.is_file():
            data=json.loads(self.registry.read_text())
            if data.get('version')!=1:raise ValueError('Unsupported workflow library version.')
            self.projects.update(data.get('projects',[]))
            self.files.update(data.get('files',[]))
        if initial_app:self.apps[self.identity(self.primary)]=initial_app
        if resume:self.get(self.identity(self.primary),resume)

    @staticmethod
    def identity(path):return hashlib.sha256(str(Path(path).resolve()).encode()).hexdigest()[:20]

    def persist(self):
        self.registry.parent.mkdir(parents=True,exist_ok=True)
        with tempfile.NamedTemporaryFile(mode='w',dir=self.registry.parent,delete=False,encoding='utf-8') as stream:
            json.dump(dict(version=1,projects=sorted(self.projects),files=sorted(self.files)),stream,indent=2)
            name=stream.name
        try:os.replace(name,self.registry)
        finally:Path(name).unlink(missing_ok=True)

    def paths(self):
        paths={Path(p) for p in self.files}
        for project in self.projects:
            root=Path(project)
            if root.is_dir():
                for pattern in ('release-workbench*.yaml','release-workbench*.yml','workflow-workbench*.yaml','workflow-workbench*.yml'):
                    # Explicitly registered folders grant access; discovery never follows
                    # a configuration symlink to a different, unregistered folder.
                    paths.update(p for p in [*root.glob(pattern),*root.glob('workflows/**/'+pattern)] if p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(root.resolve()))
        return {self.identity(p):p.resolve() for p in paths}

    def register(self,project=None,config=None):
        if bool(project)==bool(config):raise ValueError('Supply a project folder or an existing YAML file.')
        raw=Path(project or config).expanduser()
        if not raw.is_absolute():raise ValueError('Use an absolute local path.')
        path=raw.resolve()
        if config:
            if not path.is_file() or path.suffix not in ('.yaml','.yml'):raise ValueError('Select an existing YAML workflow file.')
            Store(path).read()
            self.files.add(str(path));self.projects.add(str(path.parent))
        else:
            if not path.is_dir():raise ValueError('Project folder not found.')
            self.projects.add(str(path))
        self.persist()
        return self.catalog()

    def create(self,project_id,name,filename,template='blank'):
        from .templates import make_template,starter_documents
        roots={self.identity(p):Path(p) for p in self.projects}
        if project_id not in roots:raise ValueError('Select a registered project.')
        root=roots[project_id]
        if not root.is_dir():raise ValueError('Project folder is unavailable.')
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*\.ya?ml',filename):raise ValueError('Use a YAML filename without folders, such as release-workbench-tests.yaml.')
        if not isinstance(name,str) or not name.strip() or len(name)>200:raise ValueError('Enter a workflow name of 1–200 characters.')
        value=make_template(name.strip(),template)
        if (root/filename).exists() or (root/filename).is_symlink():raise ValueError('A file already exists with this name. Choose another filename.')
        file=checked_path(root,filename)
        documents=starter_documents(filename,value,template);created=[]
        try:
            for name,document in documents.items():
                path=checked_path(root,name)
                with path.open('x',encoding='utf-8') as stream:stream.write(render_yaml(document))
                created.append(path)
        except Exception:
            for path in created:path.unlink()
            raise
        self.files.add(str(file));self.persist()
        return dict(id=self.identity(file),path=str(file))

    def get(self,key=None,resume=None):
        from .server import App
        key=key or self.identity(self.primary)
        paths=self.paths()
        if key not in paths:raise ValueError('Workflow not found in the registered library.')
        if key not in self.apps:self.apps[key]=App(paths[key],self.output,resume)
        return self.apps[key]

    def ensure_can_run(self,selected):
        for app in self.apps.values():
            if app is not selected and app.engine.busy():raise ValueError('Another workflow is running or paused: '+app.engine.workflow['name']+'. Finish or stop it before starting another workflow.')

    def catalog(self):
        rows=[]
        for key,path in sorted(self.paths().items(),key=lambda item:str(item[1]).casefold()):
            item=dict(id=key,path=str(path),project_id=self.identity(path.parent),project=str(path.parent),filename=path.name,name=path.stem,description='',steps=0,error='',busy=False,latest=None)
            try:
                value=Store(path).read()['workflow'];project=workspace_root(path.parent,value);item.update(project=str(project),project_id=self.identity(project));item.update(name=value['name'],description=value.get('description',''),steps=len(value['steps']))
                current=self.apps.get(key)
                summaries=[]
                if current:
                    snapshot=current.engine.snapshot();item['busy']=snapshot['busy'];summaries=[snapshot]
                else:
                    output=checked_path(project,self.output)
                    for report in sorted(output.glob('*/summary.json'),reverse=True):
                        try:
                            saved=json.loads(report.read_text())
                            if saved.get('signature',{}).get('workflow')==fingerprint(value):summaries=[saved];break
                        except (ValueError,OSError):continue
                if summaries:
                    saved=summaries[0];statuses=[s['status'] for s in saved['steps'].values()]
                    outcome='Running' if any(s in ('running','stopping') for s in statuses) else 'Paused' if saved.get('paused') else 'Failed' if 'failed' in statuses else 'Cancelled' if 'cancelled' in statuses else 'Complete' if statuses and all(s in ('passed','recorded','skipped') for s in statuses) else 'Awaiting evidence' if 'manual' in statuses else 'Pending'
                    item['latest']=dict(run_id=saved['run_id'],status=outcome,passed=sum(s in ('passed','recorded','skipped') for s in statuses),total=len(statuses),started=saved['started'])
            except (ValueError,OSError,KeyError,TypeError) as error:item['error']=str(error)
            rows.append(item)
        return dict(workflows=rows,projects=[dict(id=self.identity(p),path=p,name=Path(p).name or p,available=Path(p).is_dir()) for p in sorted(self.projects)],primary=self.identity(self.primary))

    def shutdown(self):
        import time
        for app in self.apps.values():app.engine.stop()
        while any(app.engine.busy() for app in self.apps.values()):time.sleep(.1)
