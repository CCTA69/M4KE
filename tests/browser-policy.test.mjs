import test from 'node:test';
import assert from 'node:assert/strict';
import {once} from 'node:events';
import {BROWSER_CSP} from '../server/browser-policy.mjs';
import {createServer} from '../server/index.mjs';

test('production server permits local WASM without JavaScript eval or remote scripts',async()=>{
  const server=createServer();server.listen(0,'127.0.0.1');await once(server,'listening');
  try{
    const response=await fetch(`http://127.0.0.1:${server.address().port}/api/health`);
    assert.equal(response.headers.get('content-security-policy'),BROWSER_CSP);
    assert.equal(BROWSER_CSP.split(';').find(s=>s.trim().startsWith('script-src')).trim(),"script-src 'self' 'wasm-unsafe-eval'");
    assert(!BROWSER_CSP.includes("'unsafe-eval'"));
    await response.json();
  }finally{server.closeAllConnections();await new Promise(resolve=>server.close(resolve));}
});
