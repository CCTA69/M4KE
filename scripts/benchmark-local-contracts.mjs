/** Isolated model replies, not production projects. No settings writes or downloads. */
import {mkdir,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
import {validateEndpoint,validateModel} from '../server/studio-inference-config.mjs';
import {vllmFetch} from '../server/studio-vllm.mjs';
import {LOCAL_MODEL_CASES,checkLocalModelCase} from '../shared/local-model-cases.mjs';

export async function boundedJson(url,options={}){
  const response=await fetch(url,{...options,redirect:'error'});
  if(!response.ok){await response.body?.cancel();throw Error(`Local service HTTP ${response.status}`);}
  let size=0,text='';const decoder=new TextDecoder();
  for await(const chunk of response.body){size+=chunk.byteLength;if(size>4*1024*1024)throw Error('Response exceeds 4 MiB.');text+=decoder.decode(chunk,{stream:true});}
  return JSON.parse(text+decoder.decode());
}
export async function assertIdle(studio){
  const value=await boundedJson(studio+'/api/studio/projects',{signal:AbortSignal.timeout(5000)});
  if(!Array.isArray(value.projects))throw Error('Cannot establish studio idle state.');
  if(value.projects.some(p=>['running','queued','cancelling'].includes(p.workflow?.status)))throw Error('Studio is busy; benchmark yielded without changing the running job.');
}
export async function screenLocalModels({provider,endpoint,studio,models,out,attempts=2,repeat=1,thinking=false}){
  endpoint=validateEndpoint(endpoint);studio=validateEndpoint(studio);
  if(!endpoint||!studio||!['ollama','vllm'].includes(provider))throw Error('Exact local Ollama/vLLM endpoints required; no online bridge.');
  if(!models.length||models.length>4||models.some(m=>!validateModel(m)))throw Error('Choose 1–4 exact installed model IDs.');
  if(!Number.isInteger(attempts)||attempts<1||attempts>3||!Number.isInteger(repeat)||repeat<1||repeat>5)throw Error('Attempts 1–3; repeat 1–5.');
  if(typeof thinking!=='boolean')throw Error('Thinking must be explicitly true or false.');
  await assertIdle(studio);
  const inventory=provider==='ollama'?await boundedJson(endpoint+'/api/tags',{signal:AbortSignal.timeout(5000)}):await vllmFetch(endpoint,'/api/tags');
  const report={schemaVersion:1,provider,startedAt:new Date().toISOString(),status:'RUNNING',scope:'Task-specific JSON/repair screen; not native CAD, full workflow, firmware or physical acceptance.',
    settings:{attempts,repeat,thinking,temperature:0.2,context:32768,maxOutputTokens:3072},models:models.map(id=>({id,digest:inventory.models?.find(m=>m.name===id)?.digest||null})),rows:[]};
  await mkdir(out,{recursive:true});const persist=()=>writeFile(resolve(out,'report.json'),JSON.stringify(report,null,2)+'\n');await persist();
  try{
    for(const model of models){
      if(!inventory.models?.some(m=>m.name===model)){report.rows.push({model,status:'NOT_INSTALLED'});await persist();continue;}
      for(let run=1;run<=repeat;run++)for(const task of LOCAL_MODEL_CASES){
        let feedback=null;
        const messages=[{role:'system',content:'Answer using the required JSON schema. Preserve every user constraint. Tool checks are facts; explanations cannot prove a physical outcome. Never execute code.'},{role:'user',content:task.prompt}];
        for(let attempt=1;attempt<=attempts;attempt++){
          await assertIdle(studio);
          if(feedback)messages.push({role:'user',content:JSON.stringify({instruction:'Repair ALL listed problems in one complete JSON response. Do not change the original requirements.',allProblems:feedback})});
          const started=performance.now(),row={model,caseId:task.id,run,attempt,status:'RUNNING',promptSha256:createHash('sha256').update(JSON.stringify(messages)).digest('hex')};
          report.rows.push(row);await persist();
          try{
            const body=JSON.stringify({model,messages,stream:false,think:thinking,format:task.schema,keep_alive:'2m',options:{temperature:0.2,seed:run,num_ctx:32768,num_predict:3072}});
            const result=provider==='vllm'?await vllmFetch(endpoint,'/api/chat',{body},180000):await boundedJson(endpoint+'/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body,signal:AbortSignal.timeout(180000)});
            if(result.error||result.model!==model||result.done!==true||!['stop',undefined].includes(result.done_reason))throw Error('Wrong model, failed, incomplete or truncated completion.');
            const content=result.message?.content;if(typeof content!=='string'||!content.trim())throw Error('No visible answer.');
            await writeFile(resolve(out,`reply-${report.rows.length}.json`),JSON.stringify({model,caseId:task.id,run,attempt,content},null,2));
            try{feedback=checkLocalModelCase(task.id,JSON.parse(content));}
            catch{feedback=['Return one complete JSON object, without markdown or surrounding prose.'];}
            row.problems=feedback;row.status=feedback.length?'SCREEN_FAIL':'SCREEN_PASS';row.elapsedMs=Math.round(performance.now()-started);
            row.outputTokens=result.eval_count??null;row.decodeTokensPerSecond=result.eval_duration?result.eval_count/(result.eval_duration/1e9):null;
            row.firstContentMs=result.inferenceMetrics?.firstContentMs??null;
            row.responseSha256=createHash('sha256').update(content).digest('hex');
            messages.push({role:'assistant',content});await persist();console.log(JSON.stringify(row));
            if(!feedback.length)break;
          }catch(e){row.status='ERROR';row.error=e.message;row.elapsedMs=Math.round(performance.now()-started);await persist();console.log(JSON.stringify(row));break;}
        }
      }
    }
    report.status='COMPLETE';
  }catch(e){report.status='STOPPED';report.reason=e.message;}
  report.finishedAt=new Date().toISOString();await persist();return report;
}
if(process.argv[1]&&import.meta.url===pathToFileURL(resolve(process.argv[1])).href){
  const args=Object.fromEntries(process.argv.slice(2).map(s=>{const i=s.indexOf('=');return [s.slice(0,i),s.slice(i+1)];}));
  if(process.env.M4KE_BENCH_COORDINATED!=='1')throw Error('Coordinate GPU use, then set M4KE_BENCH_COORDINATED=1.');
  const provider=args['--provider']||'ollama';
  const report=await screenLocalModels({provider,endpoint:args['--endpoint']||(provider==='ollama'?'http://127.0.0.1:11434':'http://127.0.0.1:8000'),
    studio:args['--studio']||'http://127.0.0.1:4173',models:(args['--models']||'').split(',').filter(Boolean),
    out:resolve(args['--output']||`test-results/local-contracts-${Date.now()}`),repeat:Number(args['--repeat']||1),attempts:Number(args['--attempts']||2),thinking:args['--thinking']==='true'});
  process.exitCode=report.status==='COMPLETE'&&report.rows.length>0&&report.rows.every(row=>row.status==='SCREEN_PASS'||row.status==='SCREEN_FAIL')&&report.models.every(m=>LOCAL_MODEL_CASES.every(t=>Array.from({length:report.settings.repeat},(_,i)=>i+1).every(run=>report.rows.some(r=>r.model===m.id&&r.caseId===t.id&&r.run===run&&r.status==='SCREEN_PASS'))))?0:1;
}
