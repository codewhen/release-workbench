import {readFile,readdir,writeFile} from 'node:fs/promises';
const root=new URL('../',import.meta.url),lock=JSON.parse(await readFile(new URL('package-lock.json',root),'utf8'));
const sections=['Third-party licenses for bundled runtime dependencies.\n'];
for(const [name,info] of Object.entries(lock.packages).sort()){
 if(!name||info.dev||!name.startsWith('node_modules/'))continue;
 const directory=new URL(name+'/',root),pkg=JSON.parse(await readFile(new URL('package.json',directory),'utf8'));
 const files=(await readdir(directory)).filter(n=>/^licen[sc]e(?:\.|$|-)/i.test(n));
 sections.push(`\n=== ${pkg.name} ${pkg.version} (${pkg.license??info.license??'see project'}) ===\n`);
 for(const file of files)sections.push(await readFile(new URL(file,directory),'utf8'));
}
await writeFile(new URL('../../src/release_workbench/THIRD_PARTY_NOTICES.txt',import.meta.url),sections.join('\n'));
