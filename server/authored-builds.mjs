import path from 'node:path';
import {readFile, realpath} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {sendArtifact} from './studio-http.mjs';

/** Read-only, explicit build package. Never masquerades as an inference job. */
export function createAuthoredBuilds(root) {
  return async (req,res,pathname) => {
    if (!pathname.startsWith('/api/authored-builds/')) return false;
    const fail = (status,message) => {res.writeHead(status,{'Content-Type':'application/json'});res.end(JSON.stringify({error:message}));return true;};
    if (!['GET','HEAD'].includes(req.method)) return fail(405,'Build packages are read-only.');
    const match = /^\/api\/authored-builds\/(echo-f1-v1|echo-f1-cn-v2)(?:\/files\/(.+))?$/.exec(pathname);
    if (!match) return fail(404,'Unknown authored build.');
    const dir=path.join(root,'builds',match[1]);
    let manifest;
    try {manifest=JSON.parse(await readFile(path.join(dir,'manifest.json'),'utf8'));}
    catch {return fail(404,'Build package is not generated yet.');}
    if(manifest.packageStatus!=='READY_FOR_FIT_CHECK') return fail(409,'Build package is incomplete; finish CAD checks and packaging first.');
    if (!match[2]) {
      await sendArtifact(req,res,Buffer.from(JSON.stringify(manifest)),{'Content-Type':'application/json','Cache-Control':'no-store'});
      return true;
    }
    const allowed=new Map([
      ['ECHO-F1-build-package.zip',null],['ECHO-F1-assembly.step',null],['instructions.html',null],
      ['BOM.csv',null],['wiring.svg',null],['preview.png',null],['connections.csv',null],['print/00_fit_coupon.stl',null],
      ['checks/geometry.json',null],['checks/engineering.json',null],['checks/firmware-tests.txt',null],
      ['checks/wire-display.json',null],
      ['checks/wire-clearance-tests.txt',null],['checks/wiring-ui.json',null],
      ['firmware/main.py',null],['firmware/controller.py',null],['firmware/config.py',null],
    ]);
    for (const p of manifest.cadParts) {
      allowed.set(`assembly-parts/${p.id}.stl`,p.sha256.stl);
      allowed.set(`step/${p.id}.step`,p.sha256.step);
    }
    for (const p of manifest.printParts) allowed.set(p.file,p.sha256);
    // Generated plate artifacts are explicit and hash-bound, never a directory wildcard.
    for (const p of [...(manifest.printPlan?.projects || []), ...(manifest.appearance?.artifacts || [])]) {
      if (/^plates\/[a-zA-Z0-9_-]+(?:\.[a-zA-Z0-9_-]+)*\.3mf$/.test(p.file) && /^[a-f0-9]{64}$/.test(p.sha256)) allowed.set(p.file,p.sha256);
      for (const plate of p.plates || []) {
        if (/^plates\/[a-zA-Z0-9_-]+\.svg$/.test(plate.preview) && /^[a-f0-9]{64}$/.test(plate.sha256Preview)) allowed.set(plate.preview,plate.sha256Preview);
      }
    }
    const name=match[2];
    if(!allowed.has(name)) return fail(404,'Not in build manifest.');
    let bytes;
    try {
      const base=await realpath(dir), file=await realpath(path.join(dir,name));
      if(!file.startsWith(base+path.sep))return fail(403,'Outside package.');
      bytes=await readFile(file);
    } catch {return fail(404,'Artifact is not available yet.');}
    if(bytes.length>128*1024*1024)return fail(413,'Artifact exceeds size limit.');
    const expected=allowed.get(name);
    if(expected&&createHash('sha256').update(bytes).digest('hex')!==expected)return fail(409,'Artifact changed; regenerate its manifest before downloading.');
    const ext=path.extname(name);
    const types={'.3mf':'model/3mf','.stl':'model/stl','.svg':'image/svg+xml','.png':'image/png','.html':'text/html; charset=utf-8','.json':'application/json','.csv':'text/csv; charset=utf-8','.txt':'text/plain; charset=utf-8','.py':'text/plain; charset=utf-8','.zip':'application/zip'};
    await sendArtifact(req,res,bytes,{'Content-Type':types[ext]||'application/octet-stream','Cache-Control':'no-store','Content-Disposition':`${['.html','.svg','.png','.json','.txt','.py'].includes(ext)?'inline':'attachment'}; filename="${path.basename(name)}"`,...['.html','.svg'].includes(ext)?{'Content-Security-Policy':"sandbox allow-downloads; default-src 'none'; style-src 'unsafe-inline'; img-src 'self' data:"}:{}});
    return true;
  };
}
