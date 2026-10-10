// Rapier is bundled locally. Permit WebAssembly compilation, not JavaScript eval
// or remote scripts; browser regressions use this same production policy.
export const BROWSER_CSP = "default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'; font-src 'self' data:; worker-src 'self' blob:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'";
