export function resultSources(workflow,step,state){
 const ids=new Set();function visit(id){if(ids.has(id))return;ids.add(id);for(const parent of workflow.steps.find(s=>s.id===id)?.needs||[])visit(parent)}for(const id of step.needs||[])visit(id);
 const sources=Object.entries(workflow.inputs||{}).map(([id,s])=>({value:`inputs.${id}`,label:`Input: ${s.label}`}));
 function add(value,label){if(!sources.some(s=>s.value===value))sources.push({value,label})}
 function keys(value,path,label,depth=0){if(depth>4||sources.length>100||value==null||typeof value!=='object')return;for(const [key,item] of Object.entries(value)){if(key.includes('.'))continue;add(path+'.'+key,label+' · '+key);keys(item,path+'.'+key,label+' · '+key,depth+1)}}
 for(const s of workflow.steps.filter(s=>ids.has(s.id))){const base=`steps.${s.id}.result`;if(s.kind==='manual')continue;if(s.kind!=='condition')add(base+'.exit_code',s.name+' · exit code');if(s.kind==='condition')add(base+'.decision',s.name+' · decision');if(s.capture==='text'||s.capture==='json')add(base+'.stdout',s.name+' · text output');if(s.kind==='action'&&!['run_tests','run_script'].includes(s.action?.type)||s.capture==='json'){add(base+'.json',s.name+' · all data');const known=s.action?.type==='set_values'?s.action.values:s.action?.type==='calculate'?{value:0}:s.action?.type==='file_exists'?{exists:true}:s.action?.type==='write_file'?{path:'',bytes:0,written:true}:state?.steps?.[s.id]?.result?.json;keys(known,base+'.json',s.name)}}
 return sources;
}
