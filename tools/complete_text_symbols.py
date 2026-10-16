#!/usr/bin/env python3
"""[РЕШЕНИЕ] Complete recommended typography without altering letter outlines."""
import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from sketchlib import Ref,OR,SUB,shift,tf,poly,write_glif
from glyphparts import _rrect
import pathops

DIR=Path('data/typographic-completion')

def main():
    DIR.mkdir(exist_ok=True);ref=Ref();params=json.loads(Path('data/params.json').read_text());upm=params['source_master']['upm'];t=params['regular']['stems_hairlines']['H_crossbar']
    result={}
    def add(ch,p,advance,donor,note):result[ch]=(p,advance,donor,note)
    for ch,n in [('‐','hyphen'),('―','emdash')]:add(ch,ref.glyph(n),ref.adv(n),n,'Exact native outline and advance')
    # Figure dash uses the zero advance and centered native minus, without scaling.
    minus=ref.glyph('minus');center=(minus.bounds[0]+minus.bounds[2])/2;zero=ref.adv('zero')
    add('‒',shift(minus,zero/2-center),zero,'minus','Centered native minus on the zero advance')
    for ch,w in [('\u2002',upm/2),('\u2003',upm),('\u2007',zero),('\u200a',upm/10),('\u200b',0),('\u2060',0),('\ufeff',0)]:add(ch,pathops.Path(),w,'space','Unicode spacing control; no ink')
    # A real prime is a slanted stroke, not the curly apostrophe.
    prime=pathops.Path();q=prime.getPen();q.moveTo((45,495));q.lineTo((78,710));q.qCurveTo((80,725),(94,725));q.qCurveTo((110,725),(105,710));q.lineTo((68,495));q.qCurveTo((65,482),(55,482));q.qCurveTo((43,482),(45,495));q.closePath()
    add('′',prime,145,'quotesingle','New tapered prime; height of superscript punctuation')
    add('″',OR(prime,shift(prime,105)),250,'quotedbl','Two native-style tapered prime strokes')
    stem=_rrect(155-t/2,0,155+t/2,720,8);bar=_rrect(35,480,275,480+t,8)
    add('†',OR(stem,bar),310,'plus','Hairline cross using H crossbar weight')
    add('‡',OR(stem,bar,shift(bar,0,-230)),310,'plus','Double dagger with matched crossbars')
    wave=ref.glyph('asciitilde')
    add('≈',OR(shift(wave,0,65),shift(wave,0,-65)),ref.adv('asciitilde'),'asciitilde','Two original waves without scaling')
    # Explicit replacement symbol: dark diamond and a custom light question mark.
    diamond=poly((375,730),(740,365),(375,0),(10,365));question=pathops.Path();q=question.getPen()
    q.moveTo((310,495));q.curveTo((310,610),(450,610),(450,510));q.curveTo((450,450),(390,440),(390,380));q.lineTo((390,345));q.lineTo((360,345));q.lineTo((360,380));q.curveTo((360,455),(420,465),(420,510));q.curveTo((420,565),(340,565),(340,495));q.closePath()
    dot=_rrect(356,240,394,278,19)
    add('�',SUB(diamond,OR(question,dot)),750,'question','Dedicated replacement diamond, not .notdef fallback')
    # Latin schwas share the already reviewed Cyrillic Ә/ә geometry.
    cfg=json.loads(Path('data/alphabet.json').read_text());from alphabet_sheet import source_items
    from build_draft_font import load
    for ch,cy,donor in [('Ə','Ә','O'),('ə','ә','o')]:
        p,w=load(source_items(cy,cfg)[0]['path']);add(ch,p,w,donor,'Reviewed Cyrillic schwa outline reused without transformation')
    manifest={}
    for ch,(p,w,donor,note) in result.items():
        path=DIR/f'uni{ord(ch):04X}.glif';write_glif(p,f'uni{ord(ch):04X}',w,ord(ch),str(path))
        manifest[ch]={'path':str(path),'advance':w,'donor':donor,'note':note,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    (DIR/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')

if __name__=='__main__':main()
