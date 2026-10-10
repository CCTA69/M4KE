import assert from 'node:assert/strict';
import {mkdir,writeFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {createServer} from 'vite';
import {chromium} from 'playwright';
import {BROWSER_CSP} from '../server/browser-policy.mjs';

const root=fileURLToPath(new URL('../',import.meta.url)),out=path.join(root,'test-results/driving-browser');await mkdir(out,{recursive:true});
const html=`<!doctype html><html><body style="margin:0;background:#111926"><div id="sandbox"></div><script type="module" src="/sandbox-fixture-entry.js"></script></body></html>`;
const entry=`
import {createApp,h} from '/node_modules/.vite/deps/vue.js';
import DrivingSandbox from '/src/components/DrivingSandbox.vue';
const parts=[{id:'chassis',name:'Fixture body',kind:'printed',material:'PLA',color:'#e35336',position:[0,0,38],rotation:[0,0,0],shape:{type:'box',size:[286,182,76]}}];
for(const side of [-1,1])for(const [end,x,r] of [['front',-85,23.4],['rear',92,21]])parts.push({id:end+'_wheel_'+side,name:end+' wheel',kind:'purchased',material:'rubber',color:'#32343a',position:[x,side*70,r],rotation:[90,0,0],shape:{type:'cylinder',radius:r,height:14}});
window.fixture=createApp({render:()=>h(DrivingSandbox,{parts,locale:'zh'})}).mount('#sandbox');
`;
const vite=await createServer({root,server:{host:'127.0.0.1',port:0},plugins:[{name:'sandbox-fixture',configureServer(server){
  server.middlewares.use(async(req,res,next)=>{
    const route=req.url?.split('?')[0];
    if(route==='/sandbox-fixture-entry.js'){res.setHeader('Content-Type','application/javascript');res.end(entry);return;}
    if(route!=='/sandbox-fixture')return next();
    res.setHeader('Content-Type','text/html');res.setHeader('Content-Security-Policy',BROWSER_CSP);
    res.end(html);
  });
}}]});
await vite.listen();const base=`http://127.0.0.1:${vite.httpServer.address().port}`;
const browser=await chromium.launch({headless:true,...(process.platform==='win32'?{executablePath:process.env.M4KE_BROWSER_EXECUTABLE||'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'}:{}),args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const page=await browser.newPage({viewport:{width:1365,height:950},deviceScaleFactor:2});const errors=[],external=[],writes=[];
page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(!r.url().startsWith(base)&&!r.url().startsWith('data:'))external.push(r.url());if(!['GET','HEAD'].includes(r.method()))writes.push(r.url());});
try{
  const response=await page.goto(base+'/sandbox-fixture');assert.equal(response.headers()['content-security-policy'],BROWSER_CSP);
  assert(!BROWSER_CSP.includes("'unsafe-eval'"));await page.locator('[data-ready="true"]').waitFor({timeout:45000});
  assert.match(await page.locator('.drive-controls').innerText(),/286.0 × 182.0 × 76.0/);
  assert.equal(await page.evaluate(()=>{const host=document.querySelector('.drive-canvas').getBoundingClientRect(),canvas=document.querySelector('.drive-canvas canvas').getBoundingClientRect();return Math.abs(host.width-canvas.width)<1&&Math.abs(host.height-canvas.height)<1;}),true,'High-DPI canvas must fit its viewport, not crop the model.');
  await page.getByRole('button',{name:'响声',exact:true}).click();await page.getByRole('button',{name:'开始 / 继续',exact:true}).click();
  await page.waitForFunction(()=>parseFloat(document.querySelector('.drive-hud strong').textContent)>0.1,{},{timeout:15000});
  const angles=await page.locator('.wheel-reading').evaluateAll(nodes=>nodes.map(n=>({id:n.dataset.wheelId,angle:Number(n.dataset.angle)})));
  assert.equal(angles.length,4);assert(angles.every(w=>Math.abs(w.angle)>.01));
  const front=angles.find(w=>w.id.startsWith('front')),rear=angles.find(w=>w.id.startsWith('rear'));
  assert.ok(Math.abs(front.angle/rear.angle-21/23.4)<1e-6,'Unequal wheel diameters must not use one fake animation speed.');
  await page.getByRole('button',{name:'安静',exact:true}).click();await page.waitForFunction(()=>parseFloat(document.querySelector('.drive-hud strong').textContent)===0,{},{timeout:15000});
  await page.getByRole('button',{name:'暂停',exact:true}).click();assert.equal(await page.locator('[data-testid="driving-sandbox"]').getAttribute('data-running'),'false');
  await page.getByRole('button',{name:'复位并应用参数',exact:true}).click();
  assert.match(await page.locator('.drive-hud').innerText(),/0.00 m/);
  assert.equal(await page.locator('.wheel-reading').evaluateAll(nodes=>nodes.every(n=>Number(n.dataset.angle)===0)),true);
  await page.locator('summary').click();const mass=page.getByLabel('总质量 / kg');await mass.focus();await page.keyboard.press('Space');
  assert.equal(await page.locator('[data-testid="driving-sandbox"]').getAttribute('data-running'),'false');await mass.fill('0');await page.getByRole('button',{name:'复位并应用参数',exact:true}).click();
  await page.getByRole('alert').waitFor();assert.equal(await page.getByRole('button',{name:'开始 / 继续',exact:true}).isDisabled(),true);
  await mass.fill('0.9');await page.getByRole('button',{name:'复位并应用参数',exact:true}).click();assert.equal(await page.getByRole('alert').count(),0);
  await page.screenshot({path:path.join(out,'sandbox.png')});await page.setViewportSize({width:390,height:844});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  assert.deepEqual(errors,[]);assert.deepEqual(external,[]);assert.deepEqual(writes,[]);
  await writeFile(path.join(out,'report.json'),JSON.stringify({scope:'Fixture browser test, not a model or physical test',status:'PASS',checks:['geometry dimensions','loud forward','quiet brake','reset','input keys do not control viewport','invalid parameters fail closed','mobile width','no external network','no design writes'],errors,external,writes},null,2));
  console.log('Driving sandbox browser checks passed.');
}finally{await browser.close();await vite.close();}
