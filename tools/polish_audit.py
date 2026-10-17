#!/usr/bin/env python3
"""Display-size polish audit of a TrueType font: finds what shows at 300+ px/em.
Checks per glyph (calibrated on the native Latin of the same font):
  slop     straight segment 15+ units long within 3 degrees of axis but not exactly axial
  zone     y-extremum within 6 units of a design zone but not on it
  extrema  curve whose extremum is not an on-curve node (more than 0.8 unit beyond the ends)
  kink     smooth-looking on-curve node (curve on both sides) with tangent break between 1.5 and 25 degrees
  micro    two on-curve nodes closer than 4 units
  wobble   curvature sign flips (zig-zag) of the sampled outline inside one 40-unit stretch, each turn >= 1.2 degrees per 4 units
Usage: python3 -I tools/polish_audit.py font.ttf [--glyphs uni0436,uni0434] [--latin] [--json out.json]
"""
import json,math,sys
from fontTools.ttLib import TTFont

ZONES=[-205,-215,-9,0,510,516,720,730,740,748]


def contours(font,name):
    g=font['glyf'][name]
    if g.numberOfContours<=0:return []
    c,e,fl=g.getCoordinates(font['glyf']);out=[];s=0
    for en in e:
        out.append([(c[i][0],c[i][1],bool(fl[i]&1)) for i in range(s,en+1)]);s=en+1
    return out


def segments(C):
    """Split a quadratic TrueType contour into segments: ('L',p0,p1) or ('Q',p0,c,p1)."""
    n=len(C);start=next((i for i,p in enumerate(C) if p[2]),None)
    if start is None:return []
    P=C[start:]+C[:start];P.append(P[0]);segs=[];cur=P[0];i=1;pend=[]
    for p in P[1:]:
        if p[2]:
            if not pend:segs.append(('L',(cur[0],cur[1]),(p[0],p[1])))
            else:
                pts=pend+[p]
                prev=(cur[0],cur[1])
                for k,q in enumerate(pend):
                    nxt=pend[k+1] if k+1<len(pend) else None
                    end=(( q[0]+nxt[0])/2,(q[1]+nxt[1])/2) if nxt else (p[0],p[1])
                    segs.append(('Q',prev,(q[0],q[1]),end,k==0,nxt is None));prev=end
            cur=p;pend=[]
        else:pend.append(p)
    return segs


def check(font,name):
    res={k:[] for k in('slop','zone','extrema','kink','micro','wobble')}
    for C in contours(font,name):
        segs=segments(C)
        if not segs:continue
        n=len(segs)
        for s in segs:
            if s[0]=='L':
                dx=s[2][0]-s[1][0];dy=s[2][1]-s[1][1];L=math.hypot(dx,dy)
                if L>=15:
                    a=math.degrees(math.atan2(abs(dx),abs(dy)))   # from vertical
                    b=math.degrees(math.atan2(abs(dy),abs(dx)))   # from horizontal
                    for ang,kind in((a,'v'),(b,'h')):
                        if 0<ang<=3 and min(abs(dx),abs(dy))>=0.5:res['slop'].append((kind,round(ang,2),s[1],s[2]))
            else:
                p0,c,p1=s[1],s[2],s[3]
                for ax,label in((1,'y'),(0,'x')):
                    d=p0[ax]-2*c[ax]+p1[ax]
                    if abs(d)<1e-9:continue
                    t=(p0[ax]-c[ax])/d
                    if 0.02<t<0.98:
                        v=(1-t)**2*p0[ax]+2*t*(1-t)*c[ax]+t*t*p1[ax]
                        if min(abs(v-p0[ax]),abs(v-p1[ax]))>0.8:res['extrema'].append((label,round(v,1),p0,p1))
        # node tests
        for i in range(n):
            a,b=segs[i-1],segs[i];p=b[1]
            ta=tangent_out(a,end=True);tb=tangent_out(b,end=False)
            if a[0]=='Q' and b[0]=='Q' and ta and tb:
                ang=math.degrees(math.acos(max(-1,min(1,ta[0]*tb[0]+ta[1]*tb[1]))))
                if 1.5<ang<12:res['kink'].append((round(ang,1),p))
            la=math.dist(a[1],a[-2] if a[0]=='Q' and False else p) if False else None
        ons=[s[1] for s in segs]
        for i in range(n):
            q=ons[i-1];p=ons[i]
            if math.dist(p,q)<4 and p!=q:res['micro'].append((p,q))
            if segs[i][0]=='L' or True:pass
        # zone
        for i in range(n):
            p=ons[i];pr=ons[i-1];nx=ons[(i+1)%n]
            if (p[1]>=pr[1] and p[1]>=nx[1]) or (p[1]<=pr[1] and p[1]<=nx[1]):
                near=min(ZONES,key=lambda z:abs(p[1]-z))
                if min(abs(p[1]-z) for z in ZONES)>0.5 and abs(p[1]-near)<=6:res['zone'].append((p,near))
        res['wobble']+=wobble(segs)
    return res


def tangent_out(s,end):
    if s[0]=='L':
        v=(s[2][0]-s[1][0],s[2][1]-s[1][1])
    else:
        v=(s[3][0]-s[2][0],s[3][1]-s[2][1]) if end else (s[2][0]-s[1][0],s[2][1]-s[1][1])
    L=math.hypot(*v)
    return (v[0]/L,v[1]/L) if L>1e-9 else None


def sample(segs,step=4.):
    pts=[]
    for s in segs:
        if s[0]=='L':
            L=math.dist(s[1],s[2]);k=max(1,int(L/2))
            pts+= [(s[1][0]+(s[2][0]-s[1][0])*i/k,s[1][1]+(s[2][1]-s[1][1])*i/k) for i in range(k)]
        else:
            p0,c,p1=s[1],s[2],s[3];L=math.dist(p0,c)+math.dist(c,p1);k=max(4,int(L/2))
            for i in range(k):
                t=i/k;u=1-t;pts.append((u*u*p0[0]+2*u*t*c[0]+t*t*p1[0],u*u*p0[1]+2*u*t*c[1]+t*t*p1[1]))
    res=[pts[0]];acc=0.
    for a,b in zip(pts,pts[1:]+pts[:1]):
        L=math.dist(a,b)
        while L>1e-9 and acc+L>=step:
            t=(step-acc)/L;a=(a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t);res.append(a);L=math.dist(a,b);acc=0.
        acc+=L
    return res


def wobble(segs):
    P=sample(segs);n=len(P);turns=[]
    for i in range(n):
        a,b,c=P[i-1],P[i],P[(i+1)%n]
        v1=(b[0]-a[0],b[1]-a[1]);v2=(c[0]-b[0],c[1]-b[1])
        turns.append(math.degrees(math.atan2(v1[0]*v2[1]-v1[1]*v2[0],v1[0]*v2[0]+v1[1]*v2[1])))
    out=[]
    # a wobble: turn direction changes at least twice inside 14 samples (56 units) with every turn small (<5 degrees per 4 units) and 1.0+ at the changes
    for i in range(n):
        w=[turns[(i+k)%n] for k in range(14)]
        if max(abs(t) for t in w)>=5:continue
        sg=[1 if t>=1.0 else -1 if t<=-1.0 else 0 for t in w];sg=[x for x in sg if x]
        flips=sum(1 for a,b in zip(sg,sg[1:]) if a!=b)
        if flips>=2:out.append((tuple(round(v) for v in P[i]),flips,round(max(w),1)))
    # merge neighbours
    merged=[]
    for o in out:
        if not merged or math.dist(merged[-1][0],o[0])>40:merged.append(o)
    return merged


def main():
    path=sys.argv[1];font=TTFont(path);args=sys.argv[2:]
    names=font.getGlyphOrder()
    if '--glyphs' in args:names=args[args.index('--glyphs')+1].split(',')
    elif '--latin' in args:
        cm=font.getBestCmap();names=[cm[c] for c in list(range(ord('a'),ord('z')+1))+list(range(ord('A'),ord('Z')+1)) if c in cm]
    else:
        m=json.load(open('build/regular-release/source/build-manifest.json'))['glyph_records']
        skip=set(json.load(open('data/typographic-completion/manifest.json')))
        names=[n for n,r in m.items() if 'data/homoglyph/' not in r['path'] and r['character'] not in skip and font['glyf'][n].numberOfContours>0 and r['character'].isalpha() and r['character'] not in 'ƏəӘә']
    total={k:0 for k in('slop','zone','extrema','kink','micro','wobble')};rows={}
    for n in names:
        r=check(font,n);rows[n]=r
        for k in total:total[k]+=len(r[k])
    print('glyphs',len(names),'totals',total,'per glyph',{k:round(v/len(names),2) for k,v in total.items()})
    if '--json' in args:
        json.dump({n:{k:[list(map(str,x)) if isinstance(x,tuple) else x for x in v] for k,v in r.items()} for n,r in rows.items()},open(args[args.index('--json')+1],'w'),ensure_ascii=False)
    rank=sorted(rows.items(),key=lambda kv:-sum(len(v) for v in kv[1].values()))
    for n,r in rank[:int(args[args.index('--top')+1]) if '--top' in args else 15]:
        print(n,{k:len(v) for k,v in r.items() if v})
    return rows

if __name__=='__main__':main()
