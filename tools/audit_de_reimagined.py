"""Check the new de source, topology and integer-rounded outline exports."""
from pathlib import Path
import argparse, json, math
import numpy as np
from glyphsLib import GSLayer
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen
from shapely.geometry import Polygon, LinearRing, LineString

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--study-dir', type=Path, default=ROOT/'build/regular/de-reimagined')
args = parser.parse_args()
study = args.study_dir.resolve()
design = json.loads((ROOT/'data/de-reimagined-outlines.json').read_text())

class SamplePen(BasePen):
    def __init__(self, gs=None):
        super().__init__(gs); self.rings=[]; self.points=[]; self.p=None
    def _moveTo(self,p): self.p=np.array(p); self.points=[tuple(p)]
    def _lineTo(self,p): self.p=np.array(p); self.points.append(tuple(p))
    def _curveToOne(self,a,b,c):
        t=np.linspace(0,1,601)[1:,None]
        points=(1-t)**3*self.p+3*(1-t)**2*t*np.array(a)+3*(1-t)*t*t*np.array(b)+t**3*np.array(c)
        self.points.extend(map(tuple,points)); self.p=np.array(c)
    def _qCurveToOne(self,a,b):
        t=np.linspace(0,1,601)[1:,None]
        points=(1-t)**2*self.p+2*(1-t)*t*np.array(a)+t*t*np.array(b)
        self.points.extend(map(tuple,points)); self.p=np.array(b)
    def _closePath(self): self.rings.append(self.points); self.points=[]

def sampled(obj,gs=None):
    p=SamplePen(gs); obj.draw(p)
    assert len(p.rings)==2
    assert all(LinearRing(r).is_simple for r in p.rings)
    poly=Polygon(p.rings[0],p.rings[1:]); assert poly.is_valid and poly.area>0
    return p.rings,poly

result={'status':'passed','sample_points_per_bezier':600,
        'limits':'Sampled topology and outline distances; visual acceptance remains open.',
        'variants':{}}
for variant, spec in design['variants'].items():
    layer=GSLayer(); pen=layer.getPen()
    for op,points in spec['commands']: getattr(pen,op)(*[tuple(p) for p in points])
    native_rings,source_poly=sampled(layer)
    assert LinearRing(native_rings[0]).is_ccw and not LinearRing(native_rings[1]).is_ccw
    curves=[];ring=[];point=None
    for op,points in spec['commands']:
        if op=='moveTo': point=points[0]; ring=[]
        elif op in {'lineTo','curveTo'}: ring.append([point]+points);point=points[-1]
        elif op=='closePath': curves.append(ring)
    corners={tuple(p) for p in spec['intentional_corner_points']}; observed=set();smooth=[]
    for ring in curves:
        for i,seg in enumerate(ring):
            nxt=ring[(i+1)%len(ring)]
            assert seg[-1]==nxt[0]
            incoming=np.array(seg[-1])-seg[-2];outgoing=np.array(nxt[1])-nxt[0]
            assert np.linalg.norm(incoming)>0 and np.linalg.norm(outgoing)>0
            cross=incoming[0]*outgoing[1]-incoming[1]*outgoing[0]
            angle=math.degrees(math.atan2(abs(float(cross)),float(np.dot(incoming,outgoing))))
            if tuple(seg[-1]) in corners: observed.add(tuple(seg[-1]))
            else: smooth.append(angle);assert angle<.000001,(variant,seg[-1],angle)
    assert observed==corners
    adjacent_duplicates=sum(tuple(n.position)==tuple(p.nodes[i-1].position)
                             for p in layer.paths for i,n in enumerate(p.nodes))
    assert adjacent_duplicates==0
    exports=[]
    for file in sorted(study.rglob(f'de-{variant}.ttf')):
        tt=TTFont(file);gs=tt.getGlyphSet();rings,poly=sampled(gs['uni0434'],gs)
        assert not LinearRing(rings[0]).is_ccw and LinearRing(rings[1]).is_ccw
        distance=max(LineString(a+[a[0]]).hausdorff_distance(LineString(b+[b[0]]))
                     for a,b in zip(native_rings,rings))
        assert distance<1.25,(file,distance)
        area_difference=abs(poly.area-source_poly.area)/source_poly.area
        assert area_difference<.005,(file,area_difference)
        assert tt['hmtx']['uni0434'][0]==spec['advance']
        exports.append({'ttf':str(file.relative_to(study)),
                        'sampled_hausdorff_units':distance,
                        'relative_area_difference':area_difference})
    assert len(exports)==4
    result['variants'][variant]={'name':spec['name'],'adjacent_cubic_duplicates':0,
        'sampled_self_intersections':0,'contours':2,'counters':1,
        'intentional_corners':spec['intentional_corner_points'],
        'max_other_source_tangent_mismatch_degrees':max(smooth),
        'source_signed_ring_areas':[Polygon(r).area*(1 if LinearRing(r).is_ccw else -1) for r in native_rings],
        'exports':exports}
(study/'outline-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
