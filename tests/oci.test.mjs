import test from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {resolve} from 'node:path';

test('OCI publishes only HTTPS ingress and trusts only its private reverse proxy',()=>{
 const config=JSON.parse(execFileSync('docker',['compose','--env-file','deploy/oci/.env.example','-f','deploy/oci/compose.yaml','config','--format','json'],{
  encoding:'utf8',env:{...process.env,SITE_HOST:'peticas.example.test',ACME_EMAIL:'ops@example.test',POSTGRES_PASSWORD:'examplepasswordonly',ADMIN_SETUP_KEY:'examplekeyonly',WHATSAPP_WEBHOOK_URL:'',WHATSAPP_WEBHOOK_TOKEN:''}
 }));
 for(const name of ['db','api','jobs'])assert.equal(config.services[name].ports,undefined,`${name} must not publish ports`);
 assert.deepEqual(config.services.proxy.ports.map(p=>Number(p.published)).sort((a,b)=>a-b),[80,443]);
 assert.equal(config.services.api.environment.SEED_DEMO,'false');
 const command=config.services.api.command;
 assert.ok(command.includes('--proxy-headers'));
 assert.equal(command[command.indexOf('--forwarded-allow-ips')+1],config.services.proxy.networks.proxy.ipv4_address);
 assert.notEqual(config.services.api.networks.proxy.ipv4_address,config.services.proxy.networks.proxy.ipv4_address);
 assert.equal(resolve(config.services.api.build.context),resolve('.'));
 assert.equal(config.services.db.volumes[0].type,'volume');
 assert.ok(config.services.proxy.volumes.some(v=>v.type==='volume'&&v.target==='/data'));
});
