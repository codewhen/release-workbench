import {resultSources} from './cardSources.js';
import test from 'node:test';import assert from 'node:assert/strict';import {appendStep,createsCycle,insertStep,autoLayout,parseCommand,formatCommand,nextExecutionSelection,clampPanelWidth,appendBranch,appendCard,connectCards,disconnectCards,disconnectNode} from './model.js';
test('ten steps append as a chain with stable IDs',()=>{let w={steps:[]};for(let i=0;i<10;i++)w=appendStep(w,w.steps.at(-1)?.id);assert.equal(w.steps.length,10);assert.deepEqual(w.steps[9].needs,['step-9']);assert.equal(new Set(w.steps.map(s=>s.id)).size,10);});
test('branches reject cycles and edge insertion preserves the join',()=>{let w=appendStep({steps:[]});w=appendStep(w,'step-1');assert(createsCycle(w.steps,'step-2','step-1'));assert(!createsCycle(w.steps,'step-1','step-2'));w=insertStep(w,'step-1','step-2');assert.deepEqual(w.steps.find(s=>s.id==='step-2').needs,['step-3']);});
test('layout separates parallel nodes and keeps dependencies to the right',()=>{const steps=autoLayout([{id:'a'},{id:'b',needs:['a']},{id:'c',needs:['a']}]);assert(steps[1].position.x>steps[0].position.x);assert.notEqual(steps[1].position.y,steps[2].position.y);});
test('command arguments round trip without shell evaluation',()=>{const args=['python','file with spaces.py','print("hello")','C:\\some\\file','${input.serial}'];assert.deepEqual(parseCommand(formatCommand(args)),args);assert.throws(()=>parseCommand('python "unfinished'));assert.deepEqual(parseCommand('echo a && echo b'),['echo','a','&&','echo','b']);});

test("multiline command arguments survive editor formatting",()=>{const args=["python","-c","print(\"first\")\nprint(\"second\")"];assert.deepEqual(parseCommand(formatCommand(args)),args);});

test('selection follows a successful running step but preserves inspection elsewhere',()=>{
 const steps=[{id:'a'},{id:'b',needs:['a']},{id:'inspect'}];
 const before={steps:{a:{status:'running'},b:{status:'queued'},inspect:{status:'passed'}}};
 const after={steps:{a:{status:'passed'},b:{status:'running'},inspect:{status:'passed'}}};
 assert.equal(nextExecutionSelection(steps,'a',before,after),'b');
 assert.equal(nextExecutionSelection(steps,'inspect',before,after),null);
 assert.equal(nextExecutionSelection(steps,'a',before,{steps:{a:{status:'failed'},b:{status:'blocked'}}}),null);
});
test('recorded manual step advances to a ready dependent, not blocked work',()=>{
 const steps=[{id:'gate',kind:'manual'},{id:'next',needs:['gate']}];
 assert.equal(nextExecutionSelection(steps,'gate',{steps:{gate:{status:'manual'}}},{steps:{gate:{status:'recorded'},next:{status:'queued'}}}),'next');
 assert.equal(nextExecutionSelection(steps,'gate',{steps:{gate:{status:'manual'}}},{steps:{gate:{status:'recorded'},next:{status:'blocked'}}}),null);
});

test('panel widths retain readable bounds and leave room for the workflow',()=>{
 assert.equal(clampPanelWidth(450,1200),450);assert.equal(clampPanelWidth(100,1200),280);
 assert.equal(clampPanelWidth(900,1200),720);assert.equal(clampPanelWidth(600,800),468);
 assert.equal(clampPanelWidth(NaN,1200),370);
});

test('If branches preserve their condition and explicit true/false routes',()=>{
 let w=appendStep({steps:[]},null,'condition');const id=w.steps[0].id;
 w=appendBranch(w,id,true);assert.deepEqual(w.steps.at(-1).when,{step:id,equals:true});
 w=appendBranch(w,id,false);assert.deepEqual(w.steps.at(-1).when,{step:id,equals:false});assert.deepEqual(w.steps.at(-1).needs,[id]);
});

test('inserting into a False branch preserves its routing',()=>{
 let w=appendStep({steps:[]},null,'condition');w=appendBranch(w,w.steps[0].id,false);
 const parent=w.steps[0].id,target=w.steps[1].id;w=insertStep(w,parent,target);
 assert.deepEqual(w.steps.at(-1).when,{step:parent,equals:false});assert.equal(w.steps.find(s=>s.id===target).when,undefined);
});

test('new cards stay independent until connected and never overlap',()=>{
 let w={steps:[]};for(let i=0;i<10;i++)w=appendCard(w);
 assert(w.steps.every(s=>s.needs.length===0));assert.equal(new Set(w.steps.map(s=>JSON.stringify(s.position))).size,10);
 w=connectCards(w,'step-1','step-2');w=connectCards(w,'step-1','step-3');
 assert.deepEqual(w.steps[1].needs,['step-1']);assert.deepEqual(w.steps[2].needs,['step-1']);assert.deepEqual(w.steps[3].needs,[]);
 assert.throws(()=>connectCards(w,'step-2','step-1'),/cycle/);
});
test('connecting and disconnecting If outputs controls their route',()=>{
 let w=appendCard({steps:[]},'condition');w=appendCard(w);w=appendCard(w);
 w=connectCards(w,'step-1','step-2','true');w=connectCards(w,'step-1','step-3','false');
 assert.deepEqual(w.steps[2].when,{step:'step-1',equals:false});
 w=disconnectCards(w,'step-1','step-3');assert.deepEqual(w.steps[2].needs,[]);assert.equal(w.steps[2].when,undefined);
});

test('no-code result picker exposes ancestor values without requiring reference text',()=>{
 const workflow={inputs:{folder:{label:'Test folder'}},steps:[{id:'values',kind:'action',name:'Set values',action:{type:'set_values',values:{ready:true}}},{id:'unrelated',kind:'action',name:'Other'},{id:'choose',kind:'condition',needs:['values']}]};
 const choices=resultSources(workflow,workflow.steps[2],{});assert(choices.some(s=>s.value==='steps.values.result.json.ready'));assert(choices.some(s=>s.value==='inputs.folder'));assert(!choices.some(s=>s.value.includes('unrelated')));
});
test('test cards expose their exit code without advertising absent JSON data',()=>{
 const w={steps:[{id:'test',kind:'action',name:'Tests',action:{type:'run_tests'}},{id:'if',kind:'condition',needs:['test']}]};const choices=resultSources(w,w.steps[1],{});
 assert.deepEqual(choices.map(c=>c.value),['steps.test.result.exit_code']);
});

test('disconnecting a node removes only its incoming/outgoing edges and branch routes',()=>{const w={steps:[{id:'a',kind:'condition'},{id:'b',needs:['a'],when:{step:'a',equals:false}},{id:'c',needs:['b','a'],when:{step:'a',equals:true}},{id:'d',needs:['c']}]};const n=disconnectNode(w,'a');assert.deepEqual(n.steps[1].needs,[]);assert.equal(n.steps[1].when,undefined);assert.deepEqual(n.steps[2].needs,['b']);assert.equal(n.steps[2].when,undefined);assert.deepEqual(n.steps[3].needs,['c']);assert.deepEqual(w.steps[1].needs,['a']);});

test('If Entry and Compute ports replace their own connection and preserve the other',()=>{let w={steps:[{id:'a'},{id:'b'},{id:'c'},{id:'d'},{id:'if',kind:'condition',needs:[],condition:{input:{}}}]};w=connectCards(w,'a','if',null,'entry');w=connectCards(w,'b','if',null,'compute');w=connectCards(w,'c','if',null,'entry');assert.deepEqual(w.steps[4].needs,['b','c']);assert.equal(w.steps[4].condition.input.step,'b');w=connectCards(w,'d','if',null,'compute');assert.deepEqual(w.steps[4].needs,['c','d']);assert.equal(w.steps[4].condition.input.step,'d');w=disconnectCards(w,'d','if');assert.deepEqual(w.steps[4].needs,['c']);assert.equal(w.steps[4].condition.input.step,undefined);});
test('moving a Compute source to Entry clears the Compute pin',()=>{let w={steps:[{id:'a'},{id:'if',kind:'condition',needs:['a'],condition:{input:{step:'a'}}}]};w=connectCards(w,'a','if',null,'entry');assert.deepEqual(w.steps[1].needs,['a']);assert.equal(w.steps[1].condition.input.step,undefined);});

test('inserting into a Compute connection preserves the Compute port',()=>{const w={steps:[{id:'a',kind:'command'},{id:'if',kind:'condition',needs:['a'],condition:{input:{step:'a'}}}]};const n=insertStep(w,'a','if');assert.equal(n.steps[1].condition.input.step,n.steps.at(-1).id);});

test('Loop cards are independent bodies with a bounded iteration count and can join a chain',()=>{const w=appendCard({steps:[]},'loop');assert.equal(w.steps[0].kind,'loop');assert.equal(w.steps[0].loop.iterations,3);const n=appendStep(w,w.steps[0].id);assert.deepEqual(n.steps[1].needs,[w.steps[0].id]);});

import {executionFocus,runSummary} from './runModel.js';
test('execution focus stays on an active parallel branch and advances after it finishes',()=>{
 const steps=[{id:'a'},{id:'b'},{id:'c'}];const state={steps:{a:{status:'running'},b:{status:'running'},c:{status:'queued'}}};
 assert.equal(executionFocus(steps,state,'b'),'b');state.steps.b.status='passed';assert.equal(executionFocus(steps,state,'b'),'a');state.steps.a.status='failed';assert.equal(executionFocus(steps,state,'a'),null);
});
test('overall progress respects selected scope and distinguishes failures from passing',()=>{
 const workflow={steps:[{id:'a'},{id:'b'},{id:'c'},{id:'d'}]};
 const state={selection:['a','b','c'],steps:{a:{status:'passed'},b:{status:'failed'},c:{status:'running'},d:{status:'pending'}}};const result=runSummary(workflow,state);
 assert.equal(result.total,3);assert.equal(result.done,2);assert.equal(result.percent,67);assert.equal(result.counts.failed,1);assert.equal(result.partial,true);
});
test('overall progress counts skipped and blocked results while manual gates remain unfinished',()=>{
 const workflow={steps:[{id:'a'},{id:'b'},{id:'c'}]};const result=runSummary(workflow,{steps:{a:{status:'skipped'},b:{status:'blocked'},c:{status:'manual'}}});assert.equal(result.done,2);assert.equal(result.counts.manual,1);assert.equal(result.partial,false);
});


import React from 'react';
import {selectOptions,nextOption,matchingOption} from './selectModel.js';
test('custom select reads mapped and fragment options without losing empty or numeric values',()=>{
 const option=(props,...text)=>React.createElement('option',props,...text);
 const children=[option({value:''},'Choose…'),React.createElement(React.Fragment,null,option({value:0},'Zero'),option({value:'python'},'Python')),option({disabled:true},'Unavailable'),option({},'Default',' label')];
 assert.deepEqual(selectOptions(children),[{value:'',label:'Choose…',disabled:false},{value:'0',label:'Zero',disabled:false},{value:'python',label:'Python',disabled:false},{value:'Unavailable',label:'Unavailable',disabled:true},{value:'Default label',label:'Default label',disabled:false}]);
});
test('dropdown keyboard navigation wraps and skips disabled choices',()=>{
 const options=[{label:'A',disabled:true},{label:'B'},{label:'C',disabled:true},{label:'D'}];assert.equal(nextOption(options,-1,1),1);assert.equal(nextOption(options,3,1),1);assert.equal(nextOption(options,1,-1),3);assert.equal(nextOption([],0,1),-1);assert.equal(nextOption([{disabled:true}],0,1),-1);
});
test('dropdown typeahead finds later enabled prefixes and wraps to earlier matches',()=>{
 const options=[{label:'Python'},{label:'PowerShell',disabled:true},{label:'Power tools'},{label:'Go'}];assert.equal(matchingOption(options,'po',0),2);assert.equal(matchingOption(options,'P',2),0);assert.equal(matchingOption(options,'missing'),-1);
});

import {wrapGroup,defaultControl,visibleSteps,nestedList} from './controlModel.js';
test('wrapping preserves internal dependencies and routes external work through group',()=>{
 const w={version:1,steps:[{id:'a',name:'a',kind:'command',position:{x:0,y:0}},{id:'b',name:'b',kind:'command',needs:['a'],position:{x:300,y:0}},{id:'c',name:'c',kind:'command',needs:['b'],position:{x:600,y:0}}]};
 const n=wrapGroup(w,['a','b'],'repeat'),group=n.steps.at(-1);
 assert.equal(n.version,2);assert.equal(n.steps[1].scope,group.id);assert.deepEqual(n.steps[1].needs,['a']);assert.deepEqual(n.steps[2].needs,[group.id]);assert.equal(group.control.outputs.b,'${steps.b.result}');assert.equal(w.version,1);
});
test('wrapping rejects multiple external exits without mutating the graph',()=>{
 const w={steps:[{id:'a'},{id:'b'},{id:'x',needs:['a']},{id:'y',needs:['b']}]};assert.throws(()=>wrapGroup(w,['a','b']),/multiple external exits/);assert.equal(w.steps.length,4);
});
test('compact controls keep their connected cards visible even in older collapsed layouts',()=>{
 const steps=[{id:'child',scope:'outer'},{id:'outer',kind:'while',collapsed:true},{id:'next'}];assert.deepEqual(visibleSteps(steps).map(s=>s.id),['outer','next','child']);assert.deepEqual(nestedList(steps).map(s=>s.id),['outer','child','next']);
});
test('new loops have safe defaults with explicit unlimited settings supported',()=>{assert.equal(defaultControl('while').limit,100);assert.equal(defaultControl('while').timeout,1800);assert.equal(defaultControl('foreach').parallel,1)});
test('ordinary connections cannot bypass a group boundary',()=>{const w={steps:[{id:'a',kind:'command'},{id:'b',kind:'command',scope:'g'}]};assert.throws(()=>connectCards(w,'a','b'),/group/)});
import {fitGroupBounds,duplicateScope,absolutePosition} from './controlModel.js';
test('old container layouts normalize to independent compact cards without changing execution',()=>{const steps=[{id:'outer',kind:'while',size:{width:840,height:720}},{id:'inner',kind:'repeat',scope:'outer',region:'body',position:{x:40,y:370},size:{width:840,height:720}}];const n=fitGroupBounds(steps);assert.equal(n[0].size,undefined);assert.equal(n[1].size,undefined);assert.equal(n[1].scope,'outer');assert.equal(n[1].position.x,340);assert.equal(steps[0].size.width,840);assert.deepEqual(fitGroupBounds(n),n)});
test('duplicate group carries children and rewrites its published references',()=>{const w={version:2,steps:[{id:'g',name:'G',kind:'repeat',control:{outputs:{x:'${steps.child.result.json}'}}},{id:'child',name:'Child',kind:'wait',scope:'g'}]};const n=duplicateScope(w,'g'),copy=n.steps[2],child=n.steps[3];assert.equal(child.scope,copy.id);assert.equal(copy.control.outputs.x,'${steps.'+child.id+'.result.json}');assert.equal(w.steps.length,2)});
test('created-card focus uses absolute coordinates for controlled cards',()=>{assert.deepEqual(absolutePosition([{id:'g',position:{x:300,y:200}},{id:'c',scope:'g',position:{x:40,y:70}}],{id:'c',scope:'g',position:{x:40,y:70}}),{x:40,y:70})});

import {controlEdges} from './controlModel.js';
test('Body port takes ownership of a complete chain and Done stays outside the loop',()=>{
 let w={version:2,steps:[{id:'loop',kind:'while',control:defaultControl('while')},{id:'a',kind:'command'},{id:'b',kind:'wait',needs:['a']},{id:'after',kind:'command'}]};w=connectCards(w,'loop','a','region:body','entry');assert.equal(w.steps[1].scope,'loop');assert.equal(w.steps[2].scope,'loop');assert.deepEqual(w.steps[1].needs,undefined);assert.deepEqual(w.steps[2].needs,['a']);w=connectCards(w,'loop','after','done','entry');assert.deepEqual(w.steps[3].needs,['loop']);assert.equal(w.steps[3].scope,undefined);assert.deepEqual(controlEdges(w.steps).map(e=>[e.source,e.target,e.sourceHandle]),[['loop','a','region:body']]);
});
test('extending a controlled chain adopts the next card and its downstream work',()=>{
 let w={steps:[{id:'loop',kind:'repeat'},{id:'a',kind:'wait',scope:'loop',region:'body'},{id:'b',kind:'wait'},{id:'c',kind:'wait',needs:['b']}]};w=connectCards(w,'a','b');assert.equal(w.steps[2].scope,'loop');assert.equal(w.steps[3].scope,'loop');assert.deepEqual(w.steps[2].needs,['a']);
});
test('Condition port configures fresh Boolean output capture and can be detached',()=>{
 let w={steps:[{id:'loop',kind:'while',control:defaultControl('while')},{id:'probe',kind:'command'}]};w=connectCards(w,'loop','probe','region:condition');assert.equal(w.steps[1].region,'condition');assert.equal(w.steps[1].capture,'json');assert.equal(w.steps[0].control.test.source,'steps.probe.result.json');w=disconnectCards(w,'loop','probe');assert.equal(w.steps[1].scope,undefined);assert.equal(w.steps[0].control.test.source,'');
});
test('Try ports own independent Body, Catch and Finally chains',()=>{
 let w={steps:[{id:'try',kind:'try'},...['body','catch','finally'].map(id=>({id,kind:'wait'}))]};for(const region of ['body','catch','finally'])w=connectCards(w,'try',region,'region:'+region);assert.deepEqual(w.steps.slice(1).map(s=>[s.scope,s.region]),[['try','body'],['try','catch'],['try','finally']]);assert.equal(controlEdges(w.steps).length,3);
});
test('control connections reject ownership cycles, ambiguous prerequisites and cross-control stealing',()=>{
 const w={steps:[{id:'loop',kind:'while'},{id:'inner',kind:'repeat',scope:'loop',region:'body'},{id:'other',kind:'try'},{id:'a',kind:'wait'},{id:'b',kind:'wait',needs:['a']}]};assert.throws(()=>connectCards(w,'inner','loop','region:body'),/ancestor|cycle/);assert.throws(()=>connectCards(w,'other','inner','region:body'),/already belongs/);assert.throws(()=>connectCards(w,'loop','b','region:body'),/first card/);assert.throws(()=>connectCards(w,'loop','a','region:catch'),/valid control/);assert.equal(w.steps[3].scope,undefined);
});
test('detaching a Body chain preserves nested loop ownership and internal dependencies',()=>{
 const w={steps:[{id:'outer',kind:'while'},{id:'inner',kind:'repeat',scope:'outer',region:'body'},{id:'child',kind:'wait',scope:'inner',region:'body'},{id:'end',kind:'wait',scope:'outer',region:'body',needs:['inner']}]};const n=disconnectCards(w,'outer','inner');assert.equal(n.steps[1].scope,undefined);assert.equal(n.steps[2].scope,'inner');assert.equal(n.steps[3].scope,undefined);assert.deepEqual(n.steps[3].needs,['inner']);assert.equal(w.steps[1].scope,'outer');
});

import {setControlOwner} from './model.js';
test('keyboard ownership moves the full chain with the same safety as canvas ports',()=>{const w={steps:[{id:'try',kind:'try'},{id:'a',kind:'wait',scope:'try',region:'body'},{id:'b',kind:'wait',scope:'try',region:'body',needs:['a']}]};const n=setControlOwner(w,'a','try','finally');assert.equal(n.steps[1].region,'finally');assert.equal(n.steps[2].region,'finally');assert.throws(()=>setControlOwner(w,'b','try','catch'),/first card/);assert.equal(w.steps[1].region,'body')});
test('Add next and If branches inherit the owning control branch',()=>{const w={steps:[{id:'if',kind:'condition',scope:'loop',region:'body'}]};assert.equal(appendStep(w,'if').steps[1].scope,'loop');const n=appendBranch(w,'if',false);assert.equal(n.steps[1].region,'body');assert.deepEqual(n.steps[1].when,{step:'if',equals:false})});
