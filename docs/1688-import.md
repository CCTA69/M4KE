# 1688 parts observations

Import operator-reviewed electronic or mechanical parts listings into M4KE's
existing hash-checked procurement store. This is an **offline intake adapter**,
not a scraper, official API client, complete 1688 database or live quotation.
It preserves specifications, exact SKU/variant identity, quantity prices and the
supplier's offer link. It does not change the application's pinned sourcing
snapshot, design choices or engineering catalog.

## Use

1. Save an offer's evidence as HTML, TXT, JSON or PDF using an authorized access
   method. Keep the actual capture time. Remove account, address, Cookie, token
   and other private information **before** importing. Hashes bind the saved or
   redacted evidence, not a claim that the file is the complete page.
2. Review the evidence and create the JSON below. Record the exact variant and
   order unit; a pack of ten is still priced per **pack**. Use one entry per SKU
   and one input file per offer. Every entry must come from that same offer.
3. Run from the repository root (Node 22.12+):

   ```sh
   node procurement/1688-import.mjs reviewed.json capture.html
   ```

   Optional `--root DIRECTORY` selects a separate procurement store. Otherwise,
   the root is the module's directory, independent of the working directory.
4. The JSON receipt includes `snapshotId`, `directory`, evidence hashes and
   `networkUsed:false`. The bundle remains under a unique `incoming/1688-...`
   directory. Reimporting identical reviewed content/evidence reuses the stored
   snapshot; it does not refresh the capture time.

The default `incoming/` and `snapshots/` directories are private and Git-ignored.
Keep custom stores out of source control too. Evidence is not rendered or
executed. Failed staging is retained for diagnosis; existing bundles are not
overwritten. Coordinate before selecting another agent's store.

## Reviewed input format

**Synthetic example only.** The offer ID, identity and price below are invented
test data. Replace them with reviewed observations. This is M4KE's input schema,
**not** a native 1688 API response schema.

```json
{
  "schemaVersion": 1,
  "url": "https://detail.1688.com/offer/123456789.html",
  "capturedAt": "2026-01-01T09:00:00Z",
  "access": "operator-authenticated",
  "extraction": "Synthetic example. Replace with how fields were checked and what was redacted.",
  "entries": [{
    "id": "test-sku-a",
    "kind": "component",
    "supplierId": "test-supplier",
    "market": "CN",
    "identity": {
      "manufacturer": "Test maker", "mpn": "TEST-1", "supplierSku": "SKU-A",
      "variant": "Pack of 10", "package": "10 pieces per pack", "manufacturerRevision": null
    },
    "evidenceIds": ["listing"],
    "price": {
      "status": "observed-tiers", "currency": "CNY", "unit": "pack",
      "tiers": [{"minimumQuantity": 2, "unitPrice": "12.50"}],
      "advertisedAmount": null, "tax": "unknown", "shipping": "unknown", "evidenceId": "listing"
    },
    "availability": {"status": "unknown", "quantity": null, "unit": null, "evidenceId": null},
    "minimumOrderQuantity": null,
    "orderMultiple": null,
    "specs": [{
      "name": "Shaft diameter", "value": "3", "unit": "mm",
      "conditions": "Supplier nominal; unmeasured", "basis": "supplier-listing", "evidenceId": "listing"
    }],
    "relatesTo": {"catalogId": null, "relationship": "unqualified-candidate", "note": "Requires independent qualification."},
    "notes": []
  }]
}
```

All six top-level fields are required; extras are rejected. `access` is `public`
or `operator-authenticated`. Only canonical
`https://detail.1688.com/offer/<numeric-id>.html` URLs are admitted. Remove tracking
parameters, fragments and credentials. `capturedAt` is UTC, never the time an old
saved page happens to be imported. Method is `operator-export`; supplier update
time remains unknown (`sourceUpdatedAt:null`).

Entries follow the [SupplierSnapshot schema](../procurement/SCHEMA.md). Evidence
references must be `listing` (or null where allowed). Resolve missing identity
before admitting a quotable entry; never invent manufacturer/MPN/SKU values.
Prices are positive decimal **strings**, not floating-point numbers. For a
headline price use `advertised-only`, `tiers:[]`, and `advertisedAmount`. Use
`unavailable` or `login-required` with no amounts where appropriate. MOQ and order
multiples stay null unless observed; a tier threshold does not prove either.
Omit unknown specifications instead of assigning zero.

All entries remain CN candidates with `catalogId:null` and
`relationship:unqualified-candidate`. Specs use `supplier-listing` basis; reseller
pages do not establish manufacturer-datasheet evidence. Hashes detect byte changes
but cannot verify listing truth or transcription (`semanticClaimsVerified:false`).

## Read and quote

Use `readImportedSnapshot(snapshotId, {root})` or
`quoteImportedSnapshot(snapshotId, request, {root})` from `procurement/import.mjs`.
The latter rechecks hashes before calculating. Requests include exact `entryId`,
`manufacturer`, `mpn`, `supplierSku`, `variant`, `quantity`, `unit` and `currency`.
There is no variant substitution, unit conversion, stock inference or purchase.
Default freshness is 24 hours. Fresh observations are still `INDICATIVE_ONLY`,
with unresolved tax/shipping/availability flags; stale prices stay stale.

## Official API connection: pending

A buyer account does not establish product API permissions. Register the app
through the [official 1688 Open Platform](https://aop.alibaba.com/) and confirm its
currently approved product/search APIs and authorization method. Credentials
belong in a local secret store, never in reviewed JSON or GitHub.

A working live adapter still needs an approved app, verified current endpoint
and response documentation, and an authorized smoke test binding exact SKU,
price unit and capture time to returned evidence. This importer assumes no API
endpoint names, signature algorithm or live access. Login, CAPTCHA and access
controls are not bypassed. Future API responses need a separate reviewed mapping;
do not automatically relabel API calls as operator exports.

## Verification

```sh
node --test tests/1688-import.test.mjs tests/procurement.test.mjs tests/studio-procurement.test.mjs
python tests/submission_package_test.py
```

Tests use synthetic evidence, real filesystem import/read/quote operations, and
the CLI. They do not prove real supplier availability, API access, dimensional
accuracy, physical fit or manufacture. Private supplier fixture tests stay
skipped when separately held captures are absent.
