import * as THREE from 'three';

/** No-slip rolling on a flat floor: travelled metres / rolling radius metres. */
export function rollingAngle(distanceM,radiusMm,frontSign=1){
  if(!Number.isFinite(distanceM)||!Number.isFinite(radiusMm)||radiusMm<5||radiusMm>100||![1,-1].includes(frontSign))throw Error('Invalid rolling geometry.');
  return frontSign*distanceM/(radiusMm/1000);
}
export const rollingRpm=(speedMps,radiusMm)=>Math.abs(rollingAngle(speedMps,radiusMm))*60/(2*Math.PI);

/** Conservative visual inference, explicitly labelled assumed. Never updates a design. */
export function inferWheelGroups(source){
  const groups=[];
  for(const part of source.children){
    const name=`${part.userData.partId} ${part.userData.partName}`;
    if(!/wheel|tire|轮圈|车轮|轮胎|轮芯/i.test(name)||/flywheel|飞轮|齿轮|支架|mount|bracket/i.test(name))continue;
    const bounds=new THREE.Box3().setFromObject(part),size=bounds.getSize(new THREE.Vector3()),center=bounds.getCenter(new THREE.Vector3());
    // This straight-line sandbox supports Y-axis wheels only. Do not rotate arbitrary parts.
    if(size.x<10||size.x>200||Math.abs(size.x-size.z)>size.x*.06||size.y>size.x*.8)continue;
    let group=groups.find(g=>Math.abs(g.center.x-center.x)<1&&Math.abs(g.center.z-center.z)<1&&Math.sign(g.center.y)===Math.sign(center.y)&&Math.abs(g.center.y-center.y)<Math.max(g.width,size.y)+4);
    if(!group){group={id:part.userData.partId,partIds:[],radiusMm:0,center,width:size.y,driven:/rear|后/i.test(name),assumed:true};groups.push(group);}
    group.partIds.push(part.userData.partId);group.radiusMm=Math.max(group.radiusMm,(size.x+size.z)/4);group.width=Math.max(group.width,size.y);
  }
  return groups;
}

/** Reparent existing wheel meshes around their axle; source vertices are never rewritten. */
export function installWheelRigs(source,descriptors){
  source.updateMatrixWorld(true);
  const parts=new Map(source.children.map(p=>[p.userData.partId,p])),used=new Set();
  const validated=descriptors.map(d=>{
    if(!d.id||!Array.isArray(d.partIds)||!d.partIds.length)throw Error('Wheel needs an ID and part IDs.');
    rollingAngle(0,d.radiusMm);
    const children=d.partIds.map(id=>{if(!parts.has(id)||used.has(id))throw Error(`Missing/duplicate wheel part: ${id}`);used.add(id);return parts.get(id);});
    const bounds=new THREE.Box3();children.forEach(child=>bounds.union(new THREE.Box3().setFromObject(child)));
    const center=bounds.getCenter(new THREE.Vector3()),size=bounds.getSize(new THREE.Vector3());
    if(Math.abs(size.x-size.z)>Math.max(size.x,size.z)*.12||size.y>size.x||Math.abs(d.radiusMm-size.x/2)>d.radiusMm*.12)throw Error(`Wheel envelope/axis mismatch: ${d.id}`);
    return {...d,children,center,width:size.y};
  });
  return validated.map(d=>{
    const pivot=new THREE.Group();pivot.name=`rolling:${d.id}`;pivot.position.copy(d.center);source.add(pivot);pivot.updateMatrixWorld(true);
    d.children.forEach(child=>pivot.attach(child));
    return {...d,pivot};
  });
}
export function setWheelTravel(rigs,distanceM,frontSign=1){
  for(const rig of rigs)rig.pivot.rotation.y=rollingAngle(distanceM,rig.radiusMm,frontSign)%(Math.PI*2);
}
