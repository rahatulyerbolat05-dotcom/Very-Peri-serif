#!/usr/bin/env python3
"""Drawing with a pen model, for Italic letters that have no native donor of the right size (в: two loops smaller than o).
A skeleton (through points, smooth Catmull-Rom spline, closed or open) is stroked by a pen whose width depends on the direction of the stroke,
calibrated on the native o of Instrument Serif Italic (grid search of the xor area between the native o and the o stroked along its own centre
line): vertical strokes 72 across, horizontal ones 14, thin axis tilted -3 degrees, w = 14 + 58 |sin(a - tilt)|^2.6. Both edges are fitted with cubic Beziers (Schneider's
method, tolerance 0.6), so the outline is made of a few smooth curves, not a polyline. Coordinates are in the de-slanted plane (ud = x - tan13*y).
"""
import math
import pathops

S=math.tan(math.radians(13))
W_MAX=72.;W_MIN=14.;TILT=math.radians(-3.);POWER=2.6     # fitted on the native o (stroked along its own centre line: 7.0 % xor area)


def width(dx,dy,w_max=None,w_min=None):
    w_max=W_MAX if w_max is None else w_max;w_min=W_MIN if w_min is None else w_min
    a=math.atan2(dy,dx)-TILT
    return w_min+(w_max-w_min)*abs(math.sin(a))**POWER


def spline(points,closed,n=24):
    """Catmull-Rom through the points, sampled: [(u,y,du,dy)] with the tangent."""
    P=list(points);m=len(P);out=[]
    rng=range(m) if closed else range(m-1)
    for i in rng:
        p0=P[i-1] if (closed or i>0) else P[i];p1=P[i];p2=P[(i+1)%m];p3=P[(i+2)%m] if (closed or i+2<m) else P[(i+1)%m]
        for k in range(n):
            t=k/n;t2=t*t;t3=t2*t
            f=lambda a,b,c,d:0.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t2+(-a+3*b-3*c+d)*t3)
            g=lambda a,b,c,d:0.5*((-a+c)+2*(2*a-5*b+4*c-d)*t+3*(-a+3*b-3*c+d)*t2)
            out.append((f(p0[0],p1[0],p2[0],p3[0]),f(p0[1],p1[1],p2[1],p3[1]),g(p0[0],p1[0],p2[0],p3[0]),g(p0[1],p1[1],p2[1],p3[1])))
    if not closed:
        a,b=P[-2],P[-1];out.append((b[0],b[1],b[0]-a[0],b[1]-a[1]))
    return out


def offsets(samples,scale=1.):
    L=[];R=[]
    for u,y,du,dy in samples:
        l=math.hypot(du,dy) or 1.;nx,ny=-dy/l,du/l;w=width(du,dy)*scale/2
        L.append((u+nx*w,y+ny*w));R.append((u-nx*w,y-ny*w))
    return L,R


# ---- cubic Bezier fitting (Schneider, Graphics Gems 1990)
def _bez(c,t):
    mt=1-t;return (mt**3*c[0][0]+3*mt*mt*t*c[1][0]+3*mt*t*t*c[2][0]+t**3*c[3][0],mt**3*c[0][1]+3*mt*mt*t*c[1][1]+3*mt*t*t*c[2][1]+t**3*c[3][1])


def _fit(pts,t1,t2,tol):
    n=len(pts)
    if n==2:
        d=math.dist(pts[0],pts[1])/3;return [[pts[0],(pts[0][0]+t1[0]*d,pts[0][1]+t1[1]*d),(pts[1][0]+t2[0]*d,pts[1][1]+t2[1]*d),pts[1]]]
    u=[0.];[u.append(u[-1]+math.dist(pts[i],pts[i-1])) for i in range(1,n)];u=[x/u[-1] for x in u]
    def gen(u):
        C=[[0,0],[0,0]];X=[0,0]
        for i,t in enumerate(u):
            b1=3*t*(1-t)**2;b2=3*t*t*(1-t);A1=(t1[0]*b1,t1[1]*b1);A2=(t2[0]*b2,t2[1]*b2)
            C[0][0]+=A1[0]*A1[0]+A1[1]*A1[1];C[0][1]+=A1[0]*A2[0]+A1[1]*A2[1];C[1][1]+=A2[0]*A2[0]+A2[1]*A2[1]
            b0=(1-t)**3;b3=t**3
            tx=pts[i][0]-(pts[0][0]*(b0+b1)+pts[-1][0]*(b2+b3));ty=pts[i][1]-(pts[0][1]*(b0+b1)+pts[-1][1]*(b2+b3))
            X[0]+=A1[0]*tx+A1[1]*ty;X[1]+=A2[0]*tx+A2[1]*ty
        C[1][0]=C[0][1];det=C[0][0]*C[1][1]-C[1][0]*C[0][1]
        seg=math.dist(pts[0],pts[-1])
        if abs(det)<1e-12:a1=a2=seg/3
        else:a1=(X[0]*C[1][1]-C[0][1]*X[1])/det;a2=(C[0][0]*X[1]-C[1][0]*X[0])/det
        if a1<1e-6*seg or a2<1e-6*seg:a1=a2=seg/3
        return [pts[0],(pts[0][0]+t1[0]*a1,pts[0][1]+t1[1]*a1),(pts[-1][0]+t2[0]*a2,pts[-1][1]+t2[1]*a2),pts[-1]]
    c=gen(u)
    for _ in range(4):                                   # reparametrise (Newton)
        nu=[]
        for i,t in enumerate(u):
            q=_bez(c,t);d1=[(3*((c[k+1][0]-c[k][0])),3*((c[k+1][1]-c[k][1]))) for k in range(3)]
            mt=1-t;qd=(d1[0][0]*mt*mt+2*d1[1][0]*mt*t+d1[2][0]*t*t,d1[0][1]*mt*mt+2*d1[1][1]*mt*t+d1[2][1]*t*t)
            d2=[(2*(d1[k+1][0]-d1[k][0]),2*(d1[k+1][1]-d1[k][1])) for k in range(2)];qdd=(d2[0][0]*mt+d2[1][0]*t,d2[0][1]*mt+d2[1][1]*t)
            num=(q[0]-pts[i][0])*qd[0]+(q[1]-pts[i][1])*qd[1];den=qd[0]**2+qd[1]**2+(q[0]-pts[i][0])*qdd[0]+(q[1]-pts[i][1])*qdd[1]
            nu.append(min(1.,max(0.,t-num/den)) if abs(den)>1e-12 else t)
        u=nu;c=gen(u)
    err=[math.dist(_bez(c,t),pts[i]) for i,t in enumerate(u)];worst=max(range(n),key=lambda i:err[i])
    if err[worst]<=tol or n<4:return [c]
    mid=max(1,min(n-2,worst));tc=(pts[mid+1][0]-pts[mid-1][0],pts[mid+1][1]-pts[mid-1][1]);l=math.hypot(*tc) or 1.;tc=(tc[0]/l,tc[1]/l)
    return _fit(pts[:mid+1],t1,(-tc[0],-tc[1]),tol)+_fit(pts[mid:],tc,t2,tol)


def fit(pts,closed,tol=1.2):
    def tan(a,b):l=math.dist(a,b) or 1.;return ((b[0]-a[0])/l,(b[1]-a[1])/l)
    if closed:
        k=max(range(len(pts)),key=lambda i:pts[i][1]);pts=pts[k:]+pts[:k]+[pts[k]]   # start at the top extremum
        t1=tan(pts[-2],pts[1]);return _fit(pts,t1,(-t1[0],-t1[1]),tol)
    return _fit(pts,tan(pts[0],pts[1]),tan(pts[-1],pts[-2]),tol)


def to_path(curves_list):
    p=pathops.Path();pen=p.getPen();X=lambda q:(q[0]+S*q[1],q[1])
    for curves in curves_list:
        pen.moveTo(X(curves[0][0]))
        for c in curves:pen.curveTo(X(c[1]),X(c[2]),X(c[3]))
        pen.closePath()
    return p


def stroke_closed(points,scale=1.):
    """Closed skeleton -> ring (outer and inner contour), filled by nonzero union."""
    L,R=offsets(spline(points,True),scale)
    outer=fit(L,True);inner=fit(R,True)
    a=to_path([outer]);b=to_path([inner])
    big,small=(a,b) if abs(_area(L))>abs(_area(R)) else (b,a)
    return pathops.op(big,small,pathops.PathOp.DIFFERENCE,fix_winding=True)


def stroke_open(points,scale=1.,cap_round=True):
    s=spline(points,False);L,R=offsets(s,scale)
    pts=L+[p for p in reversed(R)]
    return to_path([fit(pts+[pts[0]],False)])


def _area(P):
    return 0.5*sum(P[i][0]*P[(i+1)%len(P)][1]-P[(i+1)%len(P)][0]*P[i][1] for i in range(len(P)))
