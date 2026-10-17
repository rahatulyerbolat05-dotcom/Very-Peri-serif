#!/usr/bin/env python3
"""Functional checks for the installed-font draft using HarfBuzz, not table names.

Run after build_draft_font.py. Writes validation.json and an outline proof.
"""
import io
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
from build_draft_font import REF,OUT,TTF,CHARS,SYMBOLS,name_for
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.boundsPen import BoundsPen
import uharfbuzz as hb


def shape(data,font,text,features=None):
    face=hb.Face(data);hf=hb.Font(face);hf.scale=(face.upem,face.upem)
    hb.ot_font_set_funcs(hf);buf=hb.Buffer();buf.add_str(text);buf.guess_segment_properties()
    hb.shape(hf,buf,features or {})
    return [(font.getGlyphName(g.codepoint),p.x_advance,p.y_advance,p.x_offset,p.y_offset)
            for g,p in zip(buf.glyph_infos,buf.glyph_positions)]


def proof(data,font,output_dir=OUT,doc_path=Path('docs/img/draft_font_proof.svg'),final=False):
    from html import escape
    gs=font.getGlyphSet();width,height=2200,2100
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
         '<rect width="100%" height="100%" fill="#f5f2ec"/>']
    def label(x,y,text,size=27):out.append(f'<text x="{x}" y="{y}" font-family="sans-serif" font-size="{size}" fill="#69656a">{escape(text)}</text>')
    def line(text,x,y,size,features=None):
        scale=size/1000;cursor=x
        for n,advance,_,dx,dy in shape(data,font,text,features):
            pen=SVGPathPen(gs);gs[n].draw(pen)
            out.append(f'<path transform="translate({cursor+dx*scale:.3f} {y-dy*scale:.3f}) scale({scale} {-scale})" fill="#272333" d="{pen.getCommands()}"/>')
            cursor+=advance*scale
    label(55,55,font['name'].getDebugName(1)+' · Regular · '+format(font['head'].fontRevision,'.3f'),36)
    for text,y,size in [
        ('Съешь же ещё этих мягких',210,115),('французских булок, да выпей чаю.',360,105),
        ('Қазақ тілі — әдемі тіл.',540,120),('Ә Ғ Қ Ң Ө Ұ Ү Һ І · ә ғ қ ң ө ұ ү һ і',690,100),
        ('ТО ТА ГА ГО УА АТ ЛЛ · лл го то',890,110)]:line(text,55,y,size)
    label(55,1010,'Контекстные формы включены по умолчанию (calt)')
    line('пн по пк · кн ко · қн қо',55,1140,130)
    label(55,1240,'Основные каплевидные хвосты')
    line('ц щ қ ң Ц Щ Қ Ң',55,1380,135)
    label(1120,1240,'Прежние хвосты · ss09')
    line('ц щ қ ң Ц Щ Қ Ң',1120,1380,135,{'ss09':True})
    label(55,1500,'Основная т');line('текст театр',55,1620,115)
    label(1120,1500,'Альтернативная т · ss08');line('текст театр',1120,1620,115,{'ss08':True})
    label(55,1740,'Родные латинские лигатуры / акценты')
    line('office affine final · е́ ё́ Ә́ і́',55,1880,115)
    line('1 000 ₸ · 25 000 ₸ · ₸100',55,1980,80)
    label(55,2070,'Very Peri Serif Regular · русский / қазақша / Latin' if final else 'Черновая сборка: интервалы и кернинг требуют проверки в реальном макете.',28)
    # Standalone outline preview, rendered from the installed font via HarfBuzz.
    saved=out;out=[saved[0].replace('height="2100"','height="650"').replace('2200 2100','2200 650'),saved[1]]
    label(55,55,'Тенге · U+20B8 · Very Peri Serif Draft',36)
    line('₸',110,530,550)
    line('1 000 ₸',550,285,150)
    line('25 000 ₸ · ₸100',550,470,130)
    out.append('</svg>')
    if not final:Path('docs/img/tenge.svg').write_text('\n'.join(out))
    out=saved
    out.append('</svg>');svg='\n'.join(out)
    (Path(output_dir)/'proof.svg').write_text(svg)
    if doc_path is not None:Path(doc_path).write_text(svg)


def main(output_dir=OUT,ttf_path=TTF,doc_path=Path('docs/img/draft_font_proof.svg'),final=False):
    output_dir=Path(output_dir);ttf_path=Path(ttf_path)
    data=ttf_path.read_bytes();font=TTFont(ttf_path,checkChecksums=2);font.ensureDecompiled()
    native=TTFont(REF);native_data=REF.read_bytes();context=json.loads(Path('data/context/serif_bl.json').read_text())
    checks=[]
    def expect(condition,label):
        assert condition,label;checks.append(label)
    expect(font['glyf']['uni0423'].compile(font['glyf'])!=font['glyf']['uni04AE'].compile(font['glyf']),'Russian U and Kazakh Ustraight distinct')
    expect(font['glyf']['uni0423'].yMin==-9 and font['glyf']['uni04AE'].yMin==0,'capital U hook versus upright Ustraight base')
    for ch in CHARS:
        expect(shape(data,font,ch)[0][0]==name_for(ch),'Unicode '+ch)
    for text in ['₸','1 000 ₸','₸100','25 000 ₸']:
        result=shape(data,font,text)
        expect(all(r[0]!='.notdef' for r in result),'tenge price coverage '+text)
        expect(any(r[0]=='uni20B8' for r in result),'tenge Unicode mapping '+text)
    g=font['glyf']['uni20B8']
    expect(g.numberOfContours==2 and (g.yMin,g.yMax)==(0,720),'tenge height and two contours')
    for ch in SYMBOLS:
        if ch in '\u200b\u2060\ufeff':
            expect(font.getBestCmap().get(ord(ch))==name_for(ch) and sum(x[1] for x in shape(data,font,ch))==0,'invisible control '+hex(ord(ch)))
        else:expect(shape(data,font,ch)[0][0]==name_for(ch),'symbol Unicode '+hex(ord(ch)))
    for ch in '\u2009\u202f':
        name=name_for(ch)
        expect(font['glyf'][name].numberOfContours==0 and font['hmtx'][name][0]==200,'space empty and width '+hex(ord(ch)))
    for text in ['№ 12','500 ₽','500 ₴','lʼart','по‑русски','1\u2009000\u202f₸','◌\u0301']:
        expect(all(r[0]!='.notdef' for r in shape(data,font,text)),'text symbols covered '+text)
    circle=shape(data,font,'◌\u0301')
    expect(circle[-1][1]==0 and circle[-1][3]!=0,'dotted circle mark positioned')
    expect(font['glyf']['uni25CC'].numberOfContours==12,'dotted circle has twelve dots')
    import re,subprocess
    manifest=json.loads((output_dir/'build-manifest.json').read_text())
    if manifest.get('kerning_preserved'):
        oldfea=subprocess.check_output(['git','show','66f1909:font/draft-features.fea']).decode()
        pattern=r'^pos \S+ \S+ -?\d+;$'
        expect(re.findall(pattern,oldfea,re.M)==re.findall(pattern,Path('font/draft-features.fea').read_text(),re.M),'all kerning pairs preserved from 1.002')
        oldfont=TTFont(io.BytesIO(subprocess.check_output(['git','show','66f1909:'+str(ttf_path)])))
        changed=set('үұЗзч')
        for name,r in manifest['glyph_records'].items():
            if name in oldfont.getGlyphOrder() and r['character'] not in changed:
                expect(font['glyf'][name].compile(font['glyf'])==oldfont['glyf'][name].compile(oldfont['glyf']),'unmodified installed outline '+name)
    for text in ['12′ 30″','2020‒2026','10≈9','† ‡','Ə\u0301 ə\u0301','�']:
        expect(all(r[0]!='.notdef' for r in shape(data,font,text)),'completed typography '+text)
    completed=json.loads(Path('data/typographic-completion/manifest.json').read_text())
    for ch,item in completed.items():
        expect(font['hmtx'][name_for(ch)][0]==round(item['advance']),'completed advance '+hex(ord(ch)))
        if ch.isspace() or item['advance']==0:
            expect(font['glyf'][name_for(ch)].numberOfContours==0,'blank space/control '+hex(ord(ch)))
    for ch,cy in [('Ə','Ә'),('ə','ә')]:
        latin_mark=shape(data,font,ch+'\u0301')[-1]
        cy_mark=shape(data,font,cy+'\u0301')[-1]
        expect(latin_mark==cy_mark,'schwa anchor parity '+ch)
    serif_members=context['declared_class']['lower']+context['declared_class']['upper']
    head_members=context['ka_short']['declared_class']['lower']
    for left,alternate,members in [
        ('п','uni043F.flag',serif_members),
        ('қ','uni049B.context',head_members)]:
        for right in CHARS:
            expected=alternate if right in members else name_for(left)
            names=[x[0] for x in shape(data,font,left+right)]
            expect(names[0]==expected,f'calt {left+right}')
        expect(shape(data,font,left+'н',{'calt':False})[0][0]==name_for(left),'calt disabled '+left)
    # к: short head first (lookup calt_forms), then the exit foot (calt_feet); К only the foot
    for right in CHARS:
        short=right in head_members;foot=right in serif_members
        expected='uni043A'+('.short' if short else '')+('.flag' if foot else '')
        expect([x[0] for x in shape(data,font,'к'+right)][0]==expected,f'calt к{right}')
        expected_cap='uni041A.flag' if foot else 'uni041A'
        expect([x[0] for x in shape(data,font,'К'+right)][0]==expected_cap,f'calt К{right}')
    expect(shape(data,font,'кн',{'calt':False})[0][0]=='uni043A','calt disabled к')
    expect(shape(data,font,'Кн',{'calt':False})[0][0]=='uni041A','calt disabled К')
    for ch in 'цщқңЦЩҚҢ':
        expect(shape(data,font,ch,{'ss09':True})[0][0]==name_for(ch)+'.tail_old','ss09 '+ch)
    expect(shape(data,font,'қн',{'ss09':True})[0][0]=='uni049B.context.tail_old','q context plus old tail')
    expect(shape(data,font,'д',{'ss07':True})[0][0]=='uni0434.ss07','ss07 printed de')
    expect(shape(data,font,'пд',{'ss07':True})[0][0]=='uni043F.flag','ss07 printed de triggers lower serif context')
    for features in [{'ss07':True},{'ss07':True,'ss01':True,'ss08':True,'ss09':True}]:
        expect(shape(data,font,'дн',features)[0][0]=='uni0434.ss07','printed de composes with other stylistic sets')
    expect(shape(data,font,'т',{'ss08':True})[0][0]=='uni0442.ss08','ss08 te')
    for ch in 'асеё':expect(shape(data,font,ch,{'ss01':True})[0][0]==name_for(ch)+'.ss01','ss01 '+ch)
    for text in ['fi','fl','ffi','ffl']:
        expect(len(shape(data,font,text))<len(shape(data,font,text,{'liga':False})),'native liga '+text)
    for text in ['fb','fh','qj']:
        expect(shape(data,font,text,{'dlig':True})==shape(native_data,native,text,{'dlig':True}),'native dlig preserved '+text)
    expect(len(shape(data,font,'лл'))==2,'rejected el-el ligature remains disabled')
    for text in ['ТО','ТА','ГА','УА','лл','ЛЛ']:
        on=shape(data,font,text);off=shape(data,font,text,{'kern':False})
        expect(sum(x[1] for x in on)!=sum(x[1] for x in off),'kerning active '+text)
    for text in ['е\u0301','ә\u0301','Ә\u0301','і\u0301','ё\u0301','Й\u0301','Ё\u0301']:
        result=shape(data,font,text)
        expect(all(r[0]!='.notdef' for r in result),'marks covered '+text)
        expect(any(r[1]==0 and (r[3]!=0 or r[4]!=0) for r in result),'mark positioning '+text)
        gs=font.getGlyphSet()
        for name,_,_,_,dy in result:
            bounds=BoundsPen(gs);gs[name].draw(bounds)
            if bounds.bounds:
                expect(bounds.bounds[3]+dy<=font['OS/2'].usWinAscent,'accent within Windows ascent '+text+' '+name)
    latin=['AVATAR To Wa office affine final','Hamburgefontsiv 0123456789','fi fl ffi ffl','École Ångström']
    for text in latin:
        expect(shape(data,font,text)==shape(native_data,native,text),'native shaping preserved '+text)
    for n in native.getGlyphOrder():
        expect(font['glyf'][n].compile(font['glyf'])==native['glyf'][n].compile(native['glyf']),'native outline '+n)
    expect(set(CHARS).issubset(chr(c) for c in font.getBestCmap()),'complete Russian Kazakh coverage')
    web=TTFont(ttf_path.with_suffix('.woff2'));web.ensureDecompiled()
    expect(web.getBestCmap()==font.getBestCmap(),'WOFF2 cmap roundtrip')
    for tag in ('GSUB','GPOS','GDEF'):
        expect(web[tag].compile(web)==font[tag].compile(font),'WOFF2 layout roundtrip '+tag)
    from check_kerning import check as check_all_pairs
    from build_draft_font import native_kern
    kerning_checks=check_all_pairs(data,font,native,CHARS,native_kern,report_path=output_dir/'kerning-validation.json')
    expect(kerning_checks['failed']==0,'exhaustive kerning and unchanged outlines')
    proof(data,font,output_dir=output_dir,doc_path=doc_path,final=final)
    summary={'passed':len(checks),'failed':0,'checks':checks,'ttf_sha256':hashlib.sha256(data).hexdigest(),
             'kerning_checks':kerning_checks,
             'scope':'Real HarfBuzz shaping, substitutions, kerning toggles, marks, original Latin regressions and WOFF2 decoding.'}
    (output_dir/'validation.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'passed':len(checks),'failed':0},ensure_ascii=False))


if __name__=='__main__':main()
