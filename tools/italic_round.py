#!/usr/bin/env python3
"""Italic form of round capitals: not a plain shear (docs/italic-lines.md, O1-O2).
The native Italic O is the Regular O sheared by only about 11.1 degrees on the outer contour and 12.5 on the inner one
(not 13), so that its leftmost point lies at 34 percent of the height instead of 50. The correction is the same shear
reduced by a y-proportional shift  d = slope * (y - ym)  per contour class:
  outer contour of closed ovals (O, Yu, Phi, Theta): slope -0.0352     inner contour: slope -0.0088   (fit on native O)
  open round capitals (C-like: Ze, E-reversed):       slope -0.0217                                   (fit on native C)
Parts that must stay put (stems and their serifs) are protected by rectangles with a smooth 25-unit blend.
Validation on the Latin O and C: area difference to the native outline before and after (printed by main()).
"""
import math,sys
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen

S=math.tan(math.radians(13));Y0=251;YM=360.5
SLOPE={'outer':-0.0352,'inner':-0.0088,'open':-0.0217}
BLEND=25.


def smooth(u):
    u=max(0.,min(1.,u));return u*u*(3-2*u)


def rect_dist(x,y,r):
    x0,x1,y0,y1=r;dx=max(x0-x,0,x-x1);dy=max(y0-y,0,y-y1);return math.hypot(dx,dy)


def protected_weight(x,y,rects):
    if not rects:return 1.
    return smooth(min(rect_dist(x,y,r) for r in rects)/BLEND)


def signed_area(pts):
    return sum(pts[i][0]*pts[(i+1)%len(pts)][1]-pts[(i+1)%len(pts)][0]*pts[i][1] for i in range(len(pts)))/2


def round_glyph(glyph,glyf,kind,rects=(),y0=None,ym=None):
    """Shear Regular glyph by 13 degrees, then bend each contour by its class slope. kind: 'closed' or 'open'."""
    g=type(glyph)();g.__dict__.update({k:(v.copy() if hasattr(v,'copy') else v) for k,v in glyph.__dict__.items()})
    y0=Y0 if y0 is None else y0;ym=YM if ym is None else ym
    coords,ends,flags=glyph.getCoordinates(glyf)
    new=[];start=0
    for end in ends:
        pts=[(coords[i][0],coords[i][1]) for i in range(start,end+1)]
        outer=signed_area([p for p,f in zip(pts,flags[start:end+1]) if f&1])<0     # TrueType outer contours run clockwise
        slope=SLOPE['open'] if kind=='open' else (SLOPE['outer'] if outer else SLOPE['inner'])
        for x,y in pts:
            xs=x+S*(y-y0)                         # plain shear about y0 (251 for capitals, 255 for lowercase)
            xs+=slope*(y-ym)*protected_weight(x,y,rects)   # rects are in Regular coordinates
            new.append((xs,y))
        start=end+1
    from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates
    g.coordinates=GlyphCoordinates([(round(x),round(y)) for x,y in new]);g.endPtsOfContours=list(ends);g.flags=glyph.flags
    g.recalcBounds(glyf);return g

if __name__=='__main__':
    import pathops
    from pathops import PathOp
    from fontTools.pens.recordingPen import RecordingPen
    base='reference/instrument-serif/fonts/ttf/'
    it=TTFont(base+'InstrumentSerif-Italic.ttf');rg=TTFont(base+'InstrumentSerif-Regular.ttf')
    def path(font,name,glyph=None):
        p=pathops.Path();gs=font.getGlyphSet()
        if glyph is None:gs[name].draw(p.getPen(glyphSet=gs))
        else:glyph.draw(p.getPen(glyphSet=gs),font['glyf'])
        return pathops.simplify(p,fix_winding=True)
    def xor(a,b):return abs(pathops.op(a,b,PathOp.XOR).area)/abs(a.area)
    for name,kind in (('O','closed'),('C','open'),('G','open')):
        I=path(it,name)
        plain=TTGlyphPen(None);rg.getGlyphSet()[name].draw(TransformPen(plain,(1,0,S,1,-S*Y0,0)));pg=plain.glyph()
        g=round_glyph(rg['glyf'][name],rg['glyf'],kind)
        print(name,'shear only',round(xor(I,path(rg,name,pg)),3),'with round correction',round(xor(I,path(rg,name,g)),3))
