import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { DatabaseSync } from 'node:sqlite';
import { openDB } from '../server/local-db.mjs';
import worker from '../server/worker.mjs';
import { medicationSchedule, dispatchMessages, queueMessage, weeklyReport } from '../server/workflows.mjs';

test('Meeting workflows preserve history and enforce individual permissions',async()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'peticas-workflows-')),db=openDB(path.join(dir,'db.sqlite')),env={DB:db,ADMIN_SETUP_KEY:'private-test-setup'};
 const call=async(route,method='GET',data,cookie='')=>{const r=await worker.fetch(new Request('https://test.peticas/api/'+route,{method,headers:{Origin:'https://test.peticas','Content-Type':'application/json',Cookie:cookie},...(data?{body:JSON.stringify(data)}:{})}),env);return {status:r.status,data:await r.json(),cookie:r.headers.get('set-cookie')?.split(';')[0]}};
 try{
 const admin=await call('register','POST',{name:'Cris',email:'owner@test.example',password:'Password-example-123',setupKey:env.ADMIN_SETUP_KEY});assert.equal(admin.status,200);const cookie=admin.cookie;
 const profile={name:'Volunteer',cpf:'11144477735',age:'30',address:'Test address',phone:'14999999999',signature:'Volunteer',rules:'Sim',commitment:'Sim',email:'volunteer@test.example',permissions:['cats.submit','cats.photos','cats.status']};
 const created=await call('users','POST',profile,cookie);assert.equal(created.status,201);
 let user=(await call('users','GET',null,cookie)).data.users.find(u=>u.id===created.data.id);assert.equal(user.role,'pending');
 assert.equal((await call('users/'+user.id,'PATCH',{role:'staff'},cookie)).status,400);
 assert.equal((await call('users/'+user.id,'PATCH',{role:'staff',password:'Password-example-123'},cookie)).status,200);
 let staff=await call('login','POST',{email:profile.email,password:'Password-example-123'});assert.equal(staff.status,200);assert.equal((await call('medical','GET',null,staff.cookie)).status,403);
 const cat={name:'Rescued cat',age:'2 anos',sex:'Fêmea',personality:'Tranquila',color:'Cinza',entryDate:'2026-10-07',rescueLocation:'Test location',rescuer:'Volunteer',rescueReport:'Rescue report',status:'Disponível',story:'Public story'};
 assert.equal((await call('cat-register','POST',cat,staff.cookie)).status,403);
 assert.equal((await call('cat-submissions','POST',cat,staff.cookie)).status,201);
 assert.equal((await call('cats')).data.cats.some(c=>c.name===cat.name),false);
 const submission=(await call('cat-submissions','GET',null,cookie)).data.submissions[0];assert.equal((await call('cat-submissions/'+submission.id,'PATCH',{status:'approved',version:submission.version},staff.cookie)).status,403);
 assert.equal((await call('cat-submissions/'+submission.id,'PATCH',{status:'approved',version:submission.version},cookie)).status,200);
 assert.equal((await call('cat-submissions/'+submission.id,'PATCH',{status:'approved',version:submission.version},cookie)).status,409);
 const publicCat=(await call('cats')).data.cats.find(c=>c.name===cat.name);assert.ok(publicCat);assert.equal(publicCat.rescuer,undefined);assert.equal(publicCat.rescueLocation,undefined);
 let state=(await call('state','GET',null,cookie)).data;
 assert.equal((await call('cats/'+publicCat.id,'PATCH',{status:'Reservado',version:state.version},staff.cookie)).status,400);
 assert.equal((await call('cats/'+publicCat.id,'PATCH',{status:'Em tratamento',version:state.version},staff.cookie)).status,200);
 state=(await call('state','GET',null,cookie)).data;
 assert.equal((await call('cats/'+publicCat.id,'PATCH',{...cat,status:'Disponível',version:state.version},cookie)).status,200);
 const answers={name:'Adopter',cpf:'52998224725',age:'30',phone:'14999999999',address:'Test address',security:'Screens',email:'adopter@test.example'};
 const adoption=await call('adoptions','POST',{cat:publicCat.id,answers});assert.equal(adoption.status,201);const rid=adoption.data.request.id;
 assert.equal((await call('attachments','POST',{ownerType:'video',ownerId:rid,name:'video.mp4',mime:'video/mp4',data:btoa('0000ftyp0000'),token:'wrong'})).status,403);
 const file=await call('attachments','POST',{ownerType:'video',ownerId:rid,name:'video.mp4',mime:'video/mp4',data:btoa('0000ftyp0000'),token:adoption.data.token});assert.equal(file.status,201);
 assert.equal((await call('attachments?adoptionId='+rid)).status,403);
 assert.equal((await call('attachments?adoptionId='+rid+'&token='+adoption.data.token)).data.files.length,1);
 const storedObjects=new Map();env.BUCKET={async put(key,bytes){storedObjects.set(key,bytes)},async get(key){return storedObjects.has(key)?{body:storedObjects.get(key)}:null},async delete(key){storedObjects.delete(key)}};
 const term=await call('attachments','POST',{ownerType:'term',ownerId:rid,name:'term.pdf',mime:'application/pdf',data:btoa('%PDF-example')},cookie);assert.equal(term.status,201);assert.equal(storedObjects.size,1);
 const termResponse=await worker.fetch(new Request('https://test.peticas/api/attachments/'+term.data.id+'?token='+adoption.data.token),env);assert.equal(termResponse.status,200);assert.equal(await termResponse.text(),'%PDF-example');
 assert.equal((await worker.fetch(new Request('https://test.peticas/api/attachments/'+term.data.id),env)).status,403);
 assert.equal((await call('adoption-records','POST',{adoptionId:rid,token:adoption.data.token})).status,403);
 for(let stage=1;stage<=4;stage++)assert.equal((await call('adoptions/'+rid,'PATCH',{stage,cat:publicCat.id,version:stage},cookie)).status,200);
 assert.equal((await call('adoptions/'+rid,'PATCH',{stage:-1,cat:publicCat.id,version:5,rejectionReason:'Incorrect'},cookie)).status,400);
 assert.equal((await call('adoptions/'+rid+'/history','POST',{kind:'followup',date:'2026-10-07',notes:'Adaptation going well',version:5},cookie)).status,200);
 assert.equal((await call('adoptions/'+rid+'/history','POST',{kind:'return',date:'2026-10-07',notes:'Family could not keep the cat',version:6},cookie)).status,200);
 assert.equal((await call('adoptions/'+rid+'/history','POST',{kind:'return',date:'2026-10-07',notes:'Duplicate',version:7},cookie)).status,409);
 const saved=(await call('state','GET',null,cookie)).data.applications.find(a=>a.id===rid);assert.equal(saved.stage,4);assert.equal(saved.history.length,2);assert.equal(saved.returned,true);assert.ok((await call('cats')).data.cats.some(c=>c.id===publicCat.id));
 const rejected=await call('adoptions','POST',{cat:null,answers});
 assert.equal((await call('adoptions/'+rejected.data.request.id,'PATCH',{stage:-1,cat:null,version:1},cookie)).status,400);
 assert.equal((await call('adoptions/'+rejected.data.request.id,'PATCH',{stage:-1,cat:null,version:1,rejectionReason:'Unprotected windows'},cookie)).status,200);
 assert.equal((await call('project-settings','PUT',{pix:'test@example.test',campaigns:[{label:'Unsafe',url:'javascript:alert(1)'}]},cookie)).status,400);
 assert.equal((await call('project-settings','PUT',{pix:'test@example.test',campaigns:[{label:'Campaign',url:'https://example.test/campaign'}]},cookie)).status,200);
 assert.equal((await call('project-settings')).data.settings.pix,'test@example.test');
 assert.equal((await call('messages','GET',null,cookie)).data.jobs.length,2);
 // Revoking permissions invalidates active sessions and prevents writes after login.
 assert.equal((await call('users/'+user.id+'/permissions','PUT',{permissions:[]},cookie)).status,200);
 assert.equal((await call('cat-submissions','POST',cat,staff.cookie)).status,401);
 staff=await call('login','POST',{email:profile.email,password:'Password-example-123'});assert.equal((await call('cat-submissions','POST',cat,staff.cookie)).status,403);
 assert.deepEqual((await call('state','GET',null,staff.cookie)).data.vaccines,[]);
 const treatment={id:crypto.randomUUID(),kind:'treatment',catId:publicCat.id,date:'2026-10-09',time:'08:00',endDate:'2026-10-11',intervalHours:12,label:'Prescription example',dose:'Prescribed dose',frequency:'12 em 12 horas',prescriber:'Test veterinarian'};
 assert.equal((await call('medical','POST',treatment,cookie)).status,201);
 const schedule=(await call('medication-schedule?start=2026-10-10&end=2026-10-11','GET',null,cookie)).data.schedule;assert.equal(schedule.length,4);
 const dose={id:crypto.randomUUID(),kind:'application',catId:publicCat.id,treatmentId:treatment.id,date:'2026-10-10',time:'08:10',scheduledAt:schedule[0].scheduledAt};
 assert.equal((await call('medical','POST',dose,cookie)).status,201);assert.equal((await call('medical','POST',{...dose,id:crypto.randomUUID()},cookie)).status,409);
 assert.equal((await call('medication-schedule?start=2026-10-10&end=2026-10-11','GET',null,cookie)).data.schedule[0].applied,true);
 // A missing gateway retains jobs; a successful gateway receives no applicant personal data.
 await dispatchMessages(env);assert.equal((await call('messages','GET',null,cookie)).data.jobs.filter(j=>j.sent).length,0);
 const originalFetch=globalThis.fetch,requests=[];globalThis.fetch=async(url,opts)=>{requests.push(JSON.parse(opts.body));return new Response('{}',{status:200})};
 try{await dispatchMessages({...env,WHATSAPP_WEBHOOK_URL:'https://gateway.example.test/send',WHATSAPP_WEBHOOK_TOKEN:'private-token',WHATSAPP_OWNER_TARGET:'owner'});await dispatchMessages({...env,WHATSAPP_WEBHOOK_URL:'https://gateway.example.test/send',WHATSAPP_WEBHOOK_TOKEN:'private-token',WHATSAPP_OWNER_TARGET:'owner'});}finally{globalThis.fetch=originalFetch;}
 assert.equal(requests.length,2);assert.ok(requests.every(r=>!r.text.includes(answers.cpf)&&!r.text.includes(answers.email)));
 }finally{db.close();fs.rmSync(dir,{recursive:true,force:true});}
});

test('Medication schedule excludes completed treatments and respects dates and intervals',()=>{
 const treatment={id:'t',kind:'treatment',cat_id:1,data:{date:'2026-10-09',time:'20:00',intervalHours:8,endDate:'2026-10-11',label:'Example',dose:'Prescribed'}};
 assert.equal(medicationSchedule([treatment],'2026-10-10','2026-10-11').length,6);
 const completion={kind:'completion',treatment_id:'t',data:{date:'2026-10-10',time:'12:00'}};
 assert.equal(medicationSchedule([treatment,completion],'2026-10-10','2026-10-11').length,1);
 assert.equal(medicationSchedule([{...treatment,data:{...treatment.data,intervalHours:undefined}}],'2026-10-10','2026-10-11').length,0);
});

test('Weekly reports are queued once and failed deliveries remain retryable',async()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'peticas-messages-')),db=openDB(path.join(dir,'db.sqlite'));
 const env={DB:db,WHATSAPP_WEBHOOK_URL:'https://gateway.example.test',WHATSAPP_WEBHOOK_TOKEN:'test-token',WHATSAPP_VOLUNTEERS_TARGET:'volunteers'};
 const originalNow=Date.now,originalFetch=globalThis.fetch;
 try{
  Date.now=()=>Date.parse('2026-10-09T15:00:00Z');
  db.prepare("INSERT INTO settings(key,value,version) VALUES('gatil',?,1)").bind(JSON.stringify({cats:[]})).run();
  await weeklyReport(env);await weeklyReport(env);
  const jobs=(await db.prepare('SELECT * FROM message_jobs').all()).results;assert.equal(jobs.length,1);assert.equal(jobs[0].id,'weekend:2026-10-10');
  let requests=0;globalThis.fetch=async()=>{requests++;return new Response('Unavailable',{status:503})};
  await dispatchMessages(env);await dispatchMessages(env);assert.equal(requests,1);
  let job=await db.prepare('SELECT * FROM message_jobs').first();assert.equal(job.attempts,1);assert.equal(job.sent,null);assert.equal(job.last_error,'HTTP 503');
  db.prepare('UPDATE message_jobs SET next_attempt=0').run();globalThis.fetch=async()=>new Response('{}',{status:200});
  await dispatchMessages(env);job=await db.prepare('SELECT * FROM message_jobs').first();assert.ok(job.sent);assert.equal(job.last_error,null);
 }finally{Date.now=originalNow;globalThis.fetch=originalFetch;db.close();fs.rmSync(dir,{recursive:true,force:true});}
});

test('Deployment repair upgrades existing attachment tables without deleting records',()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'peticas-upgrade-')),file=path.join(dir,'db.sqlite');let db=new DatabaseSync(file);
 try{
  db.exec('CREATE TABLE _local_migrations(name TEXT PRIMARY KEY)');
  for(const name of ['0000_nervous_squirrel_girl.sql','0001_broken_tenebrous.sql','0002_loving_cyclops.sql']){db.exec(fs.readFileSync('drizzle/'+name,'utf8'));db.prepare('INSERT INTO _local_migrations VALUES(?)').run(name);}
  db.exec(fs.readFileSync('docs/migrations-aplicadas/0003_meeting_workflows.sql','utf8'));
  db.prepare('INSERT INTO attachments VALUES(?,?,?,?,?,?,?)').run('existing','video','existing-adoption','existing.mp4','video/mp4','existing-file',1);
  db.prepare('INSERT INTO message_jobs(id,target,message,created) VALUES(?,?,?,?)').run('existing-message','owner','Existing queued message',1);
  db.close();db=null;const upgraded=openDB(file);
  try{assert.equal(upgraded.prepare('SELECT name FROM attachments WHERE id=?').bind('existing').first().name,'existing.mp4');assert.equal(upgraded.prepare('SELECT message FROM message_jobs WHERE id=?').bind('existing-message').first().message,'Existing queued message');assert.ok(upgraded.prepare('PRAGMA table_info(medical_records)').all().results.some(c=>c.name==='scheduled_at'));}finally{upgraded.close();}
 }finally{if(db)db.close();fs.rmSync(dir,{recursive:true,force:true});}
});
