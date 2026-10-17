#!/usr/bin/env python3
"""Fair the long smooth runs of TrueType glyphs: a chain of quadratic pieces whose curvature jumps at every
node is replaced by one cubic B-spline (C2, curvature continuous) within FAIR_TOL of the original.

Corner nodes (tangent break >= CORNER_DEG, or touching a straight piece or a piece shorter than SHORT_LEN)
bound a run; only runs of MIN_RUN+ units with three or more curved pieces are touched. The spline is a
weighted least-squares fit (ends and y/x extrema pinned) converted to quadratics with fontTools.cu2qu.
A run is replaced only if the curvature jumps at its interior nodes clearly fall and its extrema stay put.
"""
import math
import numpy as np
from fontTools.cu2qu import curve_to_quadratic

FAIR_TOL=0.5
CORNER_DEG=14.0
SHORT_LEN=14.0
MIN_RUN=70.0
EXTREMA_TOL=0.3
SPACINGS=(80,64,52,42,34)
QUAD_ERR=0.1
TV_GAIN=0.75       # curvature total variation of the new run must be below this share of the old one


class Piece:
    def __init__(s,p0,c,p1):s.p0=p0;s.c=c;s.p1=p1
    def at(s,t):
        if s.c is None:return (s.p0[0]+(s.p1[0]-s.p0[0])*t,s.p0[1]+(s.p1[1]-s.p0[1])*t)
        u=1-t;return (u*u*s.p0[0]+2*u*t*s.c[0]+t*t*s.p1[0],u*u*s.p0[1]+2*u*t*s.c[1]+t*t*s.p1[1])
    def length(s):
        pts=[s.at(i/24) for i in range(25)];return sum(math.dist(a,b) for a,b in zip(pts,pts[1:]))
    def tan(s,end):
        if s.c is None:v=(s.p1[0]-s.p0[0],s.p1[1]-s.p0[1])
        else:v=(s.p1[0]-s.c[0],s.p1[1]-s.c[1]) if end else (s.c[0]-s.p0[0],s.c[1]-s.p0[1])
        L=math.hypot(*v);return (v[0]/L,v[1]/L) if L>1e-9 else (0.,0.)
    def curvature(s,t):
        if s.c is None:return 0.
        d1=(2*((1-t)*(s.c[0]-s.p0[0])+t*(s.p1[0]-s.c[0])),2*((1-t)*(s.c[1]-s.p0[1])+t*(s.p1[1]-s.c[1])))
        d2=(2*(s.p1[0]-2*s.c[0]+s.p0[0]),2*(s.p1[1]-2*s.c[1]+s.p0[1]));n=math.hypot(*d1)**3
        return (d1[0]*d2[1]-d1[1]*d2[0])/n if n>1e-9 else 0.


def pieces_of(P):
    start=next((i for i,p in enumerate(P) if p[2]),None)
    if start is None:return None
    Q=P[start:]+P[:start];out=[];cur=(Q[0][0],Q[0][1]);offs=[]
    for p in Q[1:]+[Q[0]]:
        if p[2]:
            end=(p[0],p[1])
            if not offs:out.append(Piece(cur,None,end))
            else:
                for k,o in enumerate(offs):
                    nxt=offs[k+1] if k+1<len(offs) else None
                    e=((o[0]+nxt[0])/2,(o[1]+nxt[1])/2) if nxt else end
                    out.append(Piece(cur,(o[0],o[1]),e));cur=e
            cur=end;offs=[]
        else:offs.append(p)
    return out


def basis(knots,x):
    """B-spline basis (degree 3, clamped knots) at x; Cox-de Boor."""
    x=np.asarray(x,float);m=len(knots)-1
    N=[((x>=knots[j])&(x<knots[j+1])).astype(float) if knots[j]<knots[j+1] else np.zeros(len(x)) for j in range(m)]
    last=max(j for j in range(m) if knots[j]<knots[j+1]);N[last]=np.where(x>=knots[-1],1.0,N[last])
    for d in range(1,4):
        M=[]
        for j in range(len(knots)-d-1):
            a=0.;b=0.
            if knots[j+d]>knots[j]:a=(x-knots[j])/(knots[j+d]-knots[j])*N[j]
            if knots[j+d+1]>knots[j+1]:b=(knots[j+d+1]-x)/(knots[j+d+1]-knots[j+1])*N[j+1]
            M.append(a+b)
        N=M
    return np.array(N).T


def run_samples(seg,step=1.0):
    pts=[];acc=0.
    for p in seg:
        L=p.length();k=max(2,int(L/step)*2)
        for i in range(k):
            pts.append((*p.at(i/k),acc+L*i/k))
        acc+=L
    pts.append((*seg[-1].p1,acc));return np.array(pts),acc


def extremes(seg):
    xs=[];ys=[]
    for p in seg:
        for i in range(40):
            q=p.at(i/40);xs.append(q[0]);ys.append(q[1])
    q=seg[-1].p1;xs.append(q[0]);ys.append(q[1])
    return min(xs),max(xs),min(ys),max(ys)


def fit_run(seg):
    S,L=run_samples(seg);s=S[:,2]
    # weights: pin ends, pin extrema samples
    w=np.ones(len(S));w[s<3]=60;w[s>L-3]=60
    for col in (0,1):
        v=S[:,col];i=int(np.argmax(v));j=int(np.argmin(v))
        for k in (i,j):
            if 3<s[k]<L-3:w[max(0,k-2):k+3]=max(w[k],25)
    for spacing in SPACINGS:
        m=max(1,int(round(L/spacing))-1);interior=np.linspace(0,L,m+2)[1:-1]
        knots=np.r_[[0.]*4,interior,[L]*4]
        B=basis(knots,s);W=w[:,None]
        C=np.linalg.lstsq(B*W,S[:,:2]*W,rcond=None)[0]
        err=np.sqrt(((B@C-S[:,:2])**2).sum(1)).max()
        if err<=FAIR_TOL:return knots,C,L
    return None


def beziers(knots,C):
    eps=1e-5;uk=sorted(set(knots.tolist()));out=[]
    def val(x):return (basis(knots,np.array([x]))@C)[0]
    for a,b in zip(uk,uk[1:]):
        h=b-a;p0=val(a);p3=val(b)
        d0=(val(a+eps)-p0)/eps;d3=(p3-val(b-eps))/eps
        out.append([tuple(p0),tuple(p0+d0*h/3),tuple(p3-d3*h/3),tuple(p3)])
    return out


def fair_run(seg):
    fit=fit_run(seg)
    if fit is None:return None
    knots,C,L=fit;cubics=beziers(knots,C)
    cubics[0][0]=seg[0].p0;cubics[-1][3]=seg[-1].p1   # exact end nodes
    pts=[]     # [(x,y,on)] after the first node
    for c in cubics:
        q=curve_to_quadratic(c,QUAD_ERR)
        # q: p0, off..., p3  (quad spline; implied on-curve points between offs)
        for o in q[1:-1]:pts.append([o[0],o[1],False])
        pts.append([q[-1][0],q[-1][1],True])
    return pts


def total_variation(pieces,per=6):
    """Sum of |change of curvature| along the run, sampled inside every piece and across the joins."""
    series=[]
    for p in pieces:
        for i in range(per):series.append(p.curvature((i+0.5)/per))
    return sum(abs(a-b) for a,b in zip(series,series[1:]))


def fair_contour(P):
    pcs=pieces_of(P)
    if not pcs or len(pcs)<4:return None,0
    n=len(pcs);L=[p.length() for p in pcs]
    def corner(i):
        a,b=pcs[i-1],pcs[i]
        if a.c is None or b.c is None or L[i-1]<SHORT_LEN or L[i]<SHORT_LEN:return True
        ta,tb=a.tan(True),b.tan(False)
        return math.degrees(math.acos(max(-1,min(1,ta[0]*tb[0]+ta[1]*tb[1]))))>=CORNER_DEG
    cor=[corner(i) for i in range(n)]
    if not any(cor):return None,0
    first=cor.index(True);order=list(range(first,n))+list(range(first));runs=[];cur=[]
    for k,i in enumerate(order):
        if k>0 and cor[i]:runs.append(cur);cur=[]
        cur.append(i)
    runs.append(cur)
    out=[[pcs[order[0]].p0[0],pcs[order[0]].p0[1],True]];done=0
    for run in runs:
        seg=[pcs[i] for i in run];total=sum(L[i] for i in run);new=None
        if len(run)>=3 and total>=MIN_RUN and all(p.c is not None for p in seg):
            cand=fair_run(seg)
            if cand:
                # quality gate: curvature jumps must fall, extrema must stay
                chain=[[seg[0].p0[0],seg[0].p0[1],True]]+cand
                newp=pieces_of(chain+[[seg[-1].p1[0],seg[-1].p1[1],True]]) if False else pieces_of(chain)
                # pieces_of closes the loop to the first point; drop that last closing piece
                newp=newp[:-1] if newp and math.dist(newp[-1].p1,chain[0][:2])<1e-9 and len(chain)>1 and math.dist(chain[-1][:2],chain[0][:2])>1e-9 else newp
                old_j=total_variation(seg);new_j=total_variation(newp) if newp else 1e9
                e0=extremes(seg);e1=extremes(newp) if newp else (0,0,0,0)
                if old_j>0 and new_j<=TV_GAIN*old_j and max(abs(a-b) for a,b in zip(e0,e1))<=EXTREMA_TOL+1e-6:
                    new=cand;done+=1
        if new is None:
            new=[]
            for p in seg:
                if p.c is not None:new.append([p.c[0],p.c[1],False])
                new.append([p.p1[0],p.p1[1],True])
        out+=new
    if not done:return None,0
    out=out[:-1]   # the last node equals the first
    return out,done


def fair_points(contours):
    res=[];total=0
    for P in contours:
        new,k=fair_contour(P)
        res.append(new if new else P);total+=k
    return res,total
