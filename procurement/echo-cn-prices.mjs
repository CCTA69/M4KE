import baseline from './echo-cn-bom.mjs';
import {validateSnapshot} from './snapshot.mjs';
function freeze(value) { if(value && typeof value==='object') {Object.values(value).forEach(freeze);Object.freeze(value);} return value; }
export const ECHO_CN_BOM=freeze(baseline);
export const ECHO_CN_OBSERVATION_BINDINGS=freeze([
  {id:'controller',mpn:'DFR1063',manufacturer:'DFRobot',variant:'Romeo mini ESP32-C3; exact revision unconfirmed'},
  {id:'sound-sensor',mpn:'DFR0034',manufacturer:'DFRobot',variant:'Gravity analog sound sensor; exact revision and cable unconfirmed'},
  {id:'regulator',mpn:'DFR0379',manufacturer:'Unspecified (DFRobot store)',variant:'20W adjustable buck with display and screw terminals; envelope unconfirmed'},
]);
const SENSOR_CONFLICT=freeze({designMm:[22,30],listingMm:[22,32],
  sources:['https://wiki.dfrobot.com/dfr0034/','https://www.dfrobot.com.cn/goods-85.html'],
  required:'Confirm exact board revision, full outline/connector envelope and cable pinout. Preserve the existing CAD until the design owner resolves the discrepancy.'});

/** Verified snapshot input only. Exact listing association is NOT a fit or purchase approval. */
export function echoCnPriceCoverage(snapshot,{now=Date.now()}={}) {
  validateSnapshot(snapshot,{now});
  const lines=ECHO_CN_BOM.rows.map(row=>{
    const binding=ECHO_CN_OBSERVATION_BINDINGS.find(b=>b.id===row.id);
    const candidates=binding?snapshot.entries.filter(e=>e.kind==='component' && e.market==='CN' &&
      e.supplierId==='dfrobot-cn' && e.identity.manufacturer===binding.manufacturer &&
      e.identity.mpn===binding.mpn && e.identity.supplierSku===binding.mpn && e.identity.variant===binding.variant &&
      e.identity.package==='One board' && e.price.currency==='CNY' && e.price.unit==='piece' &&
      e.relatesTo.relationship==='unqualified-candidate' && e.price.status==='advertised-only'):[];
    const e=candidates.length===1?candidates[0]:null;
    const source=e?snapshot.evidence.find(s=>s.id===e.price.evidenceId):null;
    return {...row,status:candidates.length>1?'AMBIGUOUS_OBSERVATIONS':e?'OBSERVATION_ONLY':'MISSING_PRICE_OBSERVATION',
      qualifiedForPurchase:false,observation:e?{entryId:e.id,amountCny:e.price.advertisedAmount,
        reviewedAt:source.capturedAt,sourceUpdatedAt:source.sourceUpdatedAt,url:source.url,
        freshness:source.method==='web-extract'?'UNKNOWN':now-Date.parse(source.capturedAt)>86400000?'STALE':'WITHIN_LOCAL_TTL',
        tax:e.price.tax,shipping:e.price.shipping,stockConfirmed:false}:null,
      dimensionConflict:row.id==='sound-sensor'?SENSOR_CONFLICT:null};
  });
  const observedLineCount=lines.filter(r=>r.observation).length;
  return {buildId:ECHO_CN_BOM.buildId,scope:'AUTHORED_BASELINE_NOT_ACTIVE_PROJECT_BOM',
    sourceRevision:ECHO_CN_BOM.sourceRevision,sourceSha256:ECHO_CN_BOM.sourceSha256,sourceUrl:ECHO_CN_BOM.sourceUrl,
    confirmationUrl:ECHO_CN_BOM.confirmationUrl,lines,observedLineCount,missingObservationCount:lines.length-observedLineCount,
    budgetAllocationCny:ECHO_CN_BOM.budgetAllocationCny,totalCarCny:null,purchaseAuthorized:false,completePricedBom:false,
    limitations:['566 CNY is the design owner’s budget allocation, not a quote or amount due.',
      'This identifies the confirmed authored CN v2 baseline; it does not bind prices to another active project revision.',
      'Supplier observations do not confirm exact revision, fit, connector/cable choice, stock, tax or shipping.',
      'Motor/wheel SKU and regulator/battery-holder envelopes remain unresolved. No design or geometry is changed.']};
}
