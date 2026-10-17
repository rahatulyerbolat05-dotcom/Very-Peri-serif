#!/usr/bin/env python3
"""Measure the native Instrument Serif Italic for the construction rules (docs/italic-rules.md).
All stroke measurements are taken across the stroke in de-slanted coordinates u = x - s*y (s = tan 13 degrees):
a horizontal scan of the slanted outline measures the wrong number.
Writes data/italic-rules.json. Needs the reference fonts (tools/fetch_reference.sh).
"""
import json,math,statistics,sys
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen

REF=Path('reference/instrument-serif/fonts/ttf')
S=math.tan(math.radians(13))


class Poly(BasePen):
    def __init__(self,gs,slant):
        super().__init__(gs);self.polys=[];self.slant=slant;self.cur=None
    def _p(self,p):return (p[0]-self.slant*p[1],p[1])
    def _moveTo(self,p):self.cur=self._p(p);self.pts=[self.cur]
    def _lineTo(self,p):self.pts.append(self._p(p));self.cur=self.pts[-1]
    def _qCurveToOne(self,a,b):
        p0=self.cur;a=self._p(a);b=self._p(b)
        for i in range(1,25):
            t=i/24;u=1-t;self.pts.append((u*u*p0[0]+2*u*t*a[0]+t*t*b[0],u*u*p0[1]+2*u*t*a[1]+t*t*b[1]))
        self.cur=b
    def _curveToOne(self,a,b,c):
        p0=self.cur;a=self._p(a);b=self._p(b);c=self._p(c)
        for i in range(1,25):
            t=i/24;u=1-t;self.pts.append((u**3*p0[0]+3*u*u*t*a[0]+3*u*t*t*b[0]+t**3*c[0],u**3*p0[1]+3*u*u*t*a[1]+3*u*t*t*b[1]+t**3*c[1]))
        self.cur=c
    def _closePath(self):self.polys.append(self.pts)


def polys(font,name,slant):
    gs=font.getGlyphSet();p=Poly(gs,slant);gs[name].draw(p);return p.polys


def runs(P,y):
    xs=[]
    for poly in P:
        for a,b in zip(poly,poly[1:]+poly[:1]):
            if (a[1]-y)*(b[1]-y)<0:xs.append(a[0]+(y-a[1])*(b[0]-a[0])/(b[1]-a[1]))
    xs.sort();return [(round(a,1),round(b,1)) for a,b in zip(xs[::2],xs[1::2])]


def main():
    it=TTFont(REF/'InstrumentSerif-Italic.ttf');rg=TTFont(REF/'InstrumentSerif-Regular.ttf')
    out={'slant_tan':round(S,5)}
    # 1. strokes across the stroke at several heights (de-slanted for Italic, plain for Regular)
    stems={}
    for n in 'ilnmuhpqbdaogkvxyzrtfsHINMOTAVXKE':
        P=polys(it,n,S);Q=polys(rg,n,0.)
        stems[n]={'italic':{y:runs(P,y) for y in (60,150,255,360,450)},'regular':{y:runs(Q,y) for y in (60,150,255,360,450)}}
    out['strokes']=stems
    # 2. entries and exits (de-slanted) near the x-height and the baseline
    ee={}
    for n in 'inmuhlkr':
        P=polys(it,n,S);ee[n]={y:runs(P,y) for y in (505,495,480,460,430,10,25,40,60)}
    out['entry_exit']=ee
    # 3. advances, side bearings (raw ink bounds) Latin Regular vs Italic
    adv={}
    gsi=it.getGlyphSet();gsr=rg.getGlyphSet()
    from fontTools.pens.boundsPen import BoundsPen
    cm=it.getBestCmap()
    for c in list(range(97,123))+list(range(65,91)):
        n=cm[c]
        bi=BoundsPen(gsi);gsi[n].draw(bi);br=BoundsPen(gsr);gsr[n].draw(br)
        ai=it['hmtx'][n][0];ar=rg['hmtx'][n][0]
        adv[chr(c)]={'italic':ai,'regular':ar,'ratio':round(ai/ar,3),'lsb_i':round(bi.bounds[0]),'rsb_i':round(ai-bi.bounds[2]),'lsb_r':round(br.bounds[0]),'rsb_r':round(ar-br.bounds[2])}
    out['advances']=adv
    low=[v['ratio'] for k,v in adv.items() if k.islower()];cap=[v['ratio'] for k,v in adv.items() if k.isupper()]
    out['advance_ratio']={'lower_mean':round(statistics.mean(low),3),'lower_sd':round(statistics.pstdev(low),3),'upper_mean':round(statistics.mean(cap),3),'upper_sd':round(statistics.pstdev(cap),3)}
    # 4. vertical extremes
    ext={}
    for n in 'onuaecgpqdbfhklmrstvwxyzHIOTAVE':
        b=BoundsPen(gsi);gsi[n].draw(b);ext[n]=[round(v) for v in b.bounds]
    out['bounds']=ext
    # 5. derived numbers used by docs/italic-rules.md
    der={'entry_extra':{},'exit_extra':{},'stem_across':{},'pitch':{},'counter':{}}
    for n in 'inmur':
        e=ee.get(n) if n in ee else None
    for n in 'inmur':
        P=polys(it,n,S);r255=runs(P,255);r430=runs(P,430);r60=runs(P,60)
        stem_left=[r for r in r255][0][0]
        tip_left=min(a for a,b in r430)
        der['entry_extra'][n]=round(stem_left-tip_left,1)
        if n!='r':
            last_stem_right=r255[-1][1];tip_right=max(b for a,b in r60)
            der['exit_extra'][n]=round(tip_right-last_stem_right,1)
    for n in 'ilnmuhHIpqbdo':
        r=stems[n]['italic'][255];der['stem_across'][n]=[round(b-a,1) for a,b in r]
        if len(r)>1:
            der['pitch'][n]=[round(b[0]-a[0],1) for a,b in zip(r,r[1:])]
            der['counter'][n]=[round(b[0]-a[1],1) for a,b in zip(r,r[1:])]
    der['pitch_regular']={n:[round(b[0]-a[0],1) for a,b in zip(stems[n]['regular'][255],stems[n]['regular'][255][1:])] for n in 'nmu'}
    out['derived']=der
    fam={'n,h,m (stems+arch)':round((adv['n']['ratio']+adv['h']['ratio']+adv['m']['ratio'])/3,3),'n':adv['n']['ratio'],'m':adv['m']['ratio'],'u':adv['u']['ratio'],
         'o,c,e,p,q,b,d,g (round)':round(sum(adv[x]['ratio'] for x in 'ocepqbdg')/8,3),'a':adv['a']['ratio'],'v,w,x,y,z,k (diagonal)':round(sum(adv[x]['ratio'] for x in 'vwxyzk')/6,3),'r':adv['r']['ratio'],'capitals':out['advance_ratio']['upper_mean']}
    out['advance_families']=fam
    Path('data/italic-rules.json').write_text(json.dumps(out,ensure_ascii=False,indent=1)+'\n')
    print('written')

if __name__=='__main__':main()
