import { first, rows, run, statement } from './db.mjs';

export const permissionNames=['cats.submit','cats.photos','cats.status','medical.read','medical.write','adoptions.lookup'];
export async function permissions(env,user){
 if(user.role==='admin')return permissionNames;
 const stored=await first(env,'SELECT value FROM settings WHERE key=?','permissions:'+user.id);
 return stored?JSON.parse(stored.value):['medical.read','medical.write','adoptions.lookup'];
}
export async function queueMessage(env,key,target,message){
 await run(env,'INSERT OR IGNORE INTO message_jobs(id,target,message,created) VALUES(?,?,?,?)',key,target,message,Date.now());
}
export async function dispatchMessages(env){
 if(!env.WHATSAPP_WEBHOOK_URL||!env.WHATSAPP_WEBHOOK_TOKEN)return;
 let endpoint;try{endpoint=new URL(env.WHATSAPP_WEBHOOK_URL)}catch{return;}
 const localGateway=env.LOCAL_FILE_STORAGE===true&&endpoint.protocol==='http:'&&['127.0.0.1','localhost','[::1]'].includes(endpoint.hostname);
 if(endpoint.protocol!=='https:'&&!localGateway)return;
 if(endpoint.username||endpoint.password)return;
 for(const job of await rows(env,'SELECT * FROM message_jobs WHERE sent IS NULL AND attempts<10 AND next_attempt<=? ORDER BY created LIMIT 20',Date.now())){
  const target=job.target==='owner'?env.WHATSAPP_OWNER_TARGET:env.WHATSAPP_VOLUNTEERS_TARGET;if(!target)continue;
  const claimed=await run(env,'UPDATE message_jobs SET next_attempt=? WHERE id=? AND sent IS NULL AND next_attempt=?',Date.now()+120000,job.id,job.next_attempt);if(!claimed.meta.changes)continue;
  try{
   const reply=await fetch(endpoint,{method:'POST',redirect:'error',headers:{'Content-Type':'application/json',Authorization:'Bearer '+env.WHATSAPP_WEBHOOK_TOKEN,'Idempotency-Key':job.id},body:JSON.stringify({id:job.id,target,text:job.message}),signal:AbortSignal.timeout(15000)});
   if(!reply.ok)throw new Error('HTTP '+reply.status);
   const receipt=await reply.json();
   if(receipt.id!==job.id||receipt.accepted!==true||receipt.simulated!==false)throw new Error('Gateway não confirmou a aceitação real da mensagem.');
   await run(env,'UPDATE message_jobs SET sent=?,last_error=NULL WHERE id=?',Date.now(),job.id);
  }catch(e){await run(env,'UPDATE message_jobs SET attempts=attempts+1,next_attempt=?,last_error=? WHERE id=?',Date.now()+Math.min(3600000,60000*2**job.attempts),String(e.message).slice(0,200),job.id);}
 }
}
const datePattern=/^\d{4}-\d{2}-\d{2}$/;
export function medicationSchedule(records,start,end){
 const out=[];
 for(const t of records.filter(r=>r.kind==='treatment')){
  const d=t.data,interval=Number(d.intervalHours);
  if(!interval||!d.time||!datePattern.test(d.date))continue;
  const completion=records.find(r=>r.kind==='completion'&&r.treatment_id===t.id);
  const finish=Math.min(Date.parse(end+'T23:59:59-03:00'),d.endDate?Date.parse(d.endDate+'T23:59:59-03:00'):Infinity,completion?Date.parse(completion.data.date+'T'+(completion.data.time||'00:00')+':00-03:00')-1:Infinity);
  const origin=Date.parse(d.date+'T'+d.time+':00-03:00'),begin=Date.parse(start+'T00:00:00-03:00'),step=interval*3600000;
  for(let time=origin+Math.max(0,Math.ceil((begin-origin)/step))*step;time<=finish&&out.length<5000;time+=step){
   const local=new Date(time-3*3600000).toISOString(),date=local.slice(0,10),clock=local.slice(11,16);
   const applied=records.find(r=>r.kind==='application'&&r.treatment_id===t.id&&r.data.scheduledAt===new Date(time).toISOString());
   out.push({treatmentId:t.id,catId:t.cat_id,label:d.label,dose:d.dose,date,time:clock,scheduledAt:new Date(time).toISOString(),applied:!!applied,responsible:applied?.responsible||''});
  }
 }
 return out.sort((a,b)=>a.scheduledAt.localeCompare(b.scheduledAt));
}
export async function weeklyReport(env){
 const local=new Date(Date.now()-3*3600000),day=local.getUTCDay();
 if(day!==5)return;
 const start=new Date(local.getTime()+86400000).toISOString().slice(0,10),end=new Date(local.getTime()+2*86400000).toISOString().slice(0,10);
 const records=(await rows(env,'SELECT m.*,u.name AS responsible FROM medical_records m JOIN users u ON u.id=m.user_id')).map(r=>({...r,data:JSON.parse(r.data)}));
 const state=await first(env,"SELECT value FROM settings WHERE key='gatil'");if(!state)return;
 const cats=JSON.parse(state.value).cats;
 const schedule=medicationSchedule(records,start,end);
 const unscheduled=records.filter(r=>r.kind==='treatment'&&!r.data.intervalHours&&!records.some(c=>c.kind==='completion'&&c.treatment_id===r.id));
 const message='Medicações do fim de semana '+start+' a '+end+'\n'+(schedule.map(s=>`${s.applied?'[x]':'[ ]'} ${s.date} ${s.time} · ${cats.find(c=>c.id===s.catId)?.name||s.catId} · ${s.label} · ${s.dose}`).join('\n')||'Nenhuma dose programada.')+(unscheduled.length?'\nAtenção: '+unscheduled.length+' tratamento(s) sem intervalo estruturado. Conferir a prescrição no sistema.':'');
 await queueMessage(env,'weekend:'+start,'volunteers',message);
}

export async function workflowRoutes(req,env,ctx){
 const {path,method,user,body,json,fail,text,id,getState,requireAdmin,hash}=ctx;
 const allow=async p=>{if(!(await permissions(env,user)).includes(p))fail(403,'Sua conta não tem permissão para esta ação.');};
 const saveSetting=async(key,value)=>run(env,'INSERT INTO settings(key,value,version) VALUES(?,?,1) ON CONFLICT(key) DO UPDATE SET value=excluded.value,version=version+1',key,JSON.stringify(value));
 const editState=async(s)=>{const r=await run(env,"UPDATE settings SET value=?,version=version+1 WHERE key='gatil' AND version=?",JSON.stringify({cats:s.cats,vaccines:s.vaccines,meds:s.meds}),s.version);if(!r.meta.changes)fail(409,'Os registros mudaram. Recarregue e tente novamente.');};
 if(path==='/api/project-settings'){
  if(method==='GET'){const r=await first(env,"SELECT value FROM settings WHERE key='project-settings'");return json({settings:r?JSON.parse(r.value):{pix:'',campaigns:[]}});}
  requireAdmin(user);if(method==='PUT'){const b=await body(req);const pix=text(b.pix||'',200,false);if(!Array.isArray(b.campaigns)||b.campaigns.length>10)fail(400,'Campanhas inválidas.');const campaigns=b.campaigns.map(c=>{let url;try{url=new URL(text(c.url,1000));}catch{fail(400,'Confira o link da campanha.');}if(url.protocol!=='https:')fail(400,'Use links HTTPS.');return {label:text(c.label,100),url:url.href}});await saveSetting('project-settings',{pix,campaigns});return json({ok:true});}
 }
 if(path.match(/^\/api\/users\/[^/]+\/permissions$/)){
  requireAdmin(user);const uid=path.split('/')[3];const target=await first(env,'SELECT * FROM users WHERE id=?',uid);if(!target||target.role==='admin')fail(400,'Voluntário inválido.');
  if(method==='GET')return json({permissions:await permissions(env,target)});
  if(method==='PUT'){const b=await body(req);if(!Array.isArray(b.permissions)||b.permissions.some(p=>!permissionNames.includes(p)))fail(400,'Permissões inválidas.');await saveSetting('permissions:'+uid,[...new Set(b.permissions)]);await run(env,'DELETE FROM sessions WHERE user_id=?',uid);return json({ok:true});}
 }
 if(path==='/api/cat-submissions'){
  if(method==='GET'){const data=await rows(env,"SELECT key,value,version FROM settings WHERE key LIKE 'cat-submission:%'");return json({submissions:data.map(r=>({...JSON.parse(r.value),version:r.version})).filter(r=>user.role==='admin'||r.userId===user.id)});}
  if(method==='POST'){await allow('cats.submit');const b=await body(req);if(!['Disponível','Em tratamento'].includes(b.status))fail(400,'Novos gatos devem estar disponíveis ou em tratamento.');const cat=validateCat(b,text,fail);const submission={id:id(),cat,userId:user.id,status:'pending',created:Date.now()};await saveSetting('cat-submission:'+submission.id,submission);return json({ok:true},201);}
 }
 if(path.match(/^\/api\/cat-submissions\/[^/]+$/)&&method==='PATCH'){
  requireAdmin(user);const b=await body(req),key='cat-submission:'+path.split('/').pop(),row=await first(env,'SELECT * FROM settings WHERE key=?',key);if(!row)fail(404,'Cadastro não encontrado.');const submission=JSON.parse(row.value);if(submission.status!=='pending')fail(409,'Cadastro já revisado.');if(!['approved','rejected'].includes(b.status))fail(400,'Decisão inválida.');submission.status=b.status;submission.reason=text(b.reason||'',2000,b.status==='rejected');submission.reviewedBy=user.id;submission.reviewedAt=Date.now();
  const s=await getState(env);if(b.status==='approved')s.cats.push({...submission.cat,id:Math.max(0,...s.cats.map(c=>c.id))+1,approvedBy:user.id});
  const result=await env.DB.batch([statement(env,"UPDATE settings SET value=?,version=version+1 WHERE key='gatil' AND version=? AND EXISTS(SELECT 1 FROM settings WHERE key=? AND version=?)",JSON.stringify({cats:s.cats,vaccines:s.vaccines,meds:s.meds}),s.version,key,b.version),statement(env,'UPDATE settings SET value=?,version=version+1 WHERE key=? AND version=? AND changes()=1',JSON.stringify(submission),key,b.version)]);if(!result[0].meta.changes)fail(409,'O cadastro mudou. Recarregue.');return json({ok:true});
 }
 if(path==='/api/cat-register'&&method==='POST'){requireAdmin(user);const b=await body(req);if(!['Disponível','Em tratamento'].includes(b.status))fail(400,'Novos gatos devem estar disponíveis ou em tratamento.');const cat=validateCat(b,text,fail),s=await getState(env);s.cats.push({...cat,id:Math.max(0,...s.cats.map(c=>c.id))+1,approvedBy:user.id});await editState(s);return json({ok:true},201);}
 if(path.match(/^\/api\/cats\/\d+$/)&&method==='PATCH'){
  const b=await body(req),s=await getState(env),cat=s.cats.find(c=>c.id===Number(path.split('/').pop()));if(!cat)fail(404,'Gato não encontrado.');if(b.version!==s.version)fail(409,'Cadastro alterado. Recarregue.');
  if(user.role==='admin'){const next=validateCat({...cat,...b},text,fail);if(cat.status==='Adotado'&&next.status!=='Adotado')fail(400,'Registre a devolução pela adoção.');Object.assign(cat,next);}
  else{await allow('cats.status');if(!['Disponível','Em tratamento'].includes(cat.status)||!['Disponível','Em tratamento'].includes(b.status))fail(400,'Reserva, adoção e devolução dependem da responsável.');cat.status=b.status;}
  await editState(s);return json({ok:true});
 }
 if(path.match(/^\/api\/adoptions\/[^/]+\/history$/)){
  requireAdmin(user);const rid=path.split('/')[3],r=await first(env,'SELECT * FROM adoption_requests WHERE id=?',rid);if(!r)fail(404,'Adoção não encontrada.');const a=JSON.parse(r.data);
  if(method==='POST'){const b=await body(req);if(a.stage!==4)fail(400,'Disponível após concluir a adoção.');if(!['followup','return','term'].includes(b.kind))fail(400,'Registro inválido.');if(b.kind==='return'&&a.returned)fail(409,'Devolução já registrada.');const event={id:id(),kind:b.kind,date:text(b.date,10),notes:text(b.notes,3000),userId:user.id,created:Date.now()};if(!datePattern.test(event.date)||Number.isNaN(Date.parse(event.date)))fail(400,'Data inválida.');a.history=[...(a.history||[]),event];
   const s=await getState(env);if(b.kind==='return'){const c=s.cats.find(c=>c.id===a.cat);if(!c)fail(404,'Gato não encontrado.');if(c.status!=='Adotado')fail(409,'A situação do gato mudou.');c.status='Disponível';a.returned=true;}
   const result=await env.DB.batch([statement(env,"UPDATE settings SET value=?,version=version+1 WHERE key='gatil' AND version=? AND EXISTS(SELECT 1 FROM adoption_requests WHERE id=? AND version=?)",JSON.stringify({cats:s.cats,vaccines:s.vaccines,meds:s.meds}),s.version,rid,b.version),statement(env,'UPDATE adoption_requests SET data=?,version=version+1 WHERE id=? AND version=? AND changes()=1',JSON.stringify(a),rid,b.version)]);if(!result[0].meta.changes)fail(409,'A adoção mudou. Reabra o registro.');return json({ok:true});
  }
 }
 if(path==='/api/medication-schedule'&&method==='GET'){
  await allow('medical.read');const url=new URL(req.url),start=url.searchParams.get('start'),end=url.searchParams.get('end');if(!datePattern.test(start||'')||!datePattern.test(end||'')||!(Date.parse(end)>=Date.parse(start))||Date.parse(end)-Date.parse(start)>7*86400000)fail(400,'Escolha um período de até 7 dias.');
  const records=(await rows(env,'SELECT m.*,u.name AS responsible FROM medical_records m JOIN users u ON u.id=m.user_id ORDER BY m.created DESC')).map(r=>({...r,data:JSON.parse(r.data)}));return json({schedule:medicationSchedule(records,start,end),unscheduled:records.filter(r=>r.kind==='treatment'&&!r.data.intervalHours&&!records.some(c=>c.kind==='completion'&&c.treatment_id===r.id)).length});
 }
 if(path==='/api/messages'&&method==='GET'){requireAdmin(user);return json({configured:!!(env.WHATSAPP_WEBHOOK_URL&&env.WHATSAPP_WEBHOOK_TOKEN&&env.WHATSAPP_OWNER_TARGET&&env.WHATSAPP_VOLUNTEERS_TARGET),jobs:await rows(env,'SELECT id,target,created,sent,attempts,last_error FROM message_jobs ORDER BY created DESC LIMIT 50')});}
 return null;
}
function validateCat(b,text,fail){
 const c={};for(const [key,max] of [['name',100],['age',50],['sex',20],['personality',200],['story',3000],['color',100],['entryDate',10],['rescueLocation',300],['rescuer',200],['rescueReport',3000]])c[key]=text(b[key]||'',max,['name','age','sex','personality','color','entryDate','rescueLocation','rescuer','rescueReport'].includes(key));
 if(!datePattern.test(c.entryDate)||Number.isNaN(Date.parse(c.entryDate)))fail(400,'Data de entrada inválida.');if(!['Fêmea','Macho'].includes(c.sex)||!['Disponível','Em tratamento','Reservado','Adotado'].includes(b.status))fail(400,'Situação ou sexo inválido.');c.status=b.status;c.tags=[c.personality];c.photo=0;return c;
}
