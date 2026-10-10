import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, writeFile, rm } from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {spawnSync} from 'node:child_process';
import { sha256 } from '../procurement/snapshot.mjs';
import { importSnapshot } from '../procurement/import.mjs';
import { createProcurementService } from '../server/studio-procurement.mjs';
import { soundCarPriceCoverage, SOUND_CAR_PRICE_REQUIREMENTS } from '../procurement/car-prices.mjs';
import { installChinaCarObservations } from '../procurement/install-china-car-observations.mjs';

const now = Date.parse('2026-10-10T09:00:00Z');
const raw = Buffer.from('Synthetic supplier evidence for software tests only.');
const hash = sha256(raw);
function fixture(indices = [0]) {
  return { schemaVersion: 1, snapshotId: 'china-test', createdAt: '2026-10-10T08:00:00Z',
    evidence: [{ id: 'source', url: 'https://example.com/part', capturedAt: '2026-10-10T08:00:00Z', sourceUpdatedAt: null, method: 'direct-http', access: 'public', file: `evidence/${hash}.txt`, sha256: hash, contentType: 'text/plain', extraction: 'Synthetic test.' }],
    entries: indices.map(i => { const r = SOUND_CAR_PRICE_REQUIREMENTS[i]; return {
      id: `item-${i}`, kind: 'component', supplierId: 'test', market: 'CN',
      identity: { manufacturer: r.manufacturer, mpn: r.mpn, supplierSku: `sku-${i}`, variant: r.variant, package: r.package, manufacturerRevision: null }, evidenceIds: ['source'],
      price: { status: 'observed-tiers', currency: 'CNY', unit: r.unit, tiers: [{ minimumQuantity: 1, unitPrice: '0.10' }], advertisedAmount: null, tax: 'included', shipping: 'unknown', evidenceId: 'source' },
      availability: { status: 'in-stock', quantity: 100, unit: r.unit, evidenceId: 'source' }, minimumOrderQuantity: 1, orderMultiple: 1, specs: [],
      relatesTo: { catalogId: r.catalogId, relationship: 'same-model-revision-unverified', note: 'Test, not qualification.' }, notes: [] };
    }) };
}
test('car coverage retains seven missing lines, never a zero-cost complete car', () => {
  const s = fixture(); s.entries[0].market = 'US';
  const c = soundCarPriceCoverage(s, { now });
  assert.equal(c.lines.length, 7); assert.equal(c.pricedLineCount, 0);
  assert.deepEqual(c.partialSubtotals, []); assert.equal(c.totalCarCny, null);
  assert.equal(c.completeBom, false);
});
test('car reference counts two motors but one wheel pair and uses decimal totals', () => {
  const s = fixture([3, 4]);
  const c = soundCarPriceCoverage(s, { now });
  assert.equal(c.lines[3].quote.quantity, 2); assert.equal(c.lines[3].quote.subtotal, '0.200000');
  assert.equal(c.lines[4].quote.quantity, 1); assert.equal(c.lines[4].quote.unit, 'pack');
  assert.deepEqual(c.partialSubtotals, [{ tax: 'included', amount: '0.300000' }]);
  assert.equal(c.missingLineCount, 5); assert.equal(c.totalCarCny, null);
});
test('China car rejects bare ICs, USD, different variants, wrong pack units and other markets', () => {
  for (const change of [e => e.identity.mpn = 'DRV8833PWPR', e => e.identity.variant = 'other', e => e.price.currency = 'USD', e => e.price.unit = 'pack', e => e.market = 'US', e => e.relatesTo.relationship = 'not-equivalent']) {
    const s = fixture(); change(s.entries[0]);
    assert.equal(soundCarPriceCoverage(s, { now }).pricedLineCount, 0);
  }
});
test('stale, search-extracted, out-of-stock and advertised prices remain excluded', () => {
  for (const change of [s => s.evidence[0].capturedAt = '2026-10-01T08:00:00Z', s => s.evidence[0].method = 'web-extract', s => {s.entries[0].availability.status = 'out-of-stock'; s.entries[0].availability.quantity = 0;}, s => {s.entries[0].price.status = 'advertised-only'; s.entries[0].price.tiers = []; s.entries[0].price.advertisedAmount = '65.88';}]) {
    const s = fixture(); change(s); const c = soundCarPriceCoverage(s, { now });
    assert.equal(c.pricedLineCount, 0); assert.equal(c.lines[0].subtotal, null);
  }
});
test('duplicates need selection and tax bases never get silently added', () => {
  const s = fixture([0, 1]); s.entries[1].price.tax = 'excluded';
  assert.equal(soundCarPriceCoverage(s, { now }).partialSubtotals.length, 2);
  s.entries.push({...structuredClone(s.entries[0]), id:'duplicate'});
  assert.equal(soundCarPriceCoverage(s, { now }).lines[0].status, 'AMBIGUOUS_SOURCE');
});

test('unknown or multipair packages cannot inherit a one-pair order binding', () => {
  for (const packageName of [null, 'pack', 'Box of 10 wheel pairs']) {
    const s=fixture([4]); s.entries[0].identity.package=packageName;
    assert.equal(soundCarPriceCoverage(s,{now}).pricedLineCount,0);
  }
});

test('fresh prices with expired, unknown, backorder or mismatched stock units stay unresolved', () => {
  for (const change of [
    s=>{s.entries[0].availability={status:'unknown',quantity:null,unit:null,evidenceId:null};},
    s=>{s.entries[0].availability.status='backorder';s.entries[0].availability.quantity=null;},
    s=>{s.entries[0].availability.unit='pack';},
    s=>{s.evidence.push({...s.evidence[0],id:'old-stock',capturedAt:'2026-10-01T08:00:00Z'});s.entries[0].evidenceIds.push('old-stock');s.entries[0].availability={status:'out-of-stock',quantity:0,unit:'piece',evidenceId:'old-stock'};},
  ]) {
    const s=fixture();change(s);const c=soundCarPriceCoverage(s,{now});
    assert.equal(c.pricedLineCount,0);assert.deepEqual(c.partialSubtotals,[]);
    assert.equal(c.lines[0].status,'STOCK_UNAVAILABLE_OR_UNRESOLVED');
  }
});
test('configured snapshot is imported and exposed with coverage; tampering fails closed', async t => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'china-pricing-')); t.after(() => rm(root, {recursive:true,force:true}));
  const bundle = path.join(root, 'procurement/incoming/china-test');
  await mkdir(path.join(bundle,'evidence'), {recursive:true});
  const s = fixture(); await writeFile(path.join(bundle,'snapshot.json'), JSON.stringify(s));
  await writeFile(path.join(bundle,s.evidence[0].file), raw);
  const receipt = await importSnapshot('china-test', {root:path.join(root,'procurement'),now});
  const calls = []; const handle = createProcurementService({root, snapshotSha256:receipt.snapshotId, now:()=>now, json:(_r,status,value)=>calls.push({status,value})});
  await handle({method:'GET'}, {}, '/api/studio/procurement');
  assert.equal(calls[0].status,200); assert.equal(calls[0].value.snapshotSha256, receipt.snapshotId);
  assert.equal(calls[0].value.soundCarReference.pricedLineCount,1);
  await writeFile(path.join(root,'procurement/snapshots',receipt.snapshotId,s.evidence[0].file),'changed');
  await handle({method:'GET'}, {}, '/api/studio/procurement');
  assert.equal(calls[1].status,503); assert.deepEqual(calls[1].value.entries,[]);
  assert.throws(()=>createProcurementService({root,snapshotSha256:'../../other',json(){}}),/SHA256/);
});
test('dated research installs real observations without promoting excerpts to live quotes', async t => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'china-observations-')); t.after(()=>rm(root,{recursive:true,force:true}));
  const receipt = await installChinaCarObservations({root:path.join(root,'procurement'),now});
  const calls=[]; const handle=createProcurementService({root,snapshotSha256:receipt.snapshotId,now:()=>now,json:(_r,status,value)=>calls.push({status,value})});
  await handle({method:'GET'},{},'/api/studio/procurement');
  const d=calls[0].value; assert.equal(calls[0].status,200); assert.equal(d.entries.length,3);
  assert.equal(d.entries[1].price.tiers[0].unitPrice,'57.48');
  assert.equal(d.entries[2].price.advertisedAmount,'65.88');
  assert.equal(d.entries[2].availability.status,'out-of-stock');
  assert(d.entries.every(e=>e.price.freshness==='UNKNOWN' && e.quote.subtotal===null));
  assert.equal(d.soundCarReference.pricedLineCount,0); assert.equal(d.soundCarReference.missingLineCount,7);
  const again=await installChinaCarObservations({root:path.join(root,'procurement'),now});
  assert.equal(again.snapshotId,receipt.snapshotId); assert.equal(again.imported,false);
});

test('MCP search and quote use the same startup pin as the HTTP panel', async t => {
  const root=await mkdtemp(path.join(os.tmpdir(),'china-mcp-'));t.after(()=>rm(root,{recursive:true,force:true}));
  const receipt=await installChinaCarObservations({root:path.join(root,'procurement'),now});
  const moduleUrl=new URL('../server/studio-integrations.mjs',import.meta.url).href;
  const code=`import {createIntegrationRuntime} from ${JSON.stringify(moduleUrl)};
    const r=createIntegrationRuntime({root:process.env.M4KE_TEST_PRICE_ROOT});
    const s=await r.call('search_cached_parts',{query:'1063'});
    const q=await r.call('quote_cached_part',{entryId:s.entries[0].id,quantity:1});
    console.log(JSON.stringify({s,q}));`;
  const child=spawnSync(process.execPath,['--input-type=module','-e',code],{encoding:'utf8',timeout:10000,
    env:{...process.env,M4KE_TEST_PRICE_ROOT:root,M4KE_PROCUREMENT_SNAPSHOT_SHA256:receipt.snapshotId}});
  assert.equal(child.status,0,child.stderr);const {s,q}=JSON.parse(child.stdout);
  assert.equal(s.snapshotSha256,receipt.snapshotId);assert.equal(s.entries.length,1);
  assert.equal(s.entries[0].price.tiers[0].unitPrice,'57.48');
  assert.equal(q.status,'UNQUOTABLE');assert.equal(q.subtotal,null);assert.equal(q.purchaseMade,false);
});
