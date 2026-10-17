import { cpSync, mkdirSync, rmSync } from 'node:fs';
import path from 'node:path';
const root = path.resolve(import.meta.dirname, '../..');
const target = path.join(root, 'src/release_workbench/documentation');
const pagesOnly = process.argv.includes('--pages-only');
if (!pagesOnly) {
  rmSync(target, { recursive: true, force: true });
  mkdirSync(target, { recursive: true });
  cpSync(path.join(root, 'docs-site/.vitepress/dist'), target, { recursive: true });
}
// VitePress does not publish non-Markdown files from srcDir automatically.
for (const destination of [...(pagesOnly ? [] : [target]), path.join(root, 'docs-site/.vitepress/dist')]) {
  mkdirSync(path.join(destination, 'examples'), { recursive: true });
  cpSync(path.join(root, 'docs/examples'), path.join(destination, 'examples'), { recursive: true, filter: source => !source.includes('__pycache__') && !source.endsWith('.pyc') });
}
console.log('Bundled offline manual without modifying application assets.');
