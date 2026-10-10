import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, readdir, rm, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { import1688Observation } from '../procurement/1688-import.mjs';
import { readImportedSnapshot, quoteImportedSnapshot } from '../procurement/import.mjs';

const NOW = Date.parse('2026-10-10T10:00:00Z');
// Entirely synthetic; this offer ID and price are not supplier observations.
const raw = Buffer.from('Synthetic listing: test SKU-A, pack of 10, 2 packs at CNY 12.50.');
function observation() {
  return { schemaVersion: 1, url: 'https://detail.1688.com/offer/123456789.html',
    capturedAt: '2026-10-10T09:00:00Z', access: 'operator-authenticated',
    extraction: 'Synthetic test fixture, not real supplier data.',
    entries: [{ id: 'test-sku-a', kind: 'component', supplierId: 'test-supplier', market: 'CN',
      identity: { manufacturer: 'Test maker', mpn: 'TEST-1', supplierSku: 'SKU-A', variant: 'Pack of 10', package: '10 pieces per pack', manufacturerRevision: null },
      evidenceIds: ['listing'],
      price: { status: 'observed-tiers', currency: 'CNY', unit: 'pack', tiers: [{ minimumQuantity: 2, unitPrice: '12.50' }], advertisedAmount: null, tax: 'unknown', shipping: 'unknown', evidenceId: 'listing' },
      availability: { status: 'unknown', quantity: null, unit: null, evidenceId: null },
      minimumOrderQuantity: null, orderMultiple: null,
      specs: [{ name: 'Shaft diameter', value: '3', unit: 'mm', conditions: 'Supplier nominal; unmeasured', basis: 'supplier-listing', evidenceId: 'listing' }],
      relatesTo: { catalogId: null, relationship: 'unqualified-candidate', note: 'Requires independent qualification.' }, notes: [] }] };
}
async function rootFor(t) {
  const root = await mkdtemp(path.join(os.tmpdir(), 'm4ke-1688-'));
  t.after(() => rm(root, { recursive: true, force: true }));
  return root;
}
const request = { entryId: 'test-sku-a', manufacturer: 'Test maker', mpn: 'TEST-1', supplierSku: 'SKU-A', variant: 'Pack of 10', quantity: 2, unit: 'pack', currency: 'CNY' };

test('1688 observation survives real hash-checked import and retains units, evidence and uncertainty', async t => {
  const root = await rootFor(t);
  const receipt = await import1688Observation(observation(), raw, '.txt', { root, now: NOW });
  const { snapshot } = await readImportedSnapshot(receipt.snapshotId, { root, now: NOW });
  assert.equal(snapshot.evidence[0].url, 'https://detail.1688.com/offer/123456789.html');
  assert.equal(snapshot.evidence[0].method, 'operator-export');
  assert.equal(snapshot.evidence[0].capturedAt, '2026-10-10T09:00:00Z');
  assert.equal(snapshot.evidence[0].sourceUpdatedAt, null);
  assert.deepEqual(snapshot.entries, observation().entries);
  assert.deepEqual(await readFile(path.join(root, receipt.directory, snapshot.evidence[0].file)), raw);
  const quote = await quoteImportedSnapshot(receipt.snapshotId, request, { root, now: NOW });
  assert.equal(quote.subtotal, '25.000000');
  assert.equal(quote.unit, 'pack');
  assert.equal(quote.status, 'INDICATIVE_ONLY');
  assert.ok(quote.reasons.includes('ORDER_RULES_INCOMPLETE'));
  assert.equal(quote.engineeringQualified, false);
  assert.equal(receipt.networkUsed, false);
  assert.equal(receipt.semanticClaimsVerified, false);
  const again = await import1688Observation(observation(), raw, '.txt', { root, now: NOW });
  assert.equal(again.snapshotId, receipt.snapshotId);
  assert.equal(again.imported, false);
});

test('1688 advertised price does not become a SKU quantity price; old captures remain stale', async t => {
  const root = await rootFor(t); const data = observation();
  Object.assign(data.entries[0].price, { status: 'advertised-only', tiers: [], advertisedAmount: '12.50' });
  const receipt = await import1688Observation(data, raw, '.txt', { root, now: NOW });
  assert.equal((await quoteImportedSnapshot(receipt.snapshotId, request, { root, now: NOW })).subtotal, null);
  const old = await import1688Observation(observation(), raw, '.txt', { root, now: NOW + 48 * 3600000 });
  assert.equal((await quoteImportedSnapshot(old.snapshotId, request, { root, now: NOW + 48 * 3600000 })).status, 'STALE');
});

test('1688 rejects noncanonical source URLs and unexpected account fields before writing', async t => {
  const root = await rootFor(t);
  for (const url of ['http://detail.1688.com/offer/123.html', 'https://detail.1688.com.evil.example/offer/123.html', 'https://detail.1688.com/offer/123.html?token=secret', 'https://detail.1688.com/offer/123.html#x', 'https://1688.com/offer/123.html', 'https://detail.1688.com/offer/../123.html']) {
    await assert.rejects(import1688Observation({ ...observation(), url }, raw, '.txt', { root, now: NOW }), /1688.*URL/);
  }
  await assert.rejects(import1688Observation({ ...observation(), accessToken: 'fixture' }, raw, '.txt', { root, now: NOW }), /fields/);
  assert.deepEqual(await readdir(root), []);
});

test('1688 cannot promote a listing to engineering evidence or replace missing SKU/tiers', async t => {
  const root = await rootFor(t);
  for (const mutate of [d => { d.entries[0].specs[0].basis = 'manufacturer-datasheet'; }, d => { d.entries[0].relatesTo.catalogId = 'trusted-part'; }, d => { d.entries[0].identity.supplierSku = null; }, d => { d.entries[0].price.tiers[0].unitPrice = 12.5; }, d => { d.entries[0].price.evidenceId = 'unrelated'; }]) {
    const data = observation(); mutate(data);
    await assert.rejects(import1688Observation(data, raw, '.txt', { root, now: NOW }));
  }
  assert.deepEqual(await readdir(root), []);
});

test('1688 rejects empty/oversized evidence and executable formats', async t => {
  const root = await rootFor(t);
  for (const [bytes, ext] of [[Buffer.alloc(0), '.txt'], [Buffer.alloc(4 * 1024 * 1024 + 1), '.txt'], [raw, '.js']]) {
    await assert.rejects(import1688Observation(observation(), bytes, ext, { root, now: NOW }), /evidence/);
  }
});

test('1688 CLI imports from outside repository and never echoes malformed source contents', async t => {
  const root = await rootFor(t);
  const input = path.join(root, 'reviewed.json'); const evidence = path.join(root, 'capture.txt');
  const data = observation(); data.capturedAt = new Date(Date.now() - 3600000).toISOString();
  await writeFile(input, JSON.stringify(data)); await writeFile(evidence, raw);
  const script = fileURLToPath(new URL('../procurement/1688-import.mjs', import.meta.url));
  const result = spawnSync(process.execPath, [script, input, evidence, '--root', root], { cwd: os.tmpdir(), encoding: 'utf8' });
  assert.equal(result.status, 0, result.stderr);
  assert.equal(JSON.parse(result.stdout).networkUsed, false);
  await writeFile(input, 'secret-fixture-not-json');
  const bad = spawnSync(process.execPath, [script, input, evidence, '--root', root], { encoding: 'utf8' });
  assert.equal(bad.status, 1); assert.doesNotMatch(bad.stderr, /secret-fixture/);
});
