import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import worker from './worker.mjs';
import { openDB } from './local-db.mjs';
try{process.loadEnvFile('.env')}catch{}
fs.mkdirSync('data',{recursive:true});
const DB=openDB('data/peticas.sqlite');
const root=path.resolve('public');
const ASSETS={async fetch(req){let pathname;try{pathname=decodeURIComponent(new URL(req.url).pathname)}catch{return new Response('Invalid path',{status:400})}const target=path.resolve(root,'.'+(pathname==='/'?'/index.html':pathname));if(!target.startsWith(root+path.sep))return new Response('Forbidden',{status:403});try{const data=fs.readFileSync(target);return new Response(data,{headers:{'Content-Type':({'html':'text/html; charset=utf-8','js':'text/javascript; charset=utf-8','css':'text/css; charset=utf-8','jpg':'image/jpeg'})[target.split('.').pop()]||'application/octet-stream'}})}catch{return new Response('Not found',{status:404})}}};
const port=Number(process.env.PORT||4173);
const server=http.createServer(async(req,res)=>{try{const chunks=[];let size=0;for await(const chunk of req){size+=chunk.length;if(size>65536){res.writeHead(413);res.end('Too large');return}chunks.push(chunk)}const request=new Request('http://127.0.0.1:'+port+req.url,{method:req.method,headers:req.headers,...(!['GET','HEAD'].includes(req.method)?{body:Buffer.concat(chunks)}:{})});const reply=await worker.fetch(request,{DB,ASSETS,ADMIN_SETUP_KEY:process.env.ADMIN_SETUP_KEY});res.writeHead(reply.status,Object.fromEntries(reply.headers));res.end(Buffer.from(await reply.arrayBuffer()));}catch(e){console.error(e);res.writeHead(500);res.end('Server error')}});
server.listen(port,'127.0.0.1',()=>console.log('http://127.0.0.1:'+port));
