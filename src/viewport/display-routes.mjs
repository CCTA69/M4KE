import {hasWireRoute} from './interaction.mjs';

const samePoint = (a, b) => Array.isArray(a) && Array.isArray(b)
  && a.length === 3 && b.length === 3 && a.every((v, i) => Number.isFinite(v) && v === b[i]);
const sameEndpoint = (a, b) => a && b && a.partId === b.partId && a.terminal === b.terminal;

/**
 * Merge separately checked DISPLAY routes without changing the electrical netlist.
 * Stale geometry, placement, endpoints or missing evidence fail closed to 2D only.
 * @param {import('./types').ToyPart[]} parts
 * @param {import('./types').CadPart[]} cadParts
 * @param {import('./types').ElectricalConnection[]} connections
 * @param {import('./types').WireDisplayReport|undefined} report
 * @returns {import('./types').ElectricalConnection[]}
 */
export function withDisplayRoutes(parts, cadParts, connections, report) {
  const bindings = report?.modelBindings;
  const validModel = report?.schemaVersion === 1
    && report.purpose === 'DISPLAY_ONLY_NOT_MANUFACTURING_WIRE_HARNESS'
    && report.includesClosedShellInCollisionCheck === true && bindings
    && parts.length > 0 && cadParts.length === parts.length
    && new Set(parts.map(p => p.id)).size === parts.length
    && new Set(cadParts.map(p => p.id)).size === parts.length
    && Object.keys(bindings).length === parts.length
    && cadParts.every(c => {
      const p = parts.find(part => part.id === c.id), binding = bindings[c.id];
      return p && binding && /^[a-f0-9]{64}$/.test(c.sha256?.stl || '')
        && /^[a-f0-9]{64}$/.test(c.sha256?.step || '')
        && binding.stl === c.sha256.stl && binding.step === c.sha256.step
        && samePoint(binding.position, p.position) && samePoint(binding.rotation, p.rotation);
    });
  const records = Array.isArray(report?.connections) ? report.connections : [];
  const validRecords = new Set(records.map(r => r.id)).size === records.length;
  return connections.map(connection => {
    // Do not accidentally resurrect the old centre-to-centre placeholder lines.
    const {fromAnchorMm, toAnchorMm, polylineMm, displayWireRadiusMm, anchorStatus, ...logical} = connection;
    const fallback = {...logical, routingStatus: /** @type {const} */ ('MISSING_ANCHORS')};
    const route = validModel && validRecords ? records.find(r => r.id === connection.id) : undefined;
    if (!route || route.status !== 'DISPLAY_CLEAR'
      || route.anchorStatus !== 'VIRTUAL_SURFACE_PORT_NOT_REAL_PIN'
      || !sameEndpoint(route.endpoints?.from, connection.from) || !sameEndpoint(route.endpoints?.to, connection.to)
      || route.wireRadiusMm !== report.wireRadiusMm || route.clearanceMm !== report.partClearanceMm
      || !(route.clearanceMm >= 0) || !Array.isArray(route.collisions) || route.collisions.length) return fallback;
    const candidate = {...logical, routingStatus: /** @type {const} */ ('MODEL_ASSUMED'),
      fromAnchorMm: route.fromAnchorMm, toAnchorMm: route.toAnchorMm, polylineMm: route.polylineMm,
      displayWireRadiusMm: route.wireRadiusMm, anchorStatus: route.anchorStatus};
    return hasWireRoute(candidate) ? candidate : fallback;
  });
}
