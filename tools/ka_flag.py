#!/usr/bin/env python3
"""Exit foot (flag) for к, к.short and К before letters with a lower-left serif.
The right leg of к ends in a flat symmetric foot serif that stands against the foot serif
of the next letter. п.flag and the right stem of н use the exit tail of the native u
instead (tools/glyphparts.py: pe_flag). The same foot is built here into the leg of к:
the lower 150 units of the leg are replaced by the right-stem foot of u, sheared to the
slope of the leg and widened to its thickness. қ and Қ keep their drop tail (author, 17.10.2026).
Sources are pinned by SHA256; new glyphs go to data/ka-flag/.
"""
import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import pathops
from sketchlib import Ref,rect,poly,AND,OR,SUB,tf,write_glif
from glyphparts import _u_taper,_u_edge_fix
from audit_author_glyphs import runs
from finish_regular import load
from declump import pchip,warp_contours
from outline_clean import contours_of
from refine_widths import path_from

OUT=Path('data/ka-flag')
YC=150.0
BASES={'uni043A.flag':('data/codex/uni043A-02.glif','к'),
       'uni043A.short.flag':('data/ka/ka_short.glif','к'),
       'uni041A.flag':('data/homoglyph/Ka-cy.glif','К')}


def foot_piece(ref,left,width,slope):
    """u right-stem foot, widened to the leg thickness and sheared to the leg slope."""
    U=ref.glyph('u')
    piece=AND(OR(AND(U,_u_taper()),_u_edge_fix()),rect(0,-50,700,YC))
    delta=width-68.0
    if abs(delta)>.01:
        contours=[[list(seg[1:]) for seg in c] for c in contours_of(piece)]
        piece=pathops.simplify(path_from(warp_contours(contours,[[300,300],[312,312],[380,380+delta],[392,392+delta]],.15)),fix_winding=True,clockwise=True)
    return tf(piece,(1,0,-slope,1,left-312.0+slope*YC,0))


def build(ref,source):
    base,advance=load(source);base=pathops.simplify(base,fix_winding=True,clockwise=True)
    foot=runs(base,10)                      # [stem foot serif, leg foot serif]
    cut=(foot[0][1]+foot[1][0])/2           # inside the gap between the two foot serifs
    r150,r200=runs(base,YC)[-1],runs(base,YC+50)[-1]
    left,width=r150[0],r150[1]-r150[0]
    slope=(r200[0]-r150[0])/-50.0           # x grows as y falls
    slope=-slope if slope<0 else slope
    piece=foot_piece(ref,left,width,slope)
    leg_kept=SUB(base,rect(cut,-60,900,YC))
    out=pathops.simplify(OR(leg_kept,piece),fix_winding=True,clockwise=True)
    info=dict(cut_x=round(cut,1),leg_left=round(left,1),leg_width=round(width,1),slope=round(slope,3),
              advance=advance,xmax=round(out.bounds[2],1),ymin=round(out.bounds[1],1))
    return out,advance,info


def main():
    ref=Ref();OUT.mkdir(exist_ok=True);manifest={}
    for number,(name,(source,ch)) in enumerate(BASES.items()):
        sha=hashlib.sha256(Path(source).read_bytes()).hexdigest()
        path,advance,info=build(ref,source)
        target=OUT/f'{name}.glif';write_glif(path,name,advance,0xE200+number,str(target))
        manifest[name]=dict(character=ch,source=source,source_sha256=sha,glif_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),**info)
        print(name,info)
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=1)+'\n')

if __name__=='__main__':main()
