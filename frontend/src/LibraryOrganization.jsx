import React,{useEffect,useRef,useState} from 'react';
import {Folder,FolderPlus,FolderInput,ArrowRight,Pencil,Trash2,Copy} from 'lucide-react';
import {CardMenu} from './cards.jsx';
export function useLibraryOrganization({library,folder,onSelect,api,refresh,act,pending,onOpen}){
 const press=useRef(null),suppressTap=useRef(false);
 const [menu,setMenu]=useState(null),[edit,setEdit]=useState(null),[value,setValue]=useState('');const formRef=useRef(null);
 const folders=library?.folders||[];
 useEffect(()=>{if(!edit)return;const frame=requestAnimationFrame(()=>formRef.current?.querySelector('input,select,button')?.focus());return()=>cancelAnimationFrame(frame)},[edit]);
 useEffect(()=>()=>clearTimeout(press.current?.timer),[]);
 function start(action,target){setMenu(null);setEdit({action,target});setValue(action==='rename'?target.path.split('/').at(-1):action==='new'?(target.path||''):action==='move'?target.type==='folder'?(target.path.includes('/')?target.path.slice(0,target.path.lastIndexOf('/')):''):(target.workflow.folder||''):'');}
 function openMenu(event,target){if(pending)return;event.preventDefault();event.stopPropagation();const rect=event.currentTarget.getBoundingClientRect();const keyboard=event.type==='keydown';setMenu({target,x:Math.max(12,Math.min(keyboard?rect.left:event.clientX,window.innerWidth-292)),y:Math.max(12,Math.min(keyboard?rect.top+20:event.clientY,window.innerHeight-(target.type==='workflow'?330:target.path?400:160)-12))});}
 function keyMenu(event,target){if(event.key==='ContextMenu'||event.shiftKey&&event.key==='F10')openMenu(event,target)}
 function contextProps(target){return {
  onContextMenu:event=>{clearTimeout(press.current?.timer);openMenu(event,target)},onKeyDown:event=>keyMenu(event,target),
  onPointerDown:event=>{suppressTap.current=false;if(event.pointerType!=='touch')return;event.stopPropagation();clearTimeout(press.current?.timer);const point={clientX:event.clientX,clientY:event.clientY,currentTarget:event.currentTarget,type:'contextmenu',preventDefault(){},stopPropagation(){}};press.current={x:event.clientX,y:event.clientY,timer:setTimeout(()=>{suppressTap.current=true;openMenu(point,target)},550)}},
  onPointerMove:event=>{if(press.current&&Math.hypot(event.clientX-press.current.x,event.clientY-press.current.y)>12)clearTimeout(press.current.timer)},
  onPointerUp:()=>clearTimeout(press.current?.timer),onPointerCancel:()=>clearTimeout(press.current?.timer),
  onClickCapture:event=>{if(suppressTap.current){event.preventDefault();event.stopPropagation();suppressTap.current=false}},
 };}
 const target=menu?.target;const items=target?.type==='workflow'?[
  {id:'open',label:'Open workflow',icon:ArrowRight,description:'View its run and configuration'},
  {id:'move',label:'Move to folder…',icon:FolderInput,description:'Organize this entry on Home'},
  {id:'unfile',label:'Move to Unfiled',icon:Folder,description:'Remove its Home folder assignment'},
  {id:'copy',label:'Copy YAML path',icon:Copy,description:'Copy the local file location'},
 ]:target?.path?[
  {id:'open',label:'Open folder',icon:Folder,description:target.path},
  {id:'new',label:'New subfolder…',icon:FolderPlus,description:'Create a folder inside this one'},
  {id:'rename',label:'Rename folder…',icon:Pencil,description:'Update this folder and its subfolders'},
  {id:'move',label:'Move folder…',icon:FolderInput,description:'Choose a different parent folder'},
  {id:'remove',label:'Remove folder…',icon:Trash2,description:'Return its workflow entries to Unfiled'},
 ]:[{id:'new',label:'New folder…',icon:FolderPlus,description:'Organize workflow entry points'}];
 async function choose(item){const target=menu.target;setMenu(null);if(item.id==='open'){target.type==='workflow'?onOpen(target.workflow.id):onSelect(target.path);return}if(item.id==='copy'){await act(()=>navigator.clipboard.writeText(target.workflow.path));return}if(item.id==='unfile'){await act(async()=>{await api('library/organize',{action:'move',workflow:target.workflow.id,folder:''});await refresh()});return}start(item.id,target)}
 async function submit(event){event.preventDefault();await act(async()=>{
  const target=edit.target;const parent=target.path?.includes('/')?target.path.slice(0,target.path.lastIndexOf('/')):'';
  if(edit.action==='new'){const path=[value,newName.current?.value.trim()].filter(Boolean).join('/');await api('library/organize',{action:'create',folder:path});await refresh();onSelect(path)}
  else if(edit.action==='rename'){const path=[parent,value.trim()].filter(Boolean).join('/');await api('library/organize',{action:'rename',folder:target.path,new_folder:path});await refresh();if(folder===target.path||folder.startsWith(target.path+'/'))onSelect(path+folder.slice(target.path.length))}
  else if(edit.action==='move'){if(target.type==='workflow'){await api('library/organize',{action:'move',workflow:target.workflow.id,folder:value});await refresh()}else{const path=[value,target.path.split('/').at(-1)].filter(Boolean).join('/');await api('library/organize',{action:'rename',folder:target.path,new_folder:path});await refresh();if(folder===target.path||folder.startsWith(target.path+'/'))onSelect(path+folder.slice(target.path.length))}}
  else if(edit.action==='remove'){await api('library/organize',{action:'remove',folder:target.path});await refresh();if(folder===target.path||folder.startsWith(target.path+'/'))onSelect('')}
  setEdit(null);
 })}
 const newName=useRef(null);const folderOptions=folders.filter(path=>edit?.target.type!=='folder'||edit.action!=='move'||path!==edit.target.path&&!path.startsWith(edit.target.path+'/'));
 const element=<>{menu&&<CardMenu menu={menu} items={items} title={target.type==='workflow'?target.workflow.name:target.path||'Home folders'} onChoose={choose} onClose={()=>setMenu(null)}/>} {edit&&<form ref={formRef} className="library-form organization-form" onSubmit={submit} aria-labelledby="organization-heading"><h3 id="organization-heading">{edit.action==='new'?'New folder':edit.action==='rename'?'Rename folder':edit.action==='remove'?'Remove folder':edit.target.type==='workflow'?'Move workflow entry':'Move folder'}</h3><p>{edit.target.type==='workflow'?edit.target.workflow.name:edit.target.path||'Home folders'}</p>{edit.action==='new'?<div className="form-grid"><label>Folder name<input ref={newName} required maxLength={200} disabled={pending} placeholder="Builds"/></label><label>Parent folder<select value={value} disabled={pending} onChange={e=>setValue(e.target.value)}><option value="">Home</option>{folders.map(path=><option key={path}>{path}</option>)}</select></label></div>:edit.action==='rename'?<label>Folder name<input required maxLength={200} value={value} disabled={pending} onChange={e=>setValue(e.target.value)}/></label>:edit.action==='move'?<label>Destination folder<select value={value} disabled={pending} onChange={e=>setValue(e.target.value)}><option value="">{edit.target.type==='workflow'?'Unfiled':'Home'}</option>{folderOptions.map(path=><option key={path}>{path}</option>)}</select></label>:<p>This removes the folder and its subfolders from Home. Their workflow entries return to Unfiled. YAML files and run evidence stay in place.</p>}<div className="panel-actions"><button type="submit" className={edit.action==='remove'?'danger':'primary'} disabled={pending}>{edit.action==='remove'?'Remove folder':edit.action==='new'?'Create folder':edit.action==='move'?'Move':'Save name'}</button><button type="button" disabled={pending} onClick={()=>setEdit(null)}>Cancel</button></div></form>}</>;
 return {openMenu,keyMenu,contextProps,newFolder:()=>start('new',{type:'folder',path:folder==='*'?'':folder}),element};
}
