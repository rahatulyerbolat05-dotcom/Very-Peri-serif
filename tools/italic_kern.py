#!/usr/bin/env python3
"""Pair kerning of the Italic Cyrillic lowercase (docs/italic-rules.md R20; method of tools/optical_kerning.py of the Regular).
Run after the side bearings are fitted (tools/italic_respace.py): kerning is for pair exceptions only.
  gap(a,b)     optical gap: soft minimum of the ink gap over the x-height band (optical_kerning.optical)
  target       mean gap of the native letter pairs (а е ё и о п р с т у х), the rhythm the native Italic keeps
  kern         (target - gap) * STRENGTH when |target - gap| >= DEADBAND, rounded to 2 units, at most +LIMIT_PLUS / -LIMIT_MINUS,
               and never below the value that keeps MIN_CLEAR units between the facing ink at any row (no touching)
Pairs of two native letters (the Latin kerning of the font applies to them) are never written. Output: data/italic-kerning.json, a kern lookup
merged into the font (script cyrl inherits the native kern feature).
Usage: python3 -I tools/italic_kern.py [font.ttf] [--report]
"""
import glob,json,math,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from fontTools.ttLib import TTFont
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
import optical_kerning as OK
import italic_audit as A

NATIVE=set('аеёиопрстух')
STRENGTH=0.8;DEADBAND=int(next((a.split('=')[1] for a in sys.argv if a.startswith('--deadband=')),24));LIMIT_PLUS=40;LIMIT_MINUS=70;MIN_CLEAR=10;STEP=2
LETTERS='абвгдеёжзийклмнопрстуфхцчшщъыьэюя'
CAPS='АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ';CAPS_NATIVE=set('АВЕЁКМНОРСТХ')
OUT=Path('data/italic-kerning.json')


def measure(prof,cm,left,right,high,native_left,native_right):
    """(rows, target): rows[(a,b)] = (optical gap, closest row gap) for pairs with a free letter, target = mean over native/native pairs."""
    rows={};nat=[]
    for a in left:
        for b in right:
            if cm.get(ord(a)) not in prof or cm.get(ord(b)) not in prof:continue
            gap,valid=OK.gap_profile(prof[cm[ord(a)]],prof[cm[ord(b)]])
            v=OK.optical(gap,valid,high)
            if v is None:continue
            if a in native_left and b in native_right:nat.append(float(v));continue
            m=valid&(OK.Y>=-20)&(OK.Y<=high+10)
            if m.any():rows[(a,b)]=(float(v),float(gap[m].min()))
    return rows,float(np.mean(nat))


def main():
    args=[a for a in sys.argv[1:] if not a.startswith('--')]
    path=args[0] if args else sorted(glob.glob('build/italic-lower/VeryPeriSerifItalicI*.ttf'))[-1]
    font=TTFont(path);cm=font.getBestCmap();prof=OK.profiles(font)
    sets=[('строчные',LETTERS,LETTERS,510,NATIVE,NATIVE),('прописная+строчная',CAPS,LETTERS,510,CAPS_NATIVE,NATIVE),('прописные',CAPS,CAPS,720,CAPS_NATIVE,CAPS_NATIVE)]
    rows={};pairs={};targets={}
    for label,L,R,high,nl,nr in sets:
        part,target=measure(prof,cm,L,R,high,nl,nr);targets[label]=round(target,1)
        for (a,b),(v,mn) in part.items():
            d=target-v;k=0.
            if abs(d)>=DEADBAND:k=max(-LIMIT_MINUS,min(LIMIT_PLUS,d*STRENGTH))
            k=max(k,MIN_CLEAR-mn)
            k=int(round(k/STEP)*STEP)
            rows[(label,a,b)]=(v,mn,target)
            if k:pairs[a+b]=k
    target=targets['строчные']
    # report
    print('targets',targets)
    for label,*_ in sets:
        keys=[k for k in rows if k[0]==label]
        wts=np.array([math.sqrt(A.FREQ.get(a.lower(),.3)*A.FREQ.get(b.lower(),.3)) for _,a,b in keys])
        out=[]
        for stage in ('before','after'):
            g=np.array([rows[k][0]+(pairs.get(k[1]+k[2],0) if stage=='after' else 0) for k in keys])
            wm=np.sum(wts*g)/np.sum(wts);out.append(round(math.sqrt(np.sum(wts*(g-wm)**2)/np.sum(wts))/wm,3))
        n=sum(1 for k in keys if pairs.get(k[1]+k[2]));print(f'{label}: пар {len(keys)}, с кернингом {n} ({100*n/len(keys):.1f}%), cv {out[0]} -> {out[1]}')
    touching=[(a+b,round(mn+pairs.get(a+b,0),1)) for (lb,a,b),(v,mn,t) in rows.items() if mn+pairs.get(a+b,0)<MIN_CLEAR-0.5]
    print('closest rows below',MIN_CLEAR,':',touching[:10])
    OUT.write_text(json.dumps({'note':'tools/italic_kern.py','target_gaps':targets,'pairs':dict(sorted(pairs.items()))},ensure_ascii=False,indent=1)+'\n')
    if '--report' in sys.argv:return
    # apply: a separate compiled lookup merged into the font (as the Regular build does)
    from build_draft_font import merge_layout
    names=lambda ch:font.getGlyphName(cm[ord(ch)]) if False else cm[ord(ch)]
    fea=['languagesystem DFLT dflt;','languagesystem latn dflt;','languagesystem cyrl dflt;','feature kern {']
    fea+=[f'pos {cm[ord(k[0])]} {cm[ord(k[1])]} {v};' for k,v in sorted(pairs.items())]
    fea+=['} kern;']
    import copy
    extra=copy.deepcopy(font)
    for tag in ('GSUB','GPOS','GDEF'):
        if tag in extra:del extra[tag]
    addOpenTypeFeaturesFromString(extra,'\n'.join(fea)+'\n')
    merge_layout(font,extra,'GPOS')
    font.save(path);print('kerning applied to',path)


if __name__=='__main__':main()
