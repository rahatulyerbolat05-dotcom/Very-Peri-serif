#!/usr/bin/env python3
"""Roughness of outlines: the small bumps, dents, flats and bent "straight" lines the eye catches at display sizes and the node audits miss.
Method: every contour is sampled every STEP units of arc length; at each sample a cubic polynomial (in the local arc parameter) is fitted
by least squares to the samples within +-WIN units, separately in x and y, and the distance of the sample from the fit is its roughness.
A smooth curve, whatever its curvature, is followed by a cubic over 24 units; a bump, a dent, a kink or a step is not. Windows that hold a
drawn corner (turn above CORNER_DEG within 3 samples) are skipped. Calibrated on the native Latin a-z A-Z of the same font: a sample is a
defect when its roughness is above the native 99.9th percentile (and above FLOOR), neighbouring defects within 30 units are one place.
Usage: python3 -I tools/roughness_audit.py font.ttf [--chars абв...] [--json out.json] [--top N]
"""
import json,math,sys
import numpy as np
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen

STEP=2.;WIN=12.;CORNER_DEG=20.;FLOOR=0.35
LATIN='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
CYR='абвгдеёжзийклмнопрстуфхцчшщъыьэюяәғқңөұүһіАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯӘҒҚҢӨҰҮҺІ'


class Sampler(BasePen):
    def __init__(s,gs):super().__init__(gs);s.contours=[];s.cur=None
    def _moveTo(s,p):s.pts=[p];s.cur=p;s.start=p
    def _lineTo(s,p):
        L=math.dist(s.cur,p);k=max(1,int(L/0.5))
        s.pts+=[(s.cur[0]+(p[0]-s.cur[0])*i/k,s.cur[1]+(p[1]-s.cur[1])*i/k) for i in range(1,k+1)];s.cur=p
    def _qCurveToOne(s,a,b):
        p0=s.cur;L=math.dist(p0,a)+math.dist(a,b);k=max(4,int(L/0.5))
        for i in range(1,k+1):
            t=i/k;u=1-t;s.pts.append((u*u*p0[0]+2*u*t*a[0]+t*t*b[0],u*u*p0[1]+2*u*t*a[1]+t*t*b[1]))
        s.cur=b
    def _curveToOne(s,a,b,c):
        p0=s.cur;L=math.dist(p0,a)+math.dist(a,b)+math.dist(b,c);k=max(6,int(L/0.5))
        for i in range(1,k+1):
            t=i/k;u=1-t;s.pts.append((u**3*p0[0]+3*u*u*t*a[0]+3*u*t*t*b[0]+t**3*c[0],u**3*p0[1]+3*u*u*t*a[1]+3*u*t*t*b[1]+t**3*c[1]))
        s.cur=c
    def _closePath(s):
        if s.cur!=s.start:s._lineTo(s.start)
        s.contours.append(s.pts)
    _endPath=_closePath


def resample(P):
    P=np.array(P);d=np.r_[0,np.cumsum(np.hypot(*np.diff(P,axis=0).T))];n=max(8,int(d[-1]/STEP))
    s=np.linspace(0,d[-1],n,endpoint=False);return np.c_[np.interp(s,d,P[:,0]),np.interp(s,d,P[:,1])]


def roughness(Q):
    n=len(Q);h=int(WIN/STEP)
    if n<2*h+3:return np.zeros(n),np.zeros(n,bool)
    v=np.roll(Q,-1,0)-Q;a=np.degrees(np.arctan2(v[:,1],v[:,0]));turn=np.abs((np.roll(a,-1)-a+180)%360-180)
    corner=np.array([turn[(i+np.arange(-3,4))%n].sum()>CORNER_DEG for i in range(n)])
    t=np.arange(-h,h+1)*STEP;A=np.vander(t,4);pinv=np.linalg.pinv(A)
    r=np.zeros(n);skip=np.zeros(n,bool)
    for i in range(n):
        idx=(i+np.arange(-h,h+1))%n
        if corner[idx].any():skip[i]=True;continue
        W=Q[idx];cx=pinv@W[:,0];cy=pinv@W[:,1]
        r[i]=math.hypot(W[h,0]-cx[3],W[h,1]-cy[3])
    return r,skip


def curvature(Q,h=6):
    """Signed curvature at every sample from the local cubic fit (nan inside corner windows)."""
    n=len(Q);t=np.arange(-h,h+1)*STEP;A=np.vander(t,4);pinv=np.linalg.pinv(A);k=np.full(n,np.nan)
    if n<2*h+3:return k
    v=np.roll(Q,-1,0)-Q;a=np.degrees(np.arctan2(v[:,1],v[:,0]));turn=np.abs((np.roll(a,-1)-a+180)%360-180)
    for i in range(n):
        idx=(i+np.arange(-h,h+1))%n
        if turn[idx].sum()>25:continue
        cx=pinv@Q[idx,0];cy=pinv@Q[idx,1];x1,y1=cx[2],cy[2];x2,y2=2*cx[1],2*cy[1];sp=math.hypot(x1,y1)
        k[i]=(x1*y2-y1*x2)/sp**3
    return k


def comb_noise(font,name,smooth=10):
    """Mean |curvature - its running mean over +-smooth samples| (x1000) on the curved parts: how jagged the curvature comb is.
    A fair curve has a comb whose envelope changes slowly; a rough one zigzags. Straight stems (|k| < 0.0015) are left out."""
    vals=[]
    for Q,r,skip in glyph_samples(font,name):
        k=curvature(Q);n=len(k)
        for i in range(n):
            if np.isnan(k[i]) or abs(k[i])<0.0015:continue
            w=k[(i+np.arange(-smooth,smooth+1))%n]
            if np.isnan(w).any():continue
            vals.append(abs(k[i]-w.mean()))
    return 1000*float(np.mean(vals)) if vals else 0.,len(vals)


def glyph_samples(font,name):
    gs=font.getGlyphSet();pen=Sampler(gs);gs[name].draw(pen);out=[]
    for C in pen.contours:
        if len(C)<4:continue
        Q=resample(C);r,skip=roughness(Q);out.append((Q,r,skip))
    return out


def audit(font,chars,thr):
    cm=font.getBestCmap();res={}
    for ch in chars:
        n=cm.get(ord(ch))
        if not n:continue
        places=[]
        for Q,r,skip in glyph_samples(font,n):
            for i in np.argsort(-r):
                if r[i]<thr:break
                p=tuple(np.round(Q[i]).astype(int))
                if all(math.dist(p,q[0])>30 for q in places):places.append((p,round(float(r[i]),2)))
        res[ch]=dict(glyph=n,places=places)
    return res


def native_threshold(font):
    cm=font.getBestCmap();vals=[]
    for ch in LATIN:
        n=cm.get(ord(ch))
        if not n:continue
        for Q,r,skip in glyph_samples(font,n):vals+=list(r[~skip])
    vals=np.array(vals);return max(FLOOR,float(np.percentile(vals,99.9))),float(np.percentile(vals,99)),float(np.median(vals))


def main():
    path=sys.argv[1];font=TTFont(path);args=sys.argv[2:]
    chars=args[args.index('--chars')+1] if '--chars' in args else CYR
    thr,p99,med=native_threshold(font)
    lat=audit(font,LATIN,thr);res=audit(font,chars,thr)
    nl=sum(len(v['places']) for v in lat.values());nc=sum(len(v['places']) for v in res.values())
    print(f'native Latin: median {med:.3f}, p99 {p99:.3f}, p99.9 (threshold) {thr:.3f}; places above it: Latin {nl} in {len(lat)}, checked {nc} in {len(res)}')
    rank=sorted(res.items(),key=lambda kv:-len(kv[1]['places']))
    for ch,v in rank[:int(args[args.index('--top')+1]) if '--top' in args else 40]:
        if v['places']:print(ch,v['glyph'],len(v['places']),v['places'][:6])
    if '--json' in args:json.dump(dict(threshold=thr,latin_places=nl,glyphs=res),open(args[args.index('--json')+1],'w'),ensure_ascii=False,indent=1)


if __name__=='__main__':main()
