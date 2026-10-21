#!/usr/bin/env python3
"""Inventory every glyph, including components/alternates, and flag curve waves.

Flags are review candidates, not automatic design failures. A short curvature
lobe with opposite-signed neighbours can be a construction seam or a deliberate
serif/terminal. Unlike a node-only tangent check this catches the 1.106 ya wave.
"""
import argparse, hashlib, json, math, sys
from pathlib import Path
from collections import Counter
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fontTools.ttLib import TTFont
from polish_audit import segments
from roughness_audit import glyph_samples, native_threshold
import numpy as np


def contours(font, name):
    coords, ends, flags = font['glyf'][name].getCoordinates(font['glyf'])
    result=[]; start=0
    for end in ends:
        result.append([(float(coords[i][0]),float(coords[i][1]),bool(flags[i]&1)) for i in range(start,end+1)])
        start=end+1
    return result


def angle(a,b):
    return math.degrees(math.atan2(a[0]*b[1]-a[1]*b[0], a[0]*b[0]+a[1]*b[1]))


def tangent_out(seg,end):
    # A coincident control gives a zero first derivative, but the limiting
    # tangent is still defined by the next distinct point. Never hide such a
    # join by dropping it from the audit.
    pts=list(seg[1:3] if seg[0]=='L' else seg[1:4])
    if end:
        origin=pts[-1];candidates=reversed(pts[:-1])
    else:
        origin=pts[0];candidates=iter(pts[1:])
    for p in candidates:
        v=(origin[0]-p[0],origin[1]-p[1]) if end else (p[0]-origin[0],p[1]-origin[1])
        size=math.hypot(*v)
        if size>1e-9:return (v[0]/size,v[1]/size)
    return None


def length(seg):
    if seg[0]=='L': return math.dist(seg[1],seg[2])
    a,c,b=seg[1:4]
    pts=[((1-t)**2*a[0]+2*t*(1-t)*c[0]+t*t*b[0],(1-t)**2*a[1]+2*t*(1-t)*c[1]+t*t*b[1]) for t in np.linspace(0,1,13)]
    return sum(math.dist(p,q) for p,q in zip(pts,pts[1:]))


def inspect(font,name,threshold,rough=True):
    waves=[]; kinks=[]; micro=[]
    for ci,C in enumerate(contours(font,name)):
        segs=segments(C); n=len(segs)
        if not n: continue
        starts=[]; turns=[]; lens=[]
        for s in segs:
            a,b=tangent_out(s,False),tangent_out(s,True)
            turns.append(angle(a,b) if a and b and s[0]=='Q' else 0.)
            lens.append(length(s))
        joints=[]
        for i,s in enumerate(segs):
            a,b=tangent_out(segs[i-1],True),tangent_out(s,False)
            j=abs(angle(a,b)) if a and b else 180.
            joints.append(j)
            if 1.5<j<12 and min(lens[i-1],lens[i])>=6:
                kinks.append({'xy':list(s[1]),'degrees':round(j,2),'contour':ci})
            if 0<lens[i]<3:
                micro.append({'xy':list(s[1]),'length':round(lens[i],2),'contour':ci})
        # Split at hard corners; concatenate neighbouring same-sign quadratics.
        cuts=[i for i in range(n) if joints[i]>=12 or segs[i][0]=='L']
        origin=cuts[0] if cuts else 0
        groups=[]
        for offset in range(n):
            i=(origin+offset)%n; s=segs[i]
            sign=1 if turns[i]>.2 else -1 if turns[i]<-.2 else 0
            if not sign:
                groups.append({'sign':0,'ids':[i],'turn':0,'length':lens[i]});continue
            if groups and groups[-1]['sign']==sign and joints[i]<12:
                g=groups[-1];g['ids'].append(i);g['turn']+=turns[i];g['length']+=lens[i]
            else: groups.append({'sign':sign,'ids':[i],'turn':turns[i],'length':lens[i]})
        for j,g in enumerate(groups):
            if not g['sign'] or not (4<=abs(g['turn'])<=100 and 6<=g['length']<=110):continue
            a=groups[j-1];b=groups[(j+1)%len(groups)]
            if a['sign']!=-g['sign'] or b['sign']!=-g['sign']:continue
            if min(abs(a['turn']),abs(b['turn']))<3:continue
            i0=g['ids'][0]; i1=b['ids'][0]
            if joints[i0]>=12 or joints[i1]>=12:continue
            # Store the middle of the short reversal and enough context to see it.
            pts=[segs[i][1] for i in g['ids']]+[segs[g['ids'][-1]][3]]
            xy=[sum(p[k] for p in pts)/len(pts) for k in (0,1)]
            waves.append({'xy':[round(x,2) for x in xy],'contour':ci,'turn':round(g['turn'],2),
                          'length':round(g['length'],2),'neighbour_turns':[round(a['turn'],2),round(b['turn'],2)],
                          'segment_ids':g['ids']})
    peaks=[]
    if rough:
        for Q,r,skip in glyph_samples(font,name):
            for i in np.argsort(-r):
                if r[i]<threshold:break
                xy=[round(float(v),2) for v in Q[i]]
                if all(math.dist(xy,p['xy'])>30 for p in peaks):peaks.append({'xy':xy,'residual':round(float(r[i]),3)})
    return {'waves':waves,'kinks':kinks,'micro':micro,'roughness':peaks}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root',default='fonts/ttf'); ap.add_argument('--output',default='build/curve-audit/audit.json')
    args=ap.parse_args(); report={'fonts':{},'candidates_are_not_automatic_defects':True}
    for style in ('Regular','Italic'):
        path=Path(args.root)/f'VeryPeriSerif-{style}.ttf';f=TTFont(path)
        native=TTFont(f'reference/instrument-serif/fonts/ttf/InstrumentSerif-{style}.ttf')
        threshold,_,_=native_threshold(f)
        cmap=f.getBestCmap(); reverse={}
        for cp,name in cmap.items():reverse.setdefault(name,[]).append(chr(cp))
        rows={}; unique={}; types=Counter()
        for name in f.getGlyphOrder():
            g=f['glyf'][name];C=contours(f,name)
            types['composite' if g.isComposite() else 'simple' if C else 'empty']+=1
            coords=[p for c in C for p in c];xm=min((p[0] for p in coords),default=0);ym=min((p[1] for p in coords),default=0)
            sig=hashlib.sha256(repr([[(x-xm,y-ym,on) for x,y,on in c] for c in C]).encode()).hexdigest()
            same=unique.get(sig)
            protected=name in native.getGlyphOrder() and g.compile(f['glyf'])==native['glyf'][name].compile(native['glyf'])
            if same:
                # Translate the canonical diagnostics back to this glyph.
                ref=rows[same];dx=xm-ref['origin'][0];dy=ym-ref['origin'][1]
                diag=json.loads(json.dumps(ref['diagnostics']))
                for spots in diag.values():
                    for spot in spots:spot['xy']=[round(spot['xy'][0]+dx,2),round(spot['xy'][1]+dy,2)]
            else:
                unique[sig]=name;diag=inspect(f,name,threshold) if C else {k:[] for k in ('waves','kinks','micro','roughness')}
            rows[name]={'characters':reverse.get(name,[]),'kind':'composite' if g.isComposite() else 'simple' if C else 'empty',
                        'native_unchanged':protected,'same_shape_as':same,'origin':[xm,ym],'diagnostics':diag}
        report['fonts'][style]={'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'glyph_count':len(rows),'types':dict(types),
                                'unique_shapes':len(unique),'roughness_threshold':threshold,'glyphs':rows}
        counts={k:sum(len(r['diagnostics'][k]) for r in rows.values()) for k in ('waves','kinks','micro','roughness')}
        print(style,len(rows),'glyphs;',len(unique),'unique shapes;',counts,flush=True)
    out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(out)


if __name__=='__main__': main()
