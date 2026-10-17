#!/usr/bin/env python3
"""Flat-foot form of н (uni043D.flat) for the position before letters without a lower-left serif.
The main н (data/en/n4.glif) has the exit foot of u on its right stem, which suits a neighbour
with a foot serif (п.flag, к.flag). Before о, с, е, а and the other letters without such a serif
the right stem gets the ordinary flat symmetric foot serif of ı instead (author, 17.10.2026).
The lower 150 units of the right stem are replaced by those of ı; the stem edges coincide at y=150.
Sources are pinned by SHA256; the glyph goes to data/en-flat/.
"""
import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import pathops
from sketchlib import Ref,rect,AND,OR,SUB,shift,write_glif
from audit_author_glyphs import runs
from finish_regular import load

OUT=Path('data/en-flat');SOURCE='data/en/n4.glif';YC=150.0;CUT_X=230.0;STEM_SHIFT=245.0   # ı stem 79..147 -> right stem 324..392


def build(ref):
    base,advance=load(SOURCE);base=pathops.simplify(base,fix_winding=True,clockwise=True)
    right=runs(base,YC)[-1];assert abs(right[0]-324)<.6 and abs(right[1]-392)<.6,right
    piece=shift(AND(ref.glyph('dotlessi'),rect(-50,-60,400,YC)),STEM_SHIFT)
    out=pathops.simplify(OR(SUB(base,rect(CUT_X,-60,900,YC)),piece),fix_winding=True,clockwise=True)
    return out,advance


def main():
    OUT.mkdir(exist_ok=True);path,advance=build(Ref())
    name='uni043D.flat';target=OUT/(name+'.glif');write_glif(path,name,advance,0xE210,str(target))
    info=dict(character='н',source=SOURCE,source_sha256=hashlib.sha256(Path(SOURCE).read_bytes()).hexdigest(),
              glif_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),advance=advance,bounds=[round(b,1) for b in path.bounds])
    (OUT/'manifest.json').write_text(json.dumps({name:info},ensure_ascii=False,indent=1)+'\n');print(name,info)

if __name__=='__main__':main()
