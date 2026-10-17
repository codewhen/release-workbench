/** Capture only synthetic fixture workflows, never the user's running server. */
import { createRequire } from 'node:module';
import { spawn } from 'node:child_process';
import { readFileSync, mkdirSync } from 'node:fs';
import path from 'node:path';
const root = path.resolve(import.meta.dirname, '../..');
const require = createRequire(path.join(root, 'frontend/package.json'));
const { chromium } = require('@playwright/test');
const base = 'http://127.0.0.1:3117';
const output = path.join(root, 'docs/assets/screenshots');
mkdirSync(output, { recursive: true });
const server = spawn(process.env.WORKBENCH_PYTHON || 'python', ['scripts/preview_docs.py'], { cwd: path.join(root, 'docs-site'), stdio: ['ignore', 'pipe', 'pipe'] });
let logs = '';
server.stdout.on('data', data => logs += data); server.stderr.on('data', data => logs += data);
async function ready() {
  for (let i = 0; i < 100; i++) {
    if (server.exitCode !== null) throw Error(logs);
    try { const response = await fetch(base + '/api/library'); if (response.ok) return await response.json(); } catch {}
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  throw Error('Documentation fixture server did not start: ' + logs);
}
let browser;
try {
  const library = await ready();
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1, reducedMotion: 'reduce' });
  await page.addStyleTag?.({content: ''}).catch(() => {});
  const capture = async (name, locator) => {
    await page.waitForTimeout(200);
    await (locator ?? page).screenshot({ path: path.join(output, name + '.png'), animations: 'disabled' });
    console.log('Captured ' + name);
  };
  const entries = new Map(library.entries.filter(entry => entry.folder !== "Starter").map(entry => [path.basename(entry.path), entry]));
  async function open(file, graph = 'main', card) {
    const entry = entries.get(file); if (!entry) throw Error('Missing fixture ' + file);
    await page.goto(base + '/?workflow=' + entry.id);
    await page.getByRole('button', { name: 'Edit', exact: true }).click();
    if (graph !== 'main') {
      const config = await (await fetch(base + '/api/config?workflow=' + entry.id)).json();
      const [id, fn] = Object.entries(config.workflow.functions).find(([, fn]) => fn.graph === graph);
      await page.getByRole('button', { name: 'Workflow settings', exact: true }).click();
      await page.getByRole('button', { name: (fn.name || id) + ' → ' + fn.returns, exact: true }).click();
    }
    if (card) {
      await page.getByRole('button', { name: 'List', exact: true }).click();
      await page.locator(`[data-card-id="${card}"]`).click();
      await page.getByRole('button', { name: 'Flowchart', exact: true }).click();
    }
    if (page.viewportSize().width >= 1000) await page.locator('.react-flow').waitFor();
    await page.locator('aside').evaluate(element => element.scrollTop = 0);
  }
  await page.goto(base + '/');
  await page.getByRole('heading', {name:'Your workflows', exact:true}).waitFor();
  await capture('home');
  await page.getByRole('button', {name:'Add project or file', exact:true}).click();
  await capture('add-project');
  const locations = JSON.parse(readFileSync(path.join(root, 'docs-site/card-examples.json'), 'utf8'));
  for (const [kind, location] of Object.entries(locations)) {
    await open(location.example, location.graph, location.card);
    await capture('card-' + kind);
  }
  for (const kind of ['area','collapsible','annotation']) {
    await open(kind + '.yaml');
    await page.locator('.layout-area').click({position:{x:30,y:20}});
    await capture('card-' + kind);
  }
  for (const key of ['blank','python','while','parallel','manual','recovery','poll']) {
    await open('starter-' + key + '.yaml');
    await capture('starter-' + key);
  }
  // Dedicated journey captures, not styled mockups.
  await open('start.yaml'); await capture('project-create');
  await open('python.yaml','main','operation'); await capture('wiring');
  await open('finish.yaml','main','finish'); await capture('returning-values');
  await open('return.yaml','greeting','return'); await capture('function-view');
  await open('loop.yaml');
  await page.getByRole('button', {name:'Workflow settings', exact:true}).click();
  await capture('global-variables');
  await open('loop.yaml','condition','compare'); await capture('compare-source');
  await open('python.yaml');
  await page.getByRole('button', {name:'Run', exact:true}).click();
  await page.getByRole('button', {name:'Run all', exact:true}).click();
  await page.locator('.toolbar .status.passed').waitFor();
  await page.getByRole('button', {name:'List', exact:true}).click();
  await page.locator('[data-card-id="operation"]').click();
  await capture('run-inspection');
  await open('manual.yaml');
  await page.getByRole('button', {name:'Run', exact:true}).click();
  await page.getByRole('button', {name:'Run all', exact:true}).click();
  await page.getByLabel('Evidence notes').waitFor();
  await capture('manual-prompt');
  await page.getByLabel('Evidence notes').fill('Checked the synthetic example.');
  await page.getByRole('combobox', {name:'Return Boolean', exact:true}).click();
  await page.getByRole('option', {name:'True', exact:true}).click();
  await page.getByRole('button', {name:'Return result and continue'}).click();
  await page.locator('.toolbar .status.passed').waitFor();
  await open('python.yaml');
  await page.getByRole('button', {name:'Add card', exact:true}).first().click();
  await page.getByRole('menuitem', {name:'Wait', exact:true}).click();
  await page.getByRole('button', {name:'Validate & review', exact:true}).click();
  await page.getByText(/no execution connection|connect exactly one|unreachable/i).first().waitFor();
  await capture('validation');
  await page.setViewportSize({width:390,height:844});
  await open('call.yaml');
  await page.getByRole('button', {name:'List', exact:true}).click();
  await page.evaluate(() => window.scrollTo(0, 0));
  await capture('mobile-list');
  await page.locator('[data-card-id="operation"]').click();
  await capture('mobile-details', page.locator('aside'));
  console.log('Screenshot capture complete. Review desktop and mobile output before accepting updates.');
} finally {
  await browser?.close();
  server.kill('SIGINT');
  await new Promise(resolve => { if (server.exitCode !== null) resolve(); else { server.once('exit', resolve); setTimeout(() => { server.kill('SIGKILL'); resolve(); }, 5000).unref(); } });
}
