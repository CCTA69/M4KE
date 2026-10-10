#!/usr/bin/env node
import {mkdir,writeFile,lstat,realpath} from 'node:fs/promises';
import {randomUUID} from 'node:crypto';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {sha256} from './snapshot.mjs';
import {importSnapshot,PROCUREMENT_ROOT} from './import.mjs';
import {ECHO_CN_OBSERVATION_BINDINGS} from './echo-cn-prices.mjs';
const REVIEWED='2026-10-10T10:28:00Z';
const facts=[
  {amount:'135.00',url:'https://wechat.dfrobot.com.cn/goods-3848.html',note:'DFRobot China listing for DFR1063 Romeo mini ESP32-C3 advertised CNY 135.00. Web search extraction reported a three-day-old crawl; current stock, tax, exact revision and checkout not verified.'},
  {amount:'40.00',url:'https://www.dfrobot.com.cn/goods-85.html',note:'DFR0034 China listing advertised CNY 40.00, 3.3/5 V and 22 by 32 mm. Opened web extraction reported a three-week-old crawl. The design uses 22 by 30 mm based on the English wiki. Exact board revision, connector envelope and cable pinout need confirmation; no fit approval.'},
  {amount:'20.00',url:'https://www.dfrobot.com.cn/goods-1351.html',note:'DFR0379 China listing advertised CNY 20.00 for an adjustable buck with display. Search extraction of the same URL with from=rss reported a one-month-old crawl; clean-URL open timed out. Store lists an unspecified other brand. Current stock, tax and the design’s 66 by 40 by 20 mm envelope are unverified.'},
];
export async function installEchoCnObservations({root=PROCUREMENT_ROOT,now=Date.now()}={}) {
  root=path.resolve(root);const incoming=path.join(root,'incoming');await mkdir(incoming,{recursive:true});
  if((await lstat(incoming)).isSymbolicLink() || await realpath(incoming)!==incoming)throw Error('Ordinary incoming directory required.');
  const bundle=path.join(incoming,'echo-cn-v2-20261010-'+randomUUID());await mkdir(path.join(bundle,'evidence'),{recursive:true});
  const evidence=[],entries=[];
  for(const [i,f] of facts.entries()) {
    const b=ECHO_CN_OBSERVATION_BINDINGS[i],id='dfrobot-cn-'+b.mpn.toLowerCase();
    const bytes=Buffer.from(`Attributed factual transcription, not original supplier HTML.\nSource: ${f.url}\nReviewed: ${REVIEWED}\n${f.note}\n`);
    const hash=sha256(bytes),file=`evidence/${hash}.txt`;await writeFile(path.join(bundle,file),bytes,{flag:'wx'});
    evidence.push({id,url:f.url,capturedAt:REVIEWED,sourceUpdatedAt:null,method:'web-extract',access:'public',file,sha256:hash,contentType:'text/plain',extraction:f.note});
    entries.push({id,kind:'component',supplierId:'dfrobot-cn',market:'CN',
      identity:{manufacturer:b.manufacturer,mpn:b.mpn,supplierSku:b.mpn,variant:b.variant,package:'One board',manufacturerRevision:null},
      evidenceIds:[id],price:{status:'advertised-only',currency:'CNY',unit:'piece',tiers:[],advertisedAmount:f.amount,tax:'unknown',shipping:'unknown',evidenceId:id},
      availability:{status:'unknown',quantity:null,unit:null,evidenceId:id},minimumOrderQuantity:null,orderMultiple:null,specs:[],
      relatesTo:{catalogId:null,relationship:'unqualified-candidate',note:`Listing observation for CN v2 ${b.id}; not a library geometry binding, exact variant match, or fit approval.`},
      notes:[f.note,'Dated observation only. No purchase or design substitution.']});
  }
  await writeFile(path.join(bundle,'snapshot.json'),JSON.stringify({schemaVersion:1,snapshotId:'echo-cn-v2-observations-20261010',createdAt:REVIEWED,evidence,entries},null,2)+'\n',{flag:'wx'});
  return importSnapshot(path.basename(bundle),{root,now});
}
if(process.argv[1] && path.resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  try {if(process.argv.length!==2)throw Error('Usage: node procurement/install-echo-cn-observations.mjs');console.log(JSON.stringify(await installEchoCnObservations()));}
  catch(error){console.error(error.message);process.exitCode=1;}
}
