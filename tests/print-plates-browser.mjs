// UI/download regression only: this does not operate a printer or certify a car.
import {chromium} from 'playwright';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {mkdir, writeFile} from 'node:fs/promises';

const base=process.env.ECHO_URL||'http://127.0.0.1:4176';
const out='builds/echo-f1-cn-v2/checks';
await mkdir(out,{recursive:true});
const browser=await chromium.launch({headless:true,
  executablePath:process.env.ECHO_BROWSER||'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const page=await browser.newPage({viewport:{width:1440,height:1000}});
const errors=[],badResponses=[],checks=[];
page.on('pageerror',e=>errors.push(e.message));
page.on('response',r=>{if(r.status()>=400)badResponses.push([r.status(),r.url()]);});
const check=async(name,fn)=>{await fn();checks.push({name,status:'PASS'});};
const imageCheck=()=>Array.from(document.querySelectorAll('.plate-card img')).every(i=>i.complete&&i.naturalWidth>0);
try{
  await page.goto(base+'/?build=echo-f1-cn-v2&view=print');
  const printer=page.locator('#plate-printer');
  await printer.waitFor();
  await check('No default printer; individual STL files are advanced fallback',async()=>{
    assert.equal(await printer.inputValue(),'');
    assert.equal(await page.locator('.plate-primary').count(),0);
    assert.equal(await page.locator('.echo-stl-backup').getAttribute('open'),null);
    assert.equal(await page.locator('.echo-print-grid article').count(),18);
  });
  const build=await (await page.request.get(base+'/api/authored-builds/echo-f1-cn-v2')).json();
  assert.equal(build.printPlan.artifactRevision,2);
  for(const project of build.printPlan.projects){
    await check(`${project.id}: correct plate cards and source-bound whole-project download`,async()=>{
      await printer.selectOption(project.id);
      assert.equal(await page.locator('.plate-card').count(),project.plates.length);
      await page.locator('.plate-card').last().scrollIntoViewIfNeeded();
      await page.waitForFunction(imageCheck);
      const link=await page.locator('.plate-primary').getAttribute('href');
      assert.equal(link,'/api/authored-builds/echo-f1-cn-v2/files/'+project.file);
      assert.match(project.file,/-r2\.3mf$/,'The UI must not serve the broken first revision');
      const response=await page.request.get(base+link);
      assert.equal(response.status(),200);
      assert.match(response.headers()['content-type'],/model\/3mf/);
      assert.equal(createHash('sha256').update(await response.body()).digest('hex'),project.sha256);
    });
  }
  await printer.selectOption('h2c');
  await check('Personal plate checkmarks persist; do not imply automatic acceptance',async()=>{
    await page.locator('.plate-card input').first().check();
    await page.reload();await printer.waitFor();
    assert.equal(await printer.inputValue(),'h2c');
    assert.equal(await page.locator('.plate-card input').first().isChecked(),true);
    assert.match(await page.locator('.plate-finish').innerText(),/不是自动验收/);
    await page.locator('.plate-card input').first().uncheck();
    await printer.selectOption('a1');
    assert.equal(await page.locator('.plate-card input:checked').count(),0);
    await printer.selectOption('h2c');
    assert.equal(await page.locator('.plate-card input:checked').count(),0);
  });
  await page.locator('.plate-intro').scrollIntoViewIfNeeded();
  await page.screenshot({path:out+'/print-ui.png',fullPage:true});
  await check('Unsupported printer gives explicit instruction, not mismatched 3MF',async()=>{
    await printer.selectOption('other');
    assert.equal(await page.locator('.plate-primary').count(),0);
    assert.match(await page.locator('.plate-notice').innerText(),/不要缩小模型/);
  });
  await printer.selectOption('h2c');
  await check('Print flow opens the existing eleven-step 3D assembly tutorial',async()=>{
    await page.getByRole('button',{name:'开始装配',exact:true}).click();
    assert.match(page.url(),/view=assemble/);
    assert.equal(await page.locator('.echo-step-list button').count(),11);
    await page.waitForFunction(()=>{const v=document.querySelector('.studio-viewport');return v&&Number(v.dataset.nativeTotal)>0&&v.dataset.nativeLoaded===v.dataset.nativeTotal;},null,{timeout:120000});
    await page.getByRole('button',{name:'下一步',exact:true}).click();
    await page.getByRole('button',{name:'播放装配动画',exact:true}).click();
    await page.waitForFunction(()=>Number(document.querySelector('.studio-viewport').dataset.assemblyProgress)===1);
    assert.equal(await page.locator('.viewport-error').count(),0);
    await page.screenshot({path:out+'/print-to-assembly.png'});
  });
  const guide=await browser.newPage({viewport:{width:1100,height:850}});
  guide.on('pageerror',e=>errors.push(e.message));
  await guide.goto(base+'/api/authored-builds/echo-f1-cn-v2/files/instructions.html');
  await check('Guide contains printing, wiring, assembly, firmware and physical-test records',async()=>{
    for(const id of ['printing','wiring','assembly','firmware','acceptance'])assert.equal(await guide.locator('#'+id).count(),1,id);
    await guide.locator('#printing details').first().locator('summary').click();
    await guide.waitForFunction(()=>Array.from(document.images).every(i=>i.complete&&i.naturalWidth>0));
    assert.equal(await guide.locator('#printing a[href$=".3mf"]').count(),5);
    for(const file of ['config.py','controller.py','main.py']){
      const r=await guide.request.get(base+'/api/authored-builds/echo-f1-cn-v2/files/firmware/'+file);
      assert.equal(r.status(),200,file);
    }
    await guide.screenshot({path:out+'/print-guide.png'});
  });
  await page.goto(base+'/?build=echo-f1-cn-v2&view=print');await printer.waitFor();
  await page.setViewportSize({width:390,height:844});
  await page.screenshot({path:out+'/print-mobile.png',fullPage:true});
  await check('Narrow-screen print panel and handbook have no horizontal overflow',async()=>{
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
    await guide.setViewportSize({width:390,height:844});
    assert(await guide.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  });
  await printer.selectOption(''); // Isolated test context; never mark real-world work complete.
  await guide.close();
  assert.deepEqual(errors,[]);assert.deepEqual(badResponses,[]);
  await writeFile(out+'/print-browser.json',JSON.stringify({status:'PASS',checks,errors,badResponses,physicalTest:'NOT_RUN',printSent:false},null,2));
  console.log(`PASS: ${checks.length} print/tutorial browser checks; no printing or physical acceptance.`);
}finally{await browser.close();}
