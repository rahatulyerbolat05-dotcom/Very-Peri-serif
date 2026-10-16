#!/usr/bin/env python3
"""Read-only audit of all purple author GLIFs, including alternate қ forms.

Run from repository root. Results go to ignored build/purple-audit/.
Tangent flags are candidates for visual inspection, not automatic defects.
Curve sampling is diagnostic only; original Beziers are never rewritten.
"""
import hashlib
import json
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fontTools.ufoLib.glifLib import readGlyphFromString
from fontTools.pens.pointPen import PointToSegmentPen
from fontTools.pens.basePen import BasePen
import pathops
from shapely.geometry import LinearRing

OUT = Path('build/purple-audit')


class Segments(BasePen):
    def __init__(self):
        super().__init__(None)
        self.contours = []
        self.current = []
        self.start = None
        self.open_contours = 0

    def _moveTo(self, pt):
        self.start = pt
        self.current = []

    def _lineTo(self, pt):
        self.current.append((self._getCurrentPoint(), pt))

    def _qCurveToOne(self, a, b):
        self.current.append((self._getCurrentPoint(), a, b))

    def _curveToOne(self, a, b, c):
        self.current.append((self._getCurrentPoint(), a, b, c))

    def _closePath(self):
        last = self._getCurrentPoint()
        if last != self.start:
            self.current.append((last, self.start))
        self.contours.append(self.current)

    def _endPath(self):
        self.open_contours += 1
        self.contours.append(self.current)


def sample(seg, t):
    points = list(seg)
    while len(points) > 1:
        points = [((1-t)*a[0]+t*b[0], (1-t)*a[1]+t*b[1]) for a,b in zip(points,points[1:])]
    return points[0]


def tangent(seg, end=False):
    origin = seg[-1] if end else seg[0]
    for pt in (reversed(seg[:-1]) if end else seg[1:]):
        v = (origin[0]-pt[0], origin[1]-pt[1]) if end else (pt[0]-origin[0], pt[1]-origin[1])
        if math.hypot(*v) > 1e-7:
            return v
    return (0, 0)


def rectangle(x0, y0, x1, y1):
    p = pathops.Path(); pen = p.getPen()
    pen.moveTo((x0,y0)); pen.lineTo((x1,y0)); pen.lineTo((x1,y1)); pen.lineTo((x0,y1)); pen.closePath()
    return p


def runs(path, value, vertical=False):
    strip = rectangle(value, -1000, value+.01, 2000) if vertical else rectangle(-1000, value, 2000, value+.01)
    cut = pathops.op(path, strip, pathops.PathOp.INTERSECTION)
    idx = 1 if vertical else 0
    return sorted([[round(c.bounds[idx], 3), round(c.bounds[idx+2], 3)] for c in cut.contours])


def inspect(ch, item):
    filename = Path(item['path']); raw = filename.read_bytes()
    for node in ET.fromstring(raw).findall('.//point'):
        assert math.isfinite(float(node.get('x'))) and math.isfinite(float(node.get('y')))
    meta = SimpleNamespace(); seg = Segments(); p = pathops.Path()
    readGlyphFromString(raw.decode(), meta, PointToSegmentPen(seg))
    readGlyphFromString(raw.decode(), SimpleNamespace(), PointToSegmentPen(p.getPen()))
    assert meta.width > 0
    if item['role']=='primary': assert ord(ch) in getattr(meta,'unicodes',[])
    clean = pathops.simplify(p)
    rings, joints = [], []
    for ci, contour in enumerate(seg.contours):
        points = [sample(s, n/64) for s in contour for n in range(64)]
        rings.append({'contour': ci+1, 'simple_approx': LinearRing(points).is_simple if len(points)>3 else False})
        for prev, nxt in zip(contour, contour[1:]+contour[:1]):
            if len(prev)==len(nxt)==2: continue
            if math.dist(prev[0],prev[-1])<5 or math.dist(nxt[0],nxt[-1])<5: continue
            a,b = tangent(prev,True),tangent(nxt)
            den=math.hypot(*a)*math.hypot(*b)
            if not den: continue
            angle=math.degrees(math.acos(max(-1,min(1,(a[0]*b[0]+a[1]*b[1])/den))))
            if angle>5:
                joints.append({'xy':list(prev[-1]),'angle':round(angle,2),'contour':ci+1})
    result = {'character':ch, 'role':item['role'], 'path':str(filename),
              'sha256':hashlib.sha256(raw).hexdigest(),
              'matches_registered_hash':hashlib.sha256(raw).hexdigest()==item.get('glif_sha256'),
              'unicode':list(getattr(meta,'unicodes',[])), 'advance':meta.width,
              'bounds':list(p.bounds), 'open_contours':seg.open_contours,
              'contours':[{'index':i+1,'area':c.area,'bounds':list(c.bounds),'clockwise':c.clockwise}
                          for i,c in enumerate(p.contours)],
              'normalized_contours':len(list(clean.contours)), 'area_before':p.area,'area_after':clean.area,
              'ring_diagnostics':rings, 'tangent_candidates':joints,
              'horizontal_slices':{str(y):runs(clean,y) for y in (-205,-199,0,12,150,250,380,425,470,510,513,516,600,700)},
              'vertical_slices':{str(x):runs(clean,x,True) for x in (125,200,250,275,300,350,400)}}
    return result


def render(results):
    from alphabet_sheet import canvas, glyph, text, load_glif, PathPatch, MplPen
    import matplotlib.pyplot as plt
    fig,ax=canvas(1800,2260)
    text(ax,40,25,'Авторские глифы · аудит без изменения контуров',30)
    for i,r in enumerate(results):
        col,row=i%3,i//3; x,y=col*600,row*535+90
        xmin,ymin,xmax,ymax=r['bounds']; scale=min(.49,490/(xmax-xmin))
        baseline=y+390
        for h in (0,510,720):
            ax.plot([x+35,x+565],[baseline-h*scale]*2,color='#ded8d0',lw=.6)
        glyph(ax,r['path'],x+300,baseline,scale)
        text(ax,x+30,y+5,f"{r['character']} · {r['role']}",24)
        text(ax,x+30,y+435,f"y {ymin:.1f}…{ymax:.1f} · контуров {len(r['contours'])}",18)
        dx=x+300-(xmin+xmax)*scale/2
        for j in r['tangent_candidates']:
            px,py=j['xy']
            ax.plot(dx+px*scale,baseline-py*scale,'o',ms=3,mfc='none',mec='#d64949',mew=.7)
    text(ax,40,2220,'Красные точки — кандидаты на проверку касательных; острые углы могут быть намеренными.',18)
    fig.savefig(OUT/'overview.svg');fig.savefig(OUT/'overview.png',dpi=100);plt.close(fig)
    fig,axs=plt.subplots(1,3,figsize=(15,5))
    panels=[('қ','primary',(353,366,83,99),'қ: петля под основным контуром'),
            ('ф','primary',(292,335,0,45),'ф: нижнее сочленение чаши'),
            ('Щ','primary',(165,205,15,60),'Щ: вход в нижнюю горизонталь')]
    for ax,(ch,role,bounds,title) in zip(axs,panels):
        r=next(v for v in results if v['character']==ch and v['role']==role)
        ax.add_patch(PathPatch(load_glif(r['path']).path,facecolor='#272333',edgecolor='none'))
        p=pathops.Path()
        readGlyphFromString(Path(r['path']).read_text(),SimpleNamespace(),PointToSegmentPen(p.getPen()))
        for contour in p.contours:
            if contour.area<2:
                pen=MplPen(None);contour.draw(pen)
                ax.add_patch(PathPatch(pen.result(),facecolor='none',edgecolor='#ff6688',lw=1))
        for j in r['tangent_candidates']:
            ax.plot(*j['xy'],'o',color='red',ms=3)
        ax.set_xlim(bounds[0],bounds[1]);ax.set_ylim(bounds[2],bounds[3])
        ax.set_aspect('equal');ax.set_title(title);ax.grid(alpha=.2)
    fig.tight_layout();fig.savefig(OUT/'details.svg');fig.savefig(OUT/'details.png',dpi=130);plt.close(fig)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    cfg=json.loads(Path('data/alphabet.json').read_text())
    results=[inspect(ch,v) for ch,e in cfg['user'].items() if e.get('origin')!='Claude' for v in e['variants']]
    context=json.loads(Path('data/context/serif_bl.json').read_text())
    from check_context_classes import load, test, test_top
    for r in results:
        ch=r['character']; p=load(r['path'])
        r['context_check']={
            'registered_as_current_base':context['built_bases'].get(ch)==r['path'],
            'serif_bl_measured':test(p)[0],
            'serif_bl_declared':ch in context['declared_class']['lower']+context['declared_class']['upper'],
            'head_tl_measured':test_top(p)[0] if ch.islower() else None,
            'head_tl_declared':ch in context['ka_short']['declared_class']['lower'] if ch.islower() else None,
        }
    (OUT/'audit.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
    render(results)
    for r in results:
        print(r['character'],r['role'],'contours',len(r['contours']),'->',r['normalized_contours'],
              'non-simple candidates',[d['contour'] for d in r['ring_diagnostics'] if not d['simple_approx']],
              'joints',[(tuple(round(v,1) for v in j['xy']),j['angle']) for j in r['tangent_candidates']])


if __name__=='__main__': main()
