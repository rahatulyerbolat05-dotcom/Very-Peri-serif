#!/usr/bin/env python3
"""Audit of the Italic test font: structure (points, curve defects), line laws, spacing rhythm.
Usage: python3 -I tools/italic_audit.py [font.ttf] [--json data/italic-audit.json]
Per letter: category (native donor, assembled from native parts, Regular draft), advance, ink side bearings, points, polish_audit
counts (kink, extrema, micro, wobble, slop, zone), italic_check verdict, vertical extremes. Baseline: native Latin lowercase of the
same font. Spacing: optical gap (soft minimum over the x-height band, tools/optical_kerning.py) for every lowercase pair, fitted as
c + r_a + l_b with frequency weights; per-letter side effects and the spread (cv) of the gaps against the native Latin pairs.
"""
import json,math,sys,glob
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from fontTools.ttLib import TTFont
import polish_audit as PA
from italic_check import check as line_check
import optical_kerning as OK

REF=Path('reference/instrument-serif/fonts/ttf/InstrumentSerif-Italic.ttf')
NATIVE=set('аеёорсухіһипт')                      # direct donors among the lowercase (plan: п=n т=m и=u)
ASSEMBLED=set('шщцндлкжйөғь ъ ы'.replace(' ',''))
DRAFT=set('взэчяюфбм')
FREQ=dict(zip("оеаинтсрвлкмдпуяыьгзбчйхжшюцщэф",[10.97,8.45,8.01,7.35,6.70,6.26,5.47,4.73,4.54,4.34,3.49,3.21,2.98,2.81,2.62,2.01,1.90,1.74,1.69,1.65,1.59,1.45,1.21,0.97,0.94,0.72,0.64,0.48,0.36,0.32,0.26]))
LAT=dict(zip("etaoinshrdlcumwfgypbvkjxqz",[12.7,9.1,8.2,7.5,7.0,6.7,6.3,6.1,6.0,4.3,4.0,2.8,2.8,2.4,2.4,2.2,2.0,2.0,1.9,1.5,1.0,0.8,0.15,0.15,0.1,0.07]))


def category(ch):
    if ch in NATIVE:return 'native'
    if ch in ASSEMBLED:return 'assembled'
    if ch in DRAFT:return 'draft'
    return 'other'


def structure(font,chars):
    cm=font.getBestCmap();rows={}
    for ch in chars:
        n=cm.get(ord(ch))
        if not n or font['glyf'][n].numberOfContours==0:continue
        g=font['glyf'][n];res=PA.check(font,n)
        try:
            problems,_=line_check(font,n,ch)
        except Exception as e:
            problems=['ошибка проверки']
        rows[ch]=dict(glyph=n,advance=font['hmtx'][n][0],lsb=g.xMin,rsb=font['hmtx'][n][0]-g.xMax,ymin=g.yMin,ymax=g.yMax,points=len(g.getCoordinates(font['glyf'])[0]),
                      kink=len(res['kink']),extrema=len(res['extrema']),micro=len(res['micro']),wobble=len(res['wobble']),slop=len(res['slop']),zone=len(res['zone']),lines=problems)
    return rows


def pair_gaps(font,left,right,high=510):
    prof=OK.profiles(font);cm=font.getBestCmap();G={}
    for a in left:
        for b in right:
            na,nb=cm.get(ord(a)),cm.get(ord(b))
            if na not in prof or nb not in prof:continue
            gap,valid=OK.gap_profile(prof[na],prof[nb]);v=OK.optical(gap,valid,high)
            if v is not None:G[(a,b)]=v
    return G


def fit(G,freq):
    letters_l=sorted({a for a,_ in G});letters_r=sorted({b for _,b in G})
    il={a:i for i,a in enumerate(letters_l)};ir={b:i for i,b in enumerate(letters_r)}
    A=[];y=[];w=[]
    for (a,b),v in G.items():
        row=np.zeros(1+len(il)+len(ir));row[0]=1;row[1+il[a]]=1;row[1+len(il)+ir[b]]=1
        A.append(row);y.append(v);w.append(math.sqrt(freq.get(a,0.2)*freq.get(b,0.2)))
    A=np.array(A);y=np.array(y);w=np.array(w)
    reg=np.zeros((2,A.shape[1]));reg[0,1:1+len(il)]=1;reg[1,1+len(il):]=1       # side effects sum to zero
    Aw=np.vstack([A*w[:,None],reg*100]);yw=np.r_[y*w,0,0]
    x=np.linalg.lstsq(Aw,yw,rcond=None)[0]
    fitted=A@x;res=y-fitted
    wm=np.sum(w*y)/np.sum(w);cv=math.sqrt(np.sum(w*(y-wm)**2)/np.sum(w))/wm
    cv_res=math.sqrt(np.sum(w*res**2)/np.sum(w))/wm
    return dict(c=float(x[0]),r={a:float(x[1+il[a]]) for a in letters_l},l={b:float(x[1+len(il)+ir[b]]) for b in letters_r},mean_gap=float(wm),cv=cv,cv_after_side_fit=cv_res,
                worst=sorted(((float(r),a,b) for r,(a,b) in zip(res,G)),key=lambda t:-abs(t[0]))[:12])


def main():
    args=[a for a in sys.argv[1:] if not a.startswith('--')]
    path=args[0] if args else sorted(glob.glob('build/italic-lower/VeryPeriSerifItalicI*.ttf'))[-1]
    font=TTFont(path);native=TTFont(REF)
    cyr_low=list('абвгдеёжзийклмнопрстуфхцчшщъыьэюя')
    cyr_cap=[chr(c) for c in range(0x410,0x430)]+['Ё']
    lat=list('abcdefghijklmnopqrstuvwxyz')
    out={'font':path}
    out['structure_cyr_lower']=structure(font,cyr_low)
    out['structure_cyr_caps']=structure(font,cyr_cap)
    out['structure_latin']=structure(native,lat)
    # baseline summary by category
    def summ(rows,keys=('points','kink','extrema','micro','wobble','slop','zone')):
        if not rows:return {}
        return {k:round(sum(r[k] for r in rows.values())/len(rows),2) for k in keys}
    cats={}
    for ch,r in out['structure_cyr_lower'].items():cats.setdefault(category(ch),{})[ch]=r
    out['summary']={'latin':summ(out['structure_latin'])}
    for c,rows in cats.items():out['summary'][c]=dict(letters=''.join(rows),**summ(rows))
    # spacing
    cyr=[c for c in cyr_low if c in out['structure_cyr_lower']]
    Gc=pair_gaps(font,cyr,cyr);out['spacing_cyr']=fit(Gc,FREQ)
    Gl=pair_gaps(native,lat,lat);out['spacing_latin_native']=fit(Gl,LAT)
    dest=sys.argv[sys.argv.index('--json')+1] if '--json' in sys.argv else 'data/italic-audit.json'
    Path(dest).write_text(json.dumps(out,ensure_ascii=False,indent=1)+'\n')
    print(path)
    for k,v in out['summary'].items():print(k,v)
    for k in ('spacing_cyr','spacing_latin_native'):
        s=out[k];print(k,'mean gap',round(s['mean_gap'],1),'cv',round(s['cv'],3),'cv after side fit',round(s['cv_after_side_fit'],3))
    print('worst Cyrillic pairs',[(round(r,1),a+b) for r,a,b in out['spacing_cyr']['worst'][:8]])


if __name__=='__main__':main()
