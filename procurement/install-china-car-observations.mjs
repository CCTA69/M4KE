#!/usr/bin/env node
/** Install dated, attributed facts, not raw supplier pages or a live-price feed. */
import { mkdir, writeFile, lstat, realpath } from 'node:fs/promises';
import { randomUUID } from 'node:crypto';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { sha256 } from './snapshot.mjs';
import { importSnapshot, PROCUREMENT_ROOT } from './import.mjs';
import { SOUND_CAR_PRICE_REQUIREMENTS } from './car-prices.mjs';

const CAPTURED = '2026-10-10T08:54:00Z';
const facts = [
  {id:'element14-cn-pico',supplier:'element14-cn',sku:'3643332',url:'https://www.element14.cn/en-CN/c/raspberry-pi/raspberry-pi-boards/prl/results',price:'29.25',tax:'excluded',
    text:'Raspberry Pi Pico, order code 3643332: one-unit CNY 29.25 excluding tax; displayed tax-inclusive amount 33.0525. Headerless version. Hardware revision unspecified.',
    note:'Web extraction reviewed 2026-10-10; crawler reported last week. Direct refresh returned HTTP 567. No live price or exact R3 revision confirmation.'},
  {id:'digikey-cn-adafruit-1063',supplier:'digikey-cn',sku:'1528-1013-ND',url:'https://www.digikey.cn/zh/products/detail/adafruit-industries-llc/1063/4990762',price:'57.48',tax:'included',
    text:'Adafruit 1063, DigiKey 1528-1013-ND: one-unit CNY 57.48, including 13 percent VAT.',
    note:'Opened web extraction reported last week; older search snippet said 57.47. This preserves the opened-page 57.48 observation, not a live quote or a claim of China warehouse stock.'},
  {id:'lcsc-cn-pololu-2130',supplier:'lcsc-cn',sku:'C6661942',url:'https://item.szlcsc.com/7616935.html',price:'65.88',tax:'unknown',
    text:'Pololu Corporation 2130, LCSC C6661942: structured metadata advertised CNY 65.88, OutOfStock, inventory zero. Quantity tiers and tax treatment unconfirmed.',
    note:'Facts extracted from public HTML captured 2026-10-10T08:53:46.402634Z; original SHA256 59703edc32b6bae022c75e2878b1df8d916f43e62ddb955191309764afd2012d. Original HTML excluded from public source. This extract is not a direct-http evidence file.'},
];

export async function installChinaCarObservations({root=PROCUREMENT_ROOT,now=Date.now()}={}) {
  root=path.resolve(root);
  const incoming=path.join(root,'incoming'); await mkdir(incoming,{recursive:true});
  if ((await lstat(incoming)).isSymbolicLink() || await realpath(incoming)!==incoming) throw Error('Ordinary incoming directory required.');
  const bundle=path.join(incoming,'china-car-20261010-'+randomUUID());
  await mkdir(bundle);
  await mkdir(path.join(bundle,'evidence'));
  const evidence=[], entries=[];
  for (const [i,f] of facts.entries()) {
    const r=SOUND_CAR_PRICE_REQUIREMENTS[i];
    const bytes=Buffer.from(`Research transcription, not the original page.\nSource: ${f.url}\nReviewed at: ${CAPTURED}\n${f.text}\n${f.note}\n`);
    const hash=sha256(bytes), file=`evidence/${hash}.txt`;
    await writeFile(path.join(bundle,file),bytes,{flag:'wx'});
    evidence.push({id:f.id,url:f.url,capturedAt:CAPTURED,sourceUpdatedAt:null,method:'web-extract',access:'public',file,sha256:hash,contentType:'text/plain',extraction:'Attributed factual research transcription; capture date is not price freshness. '+f.note});
    entries.push({id:f.id,kind:'component',supplierId:f.supplier,market:'CN',
      identity:{manufacturer:r.manufacturer,mpn:r.mpn,supplierSku:f.sku,variant:r.variant,package:'One board',manufacturerRevision:null},evidenceIds:[f.id],
      price:{status:i===2?'advertised-only':'observed-tiers',currency:'CNY',unit:'piece',tiers:i===2?[]:[{minimumQuantity:1,unitPrice:f.price}],advertisedAmount:i===2?f.price:null,tax:f.tax,shipping:'unknown',evidenceId:f.id},
      availability:{status:i===2?'out-of-stock':'unknown',quantity:i===2?0:null,unit:i===2?'piece':null,evidenceId:f.id},minimumOrderQuantity:null,orderMultiple:null,specs:[],
      relatesTo:{catalogId:r.catalogId,relationship:'same-model-revision-unverified',note:'Same named model; hardware revision, authenticity and physical compatibility remain unverified.'},notes:[f.note,'China-market listing, not a guarantee of domestic stock, checkout price or landed cost.']});
  }
  await writeFile(path.join(bundle,'snapshot.json'),JSON.stringify({schemaVersion:1,snapshotId:'china-car-research-20261010',createdAt:CAPTURED,evidence,entries},null,2)+'\n',{flag:'wx'});
  return importSnapshot(path.basename(bundle),{root,now});
}

if(process.argv[1] && path.resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  try {
    if(process.argv.length!==2) throw Error('Usage: node procurement/install-china-car-observations.mjs');
    console.log(JSON.stringify(await installChinaCarObservations()));
  } catch(error) { console.error(error.message); process.exitCode=1; }
}
