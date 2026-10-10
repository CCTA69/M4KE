// Local component + real imported evidence + real HTTP service. No supplier calls.
import assert from 'node:assert/strict';
import path from 'node:path';
import os from 'node:os';
import {mkdtemp, mkdir, rm, writeFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {createServer} from 'vite';
import vue from '@vitejs/plugin-vue';
import {chromium} from 'playwright';
import {installChinaCarObservations} from '../procurement/install-china-car-observations.mjs';
import {installEchoCnObservations} from '../procurement/install-echo-cn-observations.mjs';
import {createProcurementService} from '../server/studio-procurement.mjs';

const root = fileURLToPath(new URL('../', import.meta.url));
const cnMode = process.env.M4KE_TEST_ECHO_CN === '1';
const isolated = await mkdtemp(path.join(os.tmpdir(), 'm4ke-prices-ui-'));
const out = path.join(root, 'test-results', `procurement-${Date.now()}`);
let vite, browser;
try {
  await mkdir(out, {recursive:true});
  const receipt = await (cnMode ? installEchoCnObservations : installChinaCarObservations)({root:path.join(isolated,'procurement')});
  const handle = createProcurementService({root:isolated, snapshotSha256:receipt.snapshotId,
    json:(res,status,value)=>{res.writeHead(status,{'content-type':'application/json'});res.end(JSON.stringify(value));}});
  const html = `<!doctype html><html><head><title>Procurement verification</title></head><body><div id="app"></div>
    <script type="module">
    import {createApp} from 'vue';
    import {createPinia} from 'pinia';
    import Panel from '/src/components/ProcurementPanel.vue';
    import {useStudio} from '/src/studio/store.ts';
    import '/src/studio-vue.css';
    const app=createApp(Panel), pinia=createPinia();app.use(pinia);
    useStudio(pinia).locale=new URL(location.href).searchParams.get('lang') || 'en';app.mount('#app');
    </script></body></html>`;
  vite = await createServer({root,configFile:false,plugins:[vue(),{name:'evidence-test',configureServer(server){
    server.middlewares.use((req,res,next)=>{
      const pathname=new URL(req.url,'http://localhost').pathname;
      if(pathname==='/pricing-test') {server.transformIndexHtml(req.url,html).then(h=>{res.setHeader('content-type','text/html');res.end(h);}).catch(next);return;}
      handle(req,res,pathname).then(handled=>{if(!handled)next();}).catch(next);
    });
  }}],server:{host:'127.0.0.1',port:0},optimizeDeps:{entries:[]}});
  await vite.listen();
  const base=`http://127.0.0.1:${vite.httpServer.address().port}`;
  browser=await chromium.launch({headless:true,...(process.env.M4KE_BROWSER_EXECUTABLE || process.platform==='win32' ? {executablePath:process.env.M4KE_BROWSER_EXECUTABLE || 'C:/Program Files/Google/Chrome/Application/chrome.exe'} : {})});
  const page=await browser.newPage({viewport:{width:1440,height:1000}}), errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  // Block any accidental external request; this test must remain wholly local.
  await page.route('**/*',route=>new URL(route.request().url()).origin===base ? route.continue() : route.abort());
  for(const lang of ['en','zh']) {
    await page.goto(`${base}/pricing-test?lang=${lang}`);
    const coverage=page.getByTestId('car-price-coverage');await coverage.waitFor();
    assert.equal(await coverage.locator('li').count(),7);
    assert.match(await coverage.innerText(),lang==='en'?/Whole-car total: UNKNOWN/:/整车总价：未知/);
    assert.match(await coverage.innerText(),/0\/7/);
    assert.match(await coverage.innerText(),lang==='en'?/Historical/:/历史/);
    const cn=page.getByTestId('echo-cn-price-coverage');await cn.waitFor();
    assert.equal(await cn.locator('.cn-bom-line').count(),17);
    assert.match(await cn.innerText(),cnMode?/3\/17/:/0\/17/);
    assert.match(await cn.innerText(),/CNY 566/);
    assert.match(await cn.innerText(),lang==='en'?/Whole-car purchase total: UNKNOWN/:/整车采购总价：未知/);
    const conflict=cn.getByTestId('sensor-dimension-conflict');
    assert.match(await conflict.innerText(),/22 × 30 mm/);assert.match(await conflict.innerText(),/22 × 32 mm/);
    assert.match(await conflict.innerText(),/DIMENSIONS_TO_CONFIRM/);
    const body=await page.locator('body').innerText();
    for(const price of (cnMode?['135.00','40.00','20.00']:['29.25','57.48','65.88']))assert(body.includes(price));
    assert.equal(await page.locator('.source-grid > article').count(),3);
    assert.equal(await page.locator('[role="alert"]').count(),0);
    await page.screenshot({path:path.join(out,`${lang}.png`),fullPage:true});
  }
  // Corrupt a retained source; refresh must remove all prices, not retain old data.
  const snapshotPath=path.join(isolated,'procurement/snapshots',receipt.snapshotId);
  const {readFile}=await import('node:fs/promises');
  const snapshot=JSON.parse(await readFile(path.join(snapshotPath,'snapshot.json'),'utf8'));
  await writeFile(path.join(snapshotPath,snapshot.evidence[0].file),'tampered');
  await page.getByRole('button',{name:'重新检查本地证据'}).click();
  await page.getByRole('alert').waitFor();
  assert.equal(await page.getByTestId('car-price-coverage').count(),0);
  assert.equal(await page.getByTestId('echo-cn-price-coverage').count(),0);
  assert.equal(await page.locator('.source-grid > article').count(),0);
  assert.deepEqual(errors,[]);
  console.log(JSON.stringify({status:'PASS',mode:cnMode?'CN v2':'historical',snapshotSha256:receipt.snapshotId,languages:['en','zh'],entries:3,cnLines:17,cnObservedLines:cnMode?3:0,tamper:'503 clears prices',screenshots:out}));
} finally {
  await browser?.close();await vite?.close();
  await rm(isolated,{recursive:true,force:true});
}
