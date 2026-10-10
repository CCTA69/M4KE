/** Run on the DGX itself. Requires existing installed model, native CAD and built assets. */
import {readFile,access} from 'node:fs/promises';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {resolve} from 'node:path';
import {spawn} from 'node:child_process';
import {validateEndpoint,validateModel} from '../server/studio-inference-config.mjs';

export function offlineConfiguration(saved={},env=process.env){
  const provider=env.M4KE_INFERENCE_PROVIDER||saved.provider||'ollama';
  if(!['ollama','vllm'].includes(provider))throw Error('Choose a local Ollama/vLLM model first; the online bridge cannot run in offline mode.');
  const endpoint=validateEndpoint(env.OLLAMA_URL||saved.endpoint||'');
  const model=validateModel(env.QWEN_MODEL||saved.model||'');
  if(!endpoint||!model)throw Error('Set OLLAMA_URL and QWEN_MODEL to an already installed local model. Nothing is downloaded automatically.');
  return {provider,endpoint,model};
}
if(process.argv[1]&&import.meta.url===pathToFileURL(resolve(process.argv[1])).href){
  const root=fileURLToPath(new URL('../',import.meta.url));
  // Load local configuration before validating, then override any network/bridge flags below.
  try{process.loadEnvFile(resolve(root,'.env'));}catch(e){if(e.code!=='ENOENT')throw e;}
  let saved={};try{saved=JSON.parse(await readFile(resolve(root,'data/settings.json'),'utf8'));}catch(e){if(e.code!=='ENOENT')throw e;}
  const config=offlineConfiguration(saved);await access(resolve(root,'dist/index.html'));
  const child=spawn(process.execPath,[resolve(root,'server/index.mjs')],{cwd:root,stdio:'inherit',env:{...process.env,
    M4KE_OFFLINE_ONLY:'1',M4KE_ALLOW_WEB:'0',HF_HUB_OFFLINE:'1',TRANSFORMERS_OFFLINE:'1',
    M4KE_INFERENCE_PROVIDER:config.provider,OLLAMA_URL:config.endpoint,QWEN_MODEL:config.model}});
  console.log('Offline-only application mode: local model, cached library, no online bridge/web research. Disconnect networking separately for acceptance.');
  for(const signal of ['SIGINT','SIGTERM'])process.on(signal,()=>child.kill(signal));
  child.once('error',e=>{console.error(e.message);process.exitCode=1;});
  child.once('exit',code=>{process.exitCode=code??1;});
}
