#!/usr/bin/env node
// Linux Chromium acceptance of the actual six published font files.
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const crypto = require('node:crypto');
const {execFileSync}=require('node:child_process');
let chromium;
try { ({chromium}=require('playwright')); }
catch { ({chromium}=require(path.resolve(__dirname,'../build/browser-tools/node_modules/playwright'))); }
const root = path.resolve(__dirname, '..');
const dest = path.join(root, 'build/premium/browser');
fs.mkdirSync(dest, {recursive:true});
const server = http.createServer((req,res) => {
  const name=path.resolve(root, '.'+decodeURIComponent(new URL(req.url,'http://localhost').pathname));
  if (!name.startsWith(root+path.sep)) {res.writeHead(403);res.end();return;}
  const types={'.html':'text/html; charset=utf-8','.css':'text/css','.ttf':'font/ttf','.otf':'font/otf','.woff2':'font/woff2'};
  fs.readFile(name,(err,data)=>{res.writeHead(err?404:200,{'Content-Type':types[path.extname(name)]||'application/octet-stream'});res.end(err?'Missing':data);});
});
(async()=>{
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',headless:true,
                                       args:['--no-sandbox','--disable-dev-shm-usage']});
  try {
    const page=await browser.newPage({viewport:{width:1440,height:1100},deviceScaleFactor:1});
    const errors=[];page.on('pageerror',e=>errors.push(String(e)));
    page.on('requestfailed',r=>errors.push(r.url()+': '+r.failure().errorText));
    await page.goto('http://127.0.0.1:'+server.address().port+'/docs/specimen/family.html');
    const report=await page.evaluate(async()=>{
      const formats=['ttf','otf','webfonts'];const results=[];
      for (const format of formats) for(const style of ['Regular','Italic']) {
        const family='Test-'+format+'-'+style;
        const file='../../fonts/'+format+'/VeryPeriSerif-'+style+(format==='webfonts'?'.woff2':'.'+format);
        const face=new FontFace(family,`url("${file}")`,{style:style==='Italic'?'italic':'normal',weight:'400'});
        await face.load();document.fonts.add(face);
        const canvas=document.createElement('canvas');const ctx=canvas.getContext('2d');ctx.font=(style==='Italic'?'italic ':'')+'64px "'+family+'"';
        const texts=['Съешь же ещё этих мягких французских булок.','Қазақ тілі: жаңбыр, үміт, ұлы, өмір.',
                     'глина город дорога · гүл ертеңгі',
                     'о́ я́ ы́ э́ ю́ ә́ ү́ і́ ё́ · О́ Ә́ Ү́','office affine final · 12 500 ₸'];
        results.push({format,style,status:face.status,widths:texts.map(t=>ctx.measureText(t).width)});
      }
      await document.fonts.ready;
      const loaded=['normal','italic'].map(style=>document.fonts.check(style+' 64px VP','Қазақ өмір үміт'));
      const cell=[];
      for(const style of ['normal','italic']) {
        const row=[];
        for(const c of '0123456789') {
          const span=document.createElement('span');span.textContent=c;
          Object.assign(span.style,{fontFamily:'VP',fontSize:'64px',fontStyle:style,fontVariantNumeric:'tabular-nums',display:'inline-block'});
          document.body.append(span);row.push(span.getBoundingClientRect().width);span.remove();
        }
        cell.push(row);
      }
      return {results,loaded,tabular_cells:cell};
    });
    if(errors.length)throw Error(errors.join('\n'));
    if(!report.loaded.every(Boolean))throw Error('CSS family/style not loaded');
    for(const style of ['Regular','Italic']) {
      const rows=report.results.filter(r=>r.style===style);
      if(rows.some(r=>r.status!=='loaded'))throw Error('Font format not loaded');
      for(let i=1;i<rows.length;i++)for(let j=0;j<rows[0].widths.length;j++)
        if(Math.abs(rows[i].widths[j]-rows[0].widths[j])>.05)throw Error('Cross-format shaping widths differ');
    }
    if(report.tabular_cells.some(row=>new Set(row).size!==1))throw Error('Browser tabular widths differ');
    await page.screenshot({path:path.join(dest,'family.png'),fullPage:true});
    await page.pdf({path:path.join(dest,'live-text.pdf'),format:'A4',printBackground:true});
    const pdf=path.join(dest,'live-text.pdf');
    const extracted=execFileSync('pdftotext',[pdf,'-'],{encoding:'utf8'}).replace(/\s+/g,' ');
    report.pdf_text_occurrences={};
    for(const text of ['Красота начинается с внимания к деталям.','Қазақ тілі: жаңбыр, үміт, ұлы, өмір.','глина город дорога · гүл ертеңгі']) {
      const count=extracted.split(text).length-1;
      if(count<2)throw Error('PDF text roundtrip must pass in both styles: '+text);
      report.pdf_text_occurrences[text]=count;
    }
    const embedded=execFileSync('pdffonts',[pdf],{encoding:'utf8'});
    if(!embedded.includes('VeryPeriSerif-Regular')||!embedded.includes('VeryPeriSerif-Italic'))
      throw Error('Both font styles must be embedded in the PDF');
    report.pdf_text_roundtrip=true;report.pdf_font_table=embedded;
    const fonts={};
    for(const r of report.results) {
      const ext=r.format==='webfonts'?'woff2':r.format;
      const rel='fonts/'+r.format+'/VeryPeriSerif-'+r.style+'.'+ext;
      fonts[rel]=crypto.createHash('sha256').update(fs.readFileSync(path.join(root,rel))).digest('hex');
    }
    fs.writeFileSync(path.join(root,'docs/qa/browser-check.json'),JSON.stringify({platform:'Linux',engine:'Chromium '+browser.version(),
      checks:['All six formats loaded','CSS Regular/Italic loaded','Equal cross-format sample widths','Tabular figures equal in both styles','PDF with both styles embedded','Russian/Kazakh PDF text roundtrip'],
      fonts,results:report,failed:0,not_tested:['Windows native apps','macOS native apps','Adobe','Office','Figma application','Physical print']},null,2)+'\n');
    console.log('Browser PASS: six formats, both styles, tabular figures, PDF.');
  } finally {await browser.close();server.close();}
})().catch(e=>{console.error(e);server.close();process.exitCode=1;});
