#!/usr/bin/env python3
"""Italic capitals by shearing the Regular ones (author's idea, checked on the native Latin first).
Check: native Italic capitals against Regular capitals sheared by tan 13 degrees about y=251 (x' = x + S*(y-251)):
area difference to the native outline, stems 2-6 percent, round letters up to 12-19 percent (terminals), so
straight-stem capitals are a plain shear; round capitals only need terminals checked by eye.
Cyrillic capitals that exist in the native Italic (direct donors) are taken from it, all other ones are the
Regular outlines sheared with the same affine map (quadratics stay quadratics), Regular advance, no thinning
(stems 71 against 69 native: inside the +-2 tolerance of docs/italic-rules.md).
Writes build/italic-caps/VeryPeriSerifItalicT0-caps.ttf: native Italic + all Cyrillic capitals (and the 13 direct
lowercase letters, to read words) under a test family name.
"""
import json,math,sys
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen

sys.path.insert(0,str(Path(__file__).resolve().parent))
from italic_round import round_glyph
from italic_tidy import tidy
S=math.tan(math.radians(13));Y0=251
# round capitals: bent like the native O/C instead of the plain shear (docs/italic-lines.md); rects in Regular coordinates
ROUND={0x417:('open',()),0x42D:('open',()),0x4D8:('open',()),0x4E8:('closed',()),
       0x42E:('closed',((89,160,-20,740),(24,228,-20,35),(21,230,690,740))),
       0x424:('closed',((248,319,-20,740),(185,382,-20,35),(185,382,690,740)))}
REG=Path('dist/VeryPeriSerif/VeryPeriSerif-Regular.ttf');ITA=Path('reference/instrument-serif/fonts/ttf/InstrumentSerif-Italic.ttf')
SPACING=json.loads(Path('data/italic-caps-spacing.json').read_text())['glyphs'] if Path('data/italic-caps-spacing.json').exists() else {}
CAPS=list(range(0x410,0x430))+[0x401]+[0x4D8,0x492,0x49A,0x4A2,0x4E8,0x4B0,0x4AE,0x4BA,0x406]


def main():
    out=Path('build/italic-caps');out.mkdir(parents=True,exist_ok=True)
    plan=json.loads(Path('data/italic-plan.json').read_text());direct=plan['direct_donor_candidates']
    reg=TTFont(REG);ita=TTFont(ITA);rcm=reg.getBestCmap();grs=reg.getGlyphSet()
    order=ita.getGlyphOrder();report=[]
    for cp in CAPS:
        ch=chr(cp)
        if ch in direct:report.append(dict(character=ch,source='native Italic '+direct[ch]));continue
        name=rcm.get(cp)
        if not name:continue
        if cp in ROUND:g=round_glyph(reg['glyf'][name],reg['glyf'],*ROUND[cp])
        else:
            pen=TTGlyphPen(None);grs[name].draw(TransformPen(pen,(1,0,S,1,-S*Y0,0)))
            g=pen.glyph()
        g.recalcBounds(ita['glyf'])
        g,tstats=tidy(g,ita['glyf'])   # no name: Regular patches do not apply to sheared outlines
        new=f'uni{cp:04X}';ita['glyf'][new]=g
        adv=reg['hmtx'][name][0]
        sp=SPACING.get(ch)
        if sp:g.coordinates.translate((sp['dx'],0));g.recalcBounds(ita['glyf']);adv+=sp['dadv']
        ita['hmtx'][new]=(adv,getattr(g,'xMin',0))
        for t in ita['cmap'].tables:
            if t.isUnicode():t.cmap[cp]=new
        report.append(dict(character=ch,source='Regular sheared'+(' + round correction' if cp in ROUND else ''),advance=adv,nodes=len(g.coordinates),tidy={k:v for k,v in tstats.items() if k in ('extrema','smooth','deviation')}))
    ita.setGlyphOrder(ita['glyf'].glyphOrder)
    # native direct donors (capitals and the lowercase ones, so that words can be read)
    for ch,donor in direct.items():
        for t in ita['cmap'].tables:
            if t.isUnicode():t.cmap[ord(ch)]=donor
    family='Very Peri Serif Italic T0 caps';ps='VeryPeriSerifItalicT0caps-Italic'
    for r in ita['name'].names:
        if r.nameID==1:r.string=family
        elif r.nameID==3:r.string='0.0;caps test;'+ps
        elif r.nameID==4:r.string=family+' Italic'
        elif r.nameID==6:r.string=ps
    ita['name'].names=[r for r in ita['name'].names if r.nameID not in (16,17,21,22)]
    target=out/'VeryPeriSerifItalicT0-caps.ttf';ita.save(target)
    Path('data/italic-caps.json').write_text(json.dumps(report,ensure_ascii=False,indent=1)+'\n')
    print(target,len(report),'capitals;',sum(1 for r in report if r['source'].startswith('Regular sheared')),'sheared')

if __name__=='__main__':main()
