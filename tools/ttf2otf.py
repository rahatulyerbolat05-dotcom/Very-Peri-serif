#!/usr/bin/env python3
"""OpenType CFF (.otf) from the release TTF, as Instrument publishes fonts/otf next to fonts/ttf.
The TrueType quadratic outlines are converted to cubic ones by fontTools qu2cu (MAX_ERR font units, composites drawn out), every other
table (cmap, GSUB, GPOS, GDEF, STAT, name, OS/2, hhea, hmtx, meta) is copied unchanged; post becomes format 3 (names live in CFF),
the TrueType hinting tables go. The blue zones are the alignment zones of the Instrument sources (CLAUDE.md 2).
Reviewed ya uses exact degree elevation with fractional CFF controls; check() verifies the serialized controls separately.
Check (check()): the same glyph order, advances, vertical metrics and shaping tables, every glyph within MAX_ERR+0.5 of the TTF (Hausdorff distance of densely sampled outlines).
Usage: python3 -I tools/ttf2otf.py in.ttf out.otf
"""
import math,sys
from pathlib import Path
from fontTools.ttLib import TTFont,newTable
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.qu2cuPen import Qu2CuPen
from fontTools.pens.reverseContourPen import ReverseContourPen
from fontTools.pens.basePen import BasePen

MAX_ERR=0.5
BLUES=[-15,0,510,525,720,735,740,755];OTHER_BLUES=[-220,-205];STEM_V=68;STEM_H=30
DROP=('glyf','loca','cvt ','fpgm','prep','gasp','hdmx','LTSH','VDMX')
EXACT_CUBICS={'uni044F'}  # Preserve the reviewed ya crown and short terminal transitions.
EXACT_ITALIC_CUBICS={'uni0433','uni0493','uni0446','uni0449','uni04A3','uni0447'}


def exact_names(font):
    return EXACT_CUBICS | (EXACT_ITALIC_CUBICS if font['post'].italicAngle else set())


def convert(src,dst):
    tt=TTFont(src);gs=tt.getGlyphSet();order=tt.getGlyphOrder();cs={};exact=exact_names(tt)
    for n in order:
        pen=T2CharStringPen(tt['hmtx'][n][0],gs,roundTolerance=0 if n in exact else .5)
        if n in exact:
            # Degree elevation is exact; retaining fractional controls avoids
            # reintroducing a crown kink through integer CFF rounding/fitting.
            gs[n].draw(ReverseContourPen(pen))
        else:
            gs[n].draw(Qu2CuPen(pen,max_err=MAX_ERR,all_cubic=False,reverse_direction=True))   # TrueType outlines run clockwise, CFF counter-clockwise; a quadratic left by qu2cu (on-curve-less circles) is raised to a cubic exactly by T2CharStringPen
        cs[n]=pen.getCharString()
    name=tt['name'];post=tt['post']
    fb=FontBuilder(tt['head'].unitsPerEm,isTTF=False);fb.setupGlyphOrder(order)
    info=dict(FullName=name.getDebugName(4),FamilyName=name.getDebugName(1),Weight=name.getDebugName(2),version=name.getDebugName(5).replace('Version ',''),
              Notice=name.getDebugName(0),Copyright=name.getDebugName(0),isFixedPitch=0,ItalicAngle=post.italicAngle,
              UnderlinePosition=post.underlinePosition,UnderlineThickness=post.underlineThickness)
    fb.setupCFF(name.getDebugName(6),info,cs,dict(BlueValues=BLUES,OtherBlues=OTHER_BLUES,StdHW=STEM_H,StdVW=STEM_V))
    for tag in tt.keys():                                    # every other table from the TTF, unchanged
        if tag not in DROP+('GlyphOrder','maxp','post','CFF ') and tag not in fb.font:fb.font[tag]=tt[tag]
    for tag in ('head','hhea','hmtx','cmap','name','OS/2'):fb.font[tag]=tt[tag]
    fb.setupMaxp();fb.setupPost(keepGlyphNames=False,italicAngle=post.italicAngle,underlinePosition=post.underlinePosition,
                                underlineThickness=post.underlineThickness,isFixedPitch=post.isFixedPitch)
    fb.font['head'].glyphDataFormat=0;fb.font.recalcBBoxes=True;fb.font.recalcTimestamp=False;fb.save(dst)
    return dst


def check(ttf,otf):
    a=TTFont(ttf);b=TTFont(otf);ga=a.getGlyphSet();gb=b.getGlyphSet();bad=[];worst=0.
    assert a.getGlyphOrder()==b.getGlyphOrder(),'glyph order'
    for tag in ('cmap','GSUB','GPOS','GDEF','STAT','name','OS/2','meta'):
        if tag in a:assert a.getTableData(tag)==b.getTableData(tag),'table '+tag
    for k in ('ascent','descent','lineGap','advanceWidthMax'):assert getattr(a['hhea'],k)==getattr(b['hhea'],k),'hhea '+k   # extents follow the cubic bounds
    assert all(a['hmtx'][n][0]==b['hmtx'][n][0] for n in a.getGlyphOrder()),'advances'
    for n in a.getGlyphOrder():
        pa=samples(ga,n);pb=samples(gb,n)
        dev=max(nearest(pa,pb),nearest(pb,pa));worst=max(worst,dev)   # Hausdorff distance of the outlines
        if dev>MAX_ERR+0.5:bad.append((n,round(float(dev),3)))
    exact={n:exact_cubic_error(a,b,n) for n in exact_names(a) if n in ga}
    assert all(error<.002 for error in exact.values()),('Exact CFF outline drift',exact)
    return dict(glyphs=len(a.getGlyphOrder()),hausdorff_worst=round(float(worst),3),over_limit=bad,exact_cubic_control_error=exact)


def exact_cubic_error(ttf,otf,name):
    """Compare exported CFF with exact quadratic degree elevation, including closures."""
    class Cubics(BasePen):
        def __init__(self,gs):super().__init__(gs);self.ops=[]
        def _moveTo(self,p):self.start=p;self.ops.append(('M',(p,)))
        def _lineTo(self,p):self.ops.append(('L',(p,)))
        def _curveToOne(self,a,b,c):self.ops.append(('C',(a,b,c)))
        def _closePath(self):
            if self.ops[-1]==('L',(self.start,)):self.ops.pop()
            self.ops.append(('Z',()))
        _endPath=_closePath
    a=Cubics(ttf.getGlyphSet());b=Cubics(otf.getGlyphSet())
    ttf.getGlyphSet()[name].draw(ReverseContourPen(a));otf.getGlyphSet()[name].draw(b)
    assert [op for op,pts in a.ops]==[op for op,pts in b.ops],('Exact CFF segment structure',name)
    return max((math.dist(p,q) for (_,ps),(_,qs) in zip(a.ops,b.ops) for p,q in zip(ps,qs)),default=0.)


def samples(gs,name,spacing=4.):
    """Closed polylines along the outline, a point every SPACING units or closer (lines and cubic curves; quadratics are split by BasePen)."""
    import math
    from fontTools.pens.basePen import BasePen
    class P(BasePen):
        def __init__(s,g):super().__init__(g);s.lines=[];s.cur=[]
        def _moveTo(s,p):s.cur=[p];s.start=p
        def _lineTo(s,p):
            a=s._getCurrentPoint();k=max(1,math.ceil(math.dist(a,p)/spacing));s.cur+=[(a[0]+(p[0]-a[0])*t/k,a[1]+(p[1]-a[1])*t/k) for t in range(1,k+1)]
        def _curveToOne(s,p1,p2,p3):
            a=s._getCurrentPoint();k=max(2,math.ceil((math.dist(a,p1)+math.dist(p1,p2)+math.dist(p2,p3))/spacing))
            for t in range(1,k+1):
                u=t/k;v=1-u;s.cur.append(tuple(v**3*a[i]+3*v*v*u*p1[i]+3*v*u*u*p2[i]+u**3*p3[i] for i in (0,1)))
        def _closePath(s):s._lineTo(s.start);s.lines.append(s.cur)          # the closing edge is implicit, reversing makes it another edge
        _endPath=_closePath
    pen=P(gs);gs[name].draw(pen);return pen.lines


def nearest(p,q):
    """Largest distance from the points of polylines p to the segments of polylines q."""
    import numpy as np
    pts=np.array([x for line in p for x in line],dtype=float)
    seg=np.array([(line[i],line[i+1]) for line in q for i in range(len(line)-1)],dtype=float)
    if not len(pts):return 0.
    if not len(seg):return float('inf')
    a=seg[:,0];d=seg[:,1]-a;dd=(d*d).sum(1);dd[dd==0]=1e-12;out=np.empty(len(pts))
    for k in range(0,len(pts),256):
        w=pts[k:k+256,None,:]-a[None];t=np.clip((w*d[None]).sum(2)/dd[None],0,1)
        out[k:k+256]=np.sqrt(((w-t[...,None]*d[None])**2).sum(2)).min(1)
    return float(out.max())


if __name__=='__main__':
    out=convert(sys.argv[1],sys.argv[2]);print(out,check(sys.argv[1],out))
