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
export function visibleSteps(steps){return steps.filter(s=>![...descendantsAncestors(steps,s)].some(p=>p.collapsed)).sort((a,b)=>depth(steps,a)-depth(steps,b))}
function* descendantsAncestors(steps,s){let p=steps.find(x=>x.id===s.scope),n=0;while(p&&n++<17){yield p;p=steps.find(x=>x.id===p.scope)}}
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
 const group={id,name:kind==='while'?'While condition is true':kind==='try'?'Try with recovery':'Repeat group',kind,control:{...defaultControl(kind),inputs,outputs},needs:incoming,position:{x:left,y:top},size:{width:Math.max(840,...chosen.map(s=>(s.position?.x||0)-left+308)),height:Math.max(900,...chosen.map(s=>(s.position?.y||0)-top+580))},...(scope?{scope,region}:{})};
 const steps=workflow.steps.map(original=>{let s=original;if(set.has(s.id)){for(const outer of incoming)s=JSON.parse(JSON.stringify(s).split('steps.'+outer+'.result').join('scope.inputs.'+outer));}if(set.has(s.id))return {...s,scope:id,region:'body',needs:(s.needs||[]).filter(k=>set.has(k)),position:{x:(s.position?.x||0)-left+40,y:(s.position?.y||0)-top+370}};
 const next={...s,needs:[...new Set((s.needs||[]).map(k=>set.has(k)?id:k))]};for(const exit of exits){const old='${steps.'+exit.id+'.result',replacement='${steps.'+id+'.result.json.'+exit.id;return JSON.parse(JSON.stringify(next).split(old).join(replacement))}return next});
 if(incoming.some(k=>createsCycle([...steps,group],k,id)))throw Error('Wrapping would create a cycle.');
 return {...workflow,version:2,steps:[...steps,group]};
}
export function nestedList(steps,parent=null){return steps.filter(s=>(s.scope||null)===parent).flatMap(s=>[s,...(s.collapsed?[]:nestedList(steps,s.id))])}

export function absolutePosition(steps,s){let x=s?.position?.x||0,y=s?.position?.y||0,p=s?.scope,n=0;while(p&&n++<17){const parent=steps.find(s=>s.id===p);x+=parent?.position?.x||0;y+=parent?.position?.y||0;p=parent?.scope}return {x,y}}
export function layoutScopes(steps){
 const result=structuredClone(steps),by=new Map(result.map(s=>[s.id,s]));
 function arrange(parent=null,region='body',offset=0){const peers=result.filter(s=>(s.scope||null)===parent&&(s.region||'body')===region);const levels=new Map();function level(s){if(levels.has(s.id))return levels.get(s.id);const n=Math.max(-1,...(s.needs||[]).filter(k=>peers.some(p=>p.id===k)).map(k=>level(by.get(k))))+1;levels.set(s.id,n);return n}for(const s of peers)level(s);const columns=new Map(),rows=new Map();for(const s of peers)columns.set(levels.get(s.id),Math.max(columns.get(levels.get(s.id))||0,isGroup(s)?s.size?.width||840:228));
 for(const s of peers){const col=levels.get(s.id),row=rows.get(col)||0;rows.set(col,row+1);s.position={x:(parent?40:0)+[...columns].filter(([n])=>n<col).reduce((x,[,w])=>x+w+80,0),y:offset+row*(isGroup(s)?(s.size?.height||720)+60:260)};if(isGroup(s)){const regions=s.kind==='try'?['body','catch','finally']:['while','until'].includes(s.kind)?['condition','body']:['body'];regions.forEach((r,i)=>arrange(s.id,r,s.kind==='try'?100+i*260:r==='body'&&regions.length===2?370:100));}}
 }
 arrange();return result;
}
export function regionNames(s){return s.kind==='try'?['body','catch','finally']:['while','until'].includes(s.kind)?['condition','body']:['body']}
export function regionGeometry(s){const names=regionNames(s),total=(s.size?.height||720)-52;let top=52;return names.map((name,i)=>{const height=s.region_sizes?.[name]??(names.length===2?(i===0?240:total-240):total/names.length);const r={name,top,height};top+=height;return r})}
export function fitGroupBounds(steps){const result=structuredClone(steps);for(const s of [...result].filter(isGroup).sort((a,b)=>depth(result,b)-depth(result,a))){let width=s.size?.width||840;const geometry=regionGeometry(s);let growth=0;const sizes={};for(const r of geometry){const children=result.filter(c=>c.scope===s.id&&(c.region||'body')===r.name);for(const c of children){c.position={x:c.position?.x||40,y:Math.max(c.position?.y||0,r.top+70)+growth};width=Math.max(width,c.position.x+(isGroup(c)?c.size?.width||840:228)+40)}const bottom=Math.max(r.top+growth+r.height,...children.map(c=>c.position.y+(isGroup(c)?c.size?.height||720:c.kind==='condition'?230:210)+40));sizes[r.name]=bottom-r.top-growth;growth+=sizes[r.name]-r.height;}s.region_sizes=sizes;s.size={width,height:Math.max(s.size?.height||720,52+Object.values(sizes).reduce((a,b)=>a+b,0))};}return result}
export function duplicateScope(workflow,id){const selected=workflow.steps.find(s=>s.id===id);const ids=new Set([id,...descendants(workflow.steps,id)]);const prefix=nextId(workflow.steps),mapping=Object.fromEntries([...ids].map(k=>[k,k===id?prefix:prefix+'-'+k]));let copies=workflow.steps.filter(s=>ids.has(s.id)).map(s=>{let text=JSON.stringify(s);for(const [old,next] of Object.entries(mapping))text=text.split('steps.'+old+'.').join('steps.'+next+'.');const copy=JSON.parse(text);copy.id=mapping[s.id];copy.name=s.name+' copy';if(ids.has(s.scope))copy.scope=mapping[s.scope];copy.needs=(s.needs||[]).map(k=>mapping[k]||k);if(copy.when?.step)copy.when.step=mapping[copy.when.step]||copy.when.step;if(copy.condition?.input?.step)copy.condition.input.step=mapping[copy.condition.input.step]||copy.condition.input.step;if(s.id===id)copy.position={x:(selected.position?.x||0)+40,y:(selected.position?.y||0)+155};return copy});return {...workflow,steps:[...workflow.steps,...copies]}}
