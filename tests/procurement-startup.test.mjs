import test from 'node:test';
import assert from 'node:assert/strict';
import {cp, mkdtemp, rm, writeFile} from 'node:fs/promises';
import {spawn, spawnSync} from 'node:child_process';
import {once} from 'node:events';
import path from 'node:path';
import os from 'node:os';
import {fileURLToPath} from 'node:url';
import {installChinaCarObservations} from '../procurement/install-china-car-observations.mjs';

const source=fileURLToPath(new URL('../',import.meta.url));
async function isolated(t) {
  const root=await mkdtemp(path.join(os.tmpdir(),'m4ke-env-startup-'));
  const children=[];
  t.after(async()=>{
    for(const child of children) if(child.exitCode===null && child.signalCode===null) {
      const done=once(child,'exit');child.kill();await done;
    }
    await rm(root,{recursive:true,force:true,maxRetries:5,retryDelay:100});
  });
  await cp(path.join(source,'node_modules/fflate'),path.join(root,'node_modules/fflate'),{recursive:true});
  for(const folder of ['server','shared','engineering','printing','procurement'])
    await cp(path.join(source,folder),path.join(root,folder),{recursive:true,
      filter:p=>folder==='procurement' ? p===path.join(source,folder)||p.endsWith('.mjs') : !path.extname(p)||p.endsWith('.mjs')});
  const receipt=await installChinaCarObservations({root:path.join(root,'procurement')});
  const env={...process.env};delete env.M4KE_PROCUREMENT_SNAPSHOT_SHA256;
  return {root,receipt,env,children};
}

test('actual server loads snapshot from .env after static imports; HTTP and integrations agree', async t=>{
  const {root,receipt,env,children}=await isolated(t);
  await writeFile(path.join(root,'.env'),`M4KE_PROCUREMENT_SNAPSHOT_SHA256=${receipt.snapshotId}\n`);
  // Import the unmodified production entry point: it owns the .env load.
  await writeFile(path.join(root,'launch.mjs'),`import {createServer} from './server/index.mjs';
    const s=createServer();s.listen(0,'127.0.0.1',()=>console.log('READY '+s.address().port));`);
  const child=spawn(process.execPath,['launch.mjs'],{cwd:root,env,stdio:['ignore','pipe','pipe']});
  children.push(child);
  let output='',errors='';child.stderr.on('data',b=>errors+=b);
  const port=await new Promise((resolve,reject)=>{
    const timer=setTimeout(()=>reject(Error('Startup timeout: '+errors)),10000);
    child.once('error',e=>{clearTimeout(timer);reject(e);});
    child.once('exit',code=>{clearTimeout(timer);reject(Error(`Startup exit ${code}: ${errors}`));});
    child.stdout.on('data',b=>{output+=b;const m=output.match(/READY (\d+)/);if(m){clearTimeout(timer);resolve(Number(m[1]));}});
  });
  const response=await fetch(`http://127.0.0.1:${port}/api/studio/procurement`);
  const data=await response.json();assert.equal(response.status,200,JSON.stringify(data));
  assert.equal(data.snapshotSha256,receipt.snapshotId);assert.equal(data.entries.length,3);
  const integrations=await (await fetch(`http://127.0.0.1:${port}/api/studio/integrations`)).json();
  assert.equal(integrations.capabilities.cachedPartSearch.snapshotSha256,receipt.snapshotId);
  assert.equal(integrations.capabilities.cachedPartSearch.entries,3);
});

test('standalone MCP loads the same .env pin for search and quote',async t=>{
  const {root,receipt,env}=await isolated(t);
  await writeFile(path.join(root,'.env'),`M4KE_PROCUREMENT_SNAPSHOT_SHA256=${receipt.snapshotId}\n`);
  const input=[{jsonrpc:'2.0',id:1,method:'tools/call',params:{name:'search_cached_parts',arguments:{query:'1063'}}},
    {jsonrpc:'2.0',id:2,method:'tools/call',params:{name:'quote_cached_part',arguments:{entryId:'digikey-cn-adafruit-1063',quantity:1}}}];
  const child=spawnSync(process.execPath,['server/studio-integrations.mjs','--stdio'],{cwd:root,env,encoding:'utf8',timeout:10000,input:input.map(x=>JSON.stringify(x)).join('\n')+'\n'});
  assert.equal(child.status,0,child.stderr);
  const results=child.stdout.trim().split('\n').map(x=>JSON.parse(JSON.parse(x).result.content[0].text));
  assert.equal(results[0].snapshotSha256,receipt.snapshotId);assert.equal(results[0].entries.length,1);
  assert.equal(results[1].status,'UNQUOTABLE');assert.equal(results[1].subtotal,null);
});

test('runtime pins remain fixed after environment changes; missing and invalid pins fail closed',async t=>{
  const {root,receipt,env}=await isolated(t);
  await writeFile(path.join(root,'.env'),`M4KE_PROCUREMENT_SNAPSHOT_SHA256=${receipt.snapshotId}\n`);
  const code=`import assert from 'node:assert/strict';
    import {createIntegrationRuntime} from './server/studio-integrations.mjs';
    import {createProcurementService,resolveProcurementSnapshot,PROCUREMENT_SNAPSHOT} from './server/studio-procurement.mjs';
    process.loadEnvFile('.env');
    const expected=process.env.M4KE_PROCUREMENT_SNAPSHOT_SHA256;
    const r=createIntegrationRuntime({root:process.cwd()});let response;
    const http=createProcurementService({root:process.cwd(),json:(_r,status,data)=>response={status,data}});
    process.env.M4KE_PROCUREMENT_SNAPSHOT_SHA256='a'.repeat(64);
    const search=await r.call('search_cached_parts',{query:'1063'});
    assert.equal(search.snapshotSha256,expected);assert.equal(search.entries.length,1);
    assert.equal((await r.call('quote_cached_part',{entryId:search.entries[0].id,quantity:1})).status,'UNQUOTABLE');
    await http({method:'GET'},{},'/api/studio/procurement');assert.equal(response.status,200);assert.equal(response.data.snapshotSha256,expected);
    const missing=await createIntegrationRuntime({root:process.cwd()}).call('search_cached_parts',{});
    assert.equal(missing.snapshotSha256,'a'.repeat(64));assert.deepEqual(missing.entries,[]);
    process.env.M4KE_PROCUREMENT_SNAPSHOT_SHA256='invalid';
    assert.throws(()=>createProcurementService({root:process.cwd(),json(){}}),/SHA256/);
    assert.throws(()=>createIntegrationRuntime({root:process.cwd()}),/SHA256/);
    process.env.M4KE_PROCUREMENT_SNAPSHOT_SHA256='';assert.equal(resolveProcurementSnapshot(),PROCUREMENT_SNAPSHOT);`;
  await writeFile(path.join(root,'freeze-test.mjs'),code);
  const child=spawnSync(process.execPath,['freeze-test.mjs'],{cwd:root,env,encoding:'utf8',timeout:10000});
  assert.equal(child.status,0,child.stderr);
  // An explicit process setting wins over .env, following Node's loadEnvFile policy.
  const override=spawnSync(process.execPath,['server/studio-integrations.mjs','--stdio'],{cwd:root,
    env:{...env,M4KE_PROCUREMENT_SNAPSHOT_SHA256:'b'.repeat(64)},encoding:'utf8',timeout:10000,
    input:JSON.stringify({jsonrpc:'2.0',id:1,method:'tools/call',params:{name:'search_cached_parts',arguments:{}}})+'\n'});
  assert.equal(override.status,0,override.stderr);
  const result=JSON.parse(JSON.parse(override.stdout.trim()).result.content[0].text);
  assert.equal(result.snapshotSha256,'b'.repeat(64));assert.deepEqual(result.entries,[]);
});
