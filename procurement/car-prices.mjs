import { quoteLine, validateSnapshot } from './snapshot.mjs';

// Existing sound-car-v1 reference quantities, not a new design or the active job's BOM.
// Variant strings are explicit reviewed bindings; similarity never authorizes substitution.
export const SOUND_CAR_PRICE_REQUIREMENTS = Object.freeze([
  ['raspberry-pi-pico-r3', 'RASPBERRY-PI', 'RASPBERRY PI PICO', 'Pico RP2040 without headers; hardware revision unspecified', 1, 1, 'piece'],
  ['adafruit-max4466-1063', 'Adafruit Industries LLC', '1063', 'MAX4466 microphone amplifier board', 1, 1, 'piece'],
  ['pololu-drv8833-2130', 'Pololu Corporation', '2130', 'DRV8833 Dual Motor Driver Carrier', 1, 1, 'piece'],
  ['pololu-lp6v-1098', 'Pololu', '1098', '50:1 Micro Metal Gearmotor LP 6V', 2, 2, 'piece'],
  ['pololu-wheel-1420', 'Pololu', '1420', 'Wheel 60x8mm Pair - Black', 2, 1, 'pack'],
  ['pololu-bracket-1086', 'Pololu', '1086', 'Micro Metal Gearmotor Bracket Pair - White', 2, 1, 'pack'],
  ['pololu-caster-950', 'Pololu', '950', 'Ball Caster with 3/8 inch Plastic Ball', 1, 1, 'piece'],
].map(([catalogId, manufacturer, mpn, variant, installedQuantity, orderQuantity, unit]) =>
  Object.freeze({catalogId, manufacturer, mpn, variant, installedQuantity, orderQuantity, unit,
    package: unit === 'pack' ? 'One pair' : mpn === '1098' ? 'One motor' : mpn === '950' ? 'One caster' : 'One board'})));

const micros = value => { const [a, b = ''] = value.split('.'); return BigInt(a) * 1000000n + BigInt(b.padEnd(6, '0')); };
const decimal = value => `${value / 1000000n}.${String(value % 1000000n).padStart(6, '0')}`;

/** Caller verifies stored evidence first. This is a reference-kit comparison only. */
export function soundCarPriceCoverage(snapshot, {now = Date.now()} = {}) {
  validateSnapshot(snapshot, {now});
  const totals = new Map();
  const lines = SOUND_CAR_PRICE_REQUIREMENTS.map(r => {
    const candidates = snapshot.entries.filter(e => e.kind === 'component' && e.market === 'CN' &&
      e.relatesTo.catalogId === r.catalogId && e.relatesTo.relationship === 'same-model-revision-unverified' &&
      e.identity.manufacturer === r.manufacturer && e.identity.mpn === r.mpn && e.identity.variant === r.variant &&
      e.identity.package === r.package && e.price.unit === r.unit && e.price.currency === 'CNY' && e.identity.supplierSku);
    const line = {...r, status: candidates.length > 1 ? 'AMBIGUOUS_SOURCE' : 'MISSING_PRICE', entryId: null, subtotal: null, quote: null};
    if (candidates.length !== 1) return line;
    const e = candidates[0]; line.entryId = e.id;
    line.quote = quoteLine(snapshot, {entryId:e.id, ...Object.fromEntries(['manufacturer','mpn','supplierSku','variant'].map(k=>[k,e.identity[k]])), quantity:r.orderQuantity,unit:r.unit,currency:'CNY'}, {now,maxAgeHours:24});
    line.status = line.quote.status;
    if (line.quote.status !== 'INDICATIVE_ONLY') return line;
    if (line.quote.availability !== 'in-stock' || line.quote.reasons.includes('OBSERVED_STOCK_INSUFFICIENT') ||
        e.availability.unit !== r.unit) {
      line.status = 'STOCK_UNAVAILABLE_OR_UNRESOLVED'; return line;
    }
    if (e.price.tax === 'unknown' || line.quote.reasons.includes('ORDER_RULES_INCOMPLETE')) {
      line.status = 'ORDER_OR_TAX_UNRESOLVED'; return line;
    }
    line.subtotal = line.quote.subtotal;
    totals.set(e.price.tax, (totals.get(e.price.tax) ?? 0n) + micros(line.subtotal));
    return line;
  });
  const pricedLineCount = lines.filter(l=>l.subtotal !== null).length;
  return {kitId:'sound-car-v1', scope:'REFERENCE_KIT_NOT_ACTIVE_PROJECT_BOM', currency:'CNY', lines,
    pricedLineCount, missingLineCount:lines.length-pricedLineCount,
    partialSubtotals:[...totals].map(([tax, amount])=>({tax,amount:decimal(amount)})),
    totalCarCny:null, completeBom:false, purchaseAuthorized:false,
    limitations:['Power, wiring, fasteners and printed-material consumption are not a complete priced BOM.',
      'Partial subtotals retain separate tax bases and exclude shipping; no currency conversion.',
      'Reference identities do not prove supplier revision, physical compatibility or domestic warehouse stock.']};
}
