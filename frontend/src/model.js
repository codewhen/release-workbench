export function nextId(steps){let n=steps.length+1;while(steps.some(s=>s.id===`step-${n}`))n++;return `step-${n}`;}
export function createsCycle(steps,source,target){if(source===target)return true;const byId=new Map(steps.map(s=>[s.id,s]));const seen=new Set();function visit(id){if(id===target)return true;if(seen.has(id))return false;seen.add(id);return (byId.get(id)?.needs||[]).some(visit);}return visit(source);}
export function appendStep(workflow,after=null,kind='command'){const steps=workflow.steps;const id=nextId(steps);const parent=steps.find(s=>s.id===after);const position={x:(parent?.position?.x||0)+300,y:parent?.position?.y||0};const step={id,name:kind==='manual'?'Review evidence':kind==='condition'?'If condition':kind==='loop'?'Loop':kind==='workflow'?'Run workflow':kind==='action'?'Set values':'New step',kind,needs:after?[after]:[],...(parent?.scope?{scope:parent.scope,region:parent.region||'body'}:{}),mode:'background',position,...(parent?.kind==='condition'?{when:{step:after,equals:true}}:{}),...(kind==='action'?{action:{type:'set_values',values:{message:'Hello workflow',ready:true}}}:kind==='loop'?{workflow:'',loop:{iterations:3}}:kind==='workflow'?{workflow:''}:kind==='condition'?{condition:{input:{}}}:kind==='command'?{commands:[{argv:['${python}','-c','print("Step complete")']}]}:{description:'Record evidence before continuing.'})};return {...workflow,steps:[...steps,step]};}
export function insertStep(workflow,source,target){const added=appendStep(workflow,source);const inserted=added.steps.at(-1),original=workflow.steps.find(s=>s.id===target);if(original?.when?.step===source)inserted.when={...original.when};return {...added,steps:added.steps.map(s=>{if(s.id!==target)return s;const next={...s,needs:(s.needs||[]).map(d=>d===source?inserted.id:d)};if(next.when?.step===source)delete next.when;if(next.condition?.input?.step===source)next.condition={input:{...next.condition.input,step:inserted.id}};return next})};}
export function autoLayout(steps){const depth=new Map();function level(s,seen=new Set()){if(depth.has(s.id))return depth.get(s.id);if(seen.has(s.id))return 0;seen.add(s.id);const result=Math.max(-1,...(s.needs||[]).map(id=>{const parent=steps.find(p=>p.id===id);return parent?level(parent,new Set(seen)):0}))+1;depth.set(s.id,result);return result;}const rows=new Map();return steps.map(s=>{const x=level(s),row=rows.get(x)||0;rows.set(x,row+1);return {...s,position:{x:x*310,y:row*260}}});}
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
 let slot=0;while(slot<10000){const position={x:(slot%3)*310,y:Math.floor(slot/3)*260};if(!workflow.steps.some((s,i)=>{const p=s.position||{x:i*310,y:0};return Math.abs(p.x-position.x)<260&&Math.abs(p.y-position.y)<240})){card.position=position;break}slot++;}
 return next;
}
const controlKinds=['while','until','repeat','foreach','try'];
function branchIds(steps,id){const first=steps.find(s=>s.id===id),ids=new Set([id]);let changed=true;while(changed){changed=false;for(const s of steps)if(s.scope===first.scope&&(s.region||'body')===(first.region||'body')&&!ids.has(s.id)&&(s.needs||[]).some(k=>ids.has(k))){ids.add(s.id);changed=true}}return ids}
function moveBranch(workflow,id,scope,region){
 const ids=branchIds(workflow.steps,id);
 if(ids.has(scope))throw Error('This connection would create a control cycle.');
 let ancestor=scope;while(ancestor){if(ids.has(ancestor))throw Error('A control card cannot contain itself or its ancestor.');ancestor=workflow.steps.find(s=>s.id===ancestor)?.scope;}
 if(workflow.steps.some(s=>ids.has(s.id)&&(s.needs||[]).some(k=>!ids.has(k))))throw Error('This branch has outside prerequisites. Disconnect them first, or include them in the controlled branch.');
 return {...workflow,steps:workflow.steps.map(s=>ids.has(s.id)?{...s,scope:scope||undefined,region:scope?region:undefined}:s)};
}
export function conditionValuePath(step){
 const base='steps.'+step.id+'.result.';
 if(step.kind==='manual')return base+'json.decision';
 if(step.kind==='condition'||step.kind==='switch')return base+'decision';
 if(step.kind==='action'&&step.action?.type==='calculate')return base+'json.value';
 if(step.kind==='action'&&step.action?.type==='file_exists')return base+'json.exists';
 if(['declare','assign','update'].includes(step.kind))return base+'json.'+step.control.name;
 return base+'json';
}
export function connectCards(workflow,source,target,handle=null,targetHandle=null){
 if(!workflow.steps.some(s=>s.id===source)||!workflow.steps.some(s=>s.id===target))throw Error('Select existing cards to connect.');
 let parent=workflow.steps.find(s=>s.id===source),child=workflow.steps.find(s=>s.id===target);
 if(targetHandle==='condition-result'){
  if(!['while','until'].includes(child.kind))throw Error('Condition result belongs on a While or Until loop.');
  if(parent.scope!==target||parent.region!=='condition')throw Error('Return a card from this loop’s Condition branch. Connect Condition to its first card first.');
  return {...workflow,steps:workflow.steps.map(s=>s.id===target?{...s,control:{...s.control,test:{source:conditionValuePath(parent),operator:'is_true'}}}:s.id===source&&s.kind==='command'?{...s,capture:'json'}:s)};
 }

 if(handle==='result')throw Error('Return value connects to a Loop Condition result. Use Output to run the next card.');
 if(handle?.startsWith('region:')){
  const region=handle.slice(7),allowed=parent.kind==='try'?['body','catch','finally']:['while','until'].includes(parent.kind)?['body','condition']:['body'];
  if(!controlKinds.includes(parent.kind)||!allowed.includes(region))throw Error('Choose a valid control port.');
  if(targetHandle&&targetHandle!=='entry')throw Error('Connect control ports to the first card’s Entry.');
  if((child.needs||[]).length)throw Error('Connect this port to the first card in a branch, without incoming dependencies.');
  if(child.scope&&child.scope!==source)throw Error('This card already belongs to another control card. Disconnect its control connection first.');
  let next=moveBranch(workflow,target,source,region);
  if(region==='condition')next={...next,steps:next.steps.map(s=>s.id===source?{...s,control:{...s.control,test:{source:conditionValuePath(child),operator:'is_true'}}}:s.id===target&&['command','action'].includes(s.kind)?{...s,capture:'json'}:s)};
  return {...next,version:2};
 }
 if(createsCycle(workflow.steps,source,target))throw Error('This connection would create a dependency cycle.');
 if(parent.scope&&!child.scope){workflow=moveBranch(workflow,target,parent.scope,parent.region||'body');child=workflow.steps.find(s=>s.id===target);}
 if((parent.scope||null)!==(child.scope||null)||(parent.region||'body')!==(child.region||'body'))throw Error('Connect through a control card’s Body, Condition, Catch, Finally or Done port to cross a group boundary.');
 if(targetHandle==='compute'&&child.kind!=='condition')throw Error('Compute input belongs on an If card.');
 return {...workflow,steps:workflow.steps.map(s=>{
  if(s.id!==target)return s;
  const next={...s};let needs=[...(s.needs||[])];
  if(s.kind==='condition'){
   const compute=s.condition?.input?.step;
   if(targetHandle==='compute'){needs=needs.filter(id=>id!==compute);next.condition={input:{step:source}};}
   else {needs=needs.filter(id=>id===compute&&id!==source);if(compute===source){next.condition={input:{...s.condition.input}};delete next.condition.input.step;}}
  }
  next.needs=[...needs.filter(id=>id!==source),source];
  if(next.when&&!next.needs.includes(next.when.step))delete next.when;
  if(parent.kind==='switch'){next.when={step:source,equals:handle||'default'};}
  if(parent.kind==='condition'){
   if(next.when&&next.when.step!==source)throw Error('A card can follow one If route. Add another If card to combine decisions.');
   next.when={step:source,equals:handle!=='false'};
  }
  return next;
 })};
}
export function disconnectCards(workflow,source,target){
 const child=workflow.steps.find(s=>s.id===target),parent=workflow.steps.find(s=>s.id===source);
 if(['while','until'].includes(child?.kind)&&child.control?.test?.source?.startsWith('steps.'+source+'.result.'))return {...workflow,steps:workflow.steps.map(s=>s.id===target?{...s,control:{...s.control,test:{source:'',operator:'is_true'}}}:s)};

 if(child?.scope===source&&!(child.needs||[]).length){let next=moveBranch(workflow,target,parent?.scope,parent?.region||'body');if(child.region==='condition'&&branchIds(workflow.steps,target).has(parent?.control?.test?.source?.match(/^steps\.([^.]+)\.result\./)?.[1]))next={...next,steps:next.steps.map(s=>s.id===source?{...s,control:{...s.control,test:{source:'',operator:'is_true'}}}:s)};return next;}
 return {...workflow,steps:workflow.steps.map(s=>{if(s.id!==target)return s;const next={...s,needs:(s.needs||[]).filter(id=>id!==source)};if(next.when?.step===source)delete next.when;if(next.condition?.input?.step===source){next.condition={input:{...next.condition.input}};delete next.condition.input.step;}return next})};
}
export function disconnectNode(workflow,id){
 let next=workflow;const s=workflow.steps.find(s=>s.id===id);
 for(const owner of workflow.steps.filter(s=>['while','until'].includes(s.kind)&&s.control?.test?.source?.startsWith('steps.'+id+'.result.')))next=disconnectCards(next,id,owner.id);
 if(s?.scope&&!(s.needs||[]).length)next=disconnectCards(next,s.scope,id);
 for(const child of workflow.steps.filter(s=>s.scope===id&&!(s.needs||[]).length))next=disconnectCards(next,id,child.id);
 return {...next,steps:next.steps.map(s=>{if(s.id===id){const next={...s,needs:[]};delete next.when;if(next.condition?.input){next.condition={input:{...next.condition.input}};delete next.condition.input.step;}return next;}if(!(s.needs||[]).includes(id))return s;const next={...s,needs:s.needs.filter(dep=>dep!==id)};if(next.when?.step===id)delete next.when;if(next.condition?.input?.step===id){next.condition={input:{...next.condition.input}};delete next.condition.input.step;}return next;})};
}

export function setControlOwner(workflow,id,owner,region='body'){
 const step=workflow.steps.find(s=>s.id===id);if(!step)throw Error('Select an existing card.');
 if((step.needs||[]).length)throw Error('Change ownership from the first card of this branch, or disconnect its incoming dependencies first.');
 let next=workflow;if(step.scope)next=disconnectCards(next,step.scope,id);
 return owner?connectCards(next,owner,id,'region:'+region,'entry'):next;
}
