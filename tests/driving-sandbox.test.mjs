import test from 'node:test';
import assert from 'node:assert/strict';
import {DEFAULT_DRIVE,driveParameters,driveStep,soundGate} from '../shared/driving-sandbox.mjs';
import {DrivingWorld,initializePhysics} from '../src/simulation/world.mjs';
test('relative sound threshold has hysteresis; never calibrated SPL',()=>{
  assert.equal(soundGate(60,false,DEFAULT_DRIVE),false);
  assert.equal(soundGate(61,false,DEFAULT_DRIVE),true);
  assert.equal(soundGate(56,true,DEFAULT_DRIVE),true);
  assert.equal(soundGate(55,true,DEFAULT_DRIVE),false);
});
test('bounded parameters and units reject nonphysical input',()=>{
  assert.throws(()=>driveParameters({massKg:0}));assert.throws(()=>driveParameters({supplyVoltage:9}));
  assert.throws(()=>driveParameters({rpm:NaN}));assert.throws(()=>driveParameters({motors:1.5}));
  assert.throws(()=>driveStep(0,70,false,DEFAULT_DRIVE,2));
});
test('drive speed stays below voltage/PWM-adjusted no-load bound and quiet brakes',()=>{
  let r={speed:0,on:false};for(let i=0;i<1200;i++)r=driveStep(r.speed,80,r.on,DEFAULT_DRIVE,1/120);
  assert.ok(r.speed>0.1&&r.speed<r.noLoadSpeed);
  for(let i=0;i<240;i++)r=driveStep(r.speed,0,r.on,DEFAULT_DRIVE,1/120);
  assert.equal(r.speed,0);assert.equal(r.on,false);
  assert.equal(driveStep(0,80,false,{...DEFAULT_DRIVE,duty:0},1/120).speed,0);
});
test('Rapier wall blocks the vehicle; reset/free do not mutate parameters',async()=>{
  await initializePhysics();const original=JSON.stringify(DEFAULT_DRIVE);
  const world=new DrivingWorld([286,182,76]);let state;
  try{
    for(let i=0;i<2000;i++)state=world.step(80);
    assert.ok(state.x>2&&state.x<2.80);assert.equal(state.collided,true);
    world.setObstacle(false);for(let i=0;i<360;i++)state=world.step(80);
    assert.ok(state.x>3);for(let i=0;i<300;i++)state=world.step(0);
    assert.ok(state.speed<0.001);assert.equal(JSON.stringify(DEFAULT_DRIVE),original);
  }finally{world.dispose();}
  assert.throws(()=>world.step(80));
});
