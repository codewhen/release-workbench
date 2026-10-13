"""Shared YAML and schema boundary for the CLI, editor and runner."""
from __future__ import annotations
import copy
import hashlib
import io
import ipaddress
import json
import os
from pathlib import Path
import re
import tempfile
from jsonschema import Draft202012Validator
from ruamel.yaml import YAML

SCHEMA=json.loads(Path(__file__).with_name('schema.json').read_text())
MAX_CONFIG_BYTES=1024*1024

def yaml_codec():
    codec=YAML(typ='rt');codec.version=(1,2);codec.preserve_quotes=True
    codec.indent(mapping=2,sequence=4,offset=2)
    return codec

def parse_yaml(text):
    if len(text.encode())>MAX_CONFIG_BYTES:raise ValueError('Workflow exceeds 1 MiB.')
    from ruamel.yaml.tokens import AliasToken,TagToken
    from ruamel.yaml.error import YAMLError
    try:
        if any(isinstance(token,(AliasToken,TagToken)) for token in yaml_codec().scan(text)):
            raise ValueError('YAML aliases and explicit tags are not supported.')
        value=yaml_codec().load(text)
    except YAMLError as error:raise ValueError('Invalid YAML: '+str(error)) from None
    # Reject custom YAML tags, aliases/cycles and non-JSON configuration values.
    def plain(node,seen):
        if isinstance(node,(dict,list)):
            if id(node) in seen:raise ValueError('YAML aliases and cycles are not supported.')
            seen.add(id(node))
            if getattr(node,'tag',None) and str(node.tag) not in ('None','tag:yaml.org,2002:map','tag:yaml.org,2002:seq'):
                raise ValueError('Custom YAML tags are not supported.')
            return {str(k):plain(v,seen) for k,v in node.items()} if isinstance(node,dict) else [plain(v,seen) for v in node]
        if type(node) not in (str,int,float,bool,type(None)):
            # ruamel quoted string subclasses remain plain strings.
            if isinstance(node,str):return str(node)
            if isinstance(node,int):return int(node)
            if isinstance(node,float):return float(node)
            raise ValueError('Use plain YAML strings, numbers, booleans, arrays and mappings.')
        return node
    return plain(value,set())

def render_yaml(value,original=''):
    codec=yaml_codec()
    previous=codec.load(original) if original.strip() else None
    def merge(old,new):
        if isinstance(old,dict) and isinstance(new,dict):
            for key in list(old):
                if key not in new:del old[key]
            for key,val in new.items():old[key]=merge(old.get(key),val)
            return old
        if isinstance(old,list) and isinstance(new,list):
            keyed={v.get('id'):v for v in old if isinstance(v,dict) and v.get('id')}
            replacement=[merge(keyed.get(v.get('id')) if isinstance(v,dict) and v.get('id') else old[i] if i<len(old) else None,v) for i,v in enumerate(new)]
            old[:]=replacement;return old
        if old==new and isinstance(old,bool)==isinstance(new,bool):return old
        return copy.deepcopy(new)
    result=merge(previous,value);stream=io.StringIO();codec.dump(result,stream);return stream.getvalue()

def validate(workflow):
    errors=[]
    for error in sorted(Draft202012Validator(SCHEMA).iter_errors(workflow),key=lambda e:str(list(e.path))):
        errors.append(f'{".".join(map(str,error.path)) or "workflow"}: {error.message}')
    if errors:return errors
    for field in ('report_paths','source_paths'):
        for value in workflow.get(field,[]):
            if Path(value).is_absolute() or '..' in Path(value).parts:errors.append(f'{field}: paths must stay within the workspace.')
    steps=workflow['steps'];ids=[s['id'] for s in steps];known=set(ids)
    if len(known)!=len(ids):errors.append('Step IDs must be unique.')
    inputs=workflow.get('inputs',{})
    for key,item in inputs.items():
        if 'default' in item:
            try:input_value(key,item['default'],{**item,'required':False})
            except ValueError as error:errors.append('Invalid input default: '+str(error))
        if item['type']=='choice' and not item.get('options'):errors.append(f'Input {key}: choices need options.')
        if item.get('pattern'):
            try:re.compile(item['pattern'])
            except re.error:errors.append(f'Input {key}: invalid regular expression.')
    by_id={s['id']:s for s in steps}
    for s in steps:
        for dep in s.get('needs',[]):
            if dep not in known:errors.append(f'{s["id"]}: unknown prerequisite {dep}.')
        for key in s.get('requires_inputs',[]):
            if key not in inputs:errors.append(f'{s["id"]}: unknown input {key}.')
        if s['kind']=='command' and not s.get('commands') and not s.get('platform_commands'):
            errors.append(f'{s["id"]}: add a command before running.')
        if s['kind']=='manual' and (s.get('commands') or s.get('platform_commands')):errors.append(f'{s["id"]}: manual gates cannot execute commands.')
        if s.get('approval') and s['kind']!='manual':errors.append(f'{s["id"]}: approval must be a manual gate.')
        if s['kind']=='workflow':
            if not s.get('workflow'):errors.append(f'{s["id"]}: select a child workflow YAML file.')
            elif Path(s['workflow']).is_absolute() or '..' in Path(s['workflow']).parts:errors.append(f'{s["id"]}: child workflow must stay within the workspace.')
            if s.get('commands') or s.get('platform_commands'):errors.append(f'{s["id"]}: workflow cards cannot also define commands.')
        elif 'workflow' in s:errors.append(f'{s["id"]}: workflow path belongs on a Run workflow card.')
        if s['kind']=='condition':
            if not s.get('condition'):errors.append(f'{s["id"]}: configure an If condition.')
            if s.get('commands') or s.get('platform_commands'):errors.append(f'{s["id"]}: If cards evaluate data; they cannot run commands.')
        elif 'condition' in s:errors.append(f'{s["id"]}: condition belongs on an If card.')
        when=s.get('when')
        if when and (when['step'] not in s.get('needs',[]) or by_id.get(when['step'],{}).get('kind')!='condition'):errors.append(f'{s["id"]}: branch must directly depend on its If card.')
        if s.get('join')=='any' and not s.get('needs'):errors.append(f'{s["id"]}: branch join needs prerequisites.')
        p=s.get('progress',{})
        if p:
            try:
                regex=re.compile(p['pattern'])
                if p.get('mode','count')=='groups' and not {'done','total'}<=regex.groupindex.keys():errors.append(f'{s["id"]}: progress needs named done and total groups.')
                if p.get('mode','count')=='index' and 'done' not in regex.groupindex:errors.append(f'{s["id"]}: index progress needs named done group.')
                if p.get('mode','count')!='groups' and not p.get('total'):errors.append(f'{s["id"]}: progress parser needs total.')
            except re.error:errors.append(f'{s["id"]}: invalid progress pattern.')
        for out in s.get('outputs',[]):
            if out['input'] not in inputs:errors.append(f'{s["id"]}: output targets unknown input {out["input"]}.')
    def ancestors(key,stack=()):
        if key in stack:raise ValueError('Dependency cycle: '+' → '.join((*stack,key)))
        result=set()
        for dep in by_id.get(key,{}).get('needs',[]):
            result.add(dep);result.update(ancestors(dep,(*stack,key)))
        return result
    try:
        for s in steps:
            deps=ancestors(s['id'])
            if s['kind']=='condition' and s.get('condition'):
                source=s['condition']['source'];parts=source.split('.')
                if parts[0]=='inputs':
                    if len(parts)!=2 or parts[1] not in inputs:errors.append(f'{s["id"]}: unknown condition input.')
                elif parts[0]=='steps':
                    if len(parts)<4 or parts[1] not in deps or parts[2]!='result' or parts[3] not in ('exit_code','stdout','json','decision'):errors.append(f'{s["id"]}: condition source must reference an ancestor result.')
                else:errors.append(f'{s["id"]}: use inputs.NAME or steps.ID.result.FIELD for condition source.')
                if s['condition']['operator']!='is_true' and 'value' not in s['condition']:errors.append(f'{s["id"]}: condition comparison needs a value.')
            if s.get('approval'):
                required={v['id'] for v in steps if v.get('required',True) and not v.get('approval') and v['id']!=s['id']}
                missing=required-deps
                if missing:errors.append(f'{s["id"]}: approval must depend on required steps: {", ".join(sorted(missing))}.')
    except ValueError as error:errors.append(str(error))
    for name,selection in workflow.get('profiles',{}).items():
        if not set(selection)<=known:errors.append(f'Profile {name}: unknown step IDs.')
    return errors

def assert_valid(workflow):
    errors=validate(workflow)
    if errors:raise ValueError('\n'.join(errors))
    return workflow

def checked_path(root,value):
    path=(root/value).resolve()
    if not path.is_relative_to(root.resolve()):raise ValueError('Paths must stay beneath the workspace: '+str(value))
    return path

def input_value(key,value,spec):
    if value in ('',None):
        if spec.get('required'):raise ValueError(f'Enter {spec["label"]}.')
        return ''
    kind=spec['type']
    if kind in ('integer','pid'):
        try:
            if isinstance(value,bool) or str(value).strip()!=str(int(value)):raise ValueError()
            value=int(value)
        except (ValueError,TypeError):raise ValueError(f'{key}: use a whole number.') from None
        if kind=='pid' and value<=0:raise ValueError(f'{key}: PID must be positive.')
        if value<spec.get('minimum',value) or value>spec.get('maximum',value):raise ValueError(f'{key}: outside configured range.')
    elif kind=='boolean':
        if not isinstance(value,bool):raise ValueError(f'{key}: use true or false.')
    else:
        value=str(value)
        if len(value)>4096 or '\0' in value:raise ValueError(f'{key}: invalid value.')
        if kind=='choice' and value not in spec['options']:raise ValueError(f'{key}: select a configured option.')
        if kind=='usb_serial' and (value.startswith('-') or any(c.isspace() or ord(c)<32 for c in value)):raise ValueError(f'{key}: use a USB serial, not an option.')
        if kind=='ipv4':
            try:ip=ipaddress.IPv4Address(value)
            except ipaddress.AddressValueError:raise ValueError(f'{key}: enter an IPv4 address.') from None
            if ip.is_loopback or ip.is_unspecified or ip.is_multicast:raise ValueError(f'{key}: use a reachable LAN IPv4.')
        if spec.get('pattern') and not re.fullmatch(spec['pattern'],value):raise ValueError(f'{key}: does not match the configured pattern.')
    return value

class Store:
    def __init__(self,path):self.path=Path(path).resolve();self.root=self.path.parent
    def read(self):
        text=self.path.read_text();return dict(workflow=assert_valid(parse_yaml(text)),yaml=text,revision=hashlib.sha256(text.encode()).hexdigest())
    def save(self,value,revision):
        old=self.read()
        if old['revision']!=revision:raise ValueError('Workflow changed on disk. Reload before saving your draft.')
        if isinstance(value,str):text=value;workflow=parse_yaml(value)
        else:workflow=value;text=render_yaml(value,old['yaml'])
        assert_valid(workflow)
        with tempfile.NamedTemporaryFile(mode='w',dir=self.root,delete=False,encoding='utf-8') as stream:
            temp=Path(stream.name);stream.write(text);stream.flush();os.fsync(stream.fileno())
        try:os.replace(temp,self.path)
        finally:temp.unlink(missing_ok=True)
        return self.read()
