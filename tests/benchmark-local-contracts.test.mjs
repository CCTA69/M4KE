import test from 'node:test';import assert from 'node:assert/strict';
import http from 'node:http';import {mkdtemp,readFile,rm} from 'node:fs/promises';import {tmpdir} from 'node:os';import {join} from 'node:path';
import {screenLocalModels} from '../scripts/benchmark-local-contracts.mjs';
test('isolated benchmark gives every issue to the model and keeps the failed first attempt',async()=>{
  const requests=[],dir=await mkdtemp(join(tmpdir(),'m4ke-contract-screen-'));
  const answers=[{},
    {controller:'ESP32',material:'PLA',style:'F1',budgetCny:600,thresholdDbSpl:60,calibrationRequired:true,canClaimPhysicalPass:false,message:'保留原始要求，必须校准麦克风。'},
    null,
    {issues:['GPIO34_OUTPUT','MOTOR_OVERVOLTAGE','ADC_OVERVOLTAGE','MISSING_COMMON_GROUND'],outputGpio:25,motorSupplyV:5.5,adcMaxV:3.3,commonGround:true,canClaimPhysicalPass:false,message:'所有问题都必须修复，尚未进行实物验证。'},
    {baseRevision:7,selectedPartIds:['body_shell'],changedPartIds:['body_shell'],preserveMounts:true,preserveChassis:true,requiresConfirmation:true,canClaimPhysicalPass:false,message:'红白色外壳候选，需要确认后才能应用。'}];
  const server=http.createServer(async(req,res)=>{
    res.setHeader('Content-Type','application/json');
    if(req.url==='/api/studio/projects')return res.end(JSON.stringify({projects:[]}));
    if(req.url==='/api/tags')return res.end(JSON.stringify({models:[{name:'fixture',digest:'test-only'}]}));
    if(req.url==='/api/chat'){let body='';for await(const chunk of req)body+=chunk;requests.push(JSON.parse(body));return res.end(JSON.stringify({model:'fixture',done:true,done_reason:'stop',message:{content:JSON.stringify(answers.shift())}}));}
    res.statusCode=404;res.end('{}');
  });await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const url=`http://127.0.0.1:${server.address().port}`;
  try{
    const report=await screenLocalModels({provider:'ollama',endpoint:url,studio:url,models:['fixture'],out:dir});
    assert.equal(report.status,'COMPLETE');assert.deepEqual(report.rows.map(r=>r.status),['SCREEN_FAIL','SCREEN_PASS','SCREEN_FAIL','SCREEN_PASS','SCREEN_PASS']);
    const feedback=JSON.parse(requests[1].messages.at(-1).content);
    assert.equal(feedback.allProblems.length,report.rows[0].problems.length);assert.ok(feedback.allProblems.length>5);
    assert.equal(JSON.parse(await readFile(join(dir,'report.json'),'utf8')).rows.length,5);
    assert.equal(requests.length,5);assert.deepEqual(report.rows[2].problems,['Expected a JSON object.']);
  }finally{await new Promise(resolve=>server.close(resolve));await rm(dir,{recursive:true,force:true});}
});
test('busy production prevents even model discovery',async()=>{
  let calls=0;const server=http.createServer((req,res)=>{calls++;res.setHeader('Content-Type','application/json');res.end(JSON.stringify({projects:[{workflow:{status:'running'}}]}));});
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));const url=`http://127.0.0.1:${server.address().port}`;
  try{await assert.rejects(screenLocalModels({provider:'ollama',endpoint:url,studio:url,models:['fixture'],out:'unused'}),/busy/);assert.equal(calls,1);}
  finally{await new Promise(resolve=>server.close(resolve));}
});
