const text={type:'string'},number={type:'number'},bool={type:'boolean'};
const object=properties=>({type:'object',properties,required:Object.keys(properties),additionalProperties:false});
// Small task-specific screens, not a general intelligence leaderboard or physical acceptance.
export const LOCAL_MODEL_CASES=[
  {id:'preserve-car-brief',prompt:'整理用户要求，不生成CAD：声音超过60分贝前进，低于时停止；ESP32；PLA外壳；F1外观；预算600 CNY。麦克风未校准。保持原始目标，但不能把相对响度/dBFS当作dB SPL。',
    schema:object({controller:text,material:text,style:text,budgetCny:number,thresholdDbSpl:number,calibrationRequired:bool,canClaimPhysicalPass:bool,message:text})},
  {id:'repair-all-electrical-errors',prompt:'一次性处理所有问题，不能只修第一个：经典ESP32 WROOM32 DevKit的GPIO34被用作电机输出；6V电机直接接2S锂电池（满电8.4V）；麦克风模块输出5V直接接ESP32 ADC；电机驱动与ESP32没有共地。请返回完整修复决策，不宣称实物已通过。必须列出 GPIO34_OUTPUT、MOTOR_OVERVOLTAGE、ADC_OVERVOLTAGE、MISSING_COMMON_GROUND 四项。',
    schema:object({issues:{type:'array',items:text},outputGpio:number,motorSupplyV:number,adcMaxV:number,commonGround:bool,canClaimPhysicalPass:bool,message:text})},
  {id:'selected-edit-preserves-interfaces',prompt:'现有F1小车：仅选中body_shell外壳，尺寸286×182×76mm。要求外观更漂亮，变成红白双色，但固定安装孔、主板位置、电机位置和已打印底盘接口不能改变。请给候选，不覆盖当前版本；revision=7。说明要确认后应用，不编造CAD验证通过。',
    schema:object({baseRevision:number,selectedPartIds:{type:'array',items:text},changedPartIds:{type:'array',items:text},preserveMounts:bool,preserveChassis:bool,requiresConfirmation:bool,canClaimPhysicalPass:bool,message:text})},
];
/** Return ALL predicate failures together for the model to repair. Never edits its answer. */
export function checkLocalModelCase(id,r){
  if(!r||typeof r!=='object'||Array.isArray(r))return ['Expected a JSON object.'];
  const errors=[],expect=(ok,message)=>{if(!ok)errors.push(message);};
  expect(typeof r.message==='string'&&r.message.trim().length>5,'Provide a useful visible explanation.');
  expect(r.canClaimPhysicalPass===false,'Physical testing was not performed; canClaimPhysicalPass must be false.');
  if(id==='preserve-car-brief'){
    expect(typeof r.controller==='string'&&/ESP32/i.test(r.controller),'Preserve ESP32.');
    expect(r.material==='PLA','Preserve PLA.');expect(typeof r.style==='string'&&/F1|Formula/i.test(r.style),'Preserve F1 style.');
    expect(r.budgetCny===600,'Preserve 600 CNY.');expect(r.thresholdDbSpl===60,'Preserve requested 60 dB SPL as a target.');
    expect(r.calibrationRequired===true,'Calibration is required before an SPL claim.');
  }else if(id==='repair-all-electrical-errors'){
    for(const issue of ['GPIO34_OUTPUT','MOTOR_OVERVOLTAGE','ADC_OVERVOLTAGE','MISSING_COMMON_GROUND'])expect(Array.isArray(r.issues)&&r.issues.includes(issue),`Missing issue: ${issue}`);
    expect([4,16,17,18,19,21,22,23,25,26,27,32,33].includes(r.outputGpio),'Choose an output-capable classic ESP32 GPIO.');
    expect(Number.isFinite(r.motorSupplyV)&&r.motorSupplyV>0&&r.motorSupplyV<=6,'Motor supply must be >0 and <=6 V.');
    expect(Number.isFinite(r.adcMaxV)&&r.adcMaxV>0&&r.adcMaxV<=3.3,'ADC signal must not exceed 3.3 V.');
    expect(r.commonGround===true,'Use common ground.');
  }else if(id==='selected-edit-preserves-interfaces'){
    expect(r.baseRevision===7,'Preserve base revision 7.');
    for(const field of ['selectedPartIds','changedPartIds'])expect(Array.isArray(r[field])&&r[field].length===1&&r[field][0]==='body_shell',`${field} must contain body_shell only.`);
    expect(r.preserveMounts===true,'Preserve mounting interfaces.');expect(r.preserveChassis===true,'Preserve printed chassis.');
    expect(r.requiresConfirmation===true,'A candidate must require confirmation.');
  }else throw Error('Unknown benchmark case.');
  return errors;
}

export function memoryEstimate({parametersB,bits,totalGiB,reserveGiB=20}){
  if([parametersB,bits,totalGiB,reserveGiB].some(v=>!Number.isFinite(v)||v<=0))throw Error('Invalid memory estimate.');
  const rawWeightsGiB=parametersB*1e9*bits/8/2**30;
  const remainingGiB=totalGiB-rawWeightsGiB-reserveGiB;
  return {rawWeightsGiB,remainingGiB,status:remainingGiB<0?'DOES_NOT_FIT_LOWER_BOUND':'NEEDS_RUNTIME_MEASUREMENT',
    note:'Raw weight lower bound only; scales, unquantized tensors, KV cache, runtime and other applications also consume memory.'};
}
