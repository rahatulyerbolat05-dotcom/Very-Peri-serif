#!/usr/bin/env python3
"""Fit side-bearing shifts of the free (assembled and draft) Italic lowercase letters so that their optical gaps match the gaps of the
native letters (docs/italic-rules.md R17-R19; method of tools/respace.py for the Regular).
Model: gap(a,b) = m + s_r(a) + s_l(b) for pairs that involve a free letter; m is the mean gap of native/native pairs (а е ё и о п р с т у х),
native letters keep s=0. Weighted (letter frequency) ridge least squares; shifts rounded to even units, floor -20 on any side bearing.
Writes data/italic-spacing.json: {character: {dx, dadv}}; tools/italic_lower.py applies it. An optional manually selected advance fixes the final width independently of control-point rounding. Workflow: build with an empty spacing file, run this, build again.
Usage: python3 -I tools/italic_respace.py [font.ttf] [--reset]
--caps fits the capitals; the shifts are absolute, so it must measure a build whose capitals carry no shifts (I021: measured on a build
with shifts applied it returned only the residuals and the next build lost the spacing; every other chain flipped). Chain:
caps --reset, italic_caps, --reset, italic_lower, fit, italic_lower, --caps, italic_caps, italic_lower, italic_kern.
"""
import glob,json,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from fontTools.ttLib import TTFont
import italic_audit as A

OUT=Path('data/italic-spacing.json')
CAPS='АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ';CAPS_NATIVE=set('АВЕЁКМНОРСТХ');CAPS_OUT=Path('data/italic-caps-spacing.json')
NATIVE=set('аеёиопрстух')
RIDGE=0.3;FLOOR=-20;MIN_SHIFT=4;LIMIT=90


def main():
    caps='--caps' in sys.argv
    if '--reset' in sys.argv and caps:
        CAPS_OUT.write_text(json.dumps({'note':'side-bearing shifts of the Italic capitals, tools/italic_respace.py --caps','glyphs':{}},indent=1)+'\n');print('reset caps');return
    if '--reset' in sys.argv:
        OUT.write_text(json.dumps({'note':'side-bearing shifts of free Italic lowercase letters, tools/italic_respace.py','glyphs':{}},indent=1)+'\n');print('reset');return
    args=[a for a in sys.argv[1:] if not a.startswith('--')]
    path=args[0] if args else sorted(glob.glob('build/italic-lower/VeryPeriSerifItalicI*.ttf'))[-1]
    font=TTFont(path);cm=font.getBestCmap()
    native=CAPS_NATIVE if caps else NATIVE
    LOW='абвгдеёжзийклмнопрстуфхцчшщъыьэюя'
    has=lambda c:ord(c) in cm and font['glyf'][cm[ord(c)]].numberOfContours
    letters=[c for c in (CAPS if caps else LOW) if has(c)]
    G=A.pair_gaps(font,letters,letters,high=720 if caps else 510)
    nn=[v for (a,b),v in G.items() if a in native and b in native];m=float(np.mean(nn))
    free=[c for c in letters if c not in native];fi={c:i for i,c in enumerate(free)};n=len(free)
    rows=[];y=[];w=[]
    for (a,b),v in G.items():
        row=np.zeros(2*n)
        if a in fi:row[fi[a]]=1                       # s_r of a
        if b in fi:row[n+fi[b]]=1                     # s_l of b
        if not row.any():continue
        rows.append(row);y.append(m-v);w.append(np.sqrt(A.FREQ.get(a.lower(),0.3)*A.FREQ.get(b.lower(),0.3)))
    if caps:                                         # capital + lowercase pairs: the capital is on the left, the lowercase letters are fixed
        low=[c for c in LOW if has(c)]
        Gl=A.pair_gaps(font,letters,low,high=510)
        ml=float(np.mean([v for (a,b),v in Gl.items() if a in native and b in NATIVE]))
        for (a,b),v in Gl.items():
            if a not in fi:continue
            row=np.zeros(2*n);row[fi[a]]=1
            rows.append(row);y.append(ml-v);w.append(np.sqrt(A.FREQ.get(a.lower(),0.3)*A.FREQ.get(b,0.3))*0.8)
        print('target gaps: capital/capital',round(m,1),'capital/lowercase',round(ml,1))
    X=np.array(rows);y=np.array(y);W=np.array(w)
    Aw=np.vstack([X*W[:,None],np.sqrt(RIDGE)*np.eye(2*n)]);yw=np.r_[y*W,np.zeros(2*n)]
    sol=np.linalg.lstsq(Aw,yw,rcond=None)[0];r_,l_=sol[:n],sol[n:]
    table={'note':'side-bearing shifts of free Italic lowercase letters, tools/italic_respace.py','glyphs':{},'mean_native_gap':round(m,1)}
    for c in free:
        g=font['glyf'][cm[ord(c)]];adv=font['hmtx'][cm[ord(c)]][0];lsb=g.xMin;rsb=adv-g.xMax
        r=int(round(r_[fi[c]]/2)*2);l=int(round(l_[fi[c]]/2)*2)
        l=max(l,FLOOR-lsb) if l<0 else l;r=max(r,FLOOR-rsb) if r<0 else r
        l=max(-LIMIT,min(LIMIT,l));r=max(-LIMIT,min(LIMIT,r))
        if abs(l)<MIN_SHIFT and abs(r)<MIN_SHIFT:continue
        table['glyphs'][c]={'dx':l,'dadv':l+r}
    (CAPS_OUT if caps else OUT).write_text(json.dumps(table,ensure_ascii=False,indent=1)+'\n')
    print('native mean gap',round(m,1),'shifts',{c:(v['dx'],v['dadv']-v['dx']) for c,v in table['glyphs'].items()})


if __name__=='__main__':main()
