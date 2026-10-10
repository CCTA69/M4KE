import test from 'node:test';
import assert from 'node:assert/strict';
import {withDisplayRoutes} from '../src/viewport/display-routes.mjs';
import {hasWireRoute} from '../src/viewport/interaction.mjs';

function fixture() {
  const parts = ['a', 'b'].map(id => ({id, position:[0,0,0], rotation:[0,0,0]}));
  const cad = parts.map(p => ({id:p.id, sha256:{stl:'a'.repeat(64), step:'b'.repeat(64)}}));
  const connections = [{id:'W1',from:{partId:'a',terminal:'OUT'},to:{partId:'b',terminal:'IN'},
    kind:'signal',color:'#ffffff',routingStatus:'MISSING_ANCHORS'}];
  const report = {schemaVersion:1,purpose:'DISPLAY_ONLY_NOT_MANUFACTURING_WIRE_HARNESS',
    includesClosedShellInCollisionCheck:true,wireRadiusMm:.65,partClearanceMm:.15,
    modelBindings:Object.fromEntries(cad.map(c => [c.id,{...c.sha256,position:[0,0,0],rotation:[0,0,0]}])),
    connections:[{id:'W1',status:'DISPLAY_CLEAR',endpoints:{from:connections[0].from,to:connections[0].to},
      fromAnchorMm:[0,0,3],toAnchorMm:[10,0,3],polylineMm:[[0,0,3],[10,0,3]],
      wireRadiusMm:.65,clearanceMm:.15,collisions:[],anchorStatus:'VIRTUAL_SURFACE_PORT_NOT_REAL_PIN'}]};
  return {parts,cad,connections,report};
}
const resolve = f => withDisplayRoutes(f.parts,f.cad,f.connections,f.report);

test('checked display paths are separate from the immutable electrical netlist', () => {
  const f=fixture(), original=structuredClone(f), [route]=resolve(f);
  assert.ok(hasWireRoute(route));
  assert.equal(route.displayWireRadiusMm,.65);
  assert.equal(route.anchorStatus,'VIRTUAL_SURFACE_PORT_NOT_REAL_PIN');
  assert.deepEqual(f,original);
});

for (const [name,change] of Object.entries({
  'missing report': f => {f.report=undefined;},
  'stale STL': f => {f.cad[0].sha256.stl='c'.repeat(64);},
  'stale STEP': f => {f.cad[0].sha256.step='c'.repeat(64);},
  'moved part': f => {f.parts[0].position[0]=2;},
  'rotated part': f => {f.parts[0].rotation[2]=90;},
  'added obstacle': f => {f.parts.push({id:'c',position:[0,0,0],rotation:[0,0,0]});},
  'changed terminal': f => {f.connections[0].from={partId:'a',terminal:'WRONG'};},
  'unresolved route': f => {f.report.connections[0].status='UNRESOLVED';},
  'duplicate record': f => {f.report.connections.push({...f.report.connections[0]});},
  'failed clearance': f => {f.report.connections[0].collisions.push({partId:'a'});},
  'unchecked cover': f => {f.report.includesClosedShellInCollisionCheck=false;},
  'oversized drawing radius': f => {f.report.connections[0].wireRadiusMm=1.6;},
  'missing radius': f => {delete f.report.connections[0].wireRadiusMm;},
  'inconsistent endpoint': f => {f.report.connections[0].toAnchorMm=[10,1,3];},
  'non-finite route': f => {f.report.connections[0].polylineMm[0][0]=NaN;},
})) test(`${name} fails closed, never resurrects old centre routes`, () => {
  const f=fixture();
  Object.assign(f.connections[0],{routingStatus:'MODEL_ASSUMED',fromAnchorMm:[0,0,0],
    toAnchorMm:[10,0,0],polylineMm:[[0,0,0],[10,0,0]]});
  change(f);
  const [route]=resolve(f);
  assert.equal(route.routingStatus,'MISSING_ANCHORS');
  assert.equal(route.polylineMm,undefined);
  assert.equal(hasWireRoute(route),false);
});

test('viewport rejects invalid display radii', () => {
  const [route]=resolve(fixture());
  for(const radius of [0,-1,4,NaN,Infinity]) assert.equal(hasWireRoute({...route,displayWireRadiusMm:radius}),false);
});
