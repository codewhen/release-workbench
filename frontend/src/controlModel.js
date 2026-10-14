import {nextId,createsCycle} from './model.js';
export const GROUPS=['while','until','repeat','foreach','try'];
export const FLOW_KINDS=[...GROUPS,'switch','break','continue','wait','poll','declare','assign','update','merge','handle_error'];
export const isGroup=s=>GROUPS.includes(s?.kind);
export function defaultControl(kind){
 const limits={limit:100,timeout:1800};
 return kind==='while'||kind==='until'?{...limits,test:{source:'vars.ready',operator:'is_true'},outputs:{}}:kind==='repeat'?{...limits,count:3,outputs:{}}:kind==='foreach'?{...limits,items:[],parallel:1,outputs:{}}:kind==='try'?{outputs:{}}:kind==='poll'?{...limits,delay:1,test:{compute:{commands:[{argv:['${python}','-c','print("true")']}]}}}:kind==='switch'?{source:'vars.value',cases:[{id:'match',value:true}]}:['declare','assign','update'].includes(kind)?{name:'value',value:kind==='update'?1:0,...(kind==='update'?{operator:'add'}:{})}:kind==='merge'?{value:[],conflicts:'error'}:kind==='wait'?{delay:1}:{};
}
export function descendants(steps,id){const found=new Set();for(const s of steps){let p=s.scope;const seen=new Set();while(p&&!seen.has(p)){if(p===id){found.add(s.id);break}seen.add(p);p=steps.find(x=>x.id===p)?.scope}}return found}
export function depth(steps,s){let n=0,p=s.scope;while(p&&n<17){n++;p=steps.find(x=>x.id===p)?.scope}return n}
export function visibleSteps(steps){return [...steps].sort((a,b)=>depth(steps,a)-depth(steps,b))}
export function wrapGroup(workflow,ids,kind='while'){
 const chosen=workflow.steps.filter(s=>ids.includes(s.id));if(!chosen.length)throw Error('Select cards to wrap.');
 const scope=chosen[0].scope,region=chosen[0].region||'body';if(chosen.some(s=>s.scope!==scope||(s.region||'body')!==region))throw Error('Wrap cards from the same group region.');
 const set=new Set(ids);const incoming=[...new Set(chosen.flatMap(s=>s.needs||[]).filter(id=>!set.has(id)))];
 const exits=chosen.filter(s=>workflow.steps.some(x=>!set.has(x.id)&&(x.needs||[]).includes(s.id)));
 if(exits.length>1)throw Error('This selection has multiple external exits. Add a join or expand the selection before wrapping.');
 if(chosen.some(s=>s.when&&!set.has(s.when.step))||workflow.steps.some(s=>!set.has(s.id)&&s.when&&set.has(s.when.step)))throw Error('Include both the decision and its branches in the group.');
 const id=nextId(workflow.steps),left=Math.min(...chosen.map(s=>s.position?.x||0)),top=Math.min(...chosen.map(s=>s.position?.y||0));
 const inputs=Object.fromEntries(incoming.map(id=>[id,'${steps.'+id+'.result}']));
 const outputs=Object.fromEntries(exits.map(s=>[s.id,'${steps.'+s.id+'.result}']));
 const group={id,name:kind==='while'?'While condition is true':kind==='try'?'Try with recovery':'Repeat group',kind,control:{...defaultControl(kind),inputs,outputs},needs:incoming,position:{x:left,y:top},...(scope?{scope,region}:{})};
 const steps=workflow.steps.map(original=>{let s=original;if(set.has(s.id)){for(const outer of incoming)s=JSON.parse(JSON.stringify(s).split('steps.'+outer+'.result').join('scope.inputs.'+outer));}if(set.has(s.id))return {...s,scope:id,region:'body',needs:(s.needs||[]).filter(k=>set.has(k)),position:{x:(s.position?.x||0)+340,y:s.position?.y||0}};
 const next={...s,needs:[...new Set((s.needs||[]).map(k=>set.has(k)?id:k))]};for(const exit of exits){const old='${steps.'+exit.id+'.result',replacement='${steps.'+id+'.result.json.'+exit.id;return JSON.parse(JSON.stringify(next).split(old).join(replacement))}return next});
 if(incoming.some(k=>createsCycle([...steps,group],k,id)))throw Error('Wrapping would create a cycle.');
 return {...workflow,version:2,steps:layoutScopes([...steps,group])};
}
export function nestedList(steps,parent=null){return steps.filter(s=>(s.scope||null)===parent).flatMap(s=>[s,...nestedList(steps,s.id)])}

// Canvas coordinates are absolute. Scope is execution ownership, never a visual container.
export function absolutePosition(steps,s){return fitGroupBounds(steps).find(x=>x.id===s?.id)?.position||s?.position||{x:0,y:0}}
export function regionNames(s){return s.kind==='try'?['body','catch','finally']:['while','until'].includes(s.kind)?['condition','body']:['body']}
export function regionGeometry(s){return regionNames(s).map(name=>({name}))}
export function layoutScopes(steps){
 const result=structuredClone(steps),levels=new Map(),rows=new Map();
 function level(s,seen=new Set()){if(levels.has(s.id))return levels.get(s.id);if(seen.has(s.id))return 0;seen.add(s.id);const refs=[...(s.needs||[]),...(s.scope?[s.scope]:[])];const n=Math.max(-1,...refs.map(id=>{const p=result.find(s=>s.id===id);return p?level(p,new Set(seen)):0}))+1;levels.set(s.id,n);return n;}
 for(const s of result){const column=level(s),row=rows.get(column)||0;rows.set(column,row+1);s.position={x:column*340,y:row*280};}return result;
}
export function fitGroupBounds(steps){
 // Older drafts used relative coordinates and large container bounds. Migrate layout only.
 const result=steps.some(s=>s.size||s.region_sizes)?layoutScopes(steps):structuredClone(steps);
 for(const s of result){delete s.size;delete s.region_sizes;delete s.collapsed;}return result;
}
export function controlEdges(steps){const visible=new Set(visibleSteps(steps).map(s=>s.id));return steps.filter(s=>s.scope&&visible.has(s.id)&&visible.has(s.scope)&&!(s.needs||[]).length).map(s=>({id:`scope:${s.scope}:${s.id}`,source:s.scope,target:s.id,sourceHandle:'region:'+(s.region||'body'),targetHandle:'entry',label:(s.region||'body')}))}
export function duplicateScope(workflow,id){const selected=workflow.steps.find(s=>s.id===id);const ids=new Set([id,...descendants(workflow.steps,id)]);const prefix=nextId(workflow.steps),mapping=Object.fromEntries([...ids].map(k=>[k,k===id?prefix:prefix+'-'+k]));let copies=workflow.steps.filter(s=>ids.has(s.id)).map(s=>{let text=JSON.stringify(s);for(const [old,next] of Object.entries(mapping))text=text.split('steps.'+old+'.').join('steps.'+next+'.');const copy=JSON.parse(text);copy.id=mapping[s.id];copy.name=s.name+' copy';if(ids.has(s.scope))copy.scope=mapping[s.scope];copy.needs=(s.needs||[]).map(k=>mapping[k]||k);if(copy.when?.step)copy.when.step=mapping[copy.when.step]||copy.when.step;if(copy.condition?.input?.step)copy.condition.input.step=mapping[copy.condition.input.step]||copy.condition.input.step;copy.position={x:(s.position?.x||0)+40,y:(s.position?.y||0)+155};return copy});return {...workflow,steps:[...workflow.steps,...copies]}}
