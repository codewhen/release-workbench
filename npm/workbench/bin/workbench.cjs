#!/usr/bin/env node
// Thin runtime bootstrap. The Python package owns all CLI and execution behavior.
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const crypto = require('node:crypto');
const { spawnSync, spawn } = require('node:child_process');
function main() {
  const runtime = path.resolve(__dirname, '../runtime');
  const manifest = JSON.parse(fs.readFileSync(path.join(runtime, 'manifest.json'), 'utf8'));
  if (path.basename(manifest.wheel) !== manifest.wheel) throw Error('Invalid bundled wheel path.');
  const wheel = path.join(runtime, manifest.wheel);
  if (crypto.createHash('sha256').update(fs.readFileSync(wheel)).digest('hex') !== manifest.sha256)
    throw Error('Bundled Workbench wheel checksum does not match. Reinstall the npm package.');
  const cache = path.join(os.homedir(), '.cache', 'codewhen-workbench', manifest.sha256);
  const python = path.join(cache, process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
  if (!fs.existsSync(path.join(cache, '.ready'))) {
    const candidates = process.env.WORKBENCH_PYTHON ? [[process.env.WORKBENCH_PYTHON]] :
      process.platform === 'win32' ? [['py', '-3'], ['python'], ['python3']] : [['python3'], ['python']];
    const interpreter = candidates.find(([executable, ...args]) => spawnSync(executable,
      [...args, '-c', 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'], { stdio: 'ignore' }).status === 0);
    if (!interpreter) throw Error('Python 3.11+ is required. Install Python or set WORKBENCH_PYTHON to its executable path.');
    // Fail clearly rather than concurrently modifying the same environment.
    fs.mkdirSync(path.dirname(cache), { recursive: true });
    const lock = cache + '.lock';
    let fd;
    try { fd = fs.openSync(lock, 'wx'); } catch { throw Error('Workbench runtime setup is already running. Retry when it finishes. If interrupted, remove: ' + lock); }
    try {
      console.error('Preparing an isolated Workbench Python environment (first launch only)…');
      const execute = (exe, args) => {
        const result = spawnSync(exe, args, { stdio: 'inherit' });
        if (result.error || result.status !== 0) throw Error('Runtime setup failed; check the output above and retry.');
      };
      execute(interpreter[0], [...interpreter.slice(1), '-m', 'venv', cache]);
      execute(python, ['-m', 'pip', 'install', '--disable-pip-version-check', wheel]);
      fs.writeFileSync(path.join(cache, '.ready'), manifest.sha256);
    } finally { fs.closeSync(fd); fs.unlinkSync(lock); }
  }
  const child = spawn(python, ['-m', 'release_workbench.interfaces.cli', ...process.argv.slice(2)], { stdio: 'inherit' });
  for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => child.kill(signal));
  child.on('error', (error) => { console.error(error.message); process.exitCode = 2; });
  child.on('exit', (code, signal) => { process.exitCode = code ?? (signal === 'SIGINT' ? 130 : 1); });
}
try { main(); } catch (error) { console.error(error.message); process.exitCode = 2; }
