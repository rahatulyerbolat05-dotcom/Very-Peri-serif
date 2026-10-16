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
from build_draft_font import REF,OUT,TTF,CHARS,name_for
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


def proof(data,font):
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
    label(55,55,'Very Peri Serif Draft · Regular · 1.000',36)
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
    label(55,2015,'Черновая сборка: интервалы и кернинг требуют проверки в реальном макете.',28)
    out.append('</svg>');svg='\n'.join(out)
    (OUT/'proof.svg').write_text(svg);Path('docs/img/draft_font_proof.svg').write_text(svg)


def main():
    data=TTF.read_bytes();font=TTFont(TTF,checkChecksums=2);font.ensureDecompiled()
    native=TTFont(REF);native_data=REF.read_bytes();context=json.loads(Path('data/context/serif_bl.json').read_text())
    checks=[]
    def expect(condition,label):
        assert condition,label;checks.append(label)
    for ch in CHARS:
        expect(shape(data,font,ch)[0][0]==name_for(ch),'Unicode '+ch)
    for left,alternate,members in [
        ('п','uni043F.flag',context['declared_class']['lower']+context['declared_class']['upper']),
        ('к','uni043A.short',context['ka_short']['declared_class']['lower']),
        ('қ','uni049B.context',context['ka_short']['declared_class']['lower'])]:
        for right in CHARS:
            expected=alternate if right in members else name_for(left)
            names=[x[0] for x in shape(data,font,left+right)]
            expect(names[0]==expected,f'calt {left+right}')
        expect(shape(data,font,left+'н',{'calt':False})[0][0]==name_for(left),'calt disabled '+left)
    for ch in 'цщқңЦЩҚҢ':
        expect(shape(data,font,ch,{'ss09':True})[0][0]==name_for(ch)+'.tail_old','ss09 '+ch)
    expect(shape(data,font,'қн',{'ss09':True})[0][0]=='uni049B.context.tail_old','q context plus old tail')
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
    web=TTFont(OUT/'VeryPeriSerifDraft-Regular.woff2');web.ensureDecompiled()
    expect(web.getBestCmap()==font.getBestCmap(),'WOFF2 cmap roundtrip')
    proof(data,font)
    summary={'passed':len(checks),'failed':0,'checks':checks,'ttf_sha256':hashlib.sha256(data).hexdigest(),
             'scope':'Real HarfBuzz shaping, substitutions, kerning toggles, marks, original Latin regressions and WOFF2 decoding.'}
    (OUT/'validation.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'passed':len(checks),'failed':0},ensure_ascii=False))


if __name__=='__main__':main()
