import fs from 'node:fs';
import path from 'node:path';
import { build } from 'esbuild';
// Recriar apenas saídas geradas para não publicar assets/migrações removidos.
for(const relative of ['dist/client','dist/server','dist/.openai/drizzle']){
 const target=path.resolve(relative),root=path.resolve('dist');
 if(!target.startsWith(root+path.sep))throw new Error('Invalid build output path');
 fs.rmSync(target,{recursive:true,force:true});
}
fs.mkdirSync('dist/client',{recursive:true});
for(const file of fs.readdirSync('public'))fs.cpSync(path.join('public',file),path.join('dist/client',file),{recursive:true});
await build({entryPoints:['server/worker.mjs'],outfile:'dist/server/index.js',bundle:true,format:'esm',platform:'browser',target:'es2022'});
fs.mkdirSync('dist/.openai',{recursive:true});
fs.copyFileSync('.openai/hosting.json','dist/.openai/hosting.json');
fs.cpSync('drizzle','dist/.openai/drizzle',{recursive:true});
console.log('Peticas: Worker, assets and migrations ready.');
