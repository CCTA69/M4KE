import test from 'node:test';import assert from 'node:assert/strict';
import {checkLocalModelCase,memoryEstimate} from '../shared/local-model-cases.mjs';
test('reports all failures in one batch instead of patching them automatically',()=>{
  const errors=checkLocalModelCase('repair-all-electrical-errors',{});
  assert.equal(errors.length,10);
  for(const id of ['GPIO34_OUTPUT','MOTOR_OVERVOLTAGE','ADC_OVERVOLTAGE','MISSING_COMMON_GROUND'])assert.ok(errors.some(e=>e.includes(id)));
});
test('accepts complete electrical decisions without pretending a physical test',()=>{
  const answer={issues:['GPIO34_OUTPUT','MOTOR_OVERVOLTAGE','ADC_OVERVOLTAGE','MISSING_COMMON_GROUND'],outputGpio:25,motorSupplyV:5.5,adcMaxV:3.3,commonGround:true,canClaimPhysicalPass:false,message:'全部四项分别修复，仍然需要实物检查。'};
  const original=JSON.stringify(answer);assert.deepEqual(checkLocalModelCase('repair-all-electrical-errors',answer),[]);assert.equal(JSON.stringify(answer),original);
});
test('rejects selected-edit revision drift and unrelated modifications',()=>{
  const answer={baseRevision:8,selectedPartIds:['body_shell'],changedPartIds:['body_shell','chassis'],preserveMounts:true,preserveChassis:true,requiresConfirmation:true,canClaimPhysicalPass:false,message:'Only a candidate, not yet applied.'};
  assert.equal(checkLocalModelCase('selected-edit-preserves-interfaces',answer).length,2);
});
test('122B FP16 exceeds 128 GiB; quantized fit remains unverified',()=>{
  assert.equal(memoryEstimate({parametersB:122,bits:16,totalGiB:128}).status,'DOES_NOT_FIT_LOWER_BOUND');
  assert.equal(memoryEstimate({parametersB:122,bits:4,totalGiB:128}).status,'NEEDS_RUNTIME_MEASUREMENT');
  assert.throws(()=>memoryEstimate({parametersB:122,bits:0,totalGiB:128}));
});
