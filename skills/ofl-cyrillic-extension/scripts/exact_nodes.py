"""Lossless TrueType point reduction; no fitting, smoothing or corner movement."""
from copy import deepcopy
from fractions import Fraction as F
import hashlib

from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates


def cross(a,b): return a[0]*b[1]-a[1]*b[0]
def sub(a,b): return (a[0]-b[0],a[1]-b[1])
def dot(a,b): return a[0]*b[0]+a[1]*b[1]
def point(p): return (F(p[0]),F(p[1]))


def contours(glyph,glyf):
    xy,ends,flags=glyph.getCoordinates(glyf);out=[];start=0
    for end in ends:
        out.append([(int(xy[i][0]),int(xy[i][1]),bool(flags[i]&1)) for i in range(start,end+1)]);start=end+1
    return out


def parent_control(a,c,m,d,b):
    """Exact inverse of a split quadratic, with rational arithmetic."""
    a,c,m,d,b=map(point,(a,c,m,d,b));u,v=sub(m,c),sub(d,m)
    if cross(u,v) or dot(u,v)<=0:return None
    axis=0 if u[0]+v[0] else 1
    t=u[axis]/(u[axis]+v[axis])
    if not 0<t<1:return None
    x=tuple(a[k]+(c[k]-a[k])/t for k in (0,1))
    y=tuple(b[k]+(d[k]-b[k])/(1-t) for k in (0,1))
    return x if x==y else None


def reduce_points(points):
    p=list(points);stats={'implicit_midpoints':0,'collinear_line_points':0,'straight_controls':0,'split_quadratics':0}
    changed=True
    while changed and len(p)>3:
        changed=False;n=len(p)
        for i in range(n):
            a,m,b=p[i-1],p[i],p[(i+1)%n]
            if m[2] and not a[2] and not b[2] and (2*m[0],2*m[1])==(a[0]+b[0],a[1]+b[1]):
                del p[i];stats['implicit_midpoints']+=1;changed=True;break
            if m[2] and a[2] and b[2] and not cross(sub(m,a),sub(b,m)) and dot(sub(m,a),sub(b,m))>0:
                del p[i];stats['collinear_line_points']+=1;changed=True;break
        if changed:continue
        for i,a in enumerate(p):
            if not a[2]:continue
            q=p[i:]+p[:i];j=1
            while j<len(q) and not q[j][2]:j+=1
            if j>1 and j<len(q):
                b=q[j];direction=sub(b,a)
                if dot(direction,direction) and all(not cross(sub(v,a),direction) for v in q[1:j]):
                    ds=[dot(sub(v,a),direction) for v in q[:j+1]]
                    if all(x<=y for x,y in zip(ds,ds[1:])):
                        stats['straight_controls']+=j-1;p=[q[0]]+q[j:];changed=True;break
            # An exact merged quadratic needs stored outer endpoints. Implied
            # half-unit endpoints are left intact, so integer-grid rounding
            # cannot change adjacent curves.
            for count in (5,4):
                if len(q)<count:continue
                run=q[:count]
                if count==5 and [x[2] for x in run]==[True,False,True,False,True]:
                    a,c,m,d,b=run
                elif count==4 and [x[2] for x in run]==[True,False,False,True]:
                    a,c,d,b=run;m=((c[0]+d[0])/2,(c[1]+d[1])/2,True)
                else:continue
                control=parent_control(a,c,m,d,b)
                if control and all(x.denominator==1 for x in control):
                    # Do not change the TrueType control-point bounding box.
                    bounds=[min(x[k] for x in p) for k in (0,1)]+[max(x[k] for x in p) for k in (0,1)]
                    if not all(bounds[k]<=control[k]<=bounds[k+2] for k in (0,1)):continue
                    p=[a,(int(control[0]),int(control[1]),False),b]+q[count:]
                    stats['split_quadratics']+=count-3;changed=True;break
            if changed:break
    return p,stats


def reduce_glyph(glyph,glyf):
    if glyph.numberOfContours<=0 or (hasattr(glyph,'program') and glyph.program.getBytecode()):return glyph,{}
    # Point-attached information is not safely reindexed by this tool.
    if any(flag & ~1 for flag in glyph.flags):return glyph,{}
    out=[];total={};before=contours(glyph,glyf)
    for c in before:
        p,stats=reduce_points(c);out.append(p)
        for key,value in stats.items():total[key]=total.get(key,0)+value
    if sum(len(c) for c in out)>=sum(len(c) for c in before):return glyph,{}
    new=deepcopy(glyph);new.coordinates=GlyphCoordinates([(x,y) for c in out for x,y,on in c])
    new.flags=bytearray([1 if on else 0 for c in out for x,y,on in c]);new.endPtsOfContours=[];end=-1
    for c in out:end+=len(c);new.endPtsOfContours.append(end)
    new.recalcBounds(glyf)
    if (new.xMin,new.yMin,new.xMax,new.yMax)!=(glyph.xMin,glyph.yMin,glyph.xMax,glyph.yMax):return glyph,{}
    return new,total


def canonical_outline(font,name):
    """Independent exact path normalization for representation-only changes.

    Decomposes implicit points/components using BasePen, simplifies straight
    quadratics/lines and exact split parabolas. Fractions retain half-units.
    """
    cs,closed=read_outline_native(font,name);out=[]
    for contour in cs:
        s=[]
        for segment in contour:
            p=tuple(point(v) for v in segment.points)
            if len(p)==3 and not cross(sub(p[1],p[0]),sub(p[2],p[0])) and dot(sub(p[1],p[0]),sub(p[2],p[1]))>=0:p=(p[0],p[2])
            s.append(p)
        changed=True
        while changed and len(s)>1:
            changed=False
            for i,a in enumerate(s):
                j=(i+1)%len(s);b=s[j]
                if a[-1]!=b[0]:raise ValueError('Disconnected contour')
                merged=None
                if len(a)==len(b)==2 and not cross(sub(a[1],a[0]),sub(b[1],b[0])) and dot(sub(a[1],a[0]),sub(b[1],b[0]))>0:merged=(a[0],b[-1])
                if len(a)==len(b)==3:
                    control=parent_control(a[0],a[1],a[2],b[1],b[2])
                    if control is not None:merged=(a[0],control,b[-1])
                if merged is not None:
                    if j==0:s=[merged]+s[1:i]
                    else:s[i:j+1]=[merged]
                    changed=True;break
        if s:
            start=min(range(len(s)),key=lambda i:tuple(s[i:]+s[:i]));s=s[start:]+s[:start]
        out.append(tuple(s))
    return tuple(zip(closed,out))


def geometry_fingerprint(font,name):
    return hashlib.sha256(repr(canonical_outline(font,name)).encode()).hexdigest()


def read_outline_native(font, name):
    """Exact native-unit decomposition, with no 1000-UPM float normalization."""
    from fontTools.pens.basePen import BasePen
    from types import SimpleNamespace
    class Pen(BasePen):
        def __init__(self, gs):
            super().__init__(gs);self.skipMissingComponents=False
            self.contours=[];self.closed=[];self.current=None
        def _moveTo(self,p):
            if self.current is not None:raise ValueError('Unterminated contour')
            self.current=[];self.start=self.cursor=point(p)
        def put(self, points):
            self.current.append(SimpleNamespace(points=tuple(points)));self.cursor=points[-1]
        def _lineTo(self,p):self.put((self.cursor,point(p)))
        def _qCurveToOne(self,c,p):self.put((self.cursor,point(c),point(p)))
        def _curveToOne(self,a,b,p):self.put((self.cursor,point(a),point(b),point(p)))
        def end(self,closed):
            if closed and self.cursor!=self.start:self._lineTo(self.start)
            self.contours.append(self.current);self.closed.append(closed);self.current=None
        def _closePath(self):self.end(True)
        def _endPath(self):self.end(False)
    gs=font.getGlyphSet();pen=Pen(gs);gs[name].draw(pen)
    if pen.current is not None:raise ValueError('Open pen state')
    return pen.contours,pen.closed
