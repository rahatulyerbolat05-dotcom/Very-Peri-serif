#!/usr/bin/env python3
"""Fit side-bearing shifts so that kerning is only needed for real pair exceptions.
The optical pass (tools/optical_kerning.py) writes, for every pair with an added glyph, the
kerning that gives the target optical gap. If a glyph needs about the same correction against
almost every neighbour (ц щ ң қ: the advance holds room for the drop tail; ү ұ: wide sides), that is a
spacing error, not kerning. Model: kerning(a,b) ~ r_a + l_b. Native Latin and Cyrillic glyphs
identical to a Latin glyph stay fixed (r=l=0). The least-squares solution (weighted by letter
frequency) is rounded to even units and accumulated in data/spacing.json:
dx = outline shift, dadv = advance change (dx + r).  Workflow: build, run this, build again.
Usage: python3 -I tools/respace.py [--reset]   (needs build/kerning/pairs.json and the source-stage manifest)
"""
import json,sys
from pathlib import Path
import numpy as np

SPACING=Path('data/spacing.json');PAIRS=Path('build/kerning/pairs.json');MANIFEST=Path('build/regular-release/source/build-manifest.json')
MIN_SHIFT=6;MAX_TOTAL=120;RIDGE=0.5;FLOOR=-20   # Latin v y x have side bearings down to -14: no glyph is pushed past -20
SOURCE_TTF=Path('build/regular-release/source/VeryPeriSerifDraft-Regular.ttf')
FREQ=dict(zip("оеаинтсрвлкмдпуяыьгзбчйхжшюцщэф",[10.97,8.45,8.01,7.35,6.70,6.26,5.47,4.73,4.54,4.34,3.49,3.21,2.98,2.81,2.62,2.01,1.90,1.74,1.69,1.65,1.59,1.45,1.21,0.97,0.94,0.72,0.64,0.48,0.36,0.32,0.26]))


def main():
    if '--reset' in sys.argv:
        SPACING.write_text(json.dumps({'note':'cumulative side-bearing shifts of added glyphs, units; tools/respace.py','glyphs':{}},indent=1)+'\n');print('reset');return
    table=json.loads(SPACING.read_text()) if SPACING.exists() else {'note':'cumulative side-bearing shifts of added glyphs, units; tools/respace.py','glyphs':{}}
    rows=json.loads(PAIRS.read_text());records=json.loads(MANIFEST.read_text())['glyph_records']
    fixed=set()
    for r in rows:
        if r['identical_to_native']:fixed.update((r['left'],r['right']))
    skip=set(json.loads(Path('data/typographic-completion/manifest.json').read_text()))|set('ƏəӘә')   # symbols and completed signs keep their designed advance
    free=[n for n,r in records.items() if r['character'].isalpha() and r['character'] not in skip and n not in fixed]
    fi={g:i for i,g in enumerate(free)};m=len(free)
    def weight(g):
        r=records.get(g)
        if r is None:return 0.3
        return FREQ.get(r['character'].lower(),0.3)
    eq=[];y=[];w=[]
    for r in rows:
        if r['identical_to_native'] or r['collision_limited']:continue   # a collision-limited value is a ceiling, not a need
        a,b=r['left'],r['right'];row=np.zeros(2*m)
        if a in fi:row[fi[a]]=1
        if b in fi:row[m+fi[b]]=1
        if not row.any():continue
        eq.append(row);y.append(r['additional']);w.append(np.sqrt(weight(a)*weight(b)))
    A=np.array(eq);y=np.array(y,float);W=np.array(w)
    Aw=np.vstack([A*W[:,None],np.sqrt(RIDGE)*np.eye(2*m)]);yw=np.r_[y*W,np.zeros(2*m)]
    x=np.linalg.lstsq(Aw,yw,rcond=None)[0];r_,l_=x[:m],x[m:]
    from fontTools.ttLib import TTFont
    font=TTFont(SOURCE_TTF);glyf=font['glyf'];hmtx=font['hmtx']
    glyphs=table['glyphs'];changed=0
    for g in free:
        r=int(round(r_[fi[g]]/2)*2);l=int(round(l_[fi[g]]/2)*2)
        gl=glyf[g];lsb=gl.xMin if gl.numberOfContours else 0;rsb=hmtx[g][0]-(gl.xMax if gl.numberOfContours else 0)
        l=max(l,FLOOR-lsb) if l<0 else l;r=max(r,FLOOR-rsb) if r<0 else r        # keep side bearings above the floor
        if abs(r)<MIN_SHIFT and abs(l)<MIN_SHIFT:continue
        old=glyphs.get(g,{'dx':0,'dadv':0});dx=old['dx']+l;dadv=old['dadv']+l+r
        dx=max(-MAX_TOTAL,min(MAX_TOTAL,dx));dadv=max(-MAX_TOTAL,min(MAX_TOTAL,dadv))
        glyphs[g]={'dx':dx,'dadv':dadv,'character':records[g]['character']};changed+=1
    SPACING.write_text(json.dumps(table,ensure_ascii=False,indent=1)+'\n')
    print(f'free glyphs {m}, shifted {changed}, rms of kerning before {np.sqrt((y**2).mean()):.1f}, after fit {np.sqrt(((y-A@x)**2).mean()):.1f}')

if __name__=='__main__':main()
