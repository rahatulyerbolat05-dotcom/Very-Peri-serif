#!/usr/bin/env python3
"""Tidy sheared Italic capitals: nodes where an italic outline needs them, no superfluous ones.
A shear moves the vertical tangents away from the Regular nodes: the curve extrema end up inside curves, and the
integer rounding after the shear bends handles by 1-4 degrees at smooth nodes. Native Italic keeps nodes on extrema
(2.5 curves per glyph without, against 4.3 on the plain shear) and has 1.3 kinks per glyph (6.2 on the plain shear).
Passes, each judged against the input outline (Hausdorff, MAX_DEV of polish_outlines):
  1. polish_outlines.polish (micro segments, handles onto lines, redundant smooth nodes)
  2. split_extrema: a node at every x/y extremum of a quadratic curve (the extremum lies more than 0.8 beyond the ends)
  3. smooth_pairs: curve-curve node with a tangent break below SMOOTH_DEG: both handles turn to the mean direction when each moves
     at most HANDLE_MOVE (the break is integer rounding of 9-12 unit handles after the shear, not a drawn corner)
"""
import math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from polish_outlines import polish,contours_of,to_glyph,hausdorff,merge_micro
from italic_refit import compact_nodes as compact

BUDGET=2.6;KINK_DEG=12.;SMOOTH_DEG=12.;HANDLE_MOVE=1.5;EXTREMUM_BEYOND=0.8


def quads(P):
    """Contour -> segments ['L',a,b] or ['Q',a,c,b,start_is_node]; a Q start midway between two handles is implied."""
    if not any(p[2] for p in P):return None
    s=next(i for i,p in enumerate(P) if p[2]);Q=P[s:]+P[:s]+[P[s]]
    segs=[];i=0
    while i<len(Q)-1:
        a=Q[i][:2];j=i+1;offs=[]
        while not Q[j][2]:offs.append(Q[j][:2]);j+=1
        if not offs:segs.append(['L',a,Q[j][:2]])
        else:
            cur=a;node=True
            for k,c in enumerate(offs):
                if k==len(offs)-1:end=Q[j][:2]
                else:nx=offs[k+1];end=[(c[0]+nx[0])/2,(c[1]+nx[1])/2]
                segs.append(['Q',cur,c,end,node]);cur=end;node=False
        i=j
    return segs


def split_quad(a,c,b,t):
    m1=[a[0]+(c[0]-a[0])*t,a[1]+(c[1]-a[1])*t];m2=[c[0]+(b[0]-c[0])*t,c[1]+(b[1]-c[1])*t]
    return m1,[m1[0]+(m2[0]-m1[0])*t,m1[1]+(m2[1]-m1[1])*t],m2


def split_extrema(P):
    segs=quads(P)
    if segs is None:return P,0
    out=[];count=0;touched=set()
    for s in segs:
        if s[0]!='Q':out.append(s);continue
        a,c,b=s[1],s[2],s[3];ts=[]
        for ax in (0,1):
            d=a[ax]-2*c[ax]+b[ax]
            if abs(d)<1e-9:continue
            t=(a[ax]-c[ax])/d
            if not 0.04<t<0.96:continue
            v=(1-t)**2*a[ax]+2*t*(1-t)*c[ax]+t*t*b[ax]
            if v>max(a[ax],b[ax])+EXTREMUM_BEYOND or v<min(a[ax],b[ax])-EXTREMUM_BEYOND:ts.append(t)
        if not ts:out.append(s);continue
        ts.sort()
        if len(ts)==2 and ts[1]-ts[0]<0.06:ts=ts[:1]
        ca,cc=a,c;done=0.;pieces=[]
        for t in ts:
            m1,m,m2=split_quad(ca,cc,b,(t-done)/(1-done));m=[round(m[0]),round(m[1])]
            pieces.append((ca,m1,m));ca,cc=m,m2;done=t
        pieces.append((ca,cc,b))
        for k,(pa,pc,pb) in enumerate(pieces):out.append(['Q',pa,pc,pb,True if k else True])
        touched.add(id(out[-1]));count+=len(ts)
    # a split quad ends away from the midpoint of its handles: the node after it must be explicit
    for i,s in enumerate(out):
        if id(s) in touched:
            nxt=out[(i+1)%len(out)]
            if nxt[0]=='Q':nxt[4]=True
    nodes=[]
    for s in out:
        if s[0]=='L' or s[4]:nodes.append([round(s[1][0]),round(s[1][1]),True])
        if s[0]=='Q':nodes.append([round(s[2][0]),round(s[2][1]),False])
    return nodes,count


def break_deg(b,a,c):
    v1=(b[0]-a[0],b[1]-a[1]);v2=(c[0]-b[0],c[1]-b[1])
    d=math.atan2(v2[1],v2[0])-math.atan2(v1[1],v1[0]);return abs(math.degrees((d+math.pi)%(2*math.pi)-math.pi))


def smooth_pairs(P):
    """Curve-curve node whose handles are short (rounding noise on the integer grid): search the integer neighbours of
    both handles for the pair with the smallest tangent break, moving each handle by at most HANDLE_MOVE."""
    n=len(P);count=0
    for i in range(n):
        b=P[i];a,c=P[i-1],P[(i+1)%n]
        if not b[2] or a[2] or c[2]:continue
        l1=math.hypot(b[0]-a[0],b[1]-a[1]);l2=math.hypot(c[0]-b[0],c[1]-b[1])
        if l1<3 or l2<3:continue
        if a[0]==b[0] or a[1]==b[1] or c[0]==b[0] or c[1]==b[1]:continue      # axial handle: extremum or line joint, kept exact
        before=break_deg(b,a,c)
        if not(0.15<=before<SMOOTH_DEG):continue
        best=(before,0.,a[:2],c[:2]);R=range(-1,2)
        for dax in R:
            for day in R:
                na=(a[0]+dax,a[1]+day)
                for dcx in R:
                    for dcy in R:
                        nc=(c[0]+dcx,c[1]+dcy)
                        move=math.hypot(dax,day)+math.hypot(dcx,dcy)
                        if math.hypot(dax,day)>HANDLE_MOVE or math.hypot(dcx,dcy)>HANDLE_MOVE:continue
                        br=break_deg(b,na,nc)
                        if br<best[0]-0.05 and (br,move)<(best[0],best[1]+1e9):
                            if br<best[0]-0.05 and (br<best[0] or move<best[1]):best=(br,move,list(na),list(nc))
        if best[0]<before-0.3:
            P[i-1]=[best[2][0],best[2][1],False];P[(i+1)%n]=[best[3][0],best[3][1],False];count+=1
    return P,count


def tidy(glyph,glyf,name=None):
    """Return (glyph, stats). Every stage is kept only while the outline stays within BUDGET of the input."""
    if glyph.numberOfContours<=0:return glyph,{}
    import polish_outlines as po
    old=po.KINK_DEG;po.KINK_DEG=KINK_DEG       # rounding after the shear leaves 9-10 degree breaks at line-curve nodes
    old_r=po.STRAIGHT_LEN;po.STRAIGHT_LEN=1e9   # no straightening here: the native Italic stems bow by design (italic_lower straightens its own constructions)
    try:
        cur,st=polish(glyph,glyf,name)
        if hausdorff(glyph,cur,glyf)>BUDGET:cur=glyph;st={}
        stats=dict(st);done=[]
        for label,fn in (('extrema',split_extrema),('micro',merge_micro),('smooth',smooth_pairs),('compact',compact)):
            if fn is None:
                g,s_=polish(cur,glyf,name);n=sum(v for k,v in s_.items() if k in ('micro','smooth','align'))
            else:
                new=[];n=0
                for P in contours_of(cur,glyf):
                    P,k=fn([p[:] for p in P]);new.append(P);n+=k
                g=to_glyph(new);g.recalcBounds(glyf)
            if n and hausdorff(glyph,g,glyf)<=BUDGET:cur=g;stats[label]=n
        stats['deviation']=round(float(hausdorff(glyph,cur,glyf)),2)
        return cur,stats
    finally:po.KINK_DEG=old;po.STRAIGHT_LEN=old_r
