import json
"""Portable, accessible HTML evidence; no JavaScript or external dependencies."""
import html
import os
from collections import Counter
from pathlib import Path
from urllib.parse import quote

STYLE='''
:root{font:16px/1.6 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#182a30;background:#f5f8f9}*{box-sizing:border-box}body{margin:0}main{max-width:1000px;margin:auto;padding:32px 24px 48px}h1{font-size:28px;line-height:1.25;letter-spacing:-.025em;margin:0 0 12px;overflow-wrap:anywhere}h2{font-size:22px;line-height:1.3;margin:32px 0 12px}h3{font-size:19px;line-height:1.4;margin:0 0 8px;overflow-wrap:anywhere}h4{font-size:15px;margin:20px 0 6px}p{max-width:75ch;margin:8px 0}.metadata,.muted{font-size:14px;color:#4a6068;overflow-wrap:anywhere}.outcomes{display:flex;flex-wrap:wrap;gap:12px 24px;margin:24px 0}.outcomes>div{display:flex;gap:8px}.outcomes dt{text-transform:capitalize}.outcomes dd{margin:0;font-weight:650;font-variant-numeric:tabular-nums}a{color:#165c73;text-underline-offset:4px;overflow-wrap:anywhere}a:focus-visible,summary:focus-visible{outline:3px solid #165c73;outline-offset:3px}.evidence-link,nav a,.top-link{display:inline-flex;align-items:center;min-height:44px;padding:8px 0}details{padding:12px 0;border-block:1px solid #cbd7db}summary{cursor:pointer;min-height:44px;align-content:center;font-weight:600}nav ul{margin:0;padding:0;list-style:none;max-height:300px;overflow:auto}nav a{font-size:14px}section{border-top:1px solid #cbd7db;padding:24px 0;scroll-margin-top:20px}.step-status{display:flex;gap:12px;align-items:center;flex-wrap:wrap;font-size:14px;font-variant-numeric:tabular-nums}.badge{padding:3px 8px;border-radius:4px;background:#e8ecee;color:#52616a}.passed,.recorded{color:#146040;background:#eaf5ee}.failed,.blocked{color:#a12424;background:#fff0ef}.running,.stopping{color:#165c73;background:#e8f0f3}.attempts{padding-left:20px}pre{font:13px/1.6 ui-monospace,SFMono-Regular,Consolas,monospace;white-space:pre-wrap;overflow-wrap:anywhere;overflow:auto;padding:12px;background:#edf3f5;border-radius:6px}.checksum{font:12px/1.6 ui-monospace,SFMono-Regular,Consolas,monospace;color:#4a6068;overflow-wrap:anywhere}footer{border-top:1px solid #cbd7db;padding-top:16px;color:#4a6068;font-size:13px}::selection{background:#b7dbe7;color:#182a30}*{scrollbar-color:#9bb2bc #edf3f5}@media(max-width:600px){main{padding:24px 20px}h1{font-size:24px}.outcomes{gap:8px 16px}section{padding:20px 0}}@media print{:root{background:white}main{max-width:none;padding:0}details,.top-link{display:none}section{break-inside:avoid}}
'''

def render_report(data,root,directory):
    escape=html.escape;sections=[];navigation=[]
    for key,value in data['steps'].items():
        name=escape(value.get('name',key));status=escape(value['status']);anchor='step-'+key
        # Engine state keeps names in the workflow, supplied below by save().
        navigation.append(f'<li><a href="#{escape(anchor)}">{name}</a></li>')
        notes=(f'<h4>Error</h4><pre>{escape(value["error"])}</pre>' if value.get('error') else '')+(f'<h4>Operator evidence</h4><pre>{escape(value["note"])}</pre>' if value.get('note') else '')
        attempts=[]
        for index,attempt in enumerate(value.get('attempts',[]),1):
            files=[]
            for report in attempt.get('reports',[]):
                relative=Path(os.path.relpath(Path(root)/report['path'],directory)).as_posix()
                files.append(f'<li><a class="evidence-link" href="{escape(quote(relative,safe='/'))}">{escape(report["path"])}</a><div class="checksum">SHA256 {escape(report["sha256"])}</div></li>')
            reports='<ul>'+''.join(files)+'</ul>' if files else ''
            attempts.append(f'<li><a class="evidence-link" href="{escape(quote(attempt['log'],safe='/'))}">Attempt {index}: {escape(attempt["status"])} · {attempt.get("seconds",0):g}s</a>{reports}</li>')
        links='<h4>Attempts and files</h4><ul class="attempts">'+''.join(attempts)+'</ul>' if attempts else '<p class="muted">No attempt recorded.</p>'
        sections.append(f'<section id="{escape(anchor)}"><h3>{name}</h3><p class="step-status"><span class="badge {status}">{status}</span><span>{value.get("seconds",0):g}s elapsed</span></p>{notes}{links}</section>')
    if data.get('executions'):
        entries=[]
        for path,execution in data['executions'].items():
            entries.append('<li><strong>'+escape(path)+'</strong> · '+escape(execution.get('status','pending'))+'<pre>'+escape(json.dumps(execution,indent=2))+'</pre></li>')
        sections.append('<section><h2>Scoped executions and iterations</h2><p>Handled failures remain evidence; the enclosing scope determines continuation.</p><ul>'+''.join(entries)+'</ul></section>')
    counts=Counter(value['status'] for value in data['steps'].values())
    outcomes=''.join(f'<div><dt>{escape(status)}</dt><dd>{count}</dd></div>' for status,count in sorted(counts.items()))
    return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+escape(data['name'])+' · Workflow report</title><style>'+STYLE+'</style></head><body><main id="top"><header><h1>'+escape(data['name'])+'</h1><p class="metadata">Run '+escape(data['run_id'])+' · '+escape(data['platform'])+'</p><p>Results apply to the recorded source, workflow and selection. Pending, disabled and blocked work is not passing evidence. Manual records are operator attestations.</p><a class="evidence-link" href="summary.json">Open JSON evidence</a><dl class="outcomes" aria-label="Recorded step outcomes">'+outcomes+'</dl></header><details><summary>Jump to a step</summary><nav aria-label="Step navigation"><ul>'+''.join(navigation)+'</ul></nav></details><h2>Step results</h2>'+''.join(sections)+'<footer>Saved evidence · Workflow Workbench<a class="top-link" href="#top">Back to top</a></footer></main></body></html>'
