import test from 'node:test';import assert from 'node:assert/strict';
import {offlineConfiguration} from '../scripts/start-offline.mjs';
import {validateProvider} from '../server/studio-inference-config.mjs';
test('offline startup requires local model and never selects a cloud bridge',()=>{
  assert.throws(()=>offlineConfiguration({},{}));
  assert.throws(()=>offlineConfiguration({provider:'codex-bridge',endpoint:'http://127.0.0.1:4181',model:'demo'},{}));
  assert.throws(()=>offlineConfiguration({provider:'ollama',endpoint:'https://example.com',model:'local'},{}));
  assert.deepEqual(offlineConfiguration({provider:'ollama',endpoint:'http://127.0.0.1:11434',model:'installed-model'},{}),{provider:'ollama',endpoint:'http://127.0.0.1:11434',model:'installed-model'});
});
test('offline server rejects attempts to switch back to bridge',()=>{
  const before=process.env.M4KE_OFFLINE_ONLY;process.env.M4KE_OFFLINE_ONLY='1';
  try{assert.equal(validateProvider('vllm'),'vllm');assert.throws(()=>validateProvider('codex-bridge'),/Offline-only/);}
  finally{if(before===undefined)delete process.env.M4KE_OFFLINE_ONLY;else process.env.M4KE_OFFLINE_ONLY=before;}
});
