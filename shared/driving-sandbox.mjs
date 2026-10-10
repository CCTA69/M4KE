/** Flat-floor preview only. Never writes design geometry or verification evidence. */
export const DEFAULT_DRIVE = Object.freeze({massKg:0.9,wheelDiameterMm:42,rpm:400,
  motorVoltage:6,supplyVoltage:5.5,duty:0.45,stallTorqueNm:0.02,
  motors:2,rollingResistance:0.03,traction:0.6,brakeDeceleration:1.2,threshold:60,hysteresis:5});
const ranges={massKg:[0.05,10],wheelDiameterMm:[10,200],rpm:[1,3000],motorVoltage:[1,24],
  supplyVoltage:[0,24],duty:[0,1],stallTorqueNm:[0.0001,2],motors:[1,4],
  rollingResistance:[0,0.2],traction:[0,1.5],brakeDeceleration:[0.05,10],threshold:[5,95],hysteresis:[0,20]};
export function driveParameters(overrides={}) {
  const p={...DEFAULT_DRIVE,...overrides};
  for(const [key,value] of Object.entries(p)) {
    const range=ranges[key];
    if(!range||!Number.isFinite(value)||value<range[0]||value>range[1])throw Error(`Invalid simulation parameter: ${key}`);
  }
  if(p.supplyVoltage>p.motorVoltage)throw Error('Simulation supply exceeds the motor rating.');
  if(!Number.isInteger(p.motors))throw Error('Motor count must be an integer.');
  return p;
}
export function soundGate(level,wasOn,p) {
  if(!Number.isFinite(level)||level<0||level>100)throw Error('Relative sound level must be 0–100, not dB SPL.');
  return wasOn ? level>p.threshold-p.hysteresis : level>p.threshold;
}
export function driveStep(speed,level,wasOn,parameters,dt) {
  const p=driveParameters(parameters);
  if(!Number.isFinite(dt)||dt<=0||dt>0.05||!Number.isFinite(speed)||speed<0)throw Error('Invalid fixed simulation step.');
  const on=soundGate(level,wasOn,p),radius=p.wheelDiameterMm/2000;
  const noLoadSpeed=p.rpm*p.supplyVoltage/p.motorVoltage*p.duty*2*Math.PI*radius/60;
  const torque=p.stallTorqueNm*p.supplyVoltage/p.motorVoltage*p.duty;
  const driveForce=on&&noLoadSpeed>0 ? p.motors*torque/radius*Math.max(0,1-speed/noLoadSpeed) : 0;
  const tractionLimit=p.traction*p.massKg*9.81;
  const rollingForce=p.massKg*9.81*p.rollingResistance;
  const acceleration=on?(Math.min(driveForce,tractionLimit)-rollingForce)/p.massKg : -p.brakeDeceleration;
  const nextSpeed=Math.max(0,Math.min(noLoadSpeed, speed+acceleration*dt));
  return {on,speed:nextSpeed,noLoadSpeed,driveForce,rollingForce,tractionLimited:driveForce>tractionLimit};
}
