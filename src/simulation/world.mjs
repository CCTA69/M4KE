import RAPIER from '@dimforge/rapier3d-compat';
import {driveParameters,driveStep} from '../../shared/driving-sandbox.mjs';

let initialization;
export const initializePhysics=()=>initialization??=RAPIER.init();
export const FIXED_STEP=1/120;
/** Metres/seconds internally. A bounding-box collider, NOT exact CAD contact analysis. */
export class DrivingWorld {
  constructor(dimensionsMm,parameters={},wheels=[]) {
    if(!Array.isArray(dimensionsMm)||dimensionsMm.length!==3||dimensionsMm.some(n=>!Number.isFinite(n)||n<=0||n>2000))throw Error('Invalid vehicle envelope.');
    this.size=dimensionsMm.map(n=>n/1000);
    this.parameters=driveParameters(parameters);
    this.wheels=wheels.map(w=>{
      if(!Number.isFinite(w.centerZ)||!Number.isFinite(w.radiusM)||w.radiusM<=0)throw Error('Invalid wheel contact geometry.');
      return {...w};
    });
    this.world=new RAPIER.World({x:0,y:0,z:-9.81});
    this.world.timestep=FIXED_STEP;
    this.world.createCollider(RAPIER.ColliderDesc.cuboid(15,2,0.01).setTranslation(10,0,-0.01).setFriction(0));
    this.obstacle=this.world.createCollider(RAPIER.ColliderDesc.cuboid(0.06,0.6,0.12).setTranslation(3,0,0.12).setFriction(0));
    this.body=this.world.createRigidBody(RAPIER.RigidBodyDesc.dynamic()
      .setTranslation(0,0,this.size[2]/2+0.002).lockRotations().enabledTranslations(true,false,true).setCcdEnabled(true));
    this.world.createCollider(RAPIER.ColliderDesc.cuboid(...this.size.map(n=>n/2)).setMass(this.parameters.massKg).setFriction(0).setRestitution(0),this.body);
    this.elapsed=0;this.on=false;this.collided=false;this.obstacleEnabled=true;this.travelLimit=false;
  }
  setObstacle(enabled){this.obstacleEnabled=Boolean(enabled);this.obstacle.setEnabled(this.obstacleEnabled);}
  step(level) {
    if(!this.world)throw Error('Simulation has been disposed.');
    const before=this.body.translation().x;
    if(before>=20)this.travelLimit=true;
    const z=this.body.translation().z;
    const contacts=this.wheels.filter(w=>z+w.centerZ-w.radiusM<=0.003);
    const driven=this.wheels.filter(w=>w.driven),driveContacts=contacts.filter(w=>w.driven);
    const grounded=this.wheels.length ? contacts.length>0 : z-this.size[2]/2<=0.003;
    const canDrive=grounded&&(!driven.length||driveContacts.length===driven.length);
    const vx=this.body.linvel().x;
    const command=driveStep(Math.max(0,vx),this.travelLimit||!canDrive?0:level,this.on,this.parameters,FIXED_STEP);
    this.on=command.on;
    // Apply the bounded drive/brake impulse through the rigid body. No traction in mid-air.
    if(grounded)this.body.applyImpulse({x:(command.speed-vx)*this.parameters.massKg,y:0,z:0},true);
    this.world.step();this.elapsed+=FIXED_STEP;
    const position=this.body.translation(),speed=Math.max(0,this.body.linvel().x);
    this.collided=this.obstacleEnabled&&position.x+this.size[0]/2>=2.935&&speed<0.02;
    return {...command,speed,x:position.x,z:position.z,time:this.elapsed,collided:this.collided,travelLimit:this.travelLimit,grounded,wheelContacts:contacts.length};
  }
  dispose(){this.world?.free();this.world=null;}
}
