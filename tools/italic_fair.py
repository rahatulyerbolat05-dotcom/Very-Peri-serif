#!/usr/bin/env python3
"""Final fairing of the assembled Italic letters (I021, author: "polish every vector to the ideal, remove the roughness").
Measured on I020 against the native Italic (tools/polish_audit.py): smooth curve-curve nodes of the native letters break by 3.6 degrees
at most (u n m a o q d), the assembled ones by up to 8-11 degrees, nearly always at a seam of two donors or where the integer grid bent a
short handle. Passes, on the explicit nodes of each contour (implied nodes are smooth by construction):
  0. drop_steps: of two explicit nodes closer than STEP (a 1-2 unit step left by a seam) the second goes.
  1. fair_nodes: a node between two handles whose tangent break is below CORNER_DEG (a corner drawn on purpose is sharper) is moved by up to
     NODE_MOVE (2.5 above 6 degrees) and its handles by up to HANDLE_MOVE on the integer grid, to the combination with the smallest break; a handle on one
     axis with the node (extremum) stays on it; a handle shared with the next node counts that node's break too.
  2. fair_lines: a curve that leaves a straight piece turns its first handle onto the line (break below CORNER_DEG, move up to LINE_MOVE);
     then fair_nodes once more.
  3. snap_zones (run first, the handles it moves are faired after it): a y-extremum within ZONE_SNAP of a design height goes onto it with its axial handles.
Each pass is kept contour by contour, only while the whole glyph stays within BUDGET of its input (Hausdorff, polish_outlines.hausdorff).
"""
import math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from polish_outlines import contours_of,to_glyph,hausdorff

CORNER_DEG=15.;STEP=2.1;NODE_MOVE=2;HANDLE_MOVE=1;LINE_MOVE=2.;ZONE_SNAP=1.6;BUDGET=2.5;DRIFT=2.3   # DRIFT: no point ends farther than this from where it was after drop_steps
ZONES=[-215,-205,-9,0,510,516,720,730,740]


def brk(a,b,c):
    v1=(b[0]-a[0],b[1]-a[1]);v2=(c[0]-b[0],c[1]-b[1])
    if math.hypot(*v1)<1e-9 or math.hypot(*v2)<1e-9:return 0.
    d=math.atan2(v2[1],v2[0])-math.atan2(v1[1],v1[0]);return abs(math.degrees((d+math.pi)%(2*math.pi)-math.pi))


def other_break(P,j,h,step):
    """Break at the explicit node on the far side of handle P[j] (moved to h), if that node joins two curves."""
    n=len(P);m=P[(j+step)%n];o=P[(j+2*step)%n]
    if not m[2] or o[2]:return 0.
    return brk(h,m,o) if step==1 else brk(o,m,h)


def fair_nodes(P,ref=None):
    n=len(P);count=0;ok=lambda j,q:ref is None or math.dist(q,ref[j%n][:2])<=DRIFT
    for i in range(n):
        b=P[i];a=P[i-1];c=P[(i+1)%n]
        if not b[2] or a[2] or c[2]:continue
        before=brk(a,b,c)
        if not 0.6<before<CORNER_DEG:continue
        if math.dist(a[:2],b[:2])<4 or math.dist(b[:2],c[:2])<4:continue      # 2-3 unit handles of a serif curl: the grid break is invisible there
        ax_a=(a[0]==b[0],a[1]==b[1]);ax_c=(c[0]==b[0],c[1]==b[1])
        oa0=other_break(P,i-1,a,-1);oc0=other_break(P,(i+1)%n,c,1)
        cost0=before+oa0+oc0;best=(cost0,0.,a,b,c,before);H=range(-HANDLE_MOVE,HANDLE_MOVE+1);NM=NODE_MOVE+(0.5 if before>6 else 0);N=range(-int(NM),int(NM)+1)
        for nx in N:
            for ny in N:
                if math.hypot(nx,ny)>NM:continue
                nb=(b[0]+nx,b[1]+ny)
                if not ok(i,nb):continue
                for hx in H:
                    for hy in H:
                        na=(a[0]+hx,a[1]+hy)
                        if not ok(i-1,na):continue
                        if ax_a[0] and na[0]!=nb[0] or ax_a[1] and na[1]!=nb[1]:continue
                        oa=other_break(P,i-1,na,-1) if (hx or hy) else oa0
                        if oa>max(oa0,1.5)+0.3:continue
                        for kx in H:
                            for ky in H:
                                nc=(c[0]+kx,c[1]+ky)
                                if not ok(i+1,nc):continue
                                if ax_c[0] and nc[0]!=nb[0] or ax_c[1] and nc[1]!=nb[1]:continue
                                oc=other_break(P,(i+1)%n,nc,1) if (kx or ky) else oc0
                                if oc>max(oc0,1.5)+0.3:continue
                                if math.dist(na,nb)<3 or math.dist(nb,nc)<3:continue
                                br=brk(na,nb,nc);cost=br+oa+oc;mv=math.hypot(nx,ny)*1.5+math.hypot(hx,hy)+math.hypot(kx,ky)
                                if cost+0.15*mv<best[0]+0.15*best[1]:best=(cost,mv,na,nb,nc,br)
        if best[0]<cost0-0.4:
            P[i-1]=[best[2][0],best[2][1],False];P[i]=[best[3][0],best[3][1],True];P[(i+1)%n]=[best[4][0],best[4][1],False];count+=1
    return P,count


def fair_lines(P,ref=None):
    """On-curve node b between a straight piece (from on-curve a) and a curve (first handle c): c turns onto the line a-b."""
    n=len(P);count=0
    for i in range(n):
        b=P[i]
        if not b[2]:continue
        for sa,sc in ((-1,1),(1,-1)):
            a=P[(i+sa)%n];c=P[(i+sc)%n]
            if not a[2] or c[2]:continue
            L=math.dist(a[:2],b[:2]);h=math.dist(b[:2],c[:2])
            if L<12 or h<3:continue
            before=brk(a,b,c) if sa==-1 else brk(c,b,a)
            if not 0.6<before<CORNER_DEG:continue
            ux,uy=(b[0]-a[0])/L,(b[1]-a[1])/L;t=(c[0]-b[0])*ux+(c[1]-b[1])*uy
            if t<=0:continue
            tx,ty=b[0]+ux*t,b[1]+uy*t;bestc=None
            for dx in range(-2,3):
                for dy in range(-2,3):
                    q=(round(tx)+dx,round(ty)+dy)
                    if math.dist(q,c[:2])>LINE_MOVE or ref is not None and math.dist(q,ref[(i+sc)%n][:2])>DRIFT:continue
                    br=brk(a,b,q) if sa==-1 else brk(q,b,a)
                    o=other_break(P,(i+sc)%n,q,sc);o0=other_break(P,(i+sc)%n,c,sc)
                    if o>max(o0,1.5)+0.3:continue
                    br+=o-o0
                    if bestc is None or br<bestc[0]:bestc=(br,q)
            if bestc and bestc[0]<before-0.4:P[(i+sc)%n]=[bestc[1][0],bestc[1][1],False];count+=1
    return P,count


def drop_steps(P,ref=None):
    """Two explicit nodes closer than STEP (a 1-2 unit straight step left by a seam): the second goes."""
    count=0;i=0
    while i<len(P) and len(P)>4:
        b=P[i];c=P[(i+1)%len(P)]
        if b[2] and c[2] and math.dist(b[:2],c[:2])<STEP:del P[(i+1)%len(P)];count+=1;continue
        i+=1
    return P,count


def snap_zones(P,ref=None):
    n=len(P);count=0
    for i in range(n):
        b=P[i]
        if not b[2]:continue
        a=P[i-1];c=P[(i+1)%n]
        if not((b[1]>=a[1] and b[1]>=c[1]) or (b[1]<=a[1] and b[1]<=c[1])):continue
        z=min(ZONES,key=lambda z:abs(b[1]-z));d=z-b[1]
        if d==0 or abs(d)>ZONE_SNAP:continue
        for j in (i-1,(i+1)%n):
            if P[j][1]==b[1]:P[j]=[P[j][0],z,P[j][2]]
        P[i]=[b[0],z,True];count+=1
    return P,count


def fair(glyph,glyf):
    """Return (glyph, stats); every pass judged against the input outline."""
    if glyph.numberOfContours<=0:return glyph,{}
    cur=glyph;stats={};ref=None
    for label,fn in (('steps',drop_steps),('zones',snap_zones),('nodes',fair_nodes),('lines',fair_lines),('nodes2',fair_nodes)):
        base=[[[round(p[0]),round(p[1]),p[2]] for p in P] for P in contours_of(cur,glyf)];k=0
        if ref is None and label!='steps':ref=[[p[:] for p in P] for P in base]
        for ci in range(len(base)):                  # contour by contour: one contour over the budget does not block the others
            P,m=fn([p[:] for p in base[ci]],ref[ci] if ref else None)
            if not m:continue
            trial=base[:ci]+[P]+base[ci+1:];g=to_glyph(trial);g.recalcBounds(glyf)
            if hausdorff(glyph,g,glyf)<=BUDGET:base=trial;cur=g;k+=m
        if k:stats[label]=k
    stats['deviation']=round(float(hausdorff(glyph,cur,glyf)),2)
    return cur,stats


def fair_regular(glyph,glyf):
    """The same passes with the tolerances of the Regular polish (docs/polish.md: every added letter within 1.5 of its source):
    points move by up to 1.2, nodes by 1, the glyph stays within 1.5."""
    global DRIFT,BUDGET,NODE_MOVE,LINE_MOVE,ZONE_SNAP
    saved=(DRIFT,BUDGET,NODE_MOVE,LINE_MOVE,ZONE_SNAP);DRIFT,BUDGET,NODE_MOVE,LINE_MOVE,ZONE_SNAP=1.2,1.5,1,1.5,1.0
    try:return fair(glyph,glyf)
    finally:DRIFT,BUDGET,NODE_MOVE,LINE_MOVE,ZONE_SNAP=saved
