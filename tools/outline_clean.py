#!/usr/bin/env python3
"""Outline hygiene for the added Cyrillic glyphs (cubic stage, before TrueType export).

The source GLIFs were produced by several generators (adaptive curve fitting,
boolean operations, hand drawings), so they carry redundant nodes, nodes that
are not on extrema and near-smooth joins whose handles are not collinear.
This module, in this order and always within a stated geometric tolerance:
  0. refits chains of tiny lines (flattened curves) as cubics,
  1. merges runs of smooth, non-extremum cubic segments into one cubic,
  2. splits cubics at missing horizontal/vertical extrema (handles made exact),
  3. makes nearly smooth joins exactly smooth and extrema tangents exactly axial,
  4. drops tiny segments and collinear line nodes.
Corners are never touched. Native Latin glyphs are never passed through here.
"""
import math
import numpy as np
from fontTools.pens.recordingPen import RecordingPen
from fontTools.misc.bezierTools import splitCubicAtT, solveQuadratic

MERGE_TOL=1.0         # max deviation of a merged cubic, font units
SMOOTH_MERGE_DEG=4.0  # joint is "meant to be smooth" below this angle
SNAP_DEG=3.0          # near-smooth joints made exactly smooth below this angle
AXIS_DEG=2.0          # tangents this close to horizontal/vertical become exact
EXTREMUM_MIN=0.8      # ignore extrema that protrude less than this from the nearer node


def sub(a,b):return (a[0]-b[0],a[1]-b[1])
def add(a,b):return (a[0]+b[0],a[1]+b[1])
def mul(a,k):return (a[0]*k,a[1]*k)
def norm(a):return math.hypot(*a)
def unit(a):
    n=norm(a);return (a[0]/n,a[1]/n) if n>1e-9 else (0.,0.)
def angle(u,v):
    uu,vv=unit(u),unit(v)
    return math.degrees(math.acos(max(-1.,min(1.,uu[0]*vv[0]+uu[1]*vv[1]))))


# -- reading / writing -----------------------------------------------------

def contours_of(path):
    pen=RecordingPen();path.draw(pen);out=[];cur=None;start=None
    for op,pts in pen.value:
        if op=='moveTo':cur=[];start=pts[0];last=pts[0]
        elif op=='lineTo':cur.append(('L',last,pts[0]));last=pts[0]
        elif op=='curveTo':cur.append(('C',last,pts[0],pts[1],pts[2]));last=pts[2]
        elif op=='qCurveTo':
            offs=list(pts[:-1]);end=pts[-1]
            if end is None:   # closed contour made only of off-curve points
                start=((offs[-1][0]+offs[0][0])/2,(offs[-1][1]+offs[0][1])/2);last=start;cur=[];end=start
            for k,c in enumerate(offs):
                e=end if k==len(offs)-1 else ((c[0]+offs[k+1][0])/2,(c[1]+offs[k+1][1])/2)
                c1=add(last,mul(sub(c,last),2/3));c2=add(e,mul(sub(c,e),2/3));cur.append(('C',last,c1,c2,e));last=e
        elif op in('closePath','endPath'):
            if norm(sub(last,start))>1e-6:cur.append(('L',last,start))
            out.append(cur)
    return out


def draw_contours(contours,pen):
    for c in contours:
        pen.moveTo(c[0][1])
        for s in c:
            if s[0]=='L':pen.lineTo(s[2])
            else:pen.curveTo(s[2],s[3],s[4])
        pen.closePath()


# -- geometry helpers ------------------------------------------------------

def bez(p0,c1,c2,p1,t):
    u=1-t
    return (u**3*p0[0]+3*u*u*t*c1[0]+3*u*t*t*c2[0]+t**3*p1[0],u**3*p0[1]+3*u*u*t*c1[1]+3*u*t*t*c2[1]+t**3*p1[1])

def seg_point(s,t):
    if s[0]=='L':return (s[1][0]+(s[2][0]-s[1][0])*t,s[1][1]+(s[2][1]-s[1][1])*t)
    return bez(s[1],s[2],s[3],s[4],t)

def t_out(s):
    if s[0]=='L':return sub(s[2],s[1])
    for q in (s[2],s[3],s[4]):
        d=sub(q,s[1])
        if norm(d)>1e-6:return d
    return (0.,0.)

def t_in(s):
    if s[0]=='L':return sub(s[2],s[1])
    for q in (s[3],s[2],s[1]):
        d=sub(s[4],q)
        if norm(d)>1e-6:return d
    return (0.,0.)

def end_of(s):return s[2] if s[0]=='L' else s[4]
def start_of(s):return s[1]


def axial(d):
    """True when the direction is within AXIS_DEG of horizontal or vertical."""
    if norm(d)<1e-9:return False
    a=abs(math.degrees(math.atan2(d[1],d[0])))%180
    return min(a,abs(a-90),abs(a-180))<AXIS_DEG


# -- step 0: flattened curves ----------------------------------------------

FLAT_MAX_LEN=14.0     # a line this short inside a chain is a flattened curve
FLAT_MAX_TURN=40.0    # larger turns between short lines are real corners
FLAT_TOL=0.5


def polyline_curves(run):
    """Refit a chain of short lines as as few cubics as the tolerance allows."""
    if len(run)==1:return list(run)
    fit=fit_cubic(run)
    if fit and fit[1]<=FLAT_TOL:return [('C',)+fit[0]]
    # split at the chain's middle (by length) and fit both halves
    lengths=[norm(sub(end_of(r),start_of(r))) for r in run];half=sum(lengths)/2;acc=0;cut=1
    for i,l in enumerate(lengths):
        acc+=l
        if acc>=half:cut=min(max(i+1,1),len(run)-1);break
    return polyline_curves(run[:cut])+polyline_curves(run[cut:])


def refit_flattened(c):
    n=len(c);short=[s[0]=='L' and norm(sub(s[2],s[1]))<=FLAT_MAX_LEN for s in c]
    if sum(short)<3:return c
    # chain breaks: not short, or a real corner between neighbours
    def linked(i):   # is segment i linked to i-1 inside one flattened chain
        return short[i] and short[i-1] and angle(t_in(c[i-1]),t_out(c[i]))<=FLAT_MAX_TURN
    start=next((i for i in range(n) if not linked(i)),None)
    if start is None:return c
    order=c[start:]+c[:start];flags=[linked((start+k)%n) for k in range(n)];out=[];i=0
    while i<n:
        j=i+1
        while j<n and flags[j]:j+=1
        run=order[i:j]
        out.extend(polyline_curves(run) if len(run)>=3 else run);i=j
    return out


# -- step 1: merge ---------------------------------------------------------

def samples(run,per=24):
    pts=[]
    for s in run:
        for k in range(per):pts.append(seg_point(s,k/per))
    pts.append(end_of(run[-1]));return np.array(pts)

def fit_cubic(run):
    S=samples(run);P0=np.array(start_of(run[0]));P3=np.array(end_of(run[-1]))
    T0=np.array(unit(t_out(run[0])));T1=np.array(unit(t_in(run[-1])))
    d=np.r_[0,np.cumsum(np.hypot(*np.diff(S,axis=0).T))];u=d/d[-1]
    best=None
    for _ in range(6):
        b0=(1-u)**3;b1=3*u*(1-u)**2;b2=3*u**2*(1-u);b3=u**3
        A1=np.outer(b1,T0);A2=np.outer(b2,-T1)
        R=S-np.outer(b0+b1,P0)-np.outer(b2+b3,P3)
        M=np.array([[np.sum(A1*A1),np.sum(A1*A2)],[np.sum(A1*A2),np.sum(A2*A2)]]);r=np.array([np.sum(A1*R),np.sum(A2*R)])
        if abs(np.linalg.det(M))<1e-9:return None
        a,b=np.linalg.solve(M,r)
        if a<=0 or b<=0:return None
        C1=P0+a*T0;C2=P3-b*T1
        curve=np.array([bez(tuple(P0),tuple(C1),tuple(C2),tuple(P3),float(t)) for t in u])
        # Newton reparametrisation
        t=u.copy()
        for i,tt in enumerate(t):
            q=np.array(bez(tuple(P0),tuple(C1),tuple(C2),tuple(P3),float(tt)))
            d1=3*((1-tt)**2*(C1-P0)+2*(1-tt)*tt*(C2-C1)+tt**2*(P3-C2));d2=6*((1-tt)*(C2-2*C1+P0)+tt*(P3-2*C2+C1))
            den=np.dot(d1,d1)+np.dot(q-S[i],d2)
            if abs(den)>1e-9:t[i]=min(1.,max(0.,tt-np.dot(q-S[i],d1)/den))
        u=np.maximum.accumulate(t)
        best=(tuple(P0),tuple(C1),tuple(C2),tuple(P3))
    # true deviation both ways against dense polylines
    dense=np.array([bez(*best,float(t)) for t in np.linspace(0,1,300)])
    orig=samples(run,60)
    def hd(A,B):
        out=0.
        for i in range(0,len(A),64):
            d=np.sqrt(((A[i:i+64,None,:]-B[None,:,:])**2).sum(-1)).min(axis=1);out=max(out,d.max())
        return out
    err=max(hd(orig,dense),hd(dense,orig))
    return best,err

def smooth_joint(a,b):
    if a[0]!='C' or b[0]!='C':return False
    return angle(t_in(a),t_out(b))<SMOOTH_MERGE_DEG and not axial(t_out(b)) and not axial(t_in(a))

def merge_contour(c):
    n=len(c)
    keep=[not smooth_joint(c[i-1],c[i]) for i in range(n)]   # keep[i]: node between c[i-1] and c[i] is kept
    if not any(keep):keep[0]=True
    first=next(i for i in range(n) if keep[i]);order=c[first:]+c[:first];flags=keep[first:]+keep[:first]
    out=[];i=0
    while i<n:
        j=i+1
        while j<n and not flags[j]:j+=1
        group=order[i:j]
        if len(group)==1:out.append(group[0])
        else:
            a=0
            while a<len(group):
                best=None;b=a+1
                while b<=len(group):
                    fit=fit_cubic(group[a:b]) if b-a>1 else None
                    if fit and fit[1]<=MERGE_TOL:best=(b,fit[0])
                    elif b-a>1:break
                    b+=1
                if best and best[0]-a>1:out.append(('C',)+best[1]);a=best[0]
                else:out.append(group[a]);a+=1
        i=j
    return out


# -- step 2: extrema -------------------------------------------------------

def extrema_ts(s):
    p0,c1,c2,p1=s[1],s[2],s[3],s[4];ts=[]
    for k in (0,1):
        # derivative of the Bernstein form along axis k: A t^2 + B t + C
        A=3*(-p0[k]+3*c1[k]-3*c2[k]+p1[k]);B=6*(p0[k]-2*c1[k]+c2[k]);C=3*(c1[k]-p0[k])
        for t in solveQuadratic(A,B,C):
            if 0.03<t<0.97:
                q=bez(p0,c1,c2,p1,t)[k]
                if min(abs(q-p0[k]),abs(q-p1[k]))>=EXTREMUM_MIN:ts.append((t,k))
    return sorted(ts)

def split_extrema(c):
    out=[]
    for s in c:
        cuts=extrema_ts(s) if s[0]=='C' else []
        if not cuts:out.append(s);continue
        ts=sorted(set(round(t,6) for t,_ in cuts));kinds={round(t,6):k for t,k in cuts}
        nodes=[('C',)+tuple(p) for p in splitCubicAtT(s[1],s[2],s[3],s[4],*ts)]
        for idx,t in enumerate(ts):
            l=list(nodes[idx]);r=list(nodes[idx+1]);k=kinds[t];e=l[4]
            # tangent at an extremum is exactly axial: both handles share the node coordinate
            l[3]=(l[3][0],e[1]) if k==1 else (e[0],l[3][1])
            r[2]=(r[2][0],e[1]) if k==1 else (e[0],r[2][1])
            nodes[idx],nodes[idx+1]=tuple(l),tuple(r)
        out.extend(nodes)
    return out


# -- step 3: exact smooth joins and axial extrema ---------------------------

def set_out(s,d):
    """Rotate the outgoing handle of s to direction d keeping its length."""
    if s[0]=='L':return s
    h=sub(s[2],s[1]);L=norm(h)
    if L<1e-6:return s
    d=unit(d);return ('C',s[1],add(s[1],mul(d,L)),s[3],s[4])

def set_in(s,d):
    if s[0]=='L':return s
    h=sub(s[4],s[3]);L=norm(h)
    if L<1e-6:return s
    d=unit(d);return ('C',s[1],s[2],sub(s[4],mul(d,L)),s[4])

def smooth_contour(c):
    c=list(c);n=len(c)
    for i in range(n):
        a,b=c[i-1],c[i]
        if a[0]=='L' and b[0]=='L':continue
        ti,to=t_in(a),t_out(b)
        if norm(ti)<1e-6 or norm(to)<1e-6:continue
        th=angle(ti,to)
        if th<1e-4 or th>SNAP_DEG:continue
        if a[0]=='L':d=unit(ti)
        elif b[0]=='L':d=unit(to)
        else:
            u,v=unit(ti),unit(to);d=unit((u[0]+v[0],u[1]+v[1]))
        if axial(d):
            d=(math.copysign(1,d[0]),0.) if abs(d[0])>abs(d[1]) else (0.,math.copysign(1,d[1]))
        c[i-1]=set_in(a,d) if a[0]=='C' else a;c[i]=set_out(b,d) if b[0]=='C' else b
    return c


# -- step 4: tiny segments and collinear lines -----------------------------

def tidy_contour(c):
    changed=True
    while changed and len(c)>3:
        changed=False
        for i in range(len(c)):
            s=c[i]
            if s[0]=='L' and norm(sub(s[2],s[1]))<1.5:
                prev=c[i-1];nxt=c[(i+1)%len(c)]
                # collapse: the next segment starts where this one starts
                if nxt[0]=='L':nxt=('L',s[1],nxt[2])
                else:nxt=('C',s[1],nxt[2],nxt[3],nxt[4])
                c[(i+1)%len(c)]=nxt;del c[i];changed=True;break
        if changed:continue
        for i in range(len(c)):
            a,b=c[i-1],c[i]
            if a[0]=='L' and b[0]=='L' and angle(sub(a[2],a[1]),sub(b[2],b[1]))<0.35:
                c[i-1]=('L',a[1],b[2]);del c[i];changed=True;break
    return c


def from_truetype(path,share=0.8):
    """True when the curves are elevated quadratics, i.e. outlines taken verbatim from a TrueType font."""
    curves=quads=0
    for c in contours_of(path):
        for s in c:
            if s[0]=='L':
                if norm(sub(s[2],s[1]))<=FLAT_MAX_LEN:curves+=1   # flattened curve pieces are not native
                continue
            curves+=1;q1=sub(mul(s[2],3),s[1]);q2=sub(mul(s[3],3),s[4])
            if norm(sub(q1,q2))<0.02:quads+=1
    return curves>0 and quads/curves>=share


def clean_path(path):
    import pathops
    if from_truetype(path):return path   # native Instrument outlines are already well built
    out=[]
    for c in contours_of(path):
        c=refit_flattened(c);c=merge_contour(c);c=split_extrema(c);c=smooth_contour(c);c=tidy_contour(c);out.append(c)
    p=pathops.Path();draw_contours(out,p.getPen())
    return pathops.simplify(p,fix_winding=True,clockwise=True)


# -- verification ------------------------------------------------------------

def _dense(path,step):
    pts=[]
    for c in contours_of(path):
        for s in c:
            L=sum(norm(sub(seg_point(s,(k+1)/8),seg_point(s,k/8))) for k in range(8));n=max(6,int(L/step))
            pts.extend(seg_point(s,k/n) for k in range(n))
    return np.array(pts)


def max_deviation(a,b,step=1.0):
    """Two-sided Hausdorff distance between outlines (objects with .draw(pen))."""
    A=_dense(a,step);B=_dense(b,step);worst=0.
    for P,Q in ((A,B),(B,A)):
        for i in range(0,len(P),256):
            d=np.sqrt(((P[i:i+256,None,:]-Q[None,:,:])**2).sum(-1)).min(axis=1);worst=max(worst,float(d.max()))
    return worst


class GlyphShape:
    """Adapter: a (decomposed) glyph from a glyph set as an object with .draw(pen)."""
    def __init__(self,glyphset,name,dx=0):
        from fontTools.pens.recordingPen import DecomposingRecordingPen
        self.rec=DecomposingRecordingPen(glyphset);glyphset[name].draw(self.rec);self.dx=dx
    def draw(self,pen):
        if self.dx:
            from fontTools.pens.transformPen import TransformPen
            self.rec.replay(TransformPen(pen,(1,0,0,1,self.dx,0)))
        else:self.rec.replay(pen)
