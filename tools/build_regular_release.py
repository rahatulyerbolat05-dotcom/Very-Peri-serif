#!/usr/bin/env python3
"""Build, validate and package the final installable Regular from current sources."""
import argparse,contextlib,datetime,hashlib,json,re,shutil,subprocess,sys,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from fontTools.ttLib import TTFont,newTable
import ots
from build_draft_font import main as build_stage
from check_draft_font import main as validate


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save_json(path,value):Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def command(args,log):
    with Path(log).open('w') as stream:subprocess.run(args,stdout=stream,stderr=subprocess.STDOUT,check=True)

def specimen(ttf,path,config):
    from alphabet_sheet import canvas,text,MplPen,PathPatch,plt,UP,LOW,KZ_UP,KZ_LOW
    from matplotlib.transforms import Affine2D
    from matplotlib.backends.backend_pdf import PdfPages
    import uharfbuzz as hb
    font=TTFont(ttf);gs=font.getGlyphSet();h=hb.Font(hb.Face(Path(ttf).read_bytes()));hb.ot_font_set_funcs(h);h.scale=(1000,1000)
    def line(ax,s,x,y,size=75,features=None):
        b=hb.Buffer();b.add_str(s);b.guess_segment_properties();hb.shape(h,b,features or {});z=size/1000
        for n,pos in zip(b.glyph_infos,b.glyph_positions):
            pen=MplPen(gs);gs[font.getGlyphName(n.codepoint)].draw(pen)
            if pen.vertices:ax.add_patch(PathPatch(pen.result(),facecolor='#272333',edgecolor='none',transform=Affine2D().scale(z,-z).translate(x+pos.x_offset*z,y-pos.y_offset*z)+ax.transData))
            x+=pos.x_advance*z
    fixed=datetime.datetime.fromisoformat(config['date']).replace(tzinfo=datetime.timezone.utc)
    with PdfPages(path,metadata={'Title':config['family']+' Regular '+config['version'],'Author':'Very Peri Serif project','CreationDate':fixed,'ModDate':fixed}) as pdf:
        fig,ax=canvas(1200,1697);text(ax,50,40,config['family'],45);text(ax,50,110,'Regular · '+config['version'],24)
        for s,y,size in [('Съешь же ещё этих',340,112),('мягких французских',495,112),('булок, да выпей чаю.',650,112),('Қазақ тілі — әдемі тіл.',880,106),('Күн, гүл, үміт, ұлт, құс.',1030,100),('A thoughtful serif.',1270,120),('office affine final · 1 000 ₸',1450,100)]:line(ax,s,50,y,size)
        pdf.savefig(fig);plt.close(fig)
        fig,ax=canvas(1200,1697);text(ax,50,40,'Русский · Қазақша · Latin',33)
        for k,chars in enumerate([UP+KZ_UP,LOW+KZ_LOW]):
            for i in range(0,len(chars),14):line(ax,' '.join(chars[i:i+14]),50,270+k*550+i//14*165,95)
        line(ax,'ABCDEFGHIJKLMNOPQRSTUVWXYZ',50,1410,70);line(ax,'abcdefghijklmnopqrstuvwxyz',50,1520,86)
        pdf.savefig(fig);plt.close(fig)
        fig,ax=canvas(1200,1697);text(ax,50,40,'Альтернативы и набор',33)
        rows=[('Основные формы','дело  шёпот  тишина',{}),('Печатная д · ss07','дело  дождь  двадцать',{'ss07':True}),('Альтернативная т · ss08','текст  театр  тишина',{'ss08':True}),('Основные капли','ц щ қ ң Ц Щ Қ Ң',{}),('Прежние окончания · ss09','ц щ қ ң Ц Щ Қ Ң',{'ss09':True}),('Контекстные формы','пн по пк · кн ко · қн қо',{}),('Цены и знаки','1 000 ₸ · 500 ₽ · № 12 · «текст»',{})]
        for i,(label,s,features) in enumerate(rows):text(ax,50,150+i*210,label,22);line(ax,s,50,265+i*210,95,features)
        pdf.savefig(fig);plt.close(fig)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--quality',action='store_true',help='Also run FontBakery and Hyperglot; install font/requirements-quality.txt first');args=parser.parse_args()
    config=json.loads(Path('data/params.json').read_text())['regular_release'];out=Path(config['directory']);out.mkdir(parents=True,exist_ok=True);build=Path('build/regular-release');build.mkdir(parents=True,exist_ok=True)
    print('Building current glyphs and kerning...',flush=True)
    stage=build/'source';source_ttf=stage/'VeryPeriSerifDraft-Regular.ttf'
    with (build/'source-build.log').open('w') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):build_stage(output_dir=stage,ttf_path=source_ttf)
    font=TTFont(source_ttf);source=TTFont(source_ttf);manifest=json.loads((stage/'build-manifest.json').read_text())
    values={1:config['family'],2:config['style'],3:config['version']+';'+config['vendor_id']+';'+config['postscript_name']+';'+sha(source_ttf)[:12],4:config['family']+' '+config['style'],5:'Version '+config['version'],6:config['postscript_name'],8:'Very Peri Serif project',9:source['name'].getDebugName(9)+'; Cyrillic extension: Very Peri Serif project contributors',10:'Regular. Latin, Russian and Kazakh. Based on Instrument Serif; modified Cormorant Cyrillic de.',11:config['project_url'],13:'This Font Software is licensed under the SIL Open Font License, Version 1.1. This license is available with a FAQ at: https://openfontlicense.org',14:'https://openfontlicense.org'}
    for nid in (16,17):font['name'].removeNames(nameID=nid)
    for nid,value in values.items():
        font['name'].removeNames(nameID=nid)
        for platform,encoding in ((3,1),(1,0)):font['name'].setName(value,nid,platform,encoding,0x409 if platform==3 else 0)
    font['head'].fontRevision=float(config['version']);font['OS/2'].achVendID=config['vendor_id'];font.recalcTimestamp=False
    font['meta']=newTable('meta');font['meta'].data={'dlng':'Cyrl, Latn','slng':'Cyrl, Latn'}
    ttf=out/(config['postscript_name']+'.ttf');font.save(ttf);web=TTFont(ttf);web.recalcTimestamp=False;web.flavor='woff2';woff=ttf.with_suffix('.woff2');web.save(woff)
    manifest.update(family=config['family'],version=config['version'],release_status='final Regular',source_stage_version=manifest['version'],source_stage_ttf_sha256=sha(source_ttf),note='Current selected Regular outlines, spacing, kerning and OpenType features; final naming and release metadata.')
    save_json(out/'build-manifest.json',manifest)
    for filename in ('OFL.txt','AUTHORS.txt','Cormorant-OFL.txt','Cormorant-NOTICE.txt'):shutil.copyfile(stage/filename,out/filename)
    shutil.copyfile('font/README-regular.md',out/'README.md')
    print('Checking final TTF/WOFF2 and all kerning/feature modes...',flush=True)
    validate(output_dir=out,ttf_path=ttf,doc_path=Path('docs/img/regular_release_proof.svg'),final=True)
    final=TTFont(ttf);roundtrip=TTFont(woff);checks=[]
    def expect(ok,label):assert ok,label;checks.append(label)
    for nid in (1,2,3,4,5,6):expect(final['name'].getDebugName(nid)==values[nid],'name '+str(nid))
    expect(all(final['name'].getDebugName(i) is None for i in (16,17)),'no redundant typographic names for Regular')
    expect(final['meta'].data=={'dlng':'Cyrl, Latn','slng':'Cyrl, Latn'},'designed and supported script metadata')
    expect(final['OS/2'].fsType==0 and final['OS/2'].usWeightClass==400,'embedding and Regular weight')
    expect(not final['head'].macStyle&3 and final['post'].italicAngle==0,'upright Regular style')
    expect(set(final.getGlyphOrder())==set(source.getGlyphOrder()),'source glyph inventory unchanged')
    for n in source.getGlyphOrder():
        expect(final['glyf'][n].compile(final['glyf'])==source['glyf'][n].compile(source['glyf']),'source outline '+n)
        expect(final['hmtx'][n]==source['hmtx'][n],'source advance '+n)
    for tag in ('cmap','GSUB','GPOS','GDEF','hhea','post'):
        expect(final.getTableData(tag)==source.getTableData(tag),'source table '+tag)
    for tag in final.keys():
        if tag not in ('GlyphOrder','head'):expect(roundtrip.getTableData(tag)==final.getTableData(tag),'web roundtrip '+tag)
    for n,r in manifest['glyph_records'].items():
        if '#' not in r['path']:expect(sha(r['path'])==r['sha256'],'current source hash '+n)
    for p in (ttf,woff):
        result=ots.sanitize(str(p),str(build/(p.suffix[1:]+'-sanitized.ttf')),capture_output=True)
        expect(result.returncode==0,'OpenType Sanitizer '+p.suffix)
    release=dict(ttf_sha256=sha(ttf),woff2_sha256=sha(woff),source_stage_ttf_sha256=sha(source_ttf),passed=len(checks),failed=0,checks=checks)
    save_json(out/'release-validation.json',release)
    quality=dict(ttf_sha256=sha(ttf),woff2_sha256=sha(woff),opentype_sanitizer={'ttf':'PASS','woff2':'PASS'},functional_checks=json.loads((out/'validation.json').read_text())['passed'],harfbuzz_pairs_checked=json.loads((out/'kerning-validation.json').read_text())['harfbuzz_pairs_checked'],fontbakery='NOT RUN',hyperglot_base_primary='NOT RUN',network_checks='SKIPPED')
    if args.quality:
        print('Checking FontBakery and language coverage...',flush=True)
        command([sys.executable,'-m','fontbakery','check-googlefonts','--skip-network','--no-progress','--no-colors','--json',str(build/'fontbakery.json'),str(ttf)],build/'fontbakery.log')
        fb=json.loads((build/'fontbakery.json').read_text());quality['fontbakery']=fb['result'];expect(not any(fb['result'].get(k,0) for k in ('FAIL','ERROR')),'FontBakery no failures')
        quality['warning_checks']=[c['key'][1] for s in fb['sections'] for c in s['checks'] if any(l['status']=='WARN' for l in c['logs'])]
        command([sys.executable,'-c','from hyperglot.cli import cli; cli()',str(ttf),'--output',str(build/'hyperglot.yaml')],build/'hyperglot.log')
        match=re.search(r'\d+ languages of Cyrillic script:\n-+\n([^\n]+)',(build/'hyperglot.log').read_text());languages=match.group(1).split(', ') if match else []
        quality['hyperglot_base_primary']={k:k in languages for k in ('Russian','Kazakh')};expect(all(quality['hyperglot_base_primary'].values()),'Russian and Kazakh base coverage')
    save_json(out/'quality-summary.json',quality)
    specimen(ttf,out/'specimen.pdf',config)
    members=[ttf.name,woff.name,'README.md','OFL.txt','AUTHORS.txt','Cormorant-OFL.txt','Cormorant-NOTICE.txt','proof.svg','specimen.pdf','build-manifest.json','validation.json','kerning-validation.json','release-validation.json','quality-summary.json']
    (out/'SHA256SUMS.txt').write_text(''.join(sha(out/name)+'  '+name+'\n' for name in sorted(members)))
    archive=Path(config['archive'])
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as package:
        for name in sorted(members+['SHA256SUMS.txt']):
            info=zipfile.ZipInfo('VeryPeriSerif/'+name,date_time=tuple(map(int,config['date'].split('-')))+(0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;package.writestr(info,(out/name).read_bytes())
    with zipfile.ZipFile(archive) as package:assert package.testzip() is None
    print(json.dumps(dict(archive=str(archive),ttf=str(ttf),woff2=str(woff),ttf_sha256=sha(ttf),archive_sha256=sha(archive),quality=quality),ensure_ascii=False),flush=True)
if __name__=='__main__':main()
