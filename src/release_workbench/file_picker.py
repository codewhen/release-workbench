"""Native local file selection. No upload, copy or command execution on import."""
import os
from pathlib import Path
import shutil
import subprocess
import sys

def choose_workflow(root):
    if sys.platform=='darwin':
        script='''on run argv
    try
        activate
        return POSIX path of (choose file with prompt "Open a Workflow Workbench YAML file" of type {"yaml", "yml"} default location (POSIX file (item 1 of argv)))
    on error number -128
        return ""
    end try
end run'''
        command=['osascript','-e',script,str(root)]
    elif sys.platform=='win32':
        script='''[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding
Add-Type -AssemblyName System.Windows.Forms
$d = New-Object System.Windows.Forms.OpenFileDialog
$d.Title = 'Open a Workflow Workbench YAML file'
$d.Filter = 'YAML workflows (*.yaml;*.yml)|*.yaml;*.yml'
$d.InitialDirectory = $env:WORKBENCH_PICKER_ROOT
try { if ($d.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { [Console]::Write($d.FileName) } } finally { $d.Dispose() }'''
        command=['powershell','-NoProfile','-STA','-Command',script]
    elif not os.environ.get('DISPLAY') and not os.environ.get('WAYLAND_DISPLAY'):
        raise ValueError('No desktop session is available. Use Add project or file to enter the YAML path.')
    elif shutil.which('zenity'):
        command=['zenity','--file-selection','--title=Open a workflow YAML file','--file-filter=YAML workflows | *.yaml *.yml','--filename='+str(root)+os.sep]
    elif shutil.which('kdialog'):
        command=['kdialog','--getopenfilename',str(root),'*.yaml *.yml|YAML workflows','--title','Open a workflow YAML file']
    else:raise ValueError('Native file picker is unavailable. Use Add project or file and enter the YAML path. On Linux, install zenity or kdialog to enable the picker.')
    try:
        result=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',timeout=180,env={**os.environ,'WORKBENCH_PICKER_ROOT':str(root)})
    except subprocess.TimeoutExpired:raise ValueError('File selection timed out. Click Open YAML file to try again.') from None
    except OSError:raise ValueError('Cannot open the native file picker. Use Add project or file to enter a YAML path.') from None
    if result.returncode==1 and sys.platform not in ('darwin','win32'):return None
    if result.returncode:raise ValueError('The native file picker could not open. Use Add project or file to enter a YAML path.')
    filename=result.stdout.rstrip('\r\n')
    return Path(filename) if filename else None
