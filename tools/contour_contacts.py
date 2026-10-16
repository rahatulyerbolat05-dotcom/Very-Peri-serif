"""Independent vector intersection audit; baseline foot contacts are excluded."""
import pathops
from fontTools.pens.transformPen import TransformPen

class Auditor:
    def __init__(self,font):
        self.gs=font.getGlyphSet();self.paths={};self.clipped={};self.checked=set()
        self.region=pathops.Path();p=self.region.getPen()
        for y0,y1 in [(55,2000),(-1000,-25)]:
            p.moveTo((-2000,y0));p.lineTo((4000,y0));p.lineTo((4000,y1));p.lineTo((-2000,y1));p.closePath()
    def path(self,name):
        if name not in self.paths:
            p=pathops.Path();self.gs[name].draw(p.getPen(glyphSet=self.gs));self.paths[name]=p
            self.clipped[name]=pathops.op(p,self.region,pathops.PathOp.INTERSECTION)
        return self.paths[name]
    def check(self,a,b,advance,label):
        key=(a,b,advance)
        if key in self.checked:return
        self.checked.add(key);self.path(a);p=self.path(b);shifted=pathops.Path()
        p.draw(TransformPen(shifted.getPen(),(1,0,0,1,advance,0)))
        overlap=pathops.op(self.clipped[a],shifted,pathops.PathOp.INTERSECTION)
        assert abs(overlap.area)<.1,('Contour collision',label,a,b,advance,overlap.area,list(overlap.bounds))
