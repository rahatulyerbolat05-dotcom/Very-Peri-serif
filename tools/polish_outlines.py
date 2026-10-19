#!/usr/bin/env python3
"""Display-size polish of compiled TrueType outlines of the added glyphs.
1. Micro steps: two on-curve nodes of a straight piece shorter than MICRO units become one node at their
   midpoint (1-2 unit jogs where a stem edge meets a bracket show at 300+ px/em).
2. Exact tangent continuity: an on-curve node between two curve pieces whose tangents differ by less than
   KINK_DEG degrees (integer rounding of short handles leaves 1.5-4 degrees) is dropped when it lies within
   NODE_SHIFT units of the midpoint of its two off-curve neighbours: TrueType then derives the node as that
   midpoint, which is tangent-continuous by construction. Extremum nodes (axis-parallel tangent) stay explicit.
3. Straight edges (straighten, after the other passes): a run of lines and nearly flat curves (sag under STRAIGHT_RATIO of the length)
   that turns less than STRAIGHT_TURN degrees in all over STRAIGHT_LEN+ units is a stroke edge meant straight; when it leaves its chord by
   STRAIGHT_MIN or more (a belly, a dent, a line broken at a node: tools/straightness_audit.py) it becomes one line, its two end nodes kept,
   and the neighbouring handles turn onto it (align_handles); a nearly axial one (under 1.5 degrees, e.g. the Ц Щ bases at 0-5) goes
   exactly onto the axis, at a zone value when an end has one. The Italic sets STRAIGHT_RATIO 0.008: its native stems bow by design. The native Latin Regular has no such edge apart from the deliberate b q
   stems; the added letters had 19 (Щ Ц bases, Қ ж м я legs). Limit STRAIGHT_DEV.
Every glyph is verified against the unpolished outline (Hausdorff <= MAX_DEV) or left untouched.
"""
import json,math
from pathlib import Path
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.recordingPen import RecordingPen

PATCHES=json.loads(Path('data/polish-patches.json').read_text()) if Path('data/polish-patches.json').exists() else {}
MICRO=4.0
MICRO_CURVE=6.0
KINK_DEG=8.0
NODE_SHIFT=1.5
MAX_DEV=1.5
JOG_DEV=3.2
STRAIGHT_DEV=4.7;STRAIGHT_TURN=6.;STRAIGHT_LEN=80.;STRAIGHT_RATIO=0.012;STRAIGHT_MIN=0.4   # straighten(): see there
AXIS_EPS=0.6      # neighbours on one horizontal/vertical line: extremum node


def contours_of(glyph,glyf):
    c,e,fl=glyph.getCoordinates(glyf);out=[];s=0
    for en in e:
        out.append([[float(c[i][0]),float(c[i][1]),bool(fl[i]&1)] for i in range(s,en+1)]);s=en+1
    return out


def merge_micro(P):
    """Straight pieces shorter than MICRO and one-handle curve pieces shorter than MICRO_CURVE collapse to one node."""
    changed=True;count=0
    while changed and len(P)>5:
        changed=False;n=len(P)
        for i in range(n):
            a,b=P[i],P[(i+1)%n]
            if a[2] and b[2] and math.hypot(a[0]-b[0],a[1]-b[1])<MICRO:
                m=[round((a[0]+b[0])/2),round((a[1]+b[1])/2),True];j=(i+1)%n
                if j==0:P[0]=m;P.pop(i)
                else:P[i]=m;P.pop(j)
                changed=True;count+=1;break
            c=P[(i+2)%n]
            if a[2] and not b[2] and c[2] and math.hypot(a[0]-b[0],a[1]-b[1])+math.hypot(b[0]-c[0],b[1]-c[1])<MICRO_CURVE:
                m=[round((a[0]+c[0])/2),round((a[1]+c[1])/2),True];Q=P[i:]+P[:i];Q[0]=m;del Q[1:3];P=Q
                changed=True;count+=1;break
    return P,count


def smooth_nodes(P):
    n=len(P);drop=[];count=0
    for i in range(n):
        a,b,c=P[i-1],P[i],P[(i+1)%n]
        if not b[2] or a[2] or c[2]:continue
        v1=(b[0]-a[0],b[1]-a[1]);v2=(c[0]-b[0],c[1]-b[1])
        l1,l2=math.hypot(*v1),math.hypot(*v2)
        if l1<1e-9 or l2<1e-9:continue
        ang=math.degrees(math.acos(max(-1,min(1,(v1[0]*v2[0]+v1[1]*v2[1])/(l1*l2)))))
        if not(0.2<=ang<KINK_DEG):continue
        if abs(a[1]-c[1])<AXIS_EPS or abs(a[0]-c[0])<AXIS_EPS:continue   # extremum node
        mid=((a[0]+c[0])/2,(a[1]+c[1])/2)
        if math.hypot(b[0]-mid[0],b[1]-mid[1])>NODE_SHIFT:continue
        drop.append(i)
    # never drop two neighbouring nodes (the midpoint reference would move)
    keep=set();final=[]
    for i in drop:
        if (i-1)%n in keep or (i+1)%n in keep:continue
        keep.add(i);final.append(i)
    if len(P)-len(final)<5:return P,0
    return [p for i,p in enumerate(P) if i not in keep],len(final)


def align_handles(P):
    """Node between a straight piece and a curve: rotate the curve's handle onto the line (exact for axis-parallel lines)."""
    n=len(P);count=0
    for i in range(n):
        b=P[i]
        if not b[2]:continue
        for side in (-1,1):
            line=P[(i-side)%n];off=P[(i+side)%n]
            if not line[2] or off[2]:continue
            dx,dy=b[0]-line[0],b[1]-line[1];L=math.hypot(dx,dy)
            hx,hy=off[0]-b[0],off[1]-b[1];H=math.hypot(hx,hy)
            if L<8 or H<4:continue
            # direction of travel: line->node must continue node->off
            cosang=(dx*hx+dy*hy)/(L*H);ang=math.degrees(math.acos(max(-1,min(1,cosang))))
            if not(0.2<=ang<KINK_DEG):continue
            if abs(dx)<1e-9:new=[b[0],b[1]+math.copysign(H,hy) if abs(hy)>1e-9 else b[1]+math.copysign(H,dy)]
            elif abs(dy)<1e-9:new=[b[0]+math.copysign(H,hx) if abs(hx)>1e-9 else b[0]+math.copysign(H,dx),b[1]]
            else:
                ux,uy=dx/L,dy/L;new=[b[0]+ux*H,b[1]+uy*H]
            new=[round(new[0]),round(new[1])]
            if math.hypot(new[0]-off[0],new[1]-off[1])>2.2:continue
            if new!=[off[0],off[1]]:P[(i+side)%n]=[new[0],new[1],False];count+=1
    return P,count


def fix_jogs(P):
    """A stem edge that meets its bracket through a 10-unit wobble (on, off, off, on: x drifts 2-3 units) becomes straight:
    the bracket end and its handle take the x of the stem edge."""
    count=0;changed=True
    while changed:
        changed=False;n=len(P)
        for i in range(n):
            a,o1,o2,b=P[i],P[(i+1)%n],P[(i+2)%n],P[(i+3)%n]
            if not(a[2] and not o1[2] and not o2[2] and b[2]):continue
            dx=abs(a[0]-b[0]);dy=abs(a[1]-b[1])
            if not(0.5<=dx<=4.5 and 3<=dy<=16 and abs(o1[0]-a[0])<=4 and abs(o2[0]-b[0])<=4):continue
            before=P[(i-1)%n];after=P[(i+4)%n]
            if not before[2] and abs(before[0]-a[0])<=4 and (before[1]-a[1])*(b[1]-a[1])<0:   # a is the bracket end
                x=b[0];before[0]=x;a[0]=x
            elif not after[2] and abs(after[0]-b[0])<=4 and (after[1]-b[1])*(a[1]-b[1])<0:   # b is the bracket end
                x=a[0];after[0]=x;b[0]=x
            else:continue
            for j in sorted(((i+1)%n,(i+2)%n),reverse=True):P.pop(j)
            count+=1;changed=True;break
    return P,count


def to_glyph(contours):
    pen=TTGlyphPen(None)
    for P in contours:
        if not any(p[2] for p in P):
            pen.qCurveTo(*[(p[0],p[1]) for p in P],None);pen.closePath();continue
        start=next(i for i,p in enumerate(P) if p[2]);Q=P[start:]+P[:start]
        pen.moveTo((Q[0][0],Q[0][1]));offs=[]
        for p in Q[1:]+[Q[0]]:
            if p[2]:
                if offs:pen.qCurveTo(*offs,(p[0],p[1]))
                else:pen.lineTo((p[0],p[1]))
                offs=[]
            else:offs.append((p[0],p[1]))
        pen.closePath()
    return pen.glyph()


def hausdorff(g1,g2,glyf):
    from fontTools.pens.basePen import BasePen
    def pts(g):
        class Flat(BasePen):
            def __init__(s):super().__init__(None);s.pts=[];s.cur=None
            def _moveTo(s,p):s.cur=p;s.start=p;s.pts.append(p)
            def _lineTo(s,p):
                L=math.dist(s.cur,p);k=max(1,int(L/1.5))
                s.pts.extend((s.cur[0]+(p[0]-s.cur[0])*i/k,s.cur[1]+(p[1]-s.cur[1])*i/k) for i in range(1,k+1));s.cur=p
            def _qCurveToOne(s,a,c):
                L=math.dist(s.cur,a)+math.dist(a,c);k=max(4,int(L/1.5));p0=s.cur
                for i in range(1,k+1):
                    t=i/k;u=1-t;s.pts.append((u*u*p0[0]+2*u*t*a[0]+t*t*c[0],u*u*p0[1]+2*u*t*a[1]+t*t*c[1]))
                s.cur=c
            def _closePath(s):
                if s.cur!=s.start:s._lineTo(s.start)
        f=Flat();g.draw(f,glyf);return f.pts
    import numpy as np
    A=np.array(pts(g1));B=np.array(pts(g2))
    def one(X,Y):
        out=0.
        for i in range(0,len(X),2000):
            d=np.sqrt(((X[i:i+2000,None,:]-Y[None,:,:])**2).sum(-1)).min(axis=1);out=max(out,d.max())
        return out
    return max(one(A,B),one(B,A))


def apply_patches(contours,name):
    for patch in PATCHES.get(name,[]):
        hit=0
        for P in contours:
            for p in P:
                if 'clamp_y_max' in patch and p[0]<=patch['x_max'] and p[1]>patch['clamp_y_max']:p[1]=patch['clamp_y_max'];hit+=1
        assert hit,(name,patch)
    return contours


def polish(glyph,glyf,name=None):
    """Return (new glyph or the original, stats). Tries all passes, then fewer ones, until the shape stays within MAX_DEV."""
    if glyph.numberOfContours<=0:return glyph,{}
    base=apply_patches(contours_of(glyph,glyf),name);last={}
    patched=bool(PATCHES.get(name))
    for passes in (('micro','align','smooth'),('micro','align'),('micro',),('align','smooth'),('align',)):
        stats={'micro':0,'smooth':0,'align':0};new=[]
        for P in base:
            P=[p[:] for p in P]
            if 'micro' in passes:P,m=merge_micro(P);stats['micro']+=m
            if 'align' in passes:P,a=align_handles(P);stats['align']+=a
            if 'smooth' in passes:P,s_=smooth_nodes(P);stats['smooth']+=s_
            new.append(P)
        if not any(stats.values()) and not patched:continue
        g=to_glyph(new);g.recalcBounds(glyf);dev=hausdorff(glyph,g,glyf);stats['deviation']=round(float(dev),2)
        if dev<=MAX_DEV or (patched and dev<=8):return jogs(glyph,glyf,g,stats)
        last=dict(stats,rejected=True)
    return jogs(glyph,glyf,glyph,last if last else {})


def _explicit(P):
    """Same outline with every implied on-curve point (midpoint of two off-curves) written out."""
    out=[];n=len(P)
    for k in range(n):
        p=P[k];q=P[(k+1)%n];out.append(p[:])
        if not p[2] and not q[2]:out.append([(p[0]+q[0])/2,(p[1]+q[1])/2,True,'implied'])
    return out


def _implicit(P):
    """Drop the written-out implied nodes that are still the midpoints of two off-curve neighbours."""
    n=len(P);keep=[]
    for k,p in enumerate(P):
        a,b=P[k-1],P[(k+1)%n]
        if len(p)>3 and not a[2] and not b[2] and abs(p[0]-(a[0]+b[0])/2)<1e-6 and abs(p[1]-(a[1]+b[1])/2)<1e-6:continue
        keep.append([p[0],p[1],p[2]])
    return keep


def _ang(a,b):return math.atan2(b[1]-a[1],b[0]-a[0])
def _diff(a,b):return abs(math.degrees((b-a+math.pi)%(2*math.pi)-math.pi))
ZONES_XY=(0,-205,-215,510,720,740)


def straighten(P):
    P=_explicit(P);n=len(P);ons=[i for i in range(n) if P[i][2]]
    if len(ons)<3:return _implicit(P),0
    segs=[]
    for k,i in enumerate(ons):
        j=ons[(k+1)%len(ons)];a=P[i][:2];b=P[j][:2];L=math.dist(a,b)
        if L<1e-6:segs.append(None);continue
        if (j-i)%n==1:segs.append(dict(i=i,j=j,a0=_ang(a,b),a1=_ang(a,b),flat=True,pts=[a,b]));continue
        c=P[(i+1)%n][:2];sag=abs((c[0]-a[0])*(b[1]-a[1])-(c[1]-a[1])*(b[0]-a[0]))/L/2      # quadratic: half the control's distance
        mid=(0.25*a[0]+0.5*c[0]+0.25*b[0],0.25*a[1]+0.5*c[1]+0.25*b[1])
        segs.append(dict(i=i,j=j,a0=_ang(a,c),a1=_ang(c,b),flat=sag<=STRAIGHT_RATIO*L,pts=[a,mid,b]))
    m=len(segs);done=set();cuts=[]
    for k in range(m):
        if k in done or not segs[k] or not segs[k]['flat']:continue
        chain=[k];tot=_diff(segs[k]['a0'],segs[k]['a1'])
        for direction in (1,-1):
            while len(chain)<m:
                q=(chain[-1]+1)%m if direction>0 else (chain[0]-1)%m;s_=segs[q]
                if not s_ or not s_['flat'] or q in chain:break
                t=tot+(_diff(segs[chain[-1]]['a1'],s_['a0']) if direction>0 else _diff(s_['a1'],segs[chain[0]]['a0']))+_diff(s_['a0'],s_['a1'])
                if t>STRAIGHT_TURN:break
                (chain.append if direction>0 else lambda x:chain.insert(0,x))(q);tot=t
        done.update(chain)
        A=segs[chain[0]]['pts'][0];B=segs[chain[-1]]['pts'][-1];L=math.dist(A,B)
        if L<STRAIGHT_LEN:continue
        allp=[q for c in chain for q in segs[c]['pts']]
        d=max(abs((q[0]-A[0])*(B[1]-A[1])-(q[1]-A[1])*(B[0]-A[0]))/L for q in allp)
        ax=min(_diff(_ang(A,B),t) for t in (0,math.pi/2,math.pi,-math.pi/2))
        if d<STRAIGHT_MIN and not (0<ax<1.5 and max(abs(A[0]-B[0]),abs(A[1]-B[1]))>40 and min(abs(A[0]-B[0]),abs(A[1]-B[1]))>=0.5):continue
        cuts.append((segs[chain[0]]['i'],segs[chain[-1]]['j'],ax<1.5))
    if not cuts:return _implicit(P),0
    drop=set()
    for i,j,axial in cuts:
        k=(i+1)%n
        while k!=j:drop.add(k);k=(k+1)%n
        if axial:                                         # nearly horizontal/vertical: exactly on the axis, on a zone value if an end has one
            hor=abs(P[i][0]-P[j][0])>abs(P[i][1]-P[j][1]);c=1 if hor else 0
            vals=(P[i][c],P[j][c]);v=min(vals,key=lambda x:min(abs(x-z) for z in ZONES_XY)) if hor else round(sum(vals)/2)
            for e,nb in ((i,(i-1)%n),(j,(j+1)%n)):
                dv=v-P[e][c];P[e][c]=v
                if not P[nb][2]:P[nb][c]+=dv              # the outside handle moves with its node: the neighbouring curve keeps its tangent
    Q=[p for k,p in enumerate(P) if k not in drop];return _implicit(Q),len(cuts)


def straight_edges(original,glyf,current,stats):
    new=[];n=0
    for P in contours_of(current,glyf):
        for _ in range(4):                               # a cut can leave the next run of the same edge straight-able
            Q,k=straighten([p[:] for p in P])
            if not k:break
            Q,_=align_handles(Q);P,_=smooth_nodes(Q);n+=k
        new.append(P)
    if not n:return current,stats
    g=to_glyph(new);g.recalcBounds(glyf);dev=hausdorff(original,g,glyf)
    if dev>STRAIGHT_DEV:return current,dict(stats,straight_rejected=n)
    return g,dict(stats,straight=n,deviation=round(float(max(dev,stats.get('deviation',0))),2))


def jogs(original,glyf,current,stats):
    """Final stage: straighten bracket/stem wobbles, judged against the unpolished outline (limit JOG_DEV)."""
    new=[];n=0
    for P in contours_of(current,glyf):
        P,k=fix_jogs([p[:] for p in P]);new.append(P);n+=k
    if not n:return straight_edges(original,glyf,current,stats)
    g=to_glyph(new);g.recalcBounds(glyf);dev=hausdorff(original,g,glyf)
    if dev>JOG_DEV:return straight_edges(original,glyf,current,stats)
    return straight_edges(original,glyf,g,dict(stats,jog=n,deviation=round(float(dev),2)))
