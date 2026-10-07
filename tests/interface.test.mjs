import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

test('Final interface loads in script order and respects navigation permissions',()=>{
 const elements=new Map();
 const element=selector=>{if(!elements.has(selector))elements.set(selector,{innerHTML:'',textContent:'',open:false,scrollTop:0,querySelector:()=>null,querySelectorAll:()=>[],addEventListener(){},insertAdjacentHTML(position,html){this.innerHTML+=html},showModal(){this.open=true},close(){this.open=false}});return elements.get(selector)};
 const context=vm.createContext({console,Date,URL,crypto:globalThis.crypto,structuredClone,encodeURIComponent,setTimeout:()=>0,setInterval:()=>0,clearTimeout(){},location:{hash:'',origin:'https://test.peticas'},history:{replaceState(){}},window:{addEventListener(){},scrollTo(){}},document:{querySelector:element,hidden:false},navigator:{},fetch(){throw new Error('Unexpected network call')}});
 for(const file of ['app.js','management.js','community.js','interview-lookup.js','requirements.js'])vm.runInContext(fs.readFileSync('public/'+file,'utf8').replace(/\nboot\(\);\s*$/,''),context,{filename:file});
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
