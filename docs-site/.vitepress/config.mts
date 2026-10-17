import { defineConfig } from 'vitepress';
import fs from 'node:fs';
import path from 'node:path';
const source = path.resolve(import.meta.dirname, '../../docs');
function pages(directory: string) {
  return fs.readdirSync(path.join(source, directory)).filter(name => name.endsWith('.md') && name !== 'index.md')
    .map(name => {
      const file = fs.readFileSync(path.join(source, directory, name), 'utf8');
      return { text: file.match(/^# (.+)$/m)?.[1] ?? name, link: '/' + directory + '/' + name.replace(/\.md$/, '') };
    });
}
const cardGroups = [
  ['Workflow markers', ['start', 'finish', 'return']],
  ['Control flow', ['if', 'loop', 'break', 'continue', 'parallel', 'join', 'try']],
  ['Values', ['variable', 'calculate']],
  ['External operations', ['python', 'bash', 'script', 'program']],
  ['Files and HTTP', ['check_path', 'read_file', 'write_file', 'http']],
  ['Interventions', ['wait', 'poll', 'manual']],
  ['Functions', ['call', 'workspace']],
  ['Layout', ['area', 'collapsible', 'annotation']],
] as const;
const cardPages = pages('user/cards');
const cardSidebar = cardGroups.map(([text, slugs]) => ({ text, collapsed: true, items: slugs.map(slug => cardPages.find(page => page.link.endsWith('/' + slug))!) }));
export default defineConfig({
  srcDir: '../docs',
  vite: { resolve: { alias: { vue: path.resolve(import.meta.dirname, '../node_modules/vue') } } },
  title: 'Workbench',
  description: 'Learn to build, run and inspect local automation flowcharts.',
  lang: 'en-US',
  cleanUrls: false,
  lastUpdated: true,
  ignoreDeadLinks: false,
  srcExclude: ['reviews/**', 'acceptance.md', 'examples/**'],
  markdown: {
    image: { lazyLoading: true },
    config(md) {
      md.core.ruler.after('inline', 'workbench-downloads', state => {
        for (const token of state.tokens) for (const child of token.children || []) {
          if (child.type === 'link_open' && child.attrGet('href')?.endsWith('.py')) child.attrSet('download', '');
        }
      });
    },
  },
  themeConfig: {
    logo: undefined,
    siteTitle: 'Workbench manual',
    nav: [
      { text: 'User guide', link: '/user/introduction' },
      { text: 'Card reference', link: '/user/cards/' },
      { text: 'Developer guide', link: '/developer/' },
      { text: 'Source', link: 'https://github.com/codewhen/release-workbench' },
    ],
    sidebar: [
      { text: 'Learn Workbench', items: [
        ['Introduction', 'introduction'], ['Install and create a project', 'installation'],
        ['Your first workflow', 'first-workflow'], ['Home and projects', 'projects'],
        ['Edit flowcharts', 'editing'], ['Connections and values', 'values'],
        ['Run and inspect', 'running'], ['Settings and resources', 'settings'],
        ['Storage and backups', 'storage'], ['CLI reference', 'cli'],
        ['Troubleshooting', 'troubleshooting'], ['Glossary', 'glossary'],
      ].map(([text, slug]) => ({ text, link: '/user/' + slug })) },
      { text: 'Understand control flow', collapsed: false, items: ['completion','functions','variables','loops','parallel','recovery','http-io'].map(slug => pages('user/tutorials').find(page => page.link.endsWith('/' + slug))!) },
      { text: 'Card reference', collapsed: true, link: '/user/cards/', items: cardSidebar },
      { text: 'Starter walkthroughs', collapsed: true, items: pages('user/starters') },
      { text: 'For contributors', collapsed: true, link: '/developer/', items: pages('developer') },
    ],
    outline: { level: [2, 3], label: 'On this page' },
    search: { provider: 'local' },
    editLink: { pattern: 'https://github.com/codewhen/release-workbench/edit/codex/typed-flowcharts-preview/docs/:path' },
    footer: { message: 'Local automation. Free and open source.', copyright: 'MIT licensed · CodeWhen' },
  },
});
