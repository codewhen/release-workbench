const finished=new Set(['passed','recorded','failed','blocked','cancelled','skipped']);
export function executionFocus(steps,state,previous){
 const active=steps.filter(s=>state?.steps?.[s.id]?.status==='running').sort((a,b)=>Number(!!b.scope)-Number(!!a.scope));
 return active.find(s=>s.id===previous)?.id||active[0]?.id||null;
}
export function runSummary(workflow,state){
 const selection=new Set(state?.selection?.length?state.selection:workflow.steps.map(s=>s.id));
 const steps=workflow.steps.filter(s=>selection.has(s.id));const counts={};
 for(const step of (workflow.version===2?steps.filter(s=>!s.scope):steps)){const status=state?.steps?.[step.id]?.status||'pending';counts[status]=(counts[status]||0)+1;}
 const progressSteps=workflow.version===2?steps.filter(s=>!s.scope):steps;
 const done=progressSteps.filter(s=>finished.has(state?.steps?.[s.id]?.status)).length;
 return {steps,counts,done,total:progressSteps.length,percent:Math.round(done/Math.max(1,progressSteps.length)*100),partial:steps.length<workflow.steps.length};
}
