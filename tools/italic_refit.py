#!/usr/bin/env python3
"""Point compaction of assembled Italic glyphs (docs/italic-rules.md R8, R10, R11).
Boolean operations leave an explicit on-curve node on every quadratic segment, native TrueType outlines keep smooth chains on implied nodes
(native lowercase: 58 points, our assembled letters: 95). Two passes, each judged by the symmetric distance to the original pieces (MERGE_TOL):
  1. merge: two quadratic segments with a smooth, non-extremum joint become one quadratic (control = intersection of the end tangents);
  2. implied: two smooth segments with a non-extremum joint become a two-piece spline with an implied joint (4 points instead of 5):
     the two handle lengths are fitted along the fixed end tangents.
Corners (angle above CORNER_DEG), extremum nodes (axial tangent), line joints and the ends of straight pieces are never touched.
Usage as a module: compact(contour_nodes) -> nodes; tidy() calls it on every contour and checks the whole glyph (Hausdorff <= BUDGET).
"""
import math,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))

MERGE_TOL=1.1;CORNER_DEG=12.0;AXIS_DEG=0.8;SAMPLES=24;DENSE=1.2


def quads_of(P):
    from italic_tidy import quads
    return quads(P)


def qpts(a,c,b,n=SAMPLES):
    t=np.linspace(0,1,n)[:,None];a,c,b=map(np.array,(a,c,b))
    return (1-t)**2*a+2*t*(1-t)*c+t*t*b


def hd(P,Q):
    """Symmetric max distance between two point sets, each treated as a dense polyline."""
    def dense(X):
        out=[X[0]]
        for u,v in zip(X,X[1:]):
            k=max(1,int(np.linalg.norm(v-u)/DENSE))
            out.extend(u+(v-u)*(i/k) for i in range(1,k+1))
        return np.array(out)
    A,B=dense(P),dense(Q)
    d1=np.sqrt(((A[:,None,:]-B[None,:,:])**2).sum(-1)).min(axis=1).max()
    d2=np.sqrt(((B[:,None,:]-A[None,:,:])**2).sum(-1)).min(axis=1).max()
    return max(d1,d2)


def angle_between(u,v):
    nu,nv=np.linalg.norm(u),np.linalg.norm(v)
    if nu<1e-9 or nv<1e-9:return 0.
    return math.degrees(math.acos(max(-1,min(1,float(np.dot(u,v)/(nu*nv))))))


def tangent_out(s):return np.array(s[2])-np.array(s[1])
def tangent_in(s):return np.array(s[3])-np.array(s[2])


def smooth_joint(s1,s2):
    """Joint of two quadratic segments: smooth, not a corner, not an extremum."""
    u=tangent_in(s1);v=tangent_out(s2)
    if angle_between(u,v)>CORNER_DEG:return False
    for w in (u,v):
        n=np.linalg.norm(w)
        if n<1e-9:return False
        if abs(w[0])/n<math.sin(math.radians(AXIS_DEG)) or abs(w[1])/n<math.sin(math.radians(AXIS_DEG)):return False   # axial tangent = extremum node
    return True


def intersect(a,da,b,db):
    """Point where the line a+s*da meets b+t*db, or None."""
    M=np.array([[da[0],-db[0]],[da[1],-db[1]]],float)
    if abs(np.linalg.det(M))<1e-6:return None
    s,t=np.linalg.solve(M,np.array(b,float)-np.array(a,float))
    return np.array(a,float)+s*np.array(da,float),s,t


def try_merge(s1,s2):
    r=intersect(s1[1],tangent_out(s1),s2[3],-tangent_in(s2))
    if r is None:return None
    c,s,t=r
    if s<=0 or t<=0:return None
    orig=np.vstack([qpts(s1[1],s1[2],s1[3]),qpts(s2[1],s2[2],s2[3])[1:]])
    new=qpts(s1[1],c,s2[3],2*SAMPLES)
    return (['Q',s1[1],list(map(float,c)),s2[3],s1[4]]) if hd(orig,new)<=MERGE_TOL else None


def try_implied(s1,s2):
    """Pair -> two pieces with an implied joint: controls c1=a+x*ua, c2=b+y*ub, fitted to the original pair."""
    a,b=np.array(s1[1],float),np.array(s2[3],float)
    ua=tangent_out(s1);ub=-tangent_in(s2)
    la,lb=np.linalg.norm(ua),np.linalg.norm(ub)
    ua=ua/la;ub=ub/lb
    orig=np.vstack([qpts(s1[1],s1[2],s1[3]),qpts(s2[1],s2[2],s2[3])[1:]])
    def spline(x,y):
        c1=a+x*ua;c2=b+y*ub;m=(c1+c2)/2
        return np.vstack([qpts(a,c1,m),qpts(m,c2,b)[1:]]),c1,c2
    best=None
    x0,y0=la,lb;span=0.5
    for level in range(3):
        xs=np.linspace(x0*(1-span),x0*(1+span),9);ys=np.linspace(y0*(1-span),y0*(1+span),9)
        for x in xs:
            for y in ys:
                if x<=0 or y<=0:continue
                pts,c1,c2=spline(x,y)
                e=hd(orig,pts)
                if best is None or e<best[0]:best=(e,x,y,c1,c2)
        x0,y0=best[1],best[2];span*=0.3
    e,x,y,c1,c2=best
    c1=np.round(c1);c2=np.round(c2)
    pts=np.vstack([qpts(a,c1,(c1+c2)/2),qpts((c1+c2)/2,c2,b)[1:]])
    if hd(orig,pts)>MERGE_TOL+0.15:return None
    m=(c1+c2)/2
    return [['Q',s1[1],list(map(float,c1)),list(map(float,m)),s1[4]],['Q',list(map(float,m)),list(map(float,c2)),s2[3],False]]


def nodes_of(segs):
    out=[]
    for s in segs:
        if s[0]=='L' or s[4]:out.append([round(s[1][0]),round(s[1][1]),True])
        if s[0]=='Q':out.append([round(s[2][0]),round(s[2][1]),False])
    return out


def compact(P):
    segs=quads_of(P)
    if segs is None or len(segs)<3:return P
    # rotate so that the first segment starts at an explicit node
    k=next((i for i,s in enumerate(segs) if s[0]=='L' or s[4]),0);segs=segs[k:]+segs[:k]
    segs=[list(s) for s in segs]
    changed=True
    while changed:
        changed=False
        for i in range(len(segs)-1):
            s1,s2=segs[i],segs[i+1]
            if s1[0]!='Q' or s2[0]!='Q' or not smooth_joint(s1,s2) or not s2[4]:continue       # an implied joint stays implied
            m=try_merge(s1,s2)
            if m:
                segs[i:i+2]=[m];changed=True;break
    i=0
    while i<len(segs)-1:
        s1,s2=segs[i],segs[i+1]
        if s1[0]=='Q' and s2[0]=='Q' and s2[4] and smooth_joint(s1,s2):
            r=try_implied(s1,s2)
            if r:segs[i:i+2]=r;i+=2;continue
        i+=1
    return nodes_of(segs)


def compact_nodes(P):
    """Stage signature of italic_tidy: (nodes) -> (nodes, number of points removed)."""
    Q=compact(P);return Q,max(0,len(P)-len(Q))


def compact_glyph(glyph,glyf):
    from polish_outlines import contours_of,to_glyph
    new=[compact([p[:] for p in P]) for P in contours_of(glyph,glyf)]
    g=to_glyph(new);g.recalcBounds(glyf);return g
