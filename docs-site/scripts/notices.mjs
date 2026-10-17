// Retain license texts for the documentation toolchain and bundled theme/search dependencies.
import { readFileSync, readdirSync, existsSync, writeFileSync } from 'node:fs';
import path from 'node:path';
const directory=path.resolve(import.meta.dirname,'..');
const lock=JSON.parse(readFileSync(path.join(directory,'package-lock.json'),'utf8'));
const sections=['Third-party documentation notices. Includes build-tool dependencies for completeness.\n'];
for(const [name,info] of Object.entries(lock.packages).sort()) {
  if(!name || !name.startsWith('node_modules/'))continue;
  const folder=path.join(directory,name);if(!existsSync(folder))continue;
  const metadata=JSON.parse(readFileSync(path.join(folder,'package.json'),'utf8'));
  sections.push(`\n=== ${metadata.name} ${metadata.version} (${metadata.license || info.license || 'see project'}) ===\n`);
  for(const file of readdirSync(folder).filter(file=>/^licen[sc]e(?:\.|$|-)/i.test(file))) {
    const source=path.join(folder,file);
    try {sections.push(readFileSync(source,'utf8'));}catch{}
  }
}
writeFileSync(path.resolve(directory,'../src/release_workbench/THIRD_PARTY_DOCUMENTATION_NOTICES.txt'),sections.join('\n'));
