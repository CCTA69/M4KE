#!/usr/bin/env node
/** Operator-reviewed 1688 observations; no login, scraping, live API or purchase. */
import { lstat, mkdir, readFile, realpath, writeFile } from 'node:fs/promises';
import { randomUUID } from 'node:crypto';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { canonicalJson, LIMITS, sha256, validateSnapshot } from './snapshot.mjs';
import { importSnapshot, PROCUREMENT_ROOT } from './import.mjs';

const FORMATS = new Map([
  ['.html', 'text/html'], ['.txt', 'text/plain'], ['.json', 'application/json'], ['.pdf', 'application/pdf'],
]);
const fail = message => { throw new Error(`1688 import: ${message}`); };

export async function import1688Observation(observation, evidenceBytes, extension, { root = PROCUREMENT_ROOT, now = Date.now() } = {}) {
  const fields = ['schemaVersion', 'url', 'capturedAt', 'access', 'extraction', 'entries'];
  if (!observation || Object.getPrototypeOf(observation) !== Object.prototype
    || Object.keys(observation).length !== fields.length || !fields.every(k => Object.hasOwn(observation, k))
    || Object.values(Object.getOwnPropertyDescriptors(observation)).some(d => !Object.hasOwn(d, 'value'))) fail('observation fields differ from schema');
  if (observation.schemaVersion !== 1) fail('schemaVersion must be 1');
  // Match the original string, not URL-normalized paths; no credentials, redirects or tracking parameters.
  if (typeof observation.url !== 'string' || !/^https:\/\/detail\.1688\.com\/offer\/[1-9]\d{0,29}\.html$/.test(observation.url)) fail('URL must be a canonical HTTPS 1688 offer URL');
  if (!Buffer.isBuffer(evidenceBytes) || !evidenceBytes.length || evidenceBytes.length > LIMITS.evidenceBytes || !FORMATS.has(extension)) fail('evidence must be bounded nonempty HTML, TXT, JSON or PDF bytes');
  const bytes = Buffer.from(evidenceBytes);
  const digest = sha256(bytes);
  const offerId = observation.url.match(/\/([1-9]\d*)\.html$/)[1];
  const candidate = {
    schemaVersion: 1, snapshotId: `1688-${offerId}`, createdAt: observation.capturedAt,
    evidence: [{ id: 'listing', url: observation.url, capturedAt: observation.capturedAt,
      sourceUpdatedAt: null, method: 'operator-export', access: observation.access,
      file: `evidence/${digest}${extension}`, sha256: digest, contentType: FORMATS.get(extension), extraction: observation.extraction }],
    entries: observation.entries,
  };
  validateSnapshot(candidate, { now });
  for (const entry of candidate.entries) {
    if (entry.market !== 'CN' || entry.relatesTo.catalogId !== null || entry.relatesTo.relationship !== 'unqualified-candidate') fail('listings must remain unqualified CN candidates without catalog admission');
    if (entry.specs.some(spec => spec.basis !== 'supplier-listing')) fail('listing evidence cannot establish manufacturer-datasheet claims');
  }
  // Snapshot mutable caller objects before the first asynchronous operation.
  const snapshot = JSON.parse(canonicalJson(candidate));
  root = path.resolve(root);
  await mkdir(root, { recursive: true });
  if (await realpath(root) !== root || (await lstat(root)).isSymbolicLink()) fail('root must be an ordinary directory without links');
  const incoming = path.join(root, 'incoming');
  await mkdir(incoming, { recursive: true });
  if (await realpath(incoming) !== incoming || !(await lstat(incoming)).isDirectory() || (await lstat(incoming)).isSymbolicLink()) fail('incoming must be an ordinary directory without links');
  // A unique private bundle avoids collisions with another operator; preserve it on import failure for diagnosis.
  const bundle = path.join(incoming, `1688-${randomUUID()}`);
  await mkdir(bundle);
  await mkdir(path.join(bundle, 'evidence'));
  await writeFile(path.join(bundle, snapshot.evidence[0].file), bytes, { flag: 'wx' });
  await writeFile(path.join(bundle, 'snapshot.json'), `${canonicalJson(snapshot)}\n`, { flag: 'wx' });
  return importSnapshot(path.basename(bundle), { root, now });
}

async function readBounded(file, maximum) {
  const resolved = path.resolve(file); const stat = await lstat(resolved);
  if (!stat.isFile() || stat.isSymbolicLink() || await realpath(resolved) !== resolved || !stat.size || stat.size > maximum) fail('input must be a bounded ordinary file without links');
  const bytes = await readFile(resolved);
  if (!bytes.length || bytes.length > maximum) fail('input size changed beyond limits');
  return bytes;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    const [reviewed, evidence, flag, root, ...extra] = process.argv.slice(2);
    if (!reviewed || !evidence || extra.length || (flag !== undefined && (flag !== '--root' || !root))) fail('usage: node procurement/1688-import.mjs REVIEWED.json CAPTURE.html|txt|json|pdf [--root DIRECTORY]');
    const data = await readBounded(reviewed, LIMITS.jsonBytes);
    let observation;
    try { observation = JSON.parse(data.toString('utf8')); } catch { fail('reviewed observation is not valid JSON'); }
    const bytes = await readBounded(evidence, LIMITS.evidenceBytes);
    const receipt = await import1688Observation(observation, bytes, path.extname(evidence).toLowerCase(), root ? { root } : {});
    process.stdout.write(`${JSON.stringify(receipt)}\n`);
  } catch (error) {
    const message = /^(1688 import|Supplier snapshot|Supplier import): /.test(error.message) ? error.message : '1688 import: could not read or store local files';
    process.stderr.write(`${message}\n`); process.exitCode = 1;
  }
}
