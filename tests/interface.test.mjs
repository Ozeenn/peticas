import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

test('Final interface loads in script order and respects navigation permissions',()=>{
 const elements=new Map();
 const element=selector=>{if(!elements.has(selector))elements.set(selector,{innerHTML:'',textContent:'',open:false,scrollTop:0,querySelector:()=>null,querySelectorAll:()=>[],addEventListener(){},insertAdjacentHTML(position,html){this.innerHTML+=html},showModal(){this.open=true},close(){this.open=false}});return elements.get(selector)};
 const context=vm.createContext({console,Date,URL,crypto:globalThis.crypto,structuredClone,encodeURIComponent,setTimeout:()=>0,setInterval:()=>0,clearTimeout(){},location:{hash:'',origin:'https://test.peticas'},history:{replaceState(){}},window:{addEventListener(){},scrollTo(){}},document:{querySelector:element,hidden:false},navigator:{},fetch(){throw new Error('Unexpected network call')}});
 for(const file of ['app.js','management.js','community.js','interview-lookup.js','requirements.js','care-tracking.js'])vm.runInContext(fs.readFileSync('public/'+file,'utf8').replace(/\nboot\(\);\s*$/,''),context,{filename:file});
 const evaluate=source=>vm.runInContext(source,context);
 evaluate("ready=true;account={role:'admin',name:'Cris',permissions:[]};view='overview';render()");assert.doesNotMatch(elements.get('#app').innerHTML,/Abrir estoque|go\('stock'\)/);assert.match(elements.get('.content').innerHTML,/Novos gatos para revisar/);
 evaluate("view='cats';render();editCat(null)");assert.match(elements.get('#modal').innerHTML,/name="rescueLocation"/);assert.match(elements.get('#modal').innerHTML,/name="rescueReport"/);
 evaluate('newVolunteer()');assert.match(elements.get('#modal').innerHTML,/name="cpf"/);assert.match(elements.get('#modal').innerHTML,/Ficha|ficha/);assert.match(elements.get('#modal').innerHTML,/name="permissions"/);
 evaluate("account={role:'staff',name:'Volunteer',permissions:['cats.submit']};view='applications';render()");assert.equal(evaluate('view'),'cats');assert.doesNotMatch(elements.get('#app').innerHTML,/go\('applications'\)|loadTeam\(\)/);
 evaluate("editCat(null)");assert.match(elements.get('#modal').innerHTML,/Enviar para aprovação/);
 evaluate("account={role:'staff',name:'Reader',permissions:['medical.read']};view='health';render()");assert.match(elements.get('.content').innerHTML,/Checklist das medicações/);assert.doesNotMatch(elements.get('#app').innerHTML,/go\('cats'\)/);
 evaluate("view='public';render()");assert.match(elements.get('#app').innerHTML,/não recebe doações de ração/);
 evaluate("account={role:'admin',name:'Cris',permissions:[]};view='settings';render()");assert.match(elements.get('.content').innerHTML,/aguardando configuração/);
});

test('Navigation shows loading immediately, ignores late responses and renders once per hash change',async()=>{
 const listeners={},requests=[],draws=[];
 const element={innerHTML:'',textContent:'',querySelector:()=>null,querySelectorAll:()=>[],addEventListener(){}};
 const context=vm.createContext({console,Date,URL,crypto:globalThis.crypto,structuredClone,encodeURIComponent,setTimeout:()=>0,setInterval:()=>0,clearTimeout(){},location:{hash:'',origin:'https://test.peticas'},history:{replaceState(){}},window:{addEventListener(name,handler){listeners[name]=handler},scrollTo(){}},document:{querySelector:()=>element,hidden:false},navigator:{},fetch(){throw new Error('Unexpected network call')},requests,draws});
 for(const file of ['app.js','management.js','community.js','interview-lookup.js','requirements.js','care-tracking.js'])vm.runInContext(fs.readFileSync('public/'+file,'utf8').replace(/\nboot\(\);\s*$/,''),context,{filename:file});
 const evaluate=source=>vm.runInContext(source,context);
 evaluate("ready=true;account={id:1,role:'admin',name:'Teste',permissions:[]};render=()=>draws.push({view,pendingPage,pageLoadError});api=path=>new Promise((resolve,reject)=>requests.push({path,resolve,reject}))");
 const pendingTeam=evaluate("go('team')");
 assert.equal(requests[0].path,'users');assert.equal(draws[0].view,'team');assert.equal(draws[0].pendingPage,'team');
 context.location.hash='#team';listeners.hashchange();assert.equal(draws.length,1);
 await evaluate("go('cats')");requests[0].resolve({users:[{name:'Late response'}]});await pendingTeam;
 assert.equal(evaluate('view'),'cats');assert.equal(evaluate('team.length'),0);assert.equal(draws.length,2);
 const pendingSettings=evaluate("go('settings')");requests[1].reject(new Error('Offline'));await pendingSettings;
 assert.equal(evaluate('pendingPage'),null);assert.equal(evaluate('pageLoadError'),'Offline');
 context.location.hash='#team';listeners.hashchange();assert.equal(evaluate('view'),'team');assert.equal(evaluate('pendingPage'),'team');
 requests[2].resolve({users:[{name:'Loaded'}]});await new Promise(resolve=>setImmediate(resolve));
 assert.equal(evaluate('team[0].name'),'Loaded');assert.equal(evaluate('pendingPage'),null);
});

test('Complete CPF histories, volunteer summary and mandatory location protect the new workflows',async()=>{
 const requests=[];
 const element={innerHTML:'',textContent:'',isConnected:true,querySelector:()=>null,querySelectorAll:()=>[],addEventListener(){},insertAdjacentHTML(){}};
 const context=vm.createContext({console,Date,URL,crypto:globalThis.crypto,structuredClone,encodeURIComponent,setTimeout:()=>0,setInterval:()=>0,clearTimeout(){},location:{hash:'#tracking',origin:'https://test.peticas'},history:{replaceState(){}},window:{addEventListener(){},scrollTo(){}},document:{querySelector:()=>element,hidden:false},navigator:{},requests,fetch(){throw new Error('Unexpected network call')}});
 for(const file of ['app.js','management.js','community.js','interview-lookup.js','requirements.js','care-tracking.js'])vm.runInContext(fs.readFileSync('public/'+file,'utf8').replace(/\nboot\(\);\s*$/,''),context,{filename:file});
 const evaluate=source=>vm.runInContext(source,context);
 const html=evaluate("candidatureResults([{date:'2026-10-13',stage:2,stageHistory:[{stage:0,date:'2026-10-13T10:00:00Z'},{stage:1,date:'2026-10-13T11:00:00Z'}]},{date:'2026-10-14',stage:0,stageHistory:[]}])");
 assert.match(html,/Candidatura 1/);assert.match(html,/Candidatura 2/);
 for(const label of ['Recebida','Entrevista em análise','Visita domiciliar','Aprovada','Adoção concluída'])assert.match(html,new RegExp(label));
 assert.doesNotMatch(html,/Mensagens da responsável/);
 evaluate("account={role:'staff',name:'Voluntário',permissions:['medical.read','medical.write']}");
 const summary=evaluate('requirementsHealth()');assert.match(summary,/Medicações e vacinas/);assert.doesNotMatch(summary,/Registrar tratamento|Registrar evolução|Encerrar tratamento|Localização dos registros/);
 evaluate("submit=async(e,action)=>action(e.data);api=async(path,method,data)=>requests.push({path,method,data});loadData=async()=>{};closeModal=()=>{};render=()=>{};toast=()=>{};navigator.geolocation={getCurrentPosition(success,error){error({code:1})}};");
 await assert.rejects(evaluate("saveMedical({data:{id:'dose',kind:'application',catId:'1',treatmentId:'tratamento',date:'2026-10-13',time:'08:00'}})"),/localização é obrigatória/);
 assert.equal(requests.length,0);
 evaluate("navigator.geolocation={getCurrentPosition(success,error,options){if(options.maximumAge!==0)throw new Error('Cached location');success({coords:{latitude:-22.88,longitude:-48.44,accuracy:10},timestamp:Date.now()})}}");
 await evaluate("saveMedical({data:{id:'dose',kind:'application',catId:'1',treatmentId:'tratamento',date:'2026-10-13',time:'08:00'}})");
 assert.equal(requests.length,1);assert.equal(requests[0].data.location.latitude,-22.88);assert.equal(requests[0].data.catId,1);
});
