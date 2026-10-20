"""Local contour repairs requested by the author, after integer-grid fairing."""
from polish_outlines import contours_of,to_glyph,hausdorff


def smooth_zhe(glyph,glyf):
    """Vertical tangent at the left bowl/connector shoulder, after the redraw."""
    contours=contours_of(glyph,glyf);fixed=0
    for points in contours:
        for i,p in enumerate(points):
            a=points[i-1];b=points[(i+1)%len(points)]
            if p[2] and not a[2] and not b[2] and p[1]==334 and a[1]==278 and b[0]==p[0] and a[0]==p[0]-3:
                a[0]=p[0];fixed+=1
    assert fixed==1,('The ж shoulder changed; review the contour repair',fixed)
    result=to_glyph(contours);result.recalcBounds(glyf)
    deviation=float(hausdorff(glyph,result,glyf))
    assert deviation<=2.,('ж shoulder displacement',deviation)
    return result,{'region':'left bowl/connector shoulder','handle_dx':3,
                   'tangent_break_before_degrees':3.1,'tangent_break_after_degrees':0,
                   'outline_deviation':round(deviation,3)}


def smooth_ze(glyph,glyf):
    """The inner shoulder of з: horizontal tangent at y=489, not a 4.6° kink.

    The outgoing off-curve point was at y=487 while the incoming tangent is
    horizontal at 489. Raising that handle by 2 units moves the contour by at
    most one unit. Keep the extremum and the drop's weight/position intact.
    """
    contours=contours_of(glyph,glyf);fixed=0
    for points in contours:
        for i,p in enumerate(points):
            a=points[i-1];b=points[(i+1)%len(points)]
            if p[2] and not a[2] and not b[2] and p[1]==489 and a[1]==489 and b[1]==487 and a[0]<p[0]<b[0]:
                b[1]=489;fixed+=1
    assert fixed==1,('The з shoulder changed; review the contour repair',fixed)
    result=to_glyph(contours);result.recalcBounds(glyf)
    deviation=float(hausdorff(glyph,result,glyf))
    assert deviation<=1.2,('з shoulder displacement',deviation)
    return result,{'region':'upper inner shoulder','handle_y':[487,489],
                   'tangent_break_before_degrees':4.6,'tangent_break_after_degrees':0,
                   'outline_deviation':round(deviation,3)}
