import test from 'node:test';import assert from 'node:assert/strict';import {appendStep,createsCycle,insertStep,autoLayout,parseCommand,formatCommand,nextExecutionSelection,clampPanelWidth,appendBranch} from './model.js';
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
