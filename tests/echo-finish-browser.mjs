// Local UI test only. Never uses printer APIs or sends a print job.
import {chromium} from 'playwright';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {writeFile} from 'node:fs/promises';
const base=process.env.ECHO_URL||'http://127.0.0.1:4176';
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const page=await browser.newPage({viewport:{width:1500,height:1000}});
const errors=[];page.on('pageerror',e=>errors.push(e.message));
try{
  await page.goto(base+'/?build=echo-f1-cn-v2&view=model&finish=ember-white');
  await page.waitForFunction(()=>{const v=document.querySelector('.studio-viewport');return v&&Number(v.dataset.nativeTotal)>0&&v.dataset.nativeLoaded===v.dataset.nativeTotal;},null,{timeout:120000});
  assert.equal(await page.locator('.viewport-error').count(),0);
  assert.match(await page.locator('.build-appearance').innerText(),/灰烬红 × 冰白/);
  const model=await (await page.request.get(base+'/api/authored-builds/echo-f1-cn-v2')).json();
  assert.deepEqual(new Set(model.parts.filter(p=>p.kind==='printed').map(p=>p.color)),new Set(['#F1EFE9','#983C40']));
  assert.deepEqual(model.parts.filter(p=>p.displayFinish==='silk').map(p=>p.id).sort(),['shell_front','shell_rear']);
  await page.screenshot({path:'builds/echo-f1-cn-v2/checks/ember-white-model.png'});
  await page.getByRole('button',{name:'打印文件',exact:true}).click();
  const printer=page.locator('#plate-printer');assert.equal(await printer.inputValue(),'');
  await printer.selectOption('h2c');
  assert.equal(await page.locator('.finish-downloads a').count(),2);
  for(const a of model.appearance.artifacts){
    const response=await page.request.get(base+'/api/authored-builds/echo-f1-cn-v2/files/'+a.file);
    assert.equal(response.status(),200,a.file);
    assert.equal(createHash('sha256').update(await response.body()).digest('hex'),a.sha256);
  }
  assert.match(await page.locator('.plate-card').nth(1).innerText(),/A4 \/ PLA Basic/);
  assert.match(await page.locator('.plate-card').nth(3).innerText(),/A1 \/ PLA Silk/);
  await page.locator('.build-appearance').scrollIntoViewIfNeeded();
  await page.screenshot({path:'builds/echo-f1-cn-v2/checks/ember-white-print.png'});
  await printer.selectOption('a1');assert.equal(await page.locator('.finish-downloads').count(),0);
  assert.equal(await page.locator('.plate-primary').count(),1);
  assert.deepEqual(errors,[]);
  await writeFile('builds/echo-f1-cn-v2/checks/appearance-browser.json',JSON.stringify({status:'PASS',checks:['38 native parts load','real finish assignments','no default printer','two hash-bound downloads','plate colours agree','other printers retain original files'],printSent:false},null,2));
  console.log('PASS: appearance, native viewport, material assignments and both downloads. No print commands.');
}finally{await browser.close();}
