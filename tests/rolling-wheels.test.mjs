import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import {rollingAngle,rollingRpm,inferWheelGroups,installWheelRigs,setWheelTravel} from '../src/simulation/wheels.mjs';
import {DrivingWorld,initializePhysics} from '../src/simulation/world.mjs';

function fixture(){
  const source=new THREE.Group();
  for(const [id,radius,width] of [['rear_tire',21,19],['rear_hub',17,15]]){
    const part=new THREE.Group();part.userData={partId:id,partName:id==='rear_hub'?'轮芯':'轮胎'};
    part.position.set(92,-81.5,21);part.add(new THREE.Mesh(new THREE.CylinderGeometry(radius,radius,width,32),new THREE.MeshBasicMaterial()));source.add(part);
  }
  return source;
}
test('rolling uses travelled metres and each radius, including reversed model front',()=>{
  const circumference=2*Math.PI*.021;
  assert.ok(Math.abs(rollingAngle(circumference,21)-2*Math.PI)<1e-12);
  assert.ok(rollingAngle(circumference,23.4)<2*Math.PI);
  assert.equal(rollingAngle(circumference,21,-1),-rollingAngle(circumference,21));
  assert.equal(rollingRpm(0,21),0);assert.ok(Math.abs(rollingRpm(circumference,21)-60)<1e-9);
  assert.throws(()=>rollingAngle(1,0));
});
test('rim and tyre rotate around a shared fixed axle without editing geometry',()=>{
  const source=fixture(),before=source.children.map(p=>Array.from(p.children[0].geometry.attributes.position.array));
  const rigs=installWheelRigs(source,[{id:'rear',partIds:['rear_tire','rear_hub'],radiusMm:21,driven:true}]);
  const center=rigs[0].pivot.position.clone();setWheelTravel(rigs,.12,-1);source.updateMatrixWorld(true);
  assert.deepEqual(rigs[0].pivot.position.toArray(),center.toArray());
  assert.ok(Math.abs(rigs[0].pivot.rotation.y)>0.1);
  for(let i=0;i<2;i++)assert.deepEqual(Array.from(rigs[0].children[i].children[0].geometry.attributes.position.array),before[i]);
  const stopped=rigs[0].pivot.quaternion.clone();setWheelTravel(rigs,.12,-1);assert.ok(stopped.equals(rigs[0].pivot.quaternion));
  setWheelTravel(rigs,0);assert.equal(rigs[0].pivot.rotation.y,0);
});
test('wheel grouping joins coaxial rim/tyre but rejects flywheels and ambiguous axes',()=>{
  const source=fixture();const fake=new THREE.Group();fake.userData={partId:'flywheel',partName:'flywheel'};fake.add(new THREE.Mesh(new THREE.BoxGeometry(40,40,40)));source.add(fake);
  const groups=inferWheelGroups(source);assert.equal(groups.length,1);assert.equal(groups[0].partIds.length,2);assert.equal(groups[0].assumed,true);
  assert.throws(()=>installWheelRigs(source,[{id:'bad',partIds:['missing'],radiusMm:21}]));
});
test('airborne body receives no motor traction; quiet stops wheel rotation; wall never keeps rolling',async()=>{
  await initializePhysics();const world=new DrivingWorld([286,182,76],{},[{centerZ:-.017,radiusM:.021,driven:true}]);
  try{
    world.body.setTranslation({x:0,y:0,z:1},true);
    for(let i=0;i<20;i++){const r=world.step(80);assert.equal(r.grounded,false);assert.ok(Math.abs(r.speed)<1e-8);}
    let state;for(let i=0;i<2400;i++)state=world.step(80);
    assert.equal(state.collided,true);const angle=rollingAngle(state.x,21);
    for(let i=0;i<240;i++)state=world.step(80);
    assert.ok(Math.abs(rollingAngle(state.x,21)-angle)<.01,'Blocked body cannot accumulate fake wheel turns.');
    world.setObstacle(false);for(let i=0;i<300;i++)state=world.step(80);assert.ok(state.speed>.1);
    for(let i=0;i<300;i++)state=world.step(0);assert.equal(rollingRpm(state.speed,21),0);
  }finally{world.dispose();}
});
