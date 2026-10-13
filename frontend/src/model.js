export function nextId(steps){let n=steps.length+1;while(steps.some(s=>s.id===`step-${n}`))n++;return `step-${n}`;}
export function createsCycle(steps,source,target){if(source===target)return true;const byId=new Map(steps.map(s=>[s.id,s]));const seen=new Set();function visit(id){if(id===target)return true;if(seen.has(id))return false;seen.add(id);return (byId.get(id)?.needs||[]).some(visit);}return visit(source);}
export function appendStep(workflow,after=null,kind='command'){const steps=workflow.steps;const id=nextId(steps);const parent=steps.find(s=>s.id===after);const position={x:(parent?.position?.x||0)+300,y:parent?.position?.y||0};const step={id,name:kind==='manual'?'Review evidence':kind==='condition'?'If condition':kind==='workflow'?'Run workflow':'New step',kind,needs:after?[after]:[],mode:'background',position,...(parent?.kind==='condition'?{when:{step:after,equals:true}}:{}),...(kind==='workflow'?{workflow:''}:kind==='condition'?{condition:{source:'inputs.value',operator:'equals',value:true}}:kind==='command'?{commands:[{argv:['${python}','-c','print("Step complete")']}]}:{description:'Record evidence before continuing.'})};return {...workflow,steps:[...steps,step]};}
export function insertStep(workflow,source,target){const added=appendStep(workflow,source);const inserted=added.steps.at(-1),original=workflow.steps.find(s=>s.id===target);if(original?.when?.step===source)inserted.when={...original.when};return {...added,steps:added.steps.map(s=>{if(s.id!==target)return s;const next={...s,needs:(s.needs||[]).map(d=>d===source?inserted.id:d)};if(next.when?.step===source)delete next.when;return next})};}
export function autoLayout(steps){const depth=new Map();function level(s,seen=new Set()){if(depth.has(s.id))return depth.get(s.id);if(seen.has(s.id))return 0;seen.add(s.id);const result=Math.max(-1,...(s.needs||[]).map(id=>{const parent=steps.find(p=>p.id===id);return parent?level(parent,new Set(seen)):0}))+1;depth.set(s.id,result);return result;}const rows=new Map();return steps.map(s=>{const x=level(s),row=rows.get(x)||0;rows.set(x,row+1);return {...s,position:{x:x*310,y:row*200}}});}
export function parseCommand(text){const args=[];let token='',quote=null,started=false;for(let i=0;i<text.length;i++){const c=text[i];if(quote){if(c===quote)quote=null;else if(c==='\\'&&quote==='"'&&['"','\\'].includes(text[i+1]))token+=text[++i];else token+=c;started=true;}else if(c==='"'||c==="'"){quote=c;started=true;}else if(/\s/.test(c)){if(started){args.push(token);token='';started=false;}}else if(c==='\\'&&text[i+1]&&/[\s"'\\]/.test(text[i+1])){token+=text[++i];started=true;}else{token+=c;started=true;}}if(quote)throw Error('Close the quotation mark in the command.');if(started)args.push(token);if(!args.length)throw Error('Enter a command.');return args;}
export function formatCommand(argv){return argv.map(a=>/^[\w./:${}\-]+$/.test(a)?a:'"'+a.replace(/\\/g,'\\\\').replace(/"/g,'\\"')+'"').join(' ');}

// Advance only when the step being inspected has just completed successfully.
export function nextExecutionSelection(steps,selected,previous,current){
 if(!['running','manual'].includes(previous?.steps?.[selected]?.status)||!['passed','recorded'].includes(current?.steps?.[selected]?.status))return null;
 const eligible=steps.filter(s=>s.enabled!==false&&['running','manual','queued'].includes(current?.steps?.[s.id]?.status)&&(s.needs||[]).every(id=>['passed','recorded'].includes(current?.steps?.[id]?.status)));
 return (eligible.find(s=>(s.needs||[]).includes(selected))||eligible.find(s=>current.steps[s.id].status==='running')||eligible[0])?.id||null;
}

export function clampPanelWidth(width,workspaceWidth){return Math.round(Math.max(280,Math.min(Number.isFinite(width)?width:370,720,Math.max(280,workspaceWidth-332))));}

export function appendBranch(workflow,id,equals){const next=appendStep(workflow,id);const step=next.steps.at(-1);step.name=equals?'True branch':'False branch';step.when={step:id,equals};step.position.y+=(equals?0:180);return next;}

export function appendCard(workflow,kind='command'){
 const next=appendStep(workflow,null,kind),card=next.steps.at(-1);
 let slot=0;while(slot<10000){const position={x:(slot%3)*310,y:Math.floor(slot/3)*200};if(!workflow.steps.some((s,i)=>{const p=s.position||{x:i*310,y:0};return Math.abs(p.x-position.x)<260&&Math.abs(p.y-position.y)<180})){card.position=position;break}slot++;}
 return next;
}
export function connectCards(workflow,source,target,handle=null){
 if(!workflow.steps.some(s=>s.id===source)||!workflow.steps.some(s=>s.id===target))throw Error('Select existing cards to connect.');
 if(createsCycle(workflow.steps,source,target))throw Error('This connection would create a dependency cycle.');
 const parent=workflow.steps.find(s=>s.id===source),child=workflow.steps.find(s=>s.id===target);
 if(parent.kind==='condition'&&child.when&&child.when.step!==source)throw Error('A card can follow one If route. Add another If card to combine decisions.');
 return {...workflow,steps:workflow.steps.map(s=>s.id===target?{...s,needs:[...new Set([...(s.needs||[]),source])],...(parent.kind==='condition'?{when:{step:source,equals:handle!=='false'}}:{})}:s)};
}
export function disconnectCards(workflow,source,target){return {...workflow,steps:workflow.steps.map(s=>{if(s.id!==target)return s;const next={...s,needs:(s.needs||[]).filter(id=>id!==source)};if(next.when?.step===source)delete next.when;return next})};}
