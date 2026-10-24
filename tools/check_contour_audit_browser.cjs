#!/usr/bin/env node
// Embedded report over local HTTP, with no external requests. Managed Chromium
// blocks file:// navigation; do not disable that policy or claim it was tested.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const http=require('node:http');
let chromium;try{({chromium}=require('playwright'));}catch{({chromium}=require(path.resolve(__dirname,'../build/browser-tools/node_modules/playwright')));}
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
 const output=path.resolve(__dirname,'../build/contour-audit');fs.mkdirSync(output,{recursive:true});
 const htmlPath=path.resolve(__dirname,'../docs/specimen/contour-audit-1.110.html');
 const server=http.createServer((req,res)=>{
  if(new URL(req.url,'http://localhost').pathname!=='/audit.html'){res.writeHead(404);res.end();return;}
  res.writeHead(200,{'Content-Type':'text/html; charset=utf-8'});res.end(fs.readFileSync(htmlPath));
 });
 try{
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const origin='http://127.0.0.1:'+server.address().port;
  const page=await browser.newPage({viewport:{width:1440,height:1200}}),errors=[],remote=[];
  page.on('pageerror',e=>errors.push(String(e)));page.on('request',r=>{if(/^https?:/.test(r.url())&&!r.url().startsWith(origin+'/'))remote.push(r.url());});
  await page.goto(origin+'/audit.html');
  await page.waitForFunction(()=>Boolean(window.auditReport));
  await page.evaluate(()=>document.fonts.ready);
  const loaded=await page.evaluate(async()=>{
   await Promise.all(['Regular','Italic'].map(s=>document.fonts.load('36px proof'+s,'яӨ')));
   return ['Regular','Italic'].map(s=>document.fonts.check('36px proof'+s,'яӨ'));
  });assert(loaded.every(Boolean),'Both embedded context fonts must load');
  assert.equal(await page.locator('.card').count(),24);
  await page.screenshot({path:path.join(output,'report-first-page.png')});
  await page.locator('.card').first().screenshot({path:path.join(output,'report-first-case.png')});
  const summary=await page.evaluate(()=>({sites:window.auditReport.cases.length,fonts:Object.keys(window.auditReport.fonts).length,errors:window.auditReport.errors,summary:window.auditReport.summary}));
  assert.equal(summary.fonts,6);assert.deepEqual(summary.errors,[]);assert(summary.sites>0);assert.equal(summary.summary.visual_acceptance,false);
  await page.selectOption('#style','Regular');await page.selectOption('#format','TTF');await page.fill('#search','ж');
  await page.selectOption('#priority','0');
  assert(await page.locator('.card').count()>0);await page.screenshot({path:path.join(output,'report-regular-zhe.png'),fullPage:true});
  await page.selectOption('#mode','atlas');await page.fill('#search','Ө');assert(await page.locator('.card').count()>0);
  const ink=await page.evaluate(()=>[...document.querySelectorAll('.card canvas')].map(c=>{
   const p=c.getContext('2d').getImageData(0,0,c.width,c.height-30).data;let count=0;for(let i=3;i<p.length;i+=4)if(p[i]>0)count++;return count;
  }));assert(ink.every(n=>n>20),'Previously skipped Ө must have actual outline ink in atlas');
  await page.screenshot({path:path.join(output,'report-alloffcurve-o.png'),fullPage:true});
  await page.locator('.card details').first().locator('summary').click();
  await page.locator('.comparison canvas').nth(2).waitFor({state:'attached'});
  assert(await page.locator('.comparison canvas').count()>=3);
  await page.selectOption('#mode','queue');await page.fill('#search','');await page.selectOption('#kind','curvature_wave');assert(await page.locator('.card').count()>0);
  await page.selectOption('#format','OTF');await page.selectOption('#style','Italic');assert(await page.locator('.card').count()>0);
  await page.selectOption('#kind','');await page.fill('#search','__no_such_glyph__');assert.equal(await page.locator('.card').count(),0);assert(await page.locator('#empty').isVisible());
  await page.setViewportSize({width:390,height:844});await page.fill('#search','я');assert(await page.locator('.card').count()>0);
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1),'Mobile report overflows horizontally');
  assert.deepEqual(errors,[]);assert.deepEqual(remote,[]);
  const report={platform:'Linux',engine:'Chromium '+browser.version(),html_sha256:crypto.createHash('sha256').update(fs.readFileSync(htmlPath)).digest('hex'),checks:['Embedded report over local HTTP without external requests','All six files represented','Queue and atlas filters','Ө outline drawn','Actual TTF/OTF/WOFF2 comparison','Wave filter','Empty search','Mobile layout'],not_tested:['file:// navigation: blocked by managed Chromium policy','Other operating systems and browsers'],page_errors:errors,remote_requests:remote,summary,failed:0};
  fs.writeFileSync(path.resolve(__dirname,'../docs/qa/contour-audit-browser-1.110.json'),JSON.stringify(report,null,2)+'\n');
  console.log('Contour report browser checks passed');
 }finally{await browser.close();server.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
