const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');
const { spawnSync } = require('node:child_process');
function fixture(t, hash) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'workbench-launcher-'));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  fs.mkdirSync(path.join(root, 'bin'));
  fs.mkdirSync(path.join(root, 'runtime'));
  fs.copyFileSync(path.resolve(__dirname, '../bin/workbench.cjs'), path.join(root, 'bin/workbench.cjs'));
  fs.writeFileSync(path.join(root, 'runtime/test.whl'), 'test fixture');
  fs.writeFileSync(path.join(root, 'runtime/manifest.json'), JSON.stringify({ wheel: 'test.whl', sha256: hash }));
  return root;
}
test('rejects changed wheel before running any installer', (t) => {
  const root = fixture(t, 'incorrect');
  const result = spawnSync(process.execPath, [path.join(root, 'bin/workbench.cjs')], { encoding: 'utf8' });
  assert.equal(result.status, 2);
  assert.match(result.stderr, /checksum does not match/);
});
test('explains missing Python without modifying global installations', (t) => {
  const root = fixture(t, crypto.createHash('sha256').update('test fixture').digest('hex'));
  const result = spawnSync(process.execPath, [path.join(root, 'bin/workbench.cjs')], {
    encoding: 'utf8', env: { ...process.env, WORKBENCH_PYTHON: path.join(root, 'missing-python') },
  });
  assert.equal(result.status, 2);
  assert.match(result.stderr, /Python 3.11\+ is required/);
});
