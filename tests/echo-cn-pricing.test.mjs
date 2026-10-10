import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,rm,writeFile} from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {echoCnPriceCoverage,ECHO_CN_BOM} from '../procurement/echo-cn-prices.mjs';
import {installEchoCnObservations} from '../procurement/install-echo-cn-observations.mjs';
import {installChinaCarObservations} from '../procurement/install-china-car-observations.mjs';
import {readImportedSnapshot} from '../procurement/import.mjs';
import {createProcurementService} from '../server/studio-procurement.mjs';
import {createIntegrationRuntime} from '../server/studio-integrations.mjs';

async function setup(t,installer=installEchoCnObservations) {
  const root=await mkdtemp(path.join(os.tmpdir(),'echo-cn-pricing-'));t.after(()=>rm(root,{recursive:true,force:true}));
  const receipt=await installer({root:path.join(root,'procurement')});
  const {snapshot}=await readImportedSnapshot(receipt.snapshotId,{root:path.join(root,'procurement')});
  return {root,receipt,snapshot};
}
test('CN v2 baseline retains 17 source rows and separates installed parts from purchase units',()=>{
  assert.equal(ECHO_CN_BOM.buildId,'echo-f1-cn-v2');assert.equal(ECHO_CN_BOM.rows.length,17);
  assert.equal(ECHO_CN_BOM.sourceRevision,'65ecd8efcae04d2c8b76a0a53ad208c3c647132d');
  assert.equal(ECHO_CN_BOM.rows.reduce((sum,r)=>sum+r.quantity*r.budgetUnitCny,0),566);
  const rings=ECHO_CN_BOM.rows.find(r=>r.id==='o-rings');assert.equal(rings.quantity,1);assert.equal(rings.unit,'pack');assert.equal(rings.installedQuantity,4);assert.equal(rings.packSize,10);
  assert.equal(ECHO_CN_BOM.rows.find(r=>r.id==='bearings').quantity,4);
});
test('CN observations map only to their three exact lines and never become a whole-car quote',async t=>{
  const {snapshot}=await setup(t);const result=echoCnPriceCoverage(snapshot);
  assert.equal(result.observedLineCount,3);assert.equal(result.missingObservationCount,14);
  assert.equal(result.budgetAllocationCny,566);assert.equal(result.totalCarCny,null);assert.equal(result.purchaseAuthorized,false);
  assert.deepEqual(result.lines.filter(r=>r.observation).map(r=>r.observation.amountCny),['135.00','40.00','20.00']);
  assert(result.lines.every(r=>r.qualifiedForPurchase===false));
  const sensor=result.lines.find(r=>r.id==='sound-sensor');assert.equal(sensor.gate,'DIMENSIONS_TO_CONFIRM');
  assert.deepEqual(sensor.dimensionConflict.designMm,[22,30]);assert.deepEqual(sensor.dimensionConflict.listingMm,[22,32]);
  assert.equal(result.lines.find(r=>r.id==='motors').gate,'SELLER_MATCH_REQUIRED');
});
test('old Pico/Adafruit/Pololu observations cannot be relabeled as CN v2',async t=>{
  const {snapshot}=await setup(t,installChinaCarObservations);const c=echoCnPriceCoverage(snapshot);
  assert.equal(c.observedLineCount,0);assert.equal(c.missingObservationCount,17);assert.equal(c.totalCarCny,null);
});
test('wrong variant, currency, market, package or SKU do not match and duplicates stay ambiguous',async t=>{
  const {snapshot}=await setup(t);
  for(const change of [e=>e.identity.variant='other board',e=>e.identity.supplierSku='other',e=>e.identity.package='Ten boards',e=>e.price.currency='USD',e=>e.market='US']) {
    const s=structuredClone(snapshot);change(s.entries[0]);assert.equal(echoCnPriceCoverage(s).observedLineCount,2);
  }
  const s=structuredClone(snapshot);s.entries.push({...structuredClone(s.entries[0]),id:'duplicate'});
  assert.equal(echoCnPriceCoverage(s).lines[0].status,'AMBIGUOUS_OBSERVATIONS');
});
test('API exposes current and historical references separately; corrupted CN evidence fails closed',async t=>{
  const {root,receipt,snapshot}=await setup(t);let response;
  const handle=createProcurementService({root,snapshotSha256:receipt.snapshotId,json:(_r,status,data)=>response={status,data}});
  await handle({method:'GET'},{},'/api/studio/procurement');assert.equal(response.status,200);
  assert.equal(response.data.echoF1CnV2Reference.lines.length,17);assert.equal(response.data.soundCarReference.pricedLineCount,0);
  assert(response.data.entries.every(e=>e.quote.status==='UNQUOTABLE'));
  const runtime=createIntegrationRuntime({root,snapshotSha256:receipt.snapshotId});
  const search=await runtime.call('search_cached_parts',{query:'DFR1063'});
  assert.equal(search.snapshotSha256,receipt.snapshotId);assert.equal(search.entries.length,1);
  assert.equal(search.entries[0].identity.mpn,'DFR1063');
  const quote=await runtime.call('quote_cached_part',{entryId:search.entries[0].id,quantity:1});
  assert.equal(quote.status,'UNQUOTABLE');assert.equal(quote.subtotal,null);
  await writeFile(path.join(root,'procurement/snapshots',receipt.snapshotId,snapshot.evidence[0].file),'tampered');
  await handle({method:'GET'},{},'/api/studio/procurement');assert.equal(response.status,503);assert.equal(response.data.echoF1CnV2Reference,undefined);
});
