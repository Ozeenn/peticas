import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { openDB } from '../server/local-db.mjs';
import { dispatchMessages, queueMessage } from '../server/workflows.mjs';

test('Gateway contract protects the queue from simulated or mismatched receipts and unsafe HTTP', async()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'peticas-gateway-')),DB=openDB(path.join(dir,'db.sqlite'));
 const env={DB,WHATSAPP_WEBHOOK_URL:'http://127.0.0.1:8001/messages',WHATSAPP_WEBHOOK_TOKEN:'test-token',WHATSAPP_OWNER_TARGET:'owner'};
 const originalFetch=globalThis.fetch;let requests=0;
 try{
  await queueMessage(env,'gateway:test','owner','Aviso de teste');
  globalThis.fetch=async(url,opts)=>{
   requests++;assert.equal(opts.headers.Authorization,'Bearer test-token');
   assert.equal(opts.headers['Idempotency-Key'],'gateway:test');
   assert.deepEqual(JSON.parse(opts.body),{id:'gateway:test',target:'owner',text:'Aviso de teste'});
   return new Response(JSON.stringify({id:'gateway:test',accepted:false,simulated:true}));
  };
  await dispatchMessages(env);assert.equal(requests,0);
  env.LOCAL_FILE_STORAGE=true;await dispatchMessages(env);assert.equal(requests,1);
  let job=await DB.prepare('SELECT * FROM message_jobs').first();assert.equal(job.sent,null);assert.equal(job.attempts,1);
  for(const receipt of [{id:'other',accepted:true,simulated:false},{id:'gateway:test',accepted:true,simulated:true},{}]){
   DB.prepare('UPDATE message_jobs SET next_attempt=0').run();
   globalThis.fetch=async()=>new Response(JSON.stringify(receipt));await dispatchMessages(env);
   assert.equal((await DB.prepare('SELECT * FROM message_jobs').first()).sent,null);
  }
  DB.prepare('UPDATE message_jobs SET next_attempt=0').run();
  globalThis.fetch=async()=>new Response(JSON.stringify({id:'gateway:test',accepted:true,simulated:false}));
  env.WHATSAPP_WEBHOOK_URL='http://gateway.example/messages';await dispatchMessages(env);
  assert.equal((await DB.prepare('SELECT * FROM message_jobs').first()).sent,null);
  env.WHATSAPP_WEBHOOK_URL='not a URL';await dispatchMessages(env);
  env.WHATSAPP_WEBHOOK_URL='https://gateway.example/messages';await dispatchMessages(env);
  job=await DB.prepare('SELECT * FROM message_jobs').first();assert.ok(job.sent);assert.equal(job.last_error,null);
 }finally{globalThis.fetch=originalFetch;DB.close();fs.rmSync(dir,{recursive:true,force:true});}
});
