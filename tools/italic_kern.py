#!/usr/bin/env python3
"""Pair kerning of the Italic Cyrillic lowercase (docs/italic-rules.md R20; method of tools/optical_kerning.py of the Regular).
Run after the side bearings are fitted (tools/italic_respace.py): kerning is for pair exceptions only.
  gap(a,b)     optical gap: soft minimum of the ink gap over the x-height band (optical_kerning.optical)
  target       mean gap of the native letter pairs (а е ё и о п р с т у х), the rhythm the native Italic keeps
  kern         (target - gap) * STRENGTH when |target - gap| >= DEADBAND, rounded to 2 units, at most +LIMIT_PLUS / -LIMIT_MINUS,
               and never below the value that keeps MIN_CLEAR units between the facing ink at any row of the x-height band and DESC_CLEAR
               under the baseline (I023: tails were not protected, ү ұ + у р came to 6-9 units)
Kazakh letters are in the sets (I023), and the alternates of tools/italic_features.py (data/italic-features.json) are kerned as glyphs
against all lowercase letters; their keys in the output are 'glyph glyph'.
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

NATIVE=set('аеёиопрстухһі')
STRENGTH=0.8;DEADBAND=int(next((a.split('=')[1] for a in sys.argv if a.startswith('--deadband=')),24));LIMIT_PLUS=40;LIMIT_MINUS=70;MIN_CLEAR=20;STEP=2;DESC_CLEAR=20
LETTERS='абвгдеёжзийклмнопрстуфхцчшщъыьэюяәғқңөұүһі'
CAPS='АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯӘҒҚҢӨҰҮҺІ';CAPS_NATIVE=set('АВЕЁКМНОРСТХҺІ')
FEATURES=Path('data/italic-features.json')
BAR_LIMIT={'uni0442.ss03':24,'uni0433.ss04':24}     # printed т г: the soft minimum would tuck the neighbours under the bar (-70) and hide its ends
TARGET=set('аеёиопрстух')|set('АВЕЁКМНОРСТХ')        # the rhythm target: native pairs of I009-I022 (һ і are native but not in the mean)
OUT=Path('data/italic-kerning.json')


def measure(prof,left,right,high):
    """left/right: [(key, glyph, native)]. (rows, target): rows[(ka,kb)] = (optical gap, closest row gap in the x-height band, closest row
    gap under the baseline or None) for pairs with a free glyph, target = mean over native/native pairs."""
    rows={};nat=[]
    for ka,ga,na in left:
        for kb,gb,nb in right:
            if ga not in prof or gb not in prof:continue
            gap,valid=OK.gap_profile(prof[ga],prof[gb])
            v=OK.optical(gap,valid,high)
            if v is None:continue
            if na and nb:
                if ka in TARGET and kb in TARGET:nat.append(float(v))
                continue
            m=valid&(OK.Y>=-20)&(OK.Y<=high+10);d=valid&(OK.Y<-20)
            if m.any():rows[(ka,kb)]=(float(v),float(gap[m].min()),float(gap[d].min()) if d.any() else None)
    return rows,float(np.mean(nat))


def main():
    args=[a for a in sys.argv[1:] if not a.startswith('--')]
    path=args[0] if args else sorted(glob.glob('build/italic-lower/VeryPeriSerifItalicI*.ttf'))[-1]
    font=TTFont(path);cm=font.getBestCmap();prof=OK.profiles(font)
    items=lambda chars,native:[(c,cm[ord(c)],c in native) for c in chars if ord(c) in cm]
    # alternates and localized forms (tools/italic_features.py): measured as glyphs, a native outline counts as native
    extra=json.loads(FEATURES.read_text())['kern_glyphs'] if FEATURES.exists() else {}
    ext=[(g,g,nat) for g,(ch,nat) in extra.items() if g in prof]
    low=items(LETTERS,NATIVE)
    sets=[('строчные',low+ext,low+ext,510),('прописная+строчная',items(CAPS,CAPS_NATIVE),low+ext,510),('прописные',items(CAPS,CAPS_NATIVE),items(CAPS,CAPS_NATIVE),720)]
    glyph_of={k:g for _,L,R,_ in sets for k,g,_ in L+R}
    rows={};pairs={};targets={}
    pk=lambda a,b:a+b if len(a)==1 and len(b)==1 else a+' '+b
    for label,L,R,high in sets:
        part,target=measure(prof,L,R,high);targets[label]=round(target,1)
        for (a,b),(v,mn,md) in part.items():
            d=target-v;k=0.
            if abs(d)>=DEADBAND:k=max(-min(LIMIT_MINUS,BAR_LIMIT.get(a,LIMIT_MINUS),BAR_LIMIT.get(b,LIMIT_MINUS)),min(LIMIT_PLUS,d*STRENGTH))
            k=max(k,MIN_CLEAR-mn)
            if md is not None:k=max(k,DESC_CLEAR-md)       # tails under the baseline (ү ұ + у р touched at 6-9 units)
            k=int(round(k/STEP)*STEP)
            rows[(label,a,b)]=(v,min(mn,md if md is not None else mn),target)
            if k:pairs[pk(a,b)]=k
    target=targets['строчные']
    # report
    print('targets',targets)
    for label,*_ in sets:
        keys=[k for k in rows if k[0]==label]
        wts=np.array([math.sqrt(A.FREQ.get(a.lower(),.3)*A.FREQ.get(b.lower(),.3)) for _,a,b in keys])
        out=[]
        for stage in ('before','after'):
            g=np.array([rows[k][0]+(pairs.get(pk(k[1],k[2]),0) if stage=='after' else 0) for k in keys])
            wm=np.sum(wts*g)/np.sum(wts);out.append(round(math.sqrt(np.sum(wts*(g-wm)**2)/np.sum(wts))/wm,3))
        n=sum(1 for k in keys if pairs.get(pk(k[1],k[2])));print(f'{label}: пар {len(keys)}, с кернингом {n} ({100*n/len(keys):.1f}%), cv {out[0]} -> {out[1]}')
    touching=[(pk(a,b),round(mn+pairs.get(pk(a,b),0),1)) for (lb,a,b),(v,mn,t) in rows.items() if mn+pairs.get(pk(a,b),0)<MIN_CLEAR-0.5]
    print('closest rows below',MIN_CLEAR,':',touching[:10])
    OUT.write_text(json.dumps({'note':'tools/italic_kern.py','target_gaps':targets,'pairs':dict(sorted(pairs.items()))},ensure_ascii=False,indent=1)+'\n')
    if '--report' in sys.argv:return
    # apply: a separate compiled lookup merged into the font (as the Regular build does)
    from build_draft_font import merge_layout
    names=lambda ch:font.getGlyphName(cm[ord(ch)]) if False else cm[ord(ch)]
    fea=['languagesystem DFLT dflt;','languagesystem latn dflt;','languagesystem cyrl dflt;','feature kern {']
    fea+=[f'pos {glyph_of[k[0]]} {glyph_of[k[1]]} {v};' if len(k)==2 else 'pos {} {} {};'.format(*[glyph_of[x] for x in k.split()],v) for k,v in sorted(pairs.items())]
    fea+=['} kern;']
    import copy
    extra=copy.deepcopy(font)
    for tag in ('GSUB','GPOS','GDEF'):
        if tag in extra:del extra[tag]
    addOpenTypeFeaturesFromString(extra,'\n'.join(fea)+'\n')
    merge_layout(font,extra,'GPOS')
    font.save(path);print('kerning applied to',path)


if __name__=='__main__':main()
